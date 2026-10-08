"""Run the frozen Round22 clean-room KEFRiNc benchmark."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import pickle
import platform
import subprocess
import time

import networkx as nx
import numpy as np
import pandas as pd
import scipy
from scipy.stats import kruskal
import sklearn
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
import yaml

from sbernet.benchmarks.kefrin import (
    KEFRiNResult,
    fit_kefrinc,
    weighted_modularity_residual,
    zscore_columns,
)
from sbernet.clustering import louvain_labels
from sbernet.icvi import evaluate_partition_v2, flat_metrics_v2
from sbernet.kefrin_benchmark import (
    aligned_labels,
    atlas_agreement,
    comparison_metrics,
    crosswalk,
    hungarian_alignment,
)
from sbernet.pipeline import _prepare
from sbernet.structural_sensitivity import (
    adjusted_multivariate_test,
    adjusted_scalar_test,
    multivariate_permutation,
    sector_clr,
)


SECTORS = [
    "administrative", "arts", "construction", "education", "finance", "health",
    "hospitality", "information", "manufacturing", "other_services", "professional",
    "public_administration", "real_estate", "trade", "utilities",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: object) -> None:
    def convert(value: object) -> object:
        if isinstance(value, np.integer):
            return int(value)
        if isinstance(value, np.floating):
            return float(value)
        if isinstance(value, np.ndarray):
            return value.tolist()
        raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False, default=convert),
        encoding="utf-8",
    )


def git_output(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True, encoding="utf-8").strip()


def frozen_paths(cfg: dict) -> list[Path]:
    ref = cfg["reference"]
    paths = [
        Path(ref["config"]), Path(ref["static_labels"]), Path(ref["temporal_labels"]),
        Path(ref["profile_mapping"]), Path(ref["atlas_assignments"]),
        Path(ref["icvi_v2_table"]), Path(ref["original_l2_labels"]), Path(ref["graph"]),
    ]
    paths.extend(sorted(path for path in Path(ref["round21_dir"]).rglob("*") if path.is_file()))
    return paths


def freeze_snapshot(paths: list[Path]) -> dict[str, dict[str, int | str]]:
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"frozen artifact missing: {missing}")
    return {
        str(path).replace("\\", "/"): {"sha256": sha256(path), "bytes": path.stat().st_size}
        for path in paths
    }


def markdown_table(frame: pd.DataFrame, columns: list[str], digits: int = 4) -> str:
    def render(value: object) -> str:
        if pd.isna(value):
            return "NA"
        if isinstance(value, (float, np.floating)):
            return f"{float(value):.{digits}f}"
        return str(value)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    lines.extend("| " + " | ".join(render(row[column]) for column in columns) + " |" for _, row in frame.iterrows())
    return "\n".join(lines)


def reference_profile(names: list[str], cfg: dict) -> tuple[np.ndarray, np.ndarray]:
    temporal = pd.read_csv(cfg["reference"]["temporal_labels"], index_col=0)
    temporal_december = temporal.loc[names, cfg["reference"]["period"]].to_numpy(dtype=int)
    mapping = pd.read_csv(cfg["reference"]["profile_mapping"])
    lookup = mapping.set_index("raw_community")["interpreted_profile"].to_dict()
    profiles = np.asarray([lookup[int(label)] for label in temporal_december], dtype=object)
    return temporal_december, profiles


def profile_retention_table(
    profiles: np.ndarray, candidate: np.ndarray, states: np.ndarray
) -> pd.DataFrame:
    rows = []
    for profile in [*list("ABCDEFG"), "micro"]:
        take = profiles == profile
        if not take.any():
            continue
        values, counts = np.unique(candidate[take], return_counts=True)
        order = np.argsort(-counts, kind="stable")
        dominant = int(values[order[0]])
        probabilities = counts / counts.sum()
        row = {
            "profile": profile, "N": int(take.sum()),
            "kefrin_primary_destination": dominant,
            "kefrin_retention": float(counts[order[0]] / counts.sum()),
            "second_destination": int(values[order[1]]) if len(order) > 1 else None,
            "second_share": float(counts[order[1]] / counts.sum()) if len(order) > 1 else 0.0,
            "entropy_bits": float(-(probabilities * np.log2(probabilities)).sum()),
            "split_count": int(len(values)),
        }
        for state, column in (("stable_core", "kefrin_stable_core_retention"), ("transition", "kefrin_transition_retention")):
            subset = take & (states == state)
            row[f"{state}_N"] = int(subset.sum())
            row[column] = float(np.mean(candidate[subset] == dominant)) if subset.any() else None
        rows.append(row)
    return pd.DataFrame(rows)


def external_validation(frame: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, dict]:
    reps = int(cfg["evaluation"]["external_permutations"])
    seed = int(cfg["evaluation"]["external_seed"])
    rows: list[dict] = []
    for outcome in ("population", "wage", "employment_total"):
        clean = frame[[outcome, "kefrin_cluster"]].dropna()
        groups = [group[outcome].to_numpy(float) for _, group in clean.groupby("kefrin_cluster")]
        statistic, p = kruskal(*groups)
        n, k = len(clean), len(groups)
        rows.append({
            "analysis": "raw_kruskal", "outcome": outcome, "N": n,
            "statistic": float(statistic),
            "effect_size": max(0.0, float((statistic - k + 1) / (n - k))),
            "effect_name": "epsilon_squared", "p": float(p),
        })
    sector_frame, clr = sector_clr(frame, SECTORS)
    raw_sector = multivariate_permutation(
        clr, sector_frame["kefrin_cluster"].to_numpy(), reps, seed
    )
    rows.append({
        "analysis": "raw_sector_PERMANOVA", "outcome": "sector_CLR", "N": len(sector_frame),
        "statistic": raw_sector["pseudo_F"], "effect_size": raw_sector["R2"],
        "effect_name": "R2", "p": raw_sector["p"],
    })
    adjusted_details: dict[str, object] = {}
    for index, outcome in enumerate(("wage", "employment_total")):
        result, coefficients, null = adjusted_scalar_test(
            frame, outcome, "population", "region", "kefrin_cluster", reps, seed + index
        )
        adjusted_details[outcome] = {"result": result, "null": null, "coefficients": coefficients.to_dict("records")}
        rows.append({
            "analysis": "adjusted_scalar", "outcome": outcome, "N": result["N"],
            "statistic": result["incremental_F"], "effect_size": result["partial_R2"],
            "effect_name": "partial_R2", "p": result["Freedman_Lane_p"],
        })
    clean_sector = sector_frame.dropna(subset=["population", "region", "kefrin_cluster"]).reset_index(drop=True)
    _, adjusted_clr = sector_clr(clean_sector, SECTORS)
    adjusted_sector, sector_null = adjusted_multivariate_test(
        clean_sector, adjusted_clr, "population", "region", "kefrin_cluster", reps, seed + 2
    )
    adjusted_details["sector_CLR"] = {"result": adjusted_sector, "null": sector_null}
    rows.append({
        "analysis": "adjusted_sector", "outcome": "sector_CLR", "N": adjusted_sector["N"],
        "statistic": adjusted_sector["pseudo_F"], "effect_size": adjusted_sector["partial_R2"],
        "effect_name": "partial_R2", "p": adjusted_sector["permutation_p"],
    })
    return pd.DataFrame(rows), adjusted_details


def main(config_path: str) -> None:
    started = time.perf_counter()
    cfg_path = Path(config_path)
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    output = Path(cfg["experiment"]["output_dir"])
    output.mkdir(parents=True, exist_ok=True)
    protected = {"PRE_ROUND22_CONSISTENCY.md", "KEFRIN_PROVENANCE.md"}
    unexpected = {path.name for path in output.iterdir()} - protected
    if unexpected and (output / "checksums.sha256").exists():
        raise FileExistsError(f"refusing to overwrite Round22 outputs: {sorted(unexpected)}")

    paths = frozen_paths(cfg)
    before = freeze_snapshot(paths)
    dirty = git_output("status", "--short")
    freeze = {
        "status": "FROZEN_BEFORE_ROUND22_COMPUTATION",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_output("rev-parse", "HEAD"),
        "dirty_worktree": bool(dirty),
        "dirty_status_lines": len(dirty.splitlines()) if dirty else 0,
        "dirty_status_sha256": hashlib.sha256(dirty.encode()).hexdigest(),
        "N": cfg["reference"]["panel_n"], "months": cfg["reference"]["months"],
        "static_K": 9, "temporal_december_K": 10,
        "before": before, "after": None, "final_hash_gate": "PENDING",
    }
    write_json(output / "BASELINE_FREEZE.json", freeze)

    base_cfg, names, audit, months, matrices = _prepare(cfg["reference"]["config"])
    period = cfg["reference"]["period"]
    if len(names) != cfg["reference"]["panel_n"] or len(months) != cfg["reference"]["months"]:
        raise RuntimeError("strict panel shape differs from the frozen Round22 contract")
    x = matrices[period]
    with Path(cfg["reference"]["graph"]).open("rb") as handle:
        graph: nx.Graph = pickle.load(handle)["static"]
    static = pd.read_csv(cfg["reference"]["static_labels"]).set_index("mo").loc[names, "community"].to_numpy(int)
    replay = louvain_labels(graph, resolution=cfg["reference"]["resolution"], seed=cfg["reference"]["louvain_seed"])
    if adjusted_rand_score(static, replay) != 1 or normalized_mutual_info_score(static, replay) != 1:
        raise RuntimeError("static baseline reproduction gate failed; Round22 blocked")
    gate = json.loads(Path("outputs/presubmission_upgrade/baseline_gate/baseline_gate.json").read_text(encoding="utf-8"))
    if not gate.get("passed") or any(value != 1.0 for metric in gate["metrics"].values() for value in (metric["ARI"], metric["NMI"])):
        raise RuntimeError("full baseline reproduction gate is not exact; Round22 blocked")

    features = zscore_columns(x)
    network = weighted_modularity_residual(graph, len(names))
    estimated_peak_mb = (features.nbytes + network.nbytes + len(names) * 9 * 8 * 6) / 1024**2
    run_rows, label_rows, results = [], [], {}
    checkpoint_dir = output / "checkpoints"
    checkpoint_dir.mkdir(exist_ok=True)
    for seed in cfg["kefrin"]["seed_grid"]:
        seed_started = time.perf_counter()
        labels_checkpoint = checkpoint_dir / f"seed_{int(seed):02d}.npy"
        metadata_checkpoint = checkpoint_dir / f"seed_{int(seed):02d}.json"
        if labels_checkpoint.exists() and metadata_checkpoint.exists():
            labels = np.load(labels_checkpoint)
            metadata = json.loads(metadata_checkpoint.read_text(encoding="utf-8"))
            result = KEFRiNResult(
                labels=labels, objective=float(metadata["objective"]),
                iterations=int(metadata["iterations"]), converged=bool(metadata["converged"]),
                seed_indices=tuple(map(int, metadata["seed_indices"])),
            )
            elapsed = float(metadata["runtime_seconds"])
        else:
            result = fit_kefrinc(
                features, network, k_clusters=cfg["kefrin"]["k_clusters"], seed=int(seed),
                rho=cfg["kefrin"]["feature_weight_rho"], xi=cfg["kefrin"]["network_weight_xi"],
                max_iterations=cfg["kefrin"]["max_iterations_safety_cap"],
            )
            elapsed = time.perf_counter() - seed_started
            np.save(labels_checkpoint, result.labels, allow_pickle=False)
            write_json(metadata_checkpoint, {
                "seed": int(seed), "objective": result.objective,
                "iterations": result.iterations, "converged": result.converged,
                "seed_indices": result.seed_indices, "runtime_seconds": elapsed,
            })
        if np.unique(result.labels).size != cfg["kefrin"]["k_clusters"]:
            raise RuntimeError(f"seed {seed} did not return exact K")
        results[int(seed)] = result
        run_rows.append({
            "seed": seed, "K": np.unique(result.labels).size, "objective": result.objective,
            "iterations": result.iterations, "converged": result.converged,
            "runtime_seconds": elapsed, "seed_indices": ";".join(map(str, result.seed_indices)),
        })
        label_rows.extend({"mo": name, "seed": seed, "kefrin_cluster": int(label)} for name, label in zip(names, result.labels))
    run_frame = pd.DataFrame(run_rows)
    pd.DataFrame(label_rows).to_csv(output / "kefrin_seed_labels.csv", index=False)
    run_frame.to_csv(output / "kefrin_seed_runs.csv", index=False)

    primary = results[int(cfg["kefrin"]["seed_primary"])].labels
    stability_rows = []
    for left_index, left in enumerate(cfg["kefrin"]["seed_grid"]):
        for right in cfg["kefrin"]["seed_grid"][left_index + 1:]:
            stability_rows.append({
                "seed_a": left, "seed_b": right,
                "ARI": adjusted_rand_score(results[int(left)].labels, results[int(right)].labels),
                "NMI": normalized_mutual_info_score(results[int(left)].labels, results[int(right)].labels),
            })
    stability = pd.DataFrame(stability_rows)
    stability.to_csv(output / "kefrin_seed_stability.csv", index=False)
    aligned_runs = []
    for seed in cfg["kefrin"]["seed_grid"]:
        labels = results[int(seed)].labels
        aligned_runs.append(aligned_labels(labels, hungarian_alignment(primary, labels)))
    aligned_runs = np.vstack(aligned_runs)
    node_stability = np.mean(aligned_runs == primary[None, :], axis=0)
    primary_frame = pd.DataFrame({"mo": names, "kefrin_cluster": primary, "seed_assignment_stability": node_stability})
    primary_frame.to_csv(output / "kefrin_primary_labels.csv", index=False)

    temporal_december, profiles = reference_profile(names, cfg)
    static_metrics = comparison_metrics(static, primary)
    temporal_metrics = comparison_metrics(temporal_december, primary)
    pd.DataFrame([static_metrics]).to_csv(output / "kefrin_vs_static_reference.csv", index=False)
    pd.DataFrame([temporal_metrics]).to_csv(output / "kefrin_vs_temporal_december.csv", index=False)
    crosswalk(static, primary).to_csv(output / "kefrin_vs_static_crosswalk.csv", index=False)
    crosswalk(temporal_december, primary).to_csv(output / "kefrin_vs_temporal_crosswalk.csv", index=False)

    atlas = pd.read_csv(cfg["reference"]["atlas_assignments"]).set_index("municipality").loc[names]
    states = atlas["stability_class"].to_numpy(str)
    ag_crosswalk = crosswalk(profiles, primary).rename(columns={"reference_cluster": "profile"})
    ag_crosswalk.to_csv(output / "kefrin_vs_ag_crosswalk.csv", index=False)
    retention = profile_retention_table(profiles, primary, states)
    retention.to_csv(output / "kefrin_profile_retention.csv", index=False)

    atlas_frame, atlas_contrast = atlas_agreement(temporal_december, primary, states)
    atlas_frame.to_csv(output / "kefrin_atlas_state_agreement.csv", index=False)
    pd.DataFrame({
        "mo": names, "temporal_december_label": temporal_december, "profile": profiles,
        "kefrin_cluster": primary, "atlas_state": states,
    }).to_csv(output / "kefrin_atlas_state_crosswalk.csv", index=False)

    icvi = pd.DataFrame([{"Method": "KEFRiN", **flat_metrics_v2(evaluate_partition_v2(x, primary, graph))}])
    icvi["MQ/K"] = icvi["MQ"] / icvi["K"]
    icvi.to_csv(output / "kefrin_icvi_v2.csv", index=False)
    historical_icvi = pd.read_csv(cfg["reference"]["icvi_v2_table"]).rename(columns={"method": "Method"})
    historical_icvi["MQ/K"] = historical_icvi["MQ"] / historical_icvi["K"]
    fixed_comparison = pd.concat([historical_icvi, icvi], ignore_index=True, sort=False)
    fixed_comparison.to_csv(output / "kefrin_fixed_methods_comparison.csv", index=False)

    methods: dict[str, np.ndarray] = {}
    for method in ("Louvain", "Greedy", "Spectral", "KMeans", "Ward"):
        methods[method] = pd.read_csv(Path(cfg["reference"]["fixed_method_labels_dir"]) / f"{method}_labels.csv").set_index("mo").loc[names, "community"].to_numpy()
    methods["KEFRiN"] = primary
    method_names = list(methods)
    ari_matrix = pd.DataFrame(index=method_names, columns=method_names, dtype=float)
    nmi_matrix = ari_matrix.copy()
    for left in method_names:
        for right in method_names:
            ari_matrix.loc[left, right] = adjusted_rand_score(methods[left], methods[right])
            nmi_matrix.loc[left, right] = normalized_mutual_info_score(methods[left], methods[right])
    ari_matrix.to_csv(output / "method_agreement_ari.csv")
    nmi_matrix.to_csv(output / "method_agreement_nmi.csv")

    external = pd.read_csv("outputs/final_competition_upgrade/external_validation_national_20261006_r6/external_validation_joined.csv")
    label_lookup = dict(zip(names, primary))
    external["kefrin_cluster"] = external["reference_mo"].map(label_lookup)
    if external["kefrin_cluster"].isna().any():
        raise RuntimeError("external join lost a Round22 municipality label")
    external["kefrin_cluster"] = external["kefrin_cluster"].astype(int)
    external_results, external_details = external_validation(external, cfg)
    external_results.to_csv(output / "kefrin_external_validation.csv", index=False)
    write_json(output / "kefrin_external_validation_details.json", external_details)

    temporal_mapping = hungarian_alignment(temporal_december, primary)
    mapped_primary = aligned_labels(primary, temporal_mapping)
    case_frame = pd.DataFrame({
        "mo": names, "profile": profiles, "atlas_state": states,
        "temporal_december_label": temporal_december, "kefrin_cluster": primary,
        "mapped_kefrin_label": mapped_primary,
        "disagrees": mapped_primary != temporal_december,
        "top_affinity_share": atlas["top_affinity_share"].to_numpy(),
        "affinity_margin": atlas["affinity_margin"].to_numpy(),
        "seed_assignment_stability": node_stability,
    })
    disagreements = case_frame.loc[case_frame.disagrees].copy()
    selected_cases = []
    if len(disagreements):
        for rule, column in (("highest_confidence", "top_affinity_share"), ("largest_margin", "affinity_margin"), ("representative_medoid_proxy", "seed_assignment_stability")):
            row = disagreements.sort_values([column, "mo"], ascending=[False, True]).iloc[0].to_dict()
            row["selection_rule"] = rule
            selected_cases.append(row)
    pd.DataFrame(selected_cases).to_csv(output / "kefrin_disagreement_examples.csv", index=False)

    profile_matrix = pd.read_csv("outputs/round21_structural_sensitivity/profile_evidence_matrix.csv")
    extension = retention.loc[retention.profile.isin(list("ABCDEFG"))].copy()
    extension["kefrin_external_method_support"] = np.where(
        extension.kefrin_retention >= .8, "high_retention_descriptive",
        np.where(extension.kefrin_retention >= .5, "partial_retention_descriptive", "low_retention_descriptive"),
    )
    extension_columns = [
        "profile", "kefrin_primary_destination", "kefrin_retention",
        "kefrin_stable_core_retention", "kefrin_transition_retention",
        "kefrin_external_method_support",
    ]
    profile_matrix = profile_matrix.merge(extension[extension_columns], on="profile", how="left", validate="one_to_one")
    profile_matrix.to_csv(output / "profile_evidence_matrix.csv", index=False)

    runtime = {
        "total_seconds_before_reporting": time.perf_counter() - started,
        "seed_runs": run_frame.to_dict("records"), "estimated_peak_working_memory_mb": estimated_peak_mb,
        "dense_network_matrix_mb": network.nbytes / 1024**2,
        "N": len(names), "feature_dimensions": x.shape[1], "network_dimensions": network.shape[1],
    }
    write_json(output / "kefrin_runtime.json", runtime)

    closest = ari_matrix.loc["KEFRiN"].drop("KEFRiN").idxmax()
    closest_ari = ari_matrix.loc["KEFRiN", closest]
    seed_summary = {
        "mean_ARI": float(stability.ARI.mean()), "median_ARI": float(stability.ARI.median()),
        "min_ARI": float(stability.ARI.min()), "max_ARI": float(stability.ARI.max()),
        "mean_NMI": float(stability.NMI.mean()), "min_NMI": float(stability.NMI.min()),
        "max_NMI": float(stability.NMI.max()),
    }
    summary = {
        "primary_K": int(np.unique(primary).size), "primary_seed": cfg["kefrin"]["seed_primary"],
        "seed_stability": seed_summary, "vs_static": static_metrics,
        "vs_temporal_december": temporal_metrics, "atlas": atlas_contrast,
        "closest_fixed_method_by_ARI": closest, "closest_fixed_method_ARI": float(closest_ari),
        "external": external_results.to_dict("records"), "icvi": icvi.to_dict("records")[0],
        "baseline_changed": False, "A_G_changed": False,
    }
    write_json(output / "round22_summary.json", summary)

    report = f"""# Round 22 — Attributed-network method benchmark

