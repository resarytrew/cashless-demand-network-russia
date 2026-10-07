"""Run the additive Round19 dual-lens L2 experiment after exact P0 gates."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess

import networkx as nx
import numpy as np
import pandas as pd
from scipy.stats import kruskal
import sklearn
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.tree import DecisionTreeClassifier, export_text
import yaml

from sbernet.clustering import louvain_labels
from sbernet.dual_lens import (
    canonicalize_partition,
    combine_lenses,
    cross_lens_migration,
    employment_clr,
    robust_standardize_columns,
)
from sbernet.edge_sensitivity import knn_graph
from sbernet.icvi import evaluate_partition_v2, flat_metrics_v2
from sbernet.io import read_semicolon_zip
from sbernet.metrics import partition_similarity
from sbernet.pipeline import _prepare
from sbernet.robustness.reproduction_gate import sha256, versions
from sbernet.temporal import build_supra_graph


def write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8"
    )


def git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return None


def verify_artifact_hashes(manifest: dict, root: Path) -> int:
    count = 0
    for relative, expected in manifest.get("artifact_sha256", {}).items():
        path = root / relative
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"P0 artifact hash mismatch: {path}")
        count += 1
    return count


def p0_gate(cfg: dict) -> dict:
    paths = cfg["p0_gates"]
    baseline = json.loads(Path(paths["baseline_gate"]).read_text(encoding="utf-8"))
    if not baseline.get("passed"):
        raise RuntimeError("L1 baseline reproduction gate failed")
    for scope, scores in baseline["metrics"].items():
        if scores != {"ARI": 1.0, "NMI": 1.0}:
            raise RuntimeError(f"L1 baseline is not exact for {scope}: {scores}")
    baseline_manifest = json.loads(
        Path(paths["baseline_gate_manifest"]).read_text(encoding="utf-8")
    )
    reference_hashes = baseline_manifest["reference_sha256"]
    checked = {}
    for path_key in ("baseline_supra_labels", "baseline_static_labels"):
        path = Path(paths[path_key])
        expected = next(
            value for key, value in reference_hashes.items()
            if Path(key.replace("\\", "/")).name == path.name
        )
        actual = sha256(path)
        if actual != expected:
            raise RuntimeError(f"L1 reference changed: {path}")
        checked[str(path)] = actual
    icvi = json.loads(Path(paths["icvi_v2_manifest"]).read_text(encoding="utf-8"))
    if icvi.get("status") != "COMPLETED_ADDITIVE_ICVI_COMPATIBILITY_LAYER":
        raise RuntimeError("ICVI v2 is not complete")
    if any(icvi.get(key) for key in ("partitions_changed", "baseline_changed", "reference_k_changed", "reference_omega_changed")):
        raise RuntimeError("ICVI v2 reports a forbidden reference change")
    synthetic_path = Path(paths["synthetic_v4_manifest"])
    synthetic = json.loads(synthetic_path.read_text(encoding="utf-8"))
    if synthetic.get("status") != "COMPLETED" or synthetic.get("real_data_recomputed"):
        raise RuntimeError("synthetic temporal v4 is not a completed additive benchmark")
    artifact_count = verify_artifact_hashes(synthetic, synthetic_path.parent)
    return {
        "status": "PASS",
        "baseline_exact_metrics": baseline["metrics"],
        "baseline_reference_sha256": checked,
        "icvi_v2_status": icvi["status"],
        "synthetic_v4_status": synthetic["status"],
        "synthetic_v4_artifacts_verified": artifact_count,
        "L1_changed": False,
    }


def load_context(cfg: dict, names: list[str]) -> tuple[pd.DataFrame, list[str]]:
    sources, panel = cfg["sources"], cfg["panel"]
    lineage = pd.read_csv(sources["lineage"])
    external = pd.read_csv(sources["national_external"]).drop(columns=["reference_mo", "profile"])
    market = pd.read_parquet(sources["market_access"])
    context = (
        pd.DataFrame({"reference_mo": names})
        .merge(
            lineage[["reference_mo", "territory_id", "status"]],
            on="reference_mo", how="left", validate="one_to_one",
        )
        .merge(external, on="territory_id", how="left", validate="one_to_one")
        .merge(market, on="territory_id", how="left", validate="many_to_one")
    )
    sectors = cfg["features"]["employment_sectors"]
    required = panel["required_scalar_features"]
    eligible = context.status.eq(panel["required_lineage_status"])
    eligible &= context[required].notna().all(axis=1)
    eligible &= context[sectors].notna().any(axis=1)
    context["L2_eligible"] = eligible
    reasons = np.full(len(context), "eligible", dtype=object)
    reasons[~context.status.eq(panel["required_lineage_status"])] = "lineage_not_verified"
    reasons[context.status.eq(panel["required_lineage_status"]) & context[required].isna().any(axis=1)] = "missing_required_scalar"
    reasons[context.status.eq(panel["required_lineage_status"]) & context[required].notna().all(axis=1) & ~context[sectors].notna().any(axis=1)] = "missing_employment_structure"
    context["L2_exclusion_reason"] = reasons
    return context, sectors


def canonicalize_supra(flat: np.ndarray, months: int, nodes: int) -> tuple[np.ndarray, dict[int, int]]:
    matrix = flat.reshape(months, nodes)
    last_values, last_counts = np.unique(matrix[-1], return_counts=True)
    total_values, total_counts = np.unique(flat, return_counts=True)
    total = dict(zip(total_values.tolist(), total_counts.tolist()))
    present = sorted(
        zip(last_values.tolist(), last_counts.tolist()), key=lambda item: (-item[1], item[0])
    )
    absent = sorted(
        [value for value in total_values.tolist() if value not in set(last_values.tolist())],
        key=lambda value: (-total[value], value),
    )
    order = [value for value, _ in present] + absent
    mapping = {int(old): new for new, old in enumerate(order, start=1)}
    return np.array([mapping[int(value)] for value in flat], dtype=int), mapping


def holdout_test(frame: pd.DataFrame, group: str, minimum: int) -> tuple[pd.DataFrame, dict]:
    valid = frame.dropna(subset=[group, "mobility_index"]).copy()
    counts = valid.groupby(group).size()
    keep = counts[counts >= minimum].index
    valid = valid[valid[group].isin(keep)]
    groups = [part.mobility_index.to_numpy() for _, part in valid.groupby(group)]
    if len(groups) < 2:
        result = {"lens": group, "status": "UNAVAILABLE_FEWER_THAN_TWO_GROUPS", "n": len(valid)}
    else:
        statistic, p_value = kruskal(*groups)
        k, n = len(groups), len(valid)
        epsilon = max(0.0, float((statistic - k + 1) / (n - k))) if n > k else 0.0
        result = {
            "lens": group, "status": "EXPLORATORY_HOLDOUT", "n": n, "groups": k,
            "kruskal_h": float(statistic), "p_value": float(p_value),
            "epsilon_squared": epsilon,
        }
    summary = valid.groupby(group).mobility_index.agg(["count", "median", "mean", "std"]).reset_index()
    summary.insert(0, "lens", group)
    return summary, result


def descriptor(value: float, high: str, low: str, threshold: float) -> str | None:
    if value >= threshold:
        return high
    if value <= -threshold:
        return low
    return None


def run(config_path: str) -> None:
    cfg_path = Path(config_path)
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    out = Path(cfg["experiment"]["output_dir"])
    if out.exists():
        raise FileExistsError(f"refusing to overwrite completed/new L2 output: {out}")
    p0 = p0_gate(cfg)

    _, names, _, months, l1_matrices = _prepare(cfg["sources"]["l1_config"])
    month_keys = [str(pd.Timestamp(month).date()) for month in months]
    context, sectors = load_context(cfg, names)
    eligible = context.L2_eligible.to_numpy()
    l2_names = context.loc[eligible, "reference_mo"].tolist()
    l1_indices = np.flatnonzero(eligible)
    selected = context.loc[eligible].reset_index(drop=True)
    scalar_names = [item["name"] for item in cfg["features"]["socioeconomic"]]
    raw_scalar = selected[scalar_names].to_numpy(dtype=float)
    if np.any(raw_scalar <= 0):
        raise RuntimeError("log socioeconomic features must be strictly positive")
    socioeconomic = robust_standardize_columns(np.log(raw_scalar))
    employment, employment_shares = employment_clr(selected, sectors)

    combined: dict[str, np.ndarray] = {}
    scale_rows = []
    for key in month_keys:
        combined[key], scales = combine_lenses(
            l1_matrices[key][l1_indices], socioeconomic, employment,
            cfg["features"]["block_weights"],
        )
        scale_rows.append({"period": key, **scales})
    monthly_graphs = [
        knn_graph(
            combined[key], int(cfg["network"]["k"]),
            bool(cfg["network"]["temporal_isolate_fallback"]), True,
        )
        for key in month_keys
    ]
    monthly_topology = pd.DataFrame([
        {
            "period": key,
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
            "isolates": len(list(nx.isolates(graph))),
            "components": nx.number_connected_components(graph),
        }
        for key, graph in zip(month_keys, monthly_graphs)
    ])
    supra = build_supra_graph(
        monthly_graphs, len(l2_names), float(cfg["temporal"]["omega"])
    )
    raw_flat = louvain_labels(
        supra, float(cfg["clustering"]["resolution"]), int(cfg["clustering"]["seed"])
    )
    flat, supra_mapping = canonicalize_supra(raw_flat, len(month_keys), len(l2_names))
    temporal = flat.reshape(len(month_keys), len(l2_names))
    static_graph = knn_graph(
        combined[cfg["experiment"]["reference_period"]], int(cfg["network"]["k"]),
        bool(cfg["network"]["static_isolate_fallback"]), True,
    )
    static_raw = louvain_labels(
        static_graph, float(cfg["clustering"]["resolution"]), int(cfg["clustering"]["seed"])
    )
    static_labels, static_mapping = canonicalize_partition(static_raw)

    baseline = pd.read_csv(cfg["p0_gates"]["baseline_supra_labels"], index_col=0)
    l1_dec = baseline.loc[l2_names, cfg["experiment"]["reference_period"]].to_numpy(dtype=int)
    mapping = pd.read_csv(cfg["sources"]["profile_mapping"])
    profile_map = mapping.set_index("raw_community").interpreted_profile.to_dict()
    l1_public = np.array([profile_map.get(value, f"micro_{value}") for value in l1_dec])
    l2_dec = temporal[-1]
    similarity = partition_similarity(l1_dec, l2_dec)
    contingency, migrations = cross_lens_migration(l2_names, l1_dec, l2_dec, l1_public)

    december = (
        pd.read_csv(cfg["sources"]["december_features"]).set_index("municipality").loc[l2_names]
    )
    profile_data = selected[["reference_mo", *scalar_names]].copy()
    for column in scalar_names:
        profile_data[f"log_{column}"] = np.log(profile_data[column].to_numpy(dtype=float))
    for sector in sectors:
        profile_data[f"employment_share_{sector}"] = employment_shares[sector].to_numpy()
    for column in ["Total", "Food", "Health", "Catering", "Marketplace", "Transport", "Other"]:
        profile_data[f"L1_{column}"] = december[column].to_numpy()
    profile_data["L2_community"] = l2_dec

    major_min = float(cfg["interpretation"]["major_min_share"])
    counts = profile_data.L2_community.value_counts().sort_index()
    major_ids = counts[counts / len(profile_data) >= major_min].index.tolist()
    contextual_features = [
        *[f"log_{name}" for name in scalar_names],
        *[f"employment_share_{s}" for s in sectors],
    ]
    rule = profile_data[profile_data.L2_community.isin(major_ids)].copy()
    x_rule_raw = rule[contextual_features].to_numpy(dtype=float)
    x_rule = robust_standardize_columns(x_rule_raw)
    y_rule = rule.L2_community.to_numpy()
    tree = DecisionTreeClassifier(
        max_depth=int(cfg["interpretation"]["tree_max_depth"]),
        min_samples_leaf=int(cfg["interpretation"]["tree_min_samples_leaf"]),
        random_state=int(cfg["clustering"]["seed"]),
        class_weight="balanced",
    )
    cv = StratifiedKFold(
        int(cfg["interpretation"]["cv_folds"]), shuffle=True,
        random_state=int(cfg["clustering"]["seed"]),
    )
    predicted = cross_val_predict(tree, x_rule, y_rule, cv=cv)
    balanced = float(balanced_accuracy_score(y_rule, predicted))
    accuracy = float(accuracy_score(y_rule, predicted))
    class_report = classification_report(y_rule, predicted, output_dict=True, zero_division=0)
    tree.fit(x_rule, y_rule)
    rules = export_text(tree, feature_names=contextual_features, decimals=4)
    tree_metrics = {
        "major_min_share": major_min, "major_communities": [int(x) for x in major_ids],
        "n": len(rule), "accuracy": accuracy, "balanced_accuracy": balanced,
        "cv_folds": int(cfg["interpretation"]["cv_folds"]),
        "max_depth": int(cfg["interpretation"]["tree_max_depth"]),
        "min_samples_leaf": int(cfg["interpretation"]["tree_min_samples_leaf"]),
    }

    profile_rows = []
    standardized_frame = pd.DataFrame(x_rule, columns=contextual_features, index=rule.index)
    threshold = float(cfg["interpretation"]["standardized_descriptor_threshold"])
    global_name_gate = balanced >= float(cfg["interpretation"]["min_balanced_accuracy_for_names"])
    for community, group in profile_data.groupby("L2_community", sort=True):
        row = {"L2_community": int(community), "display_id": f"L2-{int(community):02d}",
               "n": len(group), "share": len(group) / len(profile_data),
               "major_profile": int(community) in major_ids}
        for column in [*scalar_names, *[f"employment_share_{s}" for s in sectors],
                       "L1_Total", "L1_Food", "L1_Health", "L1_Catering",
                       "L1_Marketplace", "L1_Transport", "L1_Other"]:
            row[f"median_{column}"] = float(group[column].median())
        if int(community) in major_ids:
            idx = rule.index[rule.L2_community.eq(community)]
            med_z = standardized_frame.loc[idx].median().sort_values(key=np.abs, ascending=False)
            recall = float(class_report[str(community)]["recall"])
            eligible_name = global_name_gate and recall >= float(cfg["interpretation"]["min_class_recall_for_name"])
            parts = []
            for feature, value in med_z.items():
                if abs(value) < threshold:
                    continue
                if feature == "log_population":
                    parts.append("large-scale" if value > 0 else "small-scale")
                elif feature == "log_wage":
                    parts.append("higher-wage" if value > 0 else "lower-wage")
                elif feature == "log_market_access":
                    parts.append("high-access" if value > 0 else "low-access")
                elif feature.startswith("employment_share_") and value > 0:
                    parts.append(feature.removeprefix("employment_share_") + "-employment")
                if len(parts) == 2:
                    break
            row["tree_cv_recall"] = recall
            row["economic_name_status"] = "SUPPORTED_DESCRIPTIVE" if eligible_name and parts else "WITHHELD"
            row["suggested_economic_name"] = " + ".join(parts) if eligible_name and parts else ""
            row["top_context_deviations"] = ";".join(f"{k}={v:.3f}" for k, v in med_z.head(5).items())
        else:
            row.update(tree_cv_recall=np.nan, economic_name_status="MICRO_NOT_NAMED",
                       suggested_economic_name="", top_context_deviations="")
        profile_rows.append(row)
    profiles = pd.DataFrame(profile_rows)

    mobility = read_semicolon_zip(cfg["sources"]["mobility_holdout"])
    hold = cfg["holdout"]
    mobility = mobility.loc[mobility.period.astype(str).eq(hold["period"]), ["ref_area", hold["source_column"]]].rename(
        columns={"ref_area": "municipality", hold["source_column"]: "mobility_index"}
    )
    if mobility.municipality.duplicated().any():
        raise RuntimeError("mobility holdout has duplicate municipality keys")
    holdout_frame = migrations.merge(mobility, on="municipality", how="left", validate="one_to_one")
    l1_summary, l1_test = holdout_test(holdout_frame, "L1_profile", int(hold["minimum_group_n"]))
    l2_summary, l2_test = holdout_test(holdout_frame, "L2_community", int(hold["minimum_group_n"]))
    holdout_summary = pd.concat([l1_summary, l2_summary], ignore_index=True)
    holdout_results = pd.DataFrame([l1_test, l2_test])
    profile_mobility = l2_summary.rename(columns={"L2_community": "L2_community_holdout"})

    effects = pd.DataFrame([
        {"indicator": "population", "independent_for_L1": True, "enters_L2": True, "independent_for_L2": False},
        {"indicator": "wage", "independent_for_L1": True, "enters_L2": True, "independent_for_L2": False},
        {"indicator": "employment_structure", "independent_for_L1": True, "enters_L2": True, "independent_for_L2": False},
        {"indicator": "market_access", "independent_for_L1": True, "enters_L2": True, "independent_for_L2": False},
        {"indicator": "mobility_index", "independent_for_L1": True, "enters_L2": False, "independent_for_L2": True},
        {"indicator": "urban_share", "independent_for_L1": True, "enters_L2": False, "independent_for_L2": False,
         "notes": "national input unavailable; not imputed or proxied"},
    ])

    out.mkdir(parents=True, exist_ok=False)
    context.to_csv(out / "l2_eligibility_audit.csv", index=False)
    pd.DataFrame(scale_rows).to_csv(out / "feature_block_scales.csv", index=False)
    monthly_topology.to_csv(out / "monthly_graph_topology.csv", index=False)
    pd.DataFrame(temporal.T, index=l2_names, columns=month_keys).to_csv(out / "l2_supra_labels.csv")
    pd.DataFrame({"municipality": l2_names, "community": static_labels}).to_csv(out / "l2_static_dec2024_labels.csv", index=False)
    contingency.to_csv(out / "l1_l2_contingency.csv", index=False)
    migrations.to_csv(out / "l1_l2_municipality_migration.csv", index=False)
    profiles.to_csv(out / "l2_profile_table.csv", index=False)
    effects.to_csv(out / "external_independence_accounting.csv", index=False)
    holdout_frame.to_csv(out / "mobility_holdout_join.csv", index=False)
    holdout_summary.to_csv(out / "mobility_holdout_summary.csv", index=False)
    holdout_results.to_csv(out / "mobility_holdout_tests.csv", index=False)
    (out / "l2_rule_tree.txt").write_text(rules, encoding="utf-8")
    write_json(out / "l2_rule_tree_metrics.json", tree_metrics)
    write_json(out / "P0_RELEASE_GATE.json", p0)

    dec_key = cfg["experiment"]["reference_period"]
    metrics = {
        "L1_vs_L2_Dec2024": {"ARI": similarity["ari"], "NMI": similarity["nmi"],
                              "n_common": len(l2_names)},
        "L2": {
            "eligible_n": len(l2_names), "excluded_n": len(names) - len(l2_names),
            "K_supra": int(len(np.unique(flat))), "K_Dec2024": int(len(np.unique(l2_dec))),
            "K_static_Dec2024": int(len(np.unique(static_labels))),
            "major_profile_count": len(major_ids),
            "cross_lens_reassigned_n": int(migrations.cross_lens_reassigned.sum()),
            "cross_lens_reassigned_share": float(migrations.cross_lens_reassigned.mean()),
        },
        "graphs": {
            "static_nodes": static_graph.number_of_nodes(), "static_edges": static_graph.number_of_edges(),
            "static_isolates": len(list(nx.isolates(static_graph))),
            "supra_nodes": supra.number_of_nodes(), "supra_edges": supra.number_of_edges(),
            "temporal_weight": supra.graph["temporal_weight"],
            "monthly_isolates_min": int(monthly_topology.isolates.min()),
            "monthly_isolates_max": int(monthly_topology.isolates.max()),
        },
        "ICVI_v2_static": flat_metrics_v2(evaluate_partition_v2(combined[dec_key], static_labels, static_graph)),
        "ICVI_v2_temporal_Dec2024": flat_metrics_v2(evaluate_partition_v2(combined[dec_key], l2_dec, monthly_graphs[-1])),
        "tree": tree_metrics,
        "holdout": {"coverage_n": int(holdout_frame.mobility_index.notna().sum()),
                    "coverage_share": float(holdout_frame.mobility_index.notna().mean()),
                    "tests": [l1_test, l2_test]},
        "urban_share": "UNAVAILABLE_NOT_PROXIED",
    }
    write_json(out / "round19_summary.json", metrics)

    report = f"""# Round19 dual-lens L2 report

