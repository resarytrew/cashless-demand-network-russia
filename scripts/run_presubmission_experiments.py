"""Fixed, non-destructive presubmission experiments (Round18, edge, omega)."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

import networkx as nx
import numpy as np
import pandas as pd

from sbernet.clustering import louvain_labels
from sbernet.config import load_config
from sbernet.icvi import evaluate_partition, flat_metrics
from sbernet.metrics import partition_similarity
from sbernet.pipeline import _git_commit, _prepare
from sbernet.graph import knn_graph
from sbernet.robustness.experiment_common import profile_diagnostics
from sbernet.robustness.reproduction_gate import graph_fingerprint, sha256, versions
from sbernet.temporal import build_supra_graph

PROFILE_MAP = {"A": 1, "B": 3, "C": 7, "D": 8, "E": 9, "F": 10, "G": 11}


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def fresh(path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"Output exists: {path}; choose a new output directory")
    path.mkdir(parents=True)


def gate(path: Path) -> None:
    payload = json.loads((path / "baseline_gate.json").read_text(encoding="utf-8"))
    if not payload.get("passed"):
        raise RuntimeError("Reference gate did not pass; downstream experiment is blocked")


def manifest(config_path: str, cfg: dict, experiment: str) -> dict:
    return {
        "experiment": experiment, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(), "config_path": config_path, "config_sha256": sha256(config_path),
        "baseline_config_sha256": sha256("configs/baseline.yaml"), "packages": versions(),
        "seed": cfg["clustering"]["seed"], "resolved_config": cfg,
    }


def prepared(config_path: str) -> tuple[dict, list[str], list[str], dict[str, np.ndarray]]:
    cfg, names, _, months, matrices = _prepare(config_path)
    keys = [str(pd.Timestamp(month).date()) for month in months]
    if len(names) != 1904 or len(keys) != 24:
        raise RuntimeError("Round18/presubmission requires the exact 1904 x 24 panel")
    return cfg, names, keys, matrices


def graph_stats(graph: nx.Graph) -> dict:
    degree = np.array([value for _, value in graph.degree()], dtype=float)
    components = list(nx.connected_components(graph))
    return {
        "edges": graph.number_of_edges(), "density": nx.density(graph),
        "mean_degree": float(degree.mean()), "median_degree": float(np.median(degree)),
        "connected_components": len(components),
        "largest_component_share": max(map(len, components), default=0) / graph.number_of_nodes(),
    }


def temporal_switches(labels: np.ndarray) -> dict:
    switches = np.sum(labels[1:] != labels[:-1], axis=0)
    return {"mean_switches": float(np.mean(switches)), "median_switches": float(np.median(switches)),
            "share_0_switches": float(np.mean(switches == 0)), "share_le1_switches": float(np.mean(switches <= 1)),
            "share_le2_switches": float(np.mean(switches <= 2))}


def run_round18(config_path: str) -> None:
    cfg = load_config(config_path)
    output = Path(cfg["paths"]["output_dir"])
    root = Path(cfg["experiment"]["output_root"])
    gate(Path(cfg["experiment"]["baseline_gate_dir"]))
    fresh(output)
    cfg, names, keys, matrices = prepared(config_path)
    monthly = [knn_graph(matrices[key], cfg["network"]["k"], cfg["network"]["temporal_isolate_fallback"], cfg["network"].get("mutual", True)) for key in keys]
    static = knn_graph(matrices[keys[-1]], cfg["network"]["k"], cfg["network"]["static_isolate_fallback"], cfg["network"].get("mutual", True))
    supra = build_supra_graph(monthly, len(names), cfg["temporal"]["omega"])
    static_labels = louvain_labels(static, cfg["clustering"]["resolution"], cfg["clustering"]["seed"])
    flat = louvain_labels(supra, cfg["clustering"]["resolution"], cfg["clustering"]["seed"])
    temporal_labels = flat.reshape(len(keys), len(names))
    pd.DataFrame({"mo": names, "community": static_labels}).to_csv(output / "static_dec2024_labels.csv", index=False)
    pd.DataFrame(temporal_labels.T, index=names, columns=keys).to_csv(output / "supra_labels.csv")
    static_icvi = flat_metrics(evaluate_partition(matrices[keys[-1]], static_labels, static))
    dec_icvi = flat_metrics(evaluate_partition(matrices[keys[-1]], temporal_labels[-1], monthly[-1]))
    ref = pd.read_csv("outputs/baseline/supra_labels.csv", index_col=0).loc[names, keys].to_numpy(dtype=int).T
    ref_static = pd.read_csv("outputs/baseline/static_dec2024_labels.csv").set_index("mo").loc[names, "community"].to_numpy()
    comparisons = {"static_dec2024": partition_similarity(ref_static, static_labels),
                   "temporal_dec2024": partition_similarity(ref[-1], temporal_labels[-1]),
                   "full_supra": partition_similarity(ref.ravel(), temporal_labels.ravel())}
    profiles, pairs = profile_diagnostics(ref[-1], temporal_labels[-1], PROFILE_MAP)
    atlas = pd.read_csv("outputs/stability_atlas_v2_2_1/municipality_affinity_atlas.csv")
    core = atlas.set_index("municipality").reindex(names)["stability_class"].eq("stable_core").to_numpy()
    profile_rows = pd.DataFrame(profiles)
    profile_rows["core_n_reference"] = [int(np.sum((ref[-1] == PROFILE_MAP[p]) & core)) for p in profile_rows.archetype]
    profile_rows.to_csv(output / "profile_overlap.csv", index=False)
    pd.DataFrame(pairs).to_csv(output / "profile_pair_coassignment.csv", index=False)
    data = {"metrics_static": static_icvi, "metrics_temporal_dec2024": dec_icvi, "comparisons": comparisons,
            "temporal": temporal_switches(temporal_labels), "graph_static": graph_stats(static),
            "graph_supra": {"nodes": supra.number_of_nodes(), "edges": supra.number_of_edges(),
                              "temporal_weight": supra.graph["temporal_weight"]},
            "feature_sha256_dec2024": hashlib.sha256(matrices[keys[-1]].astype("<f8").tobytes()).hexdigest(),
            "graph_fingerprints": {"static": graph_fingerprint(static), "supra": graph_fingerprint(supra)}}
    write_json(output / "metrics.json", data)
    run = manifest(config_path, cfg, cfg["experiment"]["id"])
    run.update({"input_reference_hashes": {"baseline_supra": sha256("outputs/baseline/supra_labels.csv"),
                                             "baseline_static": sha256("outputs/baseline/static_dec2024_labels.csv")},
                "status": "completed"})
    write_json(output / "run_manifest.json", run)
    write_json(output / "COMPLETED.json", {"status": "completed", "files": sorted(p.name for p in output.iterdir())})


def aggregate_round18(root: str = "outputs/round18_representation") -> None:
    root_path = Path(root)
    variants = ["reference", "r1_fivepart_clr", "r2_observed_levels"]
    entries = []
    for variant in variants:
        directory = root_path / variant
        if not (directory / "COMPLETED.json").exists():
            raise RuntimeError(f"Missing completed Round18 variant: {directory}")
        metrics = json.loads((directory / "metrics.json").read_text(encoding="utf-8"))
        entries.append({"representation": variant, **metrics["comparisons"]["temporal_dec2024"],
                        **{f"static_{k}": v for k, v in metrics["metrics_static"].items()},
                        **{f"temporal_{k}": v for k, v in metrics["metrics_temporal_dec2024"].items()},
                        **metrics["temporal"]})
    pd.DataFrame(entries).to_csv(root_path / "comparison.csv", index=False)
    overlaps = []
    for variant in variants:
        frame = pd.read_csv(root_path / variant / "profile_overlap.csv")
        frame.insert(0, "representation", variant)
        overlaps.append(frame)
    pd.concat(overlaps, ignore_index=True).to_csv(root_path / "profile_overlap.csv", index=False)
    write_json(root_path / "round18_summary.json", {"status": "COMPUTED_DESCRIPTIVE_NOT_CONFIRMATORY", "variants": variants,
               "reference_gate": "outputs/presubmission_upgrade/baseline_gate", "comparison": entries})
    (root_path / "ROUND18_AUDIT.md").write_text(
        "# Round18 representation robustness audit\n\n"
        "All three predeclared representations use the unchanged 1,904×24 panel, mutual-kNN20, adaptive RBF, omega=2, Louvain resolution=.5 and seed=0. "
        "Only the representation changes. `comparison.csv` and `profile_overlap.csv` are descriptive single-seed comparisons; they do not select a preferred representation or update A–G scientific statuses. "
        "The reference gate passed before all variants. `Other` is never constructed in R1/R2.\n", encoding="utf-8")


def run_edge(config_path: str, output: str) -> None:
    cfg = load_config(config_path); gate(Path("outputs/presubmission_upgrade/baseline_gate")); fresh(Path(output))
    cfg, names, keys, matrices = prepared(config_path); x = matrices[keys[-1]]
    reference = pd.read_csv("outputs/baseline/static_dec2024_labels.csv").set_index("mo").loc[names, "community"].to_numpy()
    rows = []
    for mutual in (True, False):
        for k in cfg["robustness"]["k_grid"]:
            graph = knn_graph(x, k, cfg["network"]["static_isolate_fallback"], mutual)
            labels = louvain_labels(graph, cfg["clustering"]["resolution"], cfg["clustering"]["seed"])
            row = {"edge_rule": "mutual" if mutual else "union", "k": k, **graph_stats(graph),
                   **flat_metrics(evaluate_partition(x, labels, graph)), **partition_similarity(reference, labels)}
            rows.append(row)
    result = pd.DataFrame(rows); result.to_csv(Path(output) / "edge_sensitivity.csv", index=False)
    result[["edge_rule", "k", "density", "MQ", "ari", "K", "connected_components"]].to_csv(Path(output) / "plot_data.csv", index=False)
    (Path(output) / "EDGE_SENSITIVITY.md").write_text(
        "# Edge-rule sensitivity\n\nMutual-kNN keeps only reciprocal local similarities, yielding a sparser graph than union-kNN, which keeps a pair when either endpoint nominates the other. "
        "This fixed grid is descriptive: it reports how sparsity and detected communities change and does not choose k by ICVI. See `edge_sensitivity.csv`.\n", encoding="utf-8")
    write_json(Path(output) / "run_manifest.json", {**manifest(config_path, cfg, "edge_sensitivity"), "status": "completed"})


def run_omega(config_path: str, output: str) -> None:
    cfg = load_config(config_path); gate(Path("outputs/presubmission_upgrade/baseline_gate")); fresh(Path(output))
    cfg, names, keys, matrices = prepared(config_path)
    monthly = [knn_graph(matrices[key], cfg["network"]["k"], cfg["network"]["temporal_isolate_fallback"], True) for key in keys]
    reference = pd.read_csv("outputs/baseline/supra_labels.csv", index_col=0).loc[names, keys].to_numpy(dtype=int).T
    rows = []
    for omega in cfg["robustness"]["omega_grid"]:
        supra = build_supra_graph(monthly, len(names), omega)
        labels = louvain_labels(supra, cfg["clustering"]["resolution"], cfg["clustering"]["seed"]).reshape(len(keys), len(names))
        dec_icvi = flat_metrics(evaluate_partition(matrices[keys[-1]], labels[-1], monthly[-1]))
        row = {"omega": omega, "K_supra": int(len(np.unique(labels))), "K_Dec2024": int(len(np.unique(labels[-1]))),
               "MQ_supra": float(nx.community.modularity(supra, [set(np.where(labels.ravel() == c)[0]) for c in np.unique(labels)], weight="weight")),
               **temporal_switches(labels), **{f"Dec2024_{k}": v for k, v in partition_similarity(reference[-1], labels[-1]).items()},
               **{f"supra_{k}": v for k, v in partition_similarity(reference.ravel(), labels.ravel()).items()}, **dec_icvi}
        rows.append(row)
    result = pd.DataFrame(rows); result.to_csv(Path(output) / "omega_sensitivity.csv", index=False)
    (Path(output) / "TEMPORAL_SENSITIVITY.md").write_text(
        "# Temporal-coupling sensitivity\n\nEach row holds features and all intralayer graphs fixed while changing only omega. "
        "Switch counts are conditional on the joint supra-graph model: they combine data similarity and temporal regularization and must not be described as persistence extracted from data alone. See `omega_sensitivity.csv`.\n", encoding="utf-8")
    write_json(Path(output) / "run_manifest.json", {**manifest(config_path, cfg, "temporal_omega_sensitivity"), "status": "completed"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    round18 = sub.add_parser("round18"); round18.add_argument("--config", required=True)
    aggregate = sub.add_parser("aggregate-round18"); aggregate.add_argument("--root", default="outputs/round18_representation")
    edge = sub.add_parser("edge"); edge.add_argument("--config", default="configs/baseline.yaml"); edge.add_argument("--output", default="outputs/presubmission_upgrade/edge_sensitivity")
    omega = sub.add_parser("omega"); omega.add_argument("--config", default="configs/baseline.yaml"); omega.add_argument("--output", default="outputs/presubmission_upgrade/temporal_sensitivity")
    args = parser.parse_args()
    if args.command == "round18": run_round18(args.config)
    elif args.command == "aggregate-round18": aggregate_round18(args.root)
    elif args.command == "edge": run_edge(args.config, args.output)
    else: run_omega(args.config, args.output)