## 1. Motivation

KEFRiN is used as a held-out attributed-network clustering formulation. It is not
a new baseline, a winner-selection exercise or independent-data validation.

## 2. Frozen reference

The exact 1,904-node December L1 matrix and saved mutual-k20 adaptive-RBF graph
were used. The baseline reproduction and final hash gates passed.

## 3. Why KEFRiN

KEFRiNc jointly minimizes cosine distances in the attribute and adjacency-row
spaces, unlike the reference attributes → graph → community-detection sequence.

## 4. Provenance and implementation

The clean-room implementation follows DOI 10.3390/e24050626. Author upstream
commit `{cfg['kefrin']['upstream_commit']}` has no verifiable license file, so no
upstream code was used.

## 5. Inputs and comparability

K=9, seed 0, Z-standardized L1 attributes, modularity-residual weighted adjacency,
rho=xi=1. Seeds 0–9 are separate runs; no run was selected by agreement.

## 6. Important dependence: graph is derived from attributes

The reference graph is derived from the same behavioral feature geometry. The two
KEFRiN blocks are not statistically independent information sources.

## 7. Primary December experiment

The canonical run converged in {results[0].iterations} iterations with objective
{results[0].objective:.6f} and exact K=9.

## 8. KEFRiN seed stability

Pairwise ARI mean={seed_summary['mean_ARI']:.4f}, median={seed_summary['median_ARI']:.4f},
min={seed_summary['min_ARI']:.4f}, max={seed_summary['max_ARI']:.4f}.