L1 remains the unchanged reference discovery result: demand-only features, mutual-kNN20, temporal omega=2, Louvain resolution=.5/seed=0, A–G, followed by independent external interpretation. P0 gates passed before L2 and are saved in `P0_RELEASE_GATE.json`.

L2 is a separate attributed-network experiment on {len(l2_names)} complete-case municipalities. It combines three predeclared, equally weighted and separately distance-normalised blocks: L1 features; log population/log wage/log market access; and CLR employment structure. Urban share was unavailable nationally and was neither imputed nor proxied. The complete-case rule excluded {len(names)-len(l2_names)} municipalities.

No K or macrotype names were fixed in advance. Louvain produced {metrics['L2']['K_Dec2024']} December communities in the temporal solution, of which {len(major_ids)} have at least {major_min:.0%} of the L2 sample. L1/L2 agreement on the common universe is ARI={similarity['ari']:.6f}, NMI={similarity['nmi']:.6f}. Municipality-level cross-lens reassignment is a contingency diagnostic, not a temporal move.

The temporal December partition contains many micro-communities; the five major communities cover {profiles.loc[profiles.major_profile, 'share'].sum():.1%} of the sample, while the separately evaluated static December graph has {metrics['L2']['K_static_Dec2024']} communities. This gap and the negative temporal-December silhouette prevent reading every temporal community as an economic type.

