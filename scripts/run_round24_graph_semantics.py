"""Run the fixed additive epsilon and co-dynamics comparisons; never tune L1."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import pickle
import subprocess
import sys

import networkx as nx
import numpy as np
import pandas as pd
import yaml

from sbernet.clustering import louvain_labels
from sbernet.edge_sensitivity import knn_graph
from sbernet.features import clr
from sbernet.graph_semantics import (
    dynamics_graph, epsilon_graph, graph_diagnostics, mean_delta_correlation, profile_overlap,
)
from sbernet.icvi import evaluate_partition_v2, flat_metrics_v2
from sbernet.io import build_strict_panel, read_semicolon_zip
from sbernet.pipeline import _git_commit
from sbernet.robustness.reproduction_gate import graph_fingerprint, sha256, similarity, versions


def write_json(path, payload):
    Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")


def file_hashes(paths):
    files = []
    for path in map(Path, paths):
        if not path.exists():
            raise FileNotFoundError(path)
        files.extend(sorted(p for p in path.rglob("*") if p.is_file()) if path.is_dir() else [path])
    return {p.as_posix(): sha256(p) for p in files}


def verify_seal(directory, context):
    seal = json.loads((directory / "COMPLETED.json").read_text(encoding="utf-8"))
    if seal["context"] != context:
        raise RuntimeError(f"checkpoint context changed: {directory}")
    for relative, expected in seal["files"].items():
        if sha256(directory / relative) != expected:
            raise RuntimeError(f"checkpoint integrity failure: {directory / relative}")
    return seal


def seal_directory(directory, context):
    paths = sorted(p for p in directory.rglob("*") if p.is_file() and p.name != "COMPLETED.json")
    write_json(directory / "COMPLETED.json", {
        "context": context, "files": {p.relative_to(directory).as_posix(): sha256(p) for p in paths},
    })


def load_clr_tensor(cfg, names, keys):
    base = yaml.safe_load(Path(cfg["experiment"]["source_config"]).read_text(encoding="utf-8"))
    panel_cfg = base["panel"]
    raw = read_semicolon_zip(base["paths"]["spending_zip"])
    required = [panel_cfg["total_category"], *panel_cfg["selected_categories"]]
    panel, panel_names, audit = build_strict_panel(raw, cfg["experiment"]["months"], required)
    if panel_names != names or audit.strict_panel_names != len(names):
        raise RuntimeError("CLR tensor panel does not match baseline axes")
    panel["period"] = pd.to_datetime(panel["period"])
    result = []
    parts = panel_cfg["selected_categories"]
    for key in keys:
        pivot = panel.loc[panel.period.eq(pd.Timestamp(key))].pivot(
            index="mo", columns="category_15", values="value"
        ).loc[names]
        other = pivot[panel_cfg["total_category"]] - pivot[parts].sum(axis=1)
        composition = np.column_stack([pivot[parts].to_numpy(float), other.to_numpy(float)])
        # CLR of positive spending parts equals CLR of their closed shares.
        result.append(clr(composition))
    return np.stack(result)


def validate_protocol(cfg):
    """Reject unsupported semantics instead of silently ignoring edited YAML."""
    expected = {
        "graph": {"kernel": "adaptive_rbf", "reference_static_fallback": True, "union_static_fallback": True},
        "epsilon": {"geometry": "reference_L1_lens_euclidean_CLR_plus_level",
                    "threshold_rule": "target_edge_order_statistic_all_unordered_pairs",
                    "ties": "include_all_at_threshold", "isolate_fallback": False,
                    "bandwidth": "same_reference_kth_neighbor_distance"},
        "dynamics": {"features": "six_unscaled_CLR_composition_components", "include_total_level": False,
                     "difference_order": 1, "correlation": "pearson", "component_aggregation": "equal_mean",
                     "constant_component_policy": "fail", "distance": "sqrt_2_times_one_minus_mean_correlation",
                     "tie_break": "ascending_panel_index", "isolate_fallback": False,
                     "remove_common_month_effect": False, "rolling_windows": False,
                     "parts": ["Food", "Health", "Catering", "Marketplace", "Transport", "Other"]},
        "reporting": {"icvi_feature_space": "reference_december_L1", "select_winner": False,
                      "change_A_G_statuses": False, "graph_metrics_comparable_as_ranking": False,
                      "comparison_scopes": ["static_december_reference", "temporal_december_reference"]},
    }
    for section, entries in expected.items():
        for key, value in entries.items():
            if cfg[section][key] != value:
                raise ValueError(f"unsupported protocol {section}.{key}")


def checkpoint(directory, graph, x, names, static_ref, temporal_ref, reference_graph, cfg, context):
    if (directory / "COMPLETED.json").exists():
        verify_seal(directory, context)
        print(f"Verified, skipped completed seed: {directory.name}", flush=True)
        return json.loads((directory / "metrics.json").read_text()), pd.read_csv(directory / "profile_overlap.csv")
    directory.mkdir(parents=True, exist_ok=True)
    gcfg = cfg["graph"]
    labels = louvain_labels(graph, gcfg["clustering_resolution"], gcfg["seed"])
    metrics = {
        "variant": directory.name, **graph_diagnostics(graph, reference_graph),
        **flat_metrics_v2(evaluate_partition_v2(x, labels, graph)),
        **{f"{key}_static": value for key, value in similarity(static_ref, labels).items()},
        **{f"{key}_temporal_december": value for key, value in similarity(temporal_ref, labels).items()},
    }
    labels_frame = pd.DataFrame({"panel_index": np.arange(len(names)), "mo": names, "community": labels})
    labels_frame.to_csv(directory / "labels.csv", index=False)
    edges = [{"source": min(i, j), "target": max(i, j), **data} for i, j, data in graph.edges(data=True)]
    pd.DataFrame(edges).sort_values(["source", "target"]).to_csv(directory / "edges.csv.gz", index=False)
    components = {i: c for c, nodes in enumerate(nx.connected_components(graph)) for i in nodes}
    pd.DataFrame({"panel_index": np.arange(len(names)), "mo": names,
                  "degree": [graph.degree(i) for i in range(len(names))],
                  "strength": [graph.degree(i, weight="weight") for i in range(len(names))],
                  "component": [components[i] for i in range(len(names))]}).to_csv(directory / "nodes.csv", index=False)
    overlap = pd.DataFrame(profile_overlap(temporal_ref, labels, cfg["reporting"]["profile_map"]))
    overlap.insert(0, "variant", directory.name)
    overlap.to_csv(directory / "profile_overlap.csv", index=False)
    for scope, reference in [("static", static_ref), ("temporal_december", temporal_ref)]:
        pd.crosstab(pd.Series(reference, name="reference_community"), pd.Series(labels, name="candidate_community")).to_csv(directory / f"crosswalk_{scope}.csv")
    write_json(directory / "graph_fingerprint.json", graph_fingerprint(graph))
    write_json(directory / "metrics.json", metrics)
    seal_directory(directory, context)
    print(json.dumps(metrics), flush=True)
    return metrics, overlap


def markdown(frame, columns):
    def fmt(v):
        return f"{v:.6f}" if isinstance(v, float) else str(v)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    lines += ["| " + " | ".join(fmt(row[c]) for c in columns) + " |" for _, row in frame.iterrows()]
    return "\n".join(lines)


def run(config_path):
    cfg = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    validate_protocol(cfg)
    exp = cfg["experiment"]
    output = Path(exp["output_dir"])
    output.mkdir(parents=True, exist_ok=True)
    gate_dir = output / "baseline_gate"
    if not gate_dir.exists():
        subprocess.run([sys.executable, "-m", "sbernet.robustness.reproduction_gate",
                        "--config", exp["source_config"], "--output", str(gate_dir)], check=True)
    gate = json.loads((gate_dir / "baseline_gate.json").read_text())
    if not gate["passed"] or any(v != 1 for m in gate["metrics"].values() for v in m.values()):
        raise RuntimeError("baseline exact partition gate failed; candidates blocked")
    fresh = json.loads((gate_dir / "graph_checksums.json").read_text())
    saved = json.loads(Path(exp["saved_graph_checksums"]).read_text())
    if fresh != saved:
        raise RuntimeError("baseline graph/config identity gate failed; candidates blocked")
    if fresh["config_file_sha256"] != sha256(exp["source_config"]):
        raise RuntimeError("baseline config changed since gate")
    base_cfg = yaml.safe_load(Path(exp["source_config"]).read_text(encoding="utf-8"))
    if (cfg["graph"]["k"] != base_cfg["network"]["k"]
            or cfg["graph"]["clustering_resolution"] != base_cfg["clustering"]["resolution"]
            or cfg["graph"]["seed"] != base_cfg["clustering"]["seed"]):
        raise RuntimeError("comparison must preserve reference k/resolution/seed")
    protected = file_hashes(exp["protected_paths"])
    input_paths = [config_path, "docs/ROUND24_PROTOCOL.md", exp["source_config"],
                   base_cfg["paths"]["spending_zip"], exp["historical_edge_table"],
                   exp["previous_matrix"], exp["saved_graph_checksums"],
                   gate_dir / "baseline_gate.json", gate_dir / "graph_checksums.json",
                   gate_dir / "baseline_graphs.pkl", gate_dir / "run_manifest.json",
                   *sorted(Path("src/sbernet").rglob("*.py")), Path(__file__)]
    context = {"inputs": file_hashes(input_paths), "protected": protected,
               "packages": versions(), "seed": cfg["graph"]["seed"]}
    if (output / "COMPLETED.json").exists():
        verify_seal(output, context)
        verify_seal(Path(exp["evidence_dir"]), context)
        print("Round24 completed output verified; all completed seeds skipped", flush=True)
        return
    freeze_path = output / "BASELINE_FREEZE.json"
    if freeze_path.exists():
        if json.loads(freeze_path.read_text(encoding="utf-8")) != context:
            raise RuntimeError("frozen context changed; preserve run and use an explicit new experiment")
    else:
        write_json(freeze_path, context)
    with (gate_dir / "baseline_graphs.pkl").open("rb") as stream:
        bundle = pickle.load(stream)
    names, keys = bundle["names"], bundle["keys"]
    if len(names) != exp["panel_n"] or len(keys) != exp["months"] or keys[-1] != exp["reference_month"]:
        raise RuntimeError("baseline panel axes differ")
    if graph_fingerprint(bundle["static"]) != fresh["static"] or graph_fingerprint(bundle["supra"]) != fresh["supra"]:
        raise RuntimeError("cached baseline graph differs from saved fingerprints")
    x = bundle["matrices"][exp["reference_month"]]
    reference = bundle["static"]
    static_ref = pd.read_csv("outputs/baseline/static_dec2024_labels.csv").set_index("mo").loc[names, "community"].to_numpy()
    temporal_ref = pd.read_csv("outputs/baseline/supra_labels.csv", index_col=0).loc[names, exp["reference_month"]].to_numpy()
    if reference.number_of_edges() != cfg["epsilon"]["target_edges"]:
        raise RuntimeError("predeclared epsilon target does not match reference edge count")
    k, tiny = cfg["graph"]["k"], cfg["graph"]["kernel_denominator_epsilon"]
    # Calibration is saved before any candidate labels/ICVI are calculated.
    eps_graph, calibration = epsilon_graph(x, cfg["epsilon"]["target_edges"], k, tiny)
    write_json(output / "epsilon_calibration.json", calibration)
    tensor = load_clr_tensor(cfg, names, keys)
    delta_similarity = mean_delta_correlation(tensor, cfg["dynamics"]["centered_norm_tolerance"])
    delta_graph = dynamics_graph(delta_similarity, k, tiny)
    np.savez_compressed(output / "features.npz", december_L1=x, monthly_CLR=tensor)
    write_json(output / "axes.json", {"names": names, "months": keys, "CLR_parts": cfg["dynamics"]["parts"]})
    graphs = {
        "reference_mutual20": reference,
        "union20": knn_graph(x, k, cfg["graph"]["union_static_fallback"], mutual=False),
        "epsilon_L1": eps_graph,
        "dynamics_mutual20": delta_graph,
    }
    rows, overlaps = [], []
    historical = pd.read_csv(exp["historical_edge_table"])
    for name, graph in graphs.items():
        metrics, overlap = checkpoint(output / "runs" / name, graph, x, names, static_ref,
                                      temporal_ref, reference, cfg, context)
        if name in ("reference_mutual20", "union20"):
            expected = historical.loc[historical.edge_rule.eq("mutual" if name == "reference_mutual20" else "union") & historical.k.eq(k)].iloc[0]
            for column in ("edges", "density", "K", "N", "SW", "CH", "CH_per_N", "S_Dbw", "AVI", "AVU", "ANUI", "MQ", "Q", "AVI_unweighted", "AVU_unweighted", "ARI", "NMI"):
                actual = metrics[column + "_static"] if column in ("ARI", "NMI") else metrics[column]
                if not np.isclose(actual, expected[column], atol=cfg["reporting"]["numeric_atol"], rtol=cfg["reporting"]["numeric_rtol"]):
                    raise RuntimeError(f"preserved edge-row gate failed: {name}/{column}")
        rows.append(metrics)
        overlaps.append(overlap)
    summary, profile_table = pd.DataFrame(rows), pd.concat(overlaps, ignore_index=True)
    summary.to_csv(output / "comparison.csv", index=False)
    profile_table.to_csv(output / "profile_overlap.csv", index=False)
    write_json(output / "round24_summary.json", {"epsilon_calibration": calibration, "comparisons": rows,
               "reference_changed": False, "A_G_status_changes": False, "winner_selected": False})
    evidence = Path(exp["evidence_dir"])
    if evidence.exists():
        raise FileExistsError(f"refusing to overwrite evidence round: {evidence}")
    evidence.mkdir(parents=True)
    matrix = pd.read_csv(exp["previous_matrix"], keep_default_na=False)
    for variant in ("epsilon_L1", "dynamics_mutual20"):
        indexed = profile_table.loc[profile_table.variant.eq(variant)].set_index("profile")
        for metric in ("retention", "precision", "Jaccard", "within_pair_coassignment"):
            matrix[f"round24_{variant}_{metric}"] = matrix.profile.map(indexed[metric])
    matrix["round24_scope"] = "static graph semantics; descriptive; A-G status unchanged"
    matrix.to_csv(evidence / "MASTER_PROFILE_EVIDENCE_MATRIX_v2.11.0.csv", index=False)
    table = markdown(summary, ["variant", "edges", "components", "isolates", "K", "ARI_static", "NMI_static", "ARI_temporal_december", "reference_edge_jaccard"])
    eps_row = summary.set_index("variant").loc["epsilon_L1"]
    dyn_row = summary.set_index("variant").loc["dynamics_mutual20"]
    interpretation = (
        f"At equal edge count, epsilon has static ARI={eps_row.ARI_static:.6f}, "
        f"{int(eps_row.isolates)} isolates and {int(eps_row.components)} components. "
        "This documents dependence on local versus global neighborhood construction, including "
        "fragmentation: equal density does not imply equal degree distribution or coverage.\n\n"
        f"Co-dynamics has static ARI={dyn_row.ARI_static:.6f} and temporal-December "
        f"ARI={dyn_row.ARI_temporal_december:.6f}. Its full-period composition co-movement "
        "partition addresses a different relation from December state similarity. "
        "Neither comparison is independent validation or a reason to replace reference L1.\n\n"
        "Strengthened: the qualification that exact boundaries depend on graph construction "
        "and on the meaning of similarity. Weakened: an unqualified claim of invariant "
        "partitions across these relations. Unchanged: the reference specification, union-k20, "
        "A–G definitions and scientific statuses, Atlas, and all earlier evidence. "
        "No winner is selected. Retention must be read with precision/Jaccard.\n"
    )
    report = (
        "# Round24 — global distance threshold and co-dynamics\n\n"
        "Additive exploratory comparisons on 1,904 municipalities. L1 denotes the unchanged "
        "CLR+level demand lens with Euclidean distance, not Manhattan distance.\n\n"
        f"Epsilon={calibration['epsilon']:.17g}, selected as the 11,787th unordered December "
        f"distance before candidate evaluation; actual edges={calibration['actual_edges']}, "
        f"boundary ties={calibration['pairs_at_threshold']}. Adaptive-RBF weights use the "
        "same reference kth-neighbor bandwidths. No epsilon fallback edges are added.\n\n"
        + table + "\n\n" + interpretation + "\n"
        "Co-dynamics uses the equal mean of six component Pearson correlations across 23 "
        "first differences of unscaled CLR features. It excludes Total and does not remove "
        "national seasonality/common shocks. Mutual-k20 uses sqrt(2(1-s)) and adaptive RBF. "
        "It is one full-period graph, not a monthly supra network. Negative similarities "
        "are eligible by rank; selected-edge counts are in comparison.csv.\n\n"
        "All ICVI feature metrics use the same December L1 matrix, including for dynamics. "
        "Thus they describe state separation of dynamic groups, not native dynamic separation. "
        "Graph ICVI uses each candidate graph and is not comparable as a method ranking. "
        "K includes singleton isolates. A–G overlap compares to temporal December; "
        "ARI_static compares to the separate static partition.\n\n"
        "See profile_overlap.csv for dominant-destination retention, precision, Jaccard and "
        "within-pair coassignment; runs/* for raw labels, weighted sparse edges, node "
        "degrees/components, crosswalks and exact graph fingerprints. Single fixed-seed "
        "results are descriptive, with no p-values or causal interpretation.\n"
    )
    (output / "ROUND24_REPORT.md").write_text(report, encoding="utf-8")
    (output / "ROUND24_AUDIT.md").write_text(
        "# Round24 audit\n\nExact fresh-process baseline ARI/NMI and historical graph checksums "
        "passed before candidates. Reference and union-k20 reproduce every numeric column "
        "of their saved ICVI-v2 rows. Protected-input hashes checked before and after run.\n\n"
        "Protocol decisions were saved in docs/ROUND24_PROTOCOL.md and YAML before candidate "
        "results. No parameters changed after results. Operational clarifications: L1 is the "
        "repository lens; the epsilon indicator defines edge support and retains RBF weights; "
        "dynamics uses six unscaled CLR components without Total; no isolate fallback for "
        "either new graph. These are explicit implementation choices, not historical "
        "preregistration claims. No other deviations.\n\n"
        "Candidate checkpoints bind raw outputs to config, code, runtime and protected inputs. "
        "Resume verifies hashes and skips completed seeds. Full-period dynamics is compared "
        "descriptively to December snapshots. No 45,696-square dense matrix is constructed.\n\n"
        + interpretation, encoding="utf-8")
    (evidence / "ROUND24_EVIDENCE_UPDATE.md").write_text(
        "# Evidence v2.11.0 — Round24 graph semantics\n\n" + table + "\n\n" + interpretation,
        encoding="utf-8")
    if protected != file_hashes(exp["protected_paths"]) or context["inputs"] != file_hashes(input_paths):
        raise RuntimeError("frozen inputs changed during run")
    write_json(output / "run_manifest.json", {
        "experiment": exp["id"], "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(), "git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], text=True)),
        "config_sha256": sha256(config_path), "seed": cfg["graph"]["seed"], "packages": versions(),
        "input_sha256": context["inputs"], "baseline_gate": gate,
        "graph_identity_gate": True, "union_historical_row_gate": True,
        "protected_inputs_unchanged": True, "reference_changed": False, "A_G_status_changes": False,
    })
    seal_directory(evidence, context)
    # Baseline pickle remains a local cache; its hash is still bound in context.
    seal_directory(output, context)
    print(f"Completed: {output / 'ROUND24_REPORT.md'}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/round24_graph_semantics.yaml")
    args = parser.parse_args()
    try:
        run(args.config)
    except Exception as error:
        config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
        directory = Path(config["experiment"]["output_dir"])
        directory.mkdir(parents=True, exist_ok=True)
        (directory / ("FAILURE_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f") + ".md")).write_text(
            f"# Round24 failure\n\n{type(error).__name__}: {error}\n\nNo reference or historical output was changed.\n",
            encoding="utf-8")
        raise