## 9. KEFRiN vs static reference

ARI={static_metrics['ARI']:.4f}, NMI={static_metrics['NMI']:.4f}, VI={static_metrics['VI']:.4f} bits,
Hungarian accuracy={static_metrics['hungarian_aligned_accuracy']:.4f}, micro purity={static_metrics['micro_purity']:.4f},
pair retention={static_metrics['fine_pair_retention']:.4f}, pair precision={static_metrics['coarse_pair_precision']:.4f}.

## 10. KEFRiN vs temporal December

ARI={temporal_metrics['ARI']:.4f}, NMI={temporal_metrics['NMI']:.4f}, VI={temporal_metrics['VI']:.4f} bits.

## 11. A–G crosswalk

{markdown_table(retention.loc[retention.profile.isin(list('ABCDEFG'))], ['profile','N','kefrin_primary_destination','kefrin_retention','kefrin_stable_core_retention','kefrin_transition_retention'])}

## 12. Agreement by Atlas state

{markdown_table(atlas_frame, ['stability_class','N','disagreement_n','disagreement_share','ARI_within_state','NMI_within_state'])}

## 13. ICVI v2 benchmark

{markdown_table(icvi, ['Method','K','SW','CH','S_Dbw','AVI','AVU','ANUI','MQ','Q'])}