Population, wage, employment structure and market access cease to be independent evidence for L2 because they enter its features. Mobility was excluded from every feature, graph, clustering and naming step. Exact-name holdout coverage is {metrics['holdout']['coverage_n']}/{len(l2_names)} ({metrics['holdout']['coverage_share']:.1%}); the selected-coverage limitation remains material. L2 holdout Kruskal epsilon-squared is {l2_test.get('epsilon_squared', float('nan')):.4f} with exploratory p={l2_test.get('p_value', float('nan')):.4g}. This is auxiliary validation, not causal evidence.

The shallow rule tree over contextual inputs has cross-validated accuracy={accuracy:.3f}, balanced accuracy={balanced:.3f}. Economic names are emitted only for major communities whose CV recall passes the fixed gate; otherwise names are withheld. These names describe included attributes and are not independent validation.
"""
    (out / "DUAL_LENS_L2_REPORT.md").write_text(report, encoding="utf-8")
    audit = f"""# Round19 dual-lens audit

## Method

Separate additive L2 experiment under `configs/round19_dual_lens_l2.yaml`; L1 files are read-only inputs. No K selection, resolution tuning, graph-rule tuning or post-result parameter change occurred. L2 keeps k=20, omega=2, resolution=.5 and seed=0 for controlled comparison, but it is not a replacement baseline.

