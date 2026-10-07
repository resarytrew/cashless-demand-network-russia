"""Run the fixed, additive Round20 targeted checks without changing L1 or L2."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

import networkx as nx
import numpy as np
import pandas as pd
import yaml

from sbernet.clustering import louvain_labels
from sbernet.dual_lens import combine_lenses, employment_clr, median_distance_scale, robust_standardize_columns
from sbernet.edge_sensitivity import knn_graph
from sbernet.metrics import partition_similarity
from sbernet.pipeline import _prepare
from sbernet.robustness.experiment_common import profile_diagnostics
from sbernet.robustness.reproduction_gate import sha256, versions
from sbernet.targeted_checks import distance_contribution_table, optimal_label_alignment, residual_profile_test
from sbernet.temporal import build_supra_graph


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def git_commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


def gate(cfg: dict) -> dict:
    paths = cfg["gates"]
    baseline = json.loads(Path(paths["baseline_gate"]).read_text(encoding="utf-8"))
    if not baseline.get("passed") or any(scores != {"ARI": 1.0, "NMI": 1.0} for scores in baseline["metrics"].values()):
        raise RuntimeError("exact L1 reproduction gate failed")
    baseline_manifest = json.loads(Path(paths["baseline_gate_manifest"]).read_text(encoding="utf-8"))
    supra = Path(paths["baseline_supra_labels"])
    expected = next(value for key, value in baseline_manifest["reference_sha256"].items() if Path(key).name == supra.name)
    if sha256(supra) != expected:
        raise RuntimeError("stored L1 supra labels changed")
    completed = json.loads(Path(paths["round19_completed"]).read_text(encoding="utf-8"))
    manifest = json.loads(Path(paths["round19_manifest"]).read_text(encoding="utf-8"))
    expected_status = "COMPLETED_SEPARATE_L2_EXPERIMENT"
    if completed.get("status") != expected_status or manifest.get("status") != expected_status:
        raise RuntimeError("Round19 L2 is not complete")
    if manifest.get("reference_specification_changed") or manifest.get("baseline_changed"):
        raise RuntimeError("Round19 reports a forbidden reference change")
    return {"status": "PASS", "baseline_metrics": baseline["metrics"], "baseline_supra_sha256": sha256(supra),
            "round19_status": manifest["status"], "L1_changed": False, "L2_weights_changed": False}


def edge_pairs(graph: nx.Graph) -> np.ndarray:
    return np.asarray(sorted((min(int(a), int(b)), max(int(a), int(b))) for a, b in graph.edges()), dtype=int)


def run(config_path: str) -> None:
    cfg_path = Path(config_path)
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    out = Path(cfg["experiment"]["output_dir"])
    if out.exists():
        raise FileExistsError(f"refusing to overwrite {out}")
    release_gate = gate(cfg)

    _, names, _, months, matrices = _prepare(cfg["sources"]["l1_config"])
    keys = [str(pd.Timestamp(month).date()) for month in months]
    reference = pd.read_csv(cfg["gates"]["baseline_supra_labels"], index_col=0).loc[names, keys].to_numpy(dtype=int).T
    mapping = pd.read_csv(cfg["sources"]["profile_mapping"])
    raw_to_profile = mapping.set_index("raw_community").interpreted_profile.to_dict()

    # External outcomes are not inputs to L1. Residual tests retain all A--G observations
    # with positive outcome/population and include fixed region indicators.
    ext = pd.read_csv(cfg["sources"]["national_external"])
    residual_cfg = cfg["residual_external"]
    ext = ext.loc[ext[residual_cfg["profile"]].isin(residual_cfg["included_profiles"])].copy()
    diagnostics, summaries, pairs = [], [], []
    residual_outputs: dict[str, pd.DataFrame] = {}
    for outcome in residual_cfg["outcomes"]:
        residuals, result, summary, pairwise = residual_profile_test(
            ext, outcome=outcome, population=residual_cfg["population"], region=residual_cfg["region"],
            profile=residual_cfg["profile"], permutation_reps=int(residual_cfg["permutation"]["reps"]),
            seed=int(residual_cfg["permutation"]["seed"]),
        )
        diagnostics.append(result); summaries.append(summary); pairs.append(pairwise); residual_outputs[outcome] = residuals

    # Omega sensitivity changes one predeclared parameter and reconstructs no L1 features.
    omega_cfg = cfg["omega_check"]
    monthly = [knn_graph(matrices[key], int(omega_cfg["k"]), False, True) for key in keys]
    supra = build_supra_graph(monthly, len(names), float(omega_cfg["sensitivity_omega"]))
    omega1 = louvain_labels(supra, float(omega_cfg["resolution"]), int(omega_cfg["seed"])).reshape(len(keys), len(names))
    similarity = partition_similarity(reference[-1], omega1[-1])
    prior = pd.read_csv(cfg["sources"]["omega_existing_summary"])
    prior = prior.loc[np.isclose(prior.omega, float(omega_cfg["sensitivity_omega"]))].iloc[0]
    if not np.isclose(similarity["ari"], prior.Dec2024_ari) or not np.isclose(similarity["nmi"], prior.Dec2024_nmi):
        raise RuntimeError("omega=1 reproduction differs from the preserved sensitivity run")
    profiles, profile_pairs = profile_diagnostics(reference[-1], omega1[-1], omega_cfg["profile_map"])
    aligned, alignment_map, match_share = optimal_label_alignment(reference[-1], omega1[-1])
    profile_labels = np.array([raw_to_profile.get(value, f"unmapped_{value}") for value in reference[-1]])
    alignment = pd.DataFrame({"municipality": names, "reference_raw": reference[-1], "reference_profile": profile_labels,
                              "omega1_raw": omega1[-1], "omega1_aligned_to_reference": aligned,
                              "changed_after_optimal_alignment": aligned != reference[-1]})
    atlas = pd.read_csv(cfg["sources"]["atlas"])[["municipality", "stability_class"]]
    atlas = atlas.merge(alignment, on="municipality", how="inner", validate="one_to_one")
    atlas_summary = atlas.groupby("stability_class").changed_after_optimal_alignment.agg(["count", "sum", "mean"]).reset_index()
    atlas_summary = atlas_summary.rename(columns={"sum": "changed_n", "mean": "changed_share"})
    atlas_profiles = atlas.groupby("reference_profile").changed_after_optimal_alignment.agg(["count", "sum", "mean"]).reset_index()
    atlas_profiles = atlas_profiles.rename(columns={"sum": "changed_n", "mean": "changed_share"})

    # Recreate Round19 coordinates exactly, then expose the five additive terms.
    l2_cfg = yaml.safe_load(Path(cfg["sources"]["l2_config"]).read_text(encoding="utf-8"))
    eligibility = pd.read_csv(cfg["sources"]["l2_eligibility"])
    eligible = eligibility.L2_eligible.astype(bool).to_numpy()
    selected = eligibility.loc[eligible].reset_index(drop=True)
    indices = np.flatnonzero(eligible)
    scalar_names = [item["name"] for item in l2_cfg["features"]["socioeconomic"]]
    socioeconomic = robust_standardize_columns(np.log(selected[scalar_names].to_numpy(dtype=float)))
    employment, _ = employment_clr(selected, l2_cfg["features"]["employment_sectors"])
    demand = matrices[cfg["l2_distance_contribution"]["period"]][indices]
    weights = l2_cfg["features"]["block_weights"]
    demand_norm, demand_scale = median_distance_scale(demand)
    socio_norm, socio_scale = median_distance_scale(socioeconomic)
    employment_norm, employment_scale = median_distance_scale(employment)
    blocks = {
        "Demand": np.sqrt(weights["l1"]) * demand_norm,
        "Population": np.sqrt(weights["socioeconomic"]) * socio_norm[:, 0:1],
        "Wage": np.sqrt(weights["socioeconomic"]) * socio_norm[:, 1:2],
        "Market_access": np.sqrt(weights["socioeconomic"]) * socio_norm[:, 2:3],
        "Employment": np.sqrt(weights["employment"]) * employment_norm,
    }
    combined = np.concatenate(list(blocks.values()), axis=1)
    expected, expected_scales = combine_lenses(demand, socioeconomic, employment, weights)
    if not np.allclose(combined, expected, rtol=0, atol=1e-14):
        raise RuntimeError("distance block decomposition does not reconstruct Round19 L2 coordinates")
    temporal_graph = knn_graph(combined, int(l2_cfg["network"]["k"]), False, True)
    static_graph = knn_graph(combined, int(l2_cfg["network"]["k"]), True, True)
    contribution_cfg = cfg["l2_distance_contribution"]
    quantiles = tuple(float(value) for value in contribution_cfg["share_quantiles"])
    contributions = pd.concat([
        distance_contribution_table(blocks, scope="all_pairs", quantiles=quantiles),
        distance_contribution_table(blocks, scope="temporal_december_edges", pairs=edge_pairs(temporal_graph), quantiles=quantiles),
        distance_contribution_table(blocks, scope="static_december_edges", pairs=edge_pairs(static_graph), quantiles=quantiles),
    ], ignore_index=True)

    out.mkdir(parents=True, exist_ok=False)
    pd.DataFrame(diagnostics).to_csv(out / "residual_global_tests.csv", index=False)
    pd.concat(summaries, ignore_index=True).to_csv(out / "residual_profile_summary.csv", index=False)
    pd.concat(pairs, ignore_index=True).to_csv(out / "residual_pairwise_tests.csv", index=False)
    for outcome, frame in residual_outputs.items(): frame.to_csv(out / f"residuals_{outcome}.csv", index=False)
    pd.DataFrame(omega1.T, index=names, columns=keys).to_csv(out / "omega1_supra_labels.csv")
    pd.DataFrame(profiles).to_csv(out / "omega1_profile_correspondence.csv", index=False)
    pd.DataFrame(profile_pairs).to_csv(out / "omega1_profile_pair_coassignment.csv", index=False)
    alignment.to_csv(out / "omega1_december_alignment.csv", index=False)
    atlas_summary.to_csv(out / "omega1_atlas_by_stability_class.csv", index=False)
    atlas_profiles.to_csv(out / "omega1_atlas_by_profile.csv", index=False)
    contributions.to_csv(out / "l2_distance_contributions.csv", index=False)
    write_json(out / "P0_RELEASE_GATE.json", release_gate)

    omega_metrics = {"reference_omega": 2.0, "sensitivity_omega": 1.0, "Dec2024_ARI": similarity["ari"],
                     "Dec2024_NMI": similarity["nmi"], "reference_K": int(np.unique(reference[-1]).size),
                     "sensitivity_K": int(np.unique(omega1[-1]).size), "optimally_aligned_match_share": match_share,
                     "optimally_aligned_changed_share": 1.0 - match_share, "alignment_map": alignment_map}
    summary = {"status": "COMPLETED_EXPLORATORY_TARGETED_CHECKS", "L1_changed": False, "L2_weights_changed": False,
               "residual_external": diagnostics, "omega": omega_metrics,
               "distance_mean_shares_all_pairs": contributions.loc[contributions.scope.eq("all_pairs")].set_index("block").mean_share.to_dict(),
               "distance_contribution_scales": {"demand": demand_scale, "socioeconomic": socio_scale, "employment": employment_scale},
               "distance_reconstruction_scales": expected_scales}
    write_json(out / "round20_summary.json", summary)
    report = ["# Round20 targeted checks", "", "This additive exploratory round does not alter L1, Round19 L2 weights, or omega=2.", "",
              "## Size- and region-controlled external contrasts", ""]
    for row in diagnostics:
        report.append(f"- `{row['outcome']}`: n={row['n']}, partial R2={row['partial_R2_profile']:.4f}, HC3 p={row['HC3_Wald_p']:.4g}, within-region Freedman–Lane p={row['Freedman_Lane_within_region_p']:.4g}.")
    report += ["", "## Omega=2 versus omega=1", "",
               f"December ARI={similarity['ari']:.4f}, NMI={similarity['nmi']:.4f}; one-to-one aligned changed share={1-match_share:.1%}. This is sensitivity evidence, not an alternative reference selection.", "",
               "## What drives L2 distance", ""]
    for row in contributions.loc[contributions.scope.eq("all_pairs")].itertuples():
        report.append(f"- {row.block}: mean share {row.mean_share:.1%}; median pair share {row.median_share:.1%}.")
    report += ["", "Shares use the preregistered Round19 weights. No weights were retuned after inspection.", ""]
    (out / "ROUND20_REPORT.md").write_text("\n".join(report), encoding="utf-8")
    (out / "ROUND20_AUDIT.md").write_text(
        "# Round20 audit\n\nThe exact L1 gate and completed Round19 gate passed before computation. "
        "Residual tests use reduced-model residuals from log outcome on log population plus region fixed effects; HC3 and within-region Freedman–Lane results are reported. "
        "Omega=1 changes only temporal coupling and reproduces the preserved sensitivity CSV. L2 distance terms exactly reconstruct the Round19 coordinates. "
        "The round is exploratory/post-hoc and does not tune weights, relabel A–G, or select omega.\n", encoding="utf-8")
    artifacts = {path.name: sha256(path) for path in sorted(out.iterdir()) if path.is_file()}
    resolved = yaml.safe_dump(cfg, allow_unicode=True, sort_keys=True)
    manifest = {"status": "COMPLETED", "timestamp_utc": datetime.now(timezone.utc).isoformat(), "git_commit": git_commit(),
                "packages": versions(), "config_path": str(cfg_path), "config_sha256": sha256(cfg_path),
                "resolved_config_sha256": hashlib.sha256(resolved.encode()).hexdigest(), "resolved_config": cfg,
                "input_sha256": {key: sha256(value) for key, value in {**cfg["gates"], **cfg["sources"]}.items()},
                "source_sha256": {str(path): sha256(path) for path in Path("src/sbernet").rglob("*.py")},
                "artifact_sha256": artifacts, "baseline_changed": False, "round19_weights_changed": False,
                "omega_reference_changed": False, "random_seed": int(residual_cfg["permutation"]["seed"])}
    write_json(out / "run_manifest.json", manifest)
    write_json(out / "COMPLETED.json", {"status": "COMPLETED", "manifest_sha256": sha256(out / "run_manifest.json")})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--config", default="configs/round20_targeted_checks.yaml")
    run(parser.parse_args().config)