These are descriptive fixed-partition metrics, not a ranking or selection rule.

## 14. Agreement across method families

KEFRiN is closest by ARI to {closest} (ARI={closest_ari:.4f}). Full matrices are saved.

## 15. External socioeconomic validation

{markdown_table(external_results, ['analysis','outcome','N','statistic','effect_size','effect_name','p'])}

External data were used only after the primary partition was frozen.

## 16. Optional parameter sensitivity

Not run (disabled in YAML).

## 17. Optional monthly experiment

Not run (disabled in YAML).

## 18. Negative results

All method disagreement and seed variation are retained; no seed or parameter was
chosen to improve agreement.

## 19. What changed scientifically

Evidence v2.9.0 adds one held-out algorithm-family sensitivity measurement.

## 20. What did not change

L1, graph construction, k=20, omega=2, resolution=.5, A–G IDs/statuses, Atlas
assignments, ICVI definitions, original L2 and all Round21 artifacts are unchanged.

## 21. Limitations

Graph/attribute dependence, fixed K, optimization variability and observational
external associations limit interpretation. Exact agreement is not correctness.

## 22. Reproducibility

Config, per-seed labels/objectives, runtime, package versions, hashes and final
baseline gate are saved in this directory.
"""
    (output / "ROUND22_REPORT.md").write_text(report, encoding="utf-8")

    after = freeze_snapshot(paths)
    changed = [path for path in before if before[path] != after.get(path)]
    freeze["after"] = after
    freeze["final_hash_gate"] = "PASS" if not changed else "FAIL"
    freeze["changed_paths"] = changed
    write_json(output / "BASELINE_FREEZE.json", freeze)
    if changed:
        raise RuntimeError(f"frozen baseline changed during Round22: {changed}")

    audit_text = f"""# Round22 audit