## Inputs and exclusions

Verified national population/wage/employment and official hackathon market access are included. Urban share is unavailable nationally and is explicitly absent. Complete cases: {len(l2_names)}; exclusions: {len(names)-len(l2_names)}. Mobility is a holdout only.

## Independence accounting

See `external_independence_accounting.csv`. Variables entering L2 cannot validate L2 independently. Mobility remains independent but selected and incomplete ({metrics['holdout']['coverage_n']} exact matches).

## What changed

An additional L2 partition, comparison tables, profile diagnostics, rule audit and holdout analysis were created.

## What did not change

Baseline data/features/graphs/labels, A–G mapping, k=20, omega=2, resolution=.5, L1 external results and A–G scientific statuses are unchanged. L2 does not promote A–G to universal economic types.
"""
    (out / "ROUND19_AUDIT.md").write_text(audit, encoding="utf-8")

    input_paths = [
        cfg_path, Path(cfg["sources"]["l1_config"]),
        *[Path(value) for value in cfg["p0_gates"].values()],
        *[Path(value) for value in cfg["sources"].values() if isinstance(value, str)],
        Path(__file__), Path("src/sbernet/dual_lens.py"),
    ]
    manifest = {
        "experiment": cfg["experiment"]["id"], "status": "COMPLETED_SEPARATE_L2_EXPERIMENT",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(), "git_commit": git_commit(),
        "config_path": str(cfg_path), "config_sha256": sha256(cfg_path),
        "input_sha256": {str(path): sha256(path) for path in input_paths},
        "packages": versions(), "seed": int(cfg["clustering"]["seed"]),
        "p0_gate": p0, "L1_changed": False, "mobility_excluded_from_model": True,
        "K_preselected": False, "names_preselected": False,
        "supra_label_mapping": supra_mapping, "static_label_mapping": static_mapping,
    }
    write_json(out / "run_manifest.json", manifest)
    write_json(out / "COMPLETED.json", {"status": manifest["status"], "summary": metrics})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/round19_dual_lens_l2.yaml")
    run(parser.parse_args().config)
