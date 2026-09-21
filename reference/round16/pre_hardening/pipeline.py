from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess

import networkx as nx
import numpy as np
import pandas as pd
import yaml

from .clustering import louvain_labels
from .config import load_config
from .features import monthly_feature_matrix
from .graph import mutual_knn_graph
from .io import build_strict_panel, read_semicolon_zip
from .temporal import build_supra_graph


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return None


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _prepare(cfg_path: str | Path):
    cfg = load_config(cfg_path)
    raw = read_semicolon_zip(cfg["paths"]["spending_zip"])

    required = [cfg["panel"]["total_category"]] + cfg["panel"]["selected_categories"]
    panel, names, audit = build_strict_panel(
        raw,
        expected_months=cfg["panel"]["expected_months"],
        required_categories=required,
    )

    panel["period"] = pd.to_datetime(panel["period"])
    months = sorted(panel["period"].unique())
    feature_matrices: dict[str, np.ndarray] = {}

    for month in months:
        key = str(pd.Timestamp(month).date())
        x, _ = monthly_feature_matrix(
            month_df=panel[panel["period"].eq(month)],
            municipality_order=names,
            total_category=cfg["panel"]["total_category"],
            selected_categories=cfg["panel"]["selected_categories"],
            other_category=cfg["panel"]["other_category"],
            structure_weight=cfg["features"]["structure_weight"],
            level_weight=cfg["features"]["level_weight"],
        )
        feature_matrices[key] = x

    return cfg, names, audit, months, feature_matrices


def inspect_panel(cfg_path: str | Path) -> dict:
    cfg, _, audit, months, _ = _prepare(cfg_path)
    return {
        "unique_names": audit.unique_names,
        "ambiguous_names": audit.ambiguous_names,
        "complete_names": audit.complete_names,
        "strict_panel_names": audit.strict_panel_names,
        "months": len(months),
        "expected_months": cfg["panel"]["expected_months"],
    }


def run(cfg_path: str | Path, mode: str = "both") -> None:
    cfg_path = Path(cfg_path)
    cfg, names, audit, months, matrices = _prepare(cfg_path)

    output_dir = Path(cfg["paths"]["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    month_keys = [str(pd.Timestamp(m).date()) for m in months]
    graph_stats = {}

    if mode in {"static", "both"}:
        x = matrices[month_keys[-1]]
        graph = mutual_knn_graph(
            x,
            k=cfg["network"]["k"],
            isolate_fallback=cfg["network"]["static_isolate_fallback"],
        )
        labels = louvain_labels(
            graph,
            resolution=cfg["clustering"]["resolution"],
            seed=cfg["clustering"]["seed"],
        )
        pd.DataFrame({"mo": names, "community": labels}).to_csv(
            output_dir / "static_dec2024_labels.csv", index=False
        )
        graph_stats["static"] = {
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
            "communities": int(len(np.unique(labels))),
            "components": nx.number_connected_components(graph),
        }

    if mode in {"temporal", "both"}:
        monthly_graphs = [
            mutual_knn_graph(
                matrices[key],
                k=cfg["network"]["k"],
                isolate_fallback=cfg["network"]["temporal_isolate_fallback"],
            )
            for key in month_keys
        ]
        supra = build_supra_graph(
            monthly_graphs,
            n_nodes=len(names),
            omega=cfg["temporal"]["omega"],
        )
        flat_labels = louvain_labels(
            supra,
            resolution=cfg["clustering"]["resolution"],
            seed=cfg["clustering"]["seed"],
        )
        labels = flat_labels.reshape(len(month_keys), len(names)).T
        pd.DataFrame(labels, index=names, columns=month_keys).to_csv(
            output_dir / "supra_labels.csv"
        )
        graph_stats["temporal"] = {
            "nodes": supra.number_of_nodes(),
            "edges": supra.number_of_edges(),
            "communities": int(len(np.unique(flat_labels))),
            "temporal_weight": supra.graph["temporal_weight"],
        }

    resolved = yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False)
    (output_dir / "resolved_config.yaml").write_text(resolved, encoding="utf-8")

    manifest = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        "config_path": str(cfg_path),
        "config_sha256": _sha256_text(resolved),
        "evidence_version": cfg["project"].get("evidence_version"),
        "panel": {
            "unique_names": audit.unique_names,
            "ambiguous_names": audit.ambiguous_names,
            "complete_names": audit.complete_names,
            "strict_panel_names": audit.strict_panel_names,
            "months": len(months),
        },
        "graph_stats": graph_stats,
    }
    (output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