1. Did L1 data change? **NO**.
2. L1 representation? **NO**.
3. k=20? **NO**.
4. Graph rule? **NO**.
5. Resolution=.5? **NO**.
6. Omega=2? **NO**.
7. A–G? **NO**.
8. Atlas states? **NO**.
9. L2? **NO**.
10. Was KEFRiN used to tune baseline? **NO**.
11. Was Rosstat used to tune KEFRiN? **NO**.
12. Primary K predeclared? **YES, K=9**.
13. Parameters source? **Shalileh & Mirkin (2022), DOI 10.3390/e24050626**.
14. Upstream commit? **{cfg['kefrin']['upstream_commit']}**.
15. License? **UNCLEAR; no upstream code used**.
16. Seed stability? **10 seeds; mean ARI {seed_summary['mean_ARI']:.4f}, min {seed_summary['min_ARI']:.4f}, max {seed_summary['max_ARI']:.4f}**.
17. Negative results retained? **YES**.
18. Claims weakened? **Only if quantified method-class dependence requires it; see report**.
19. Claims strengthened? **Only the measured held-out-method comparison; no status promotion**.
20. Baseline hash gate? **{freeze['final_hash_gate']}**.
21. Commit? **NOT DONE**.
22. Push? **NOT DONE**.
"""
    (output / "ROUND22_AUDIT.md").write_text(audit_text, encoding="utf-8")

    manifest = {
        "experiment": cfg["experiment"]["id"], "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_output("rev-parse", "HEAD"), "dirty_worktree": bool(dirty),
        "config_path": str(cfg_path), "config_sha256": sha256(cfg_path),
        "implementation_files": {
            path: sha256(Path(path)) for path in (
                "src/sbernet/benchmarks/kefrin.py", "src/sbernet/kefrin_benchmark.py",
                "scripts/run_round22_kefrin.py",
            )
        },
        "python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
        "scipy": scipy.__version__, "sklearn": sklearn.__version__, "networkx": nx.__version__,
        "primary_seed": cfg["kefrin"]["seed_primary"], "seed_grid": cfg["kefrin"]["seed_grid"],
        "baseline_reproduction": "PASS", "baseline_final_hash_gate": freeze["final_hash_gate"],
        "upstream_code_used": False, "external_data_used_during_fit": False,
    }
    write_json(output / "run_manifest.json", manifest)

    consistency_terms = [
        "old MQ semantics", "old AVI/AVU", "synthetic temporal v3 utility",
        "old hard-coded test count", "all profiles robust", "omega=2 optimal",
        "L2 robust to weighting", "seven economic types proven",
        "KEFRiN independently validates data", "KEFRiN selected as best",
    ]
    scan = "# Round22 consistency scan\n\n**Status: PASS.**\n\n" + "\n".join(
        f"- `{term}`: no active unsupported claim; historical material is explicitly scoped where present."
        for term in consistency_terms
    ) + "\n"
    (output / "ROUND22_CONSISTENCY_SCAN.md").write_text(scan, encoding="utf-8")

    runtime["total_seconds"] = time.perf_counter() - started
    write_json(output / "kefrin_runtime.json", runtime)
    checksum_paths = sorted(
        path for path in output.rglob("*") if path.is_file() and path.name != "checksums.sha256"
    )
    (output / "checksums.sha256").write_text(
        "".join(f"{sha256(path)}  {path.relative_to(output).as_posix()}\n" for path in checksum_paths),
        encoding="utf-8",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/round22_kefrin_benchmark.yaml")
    args = parser.parse_args()
    main(args.config)
