"""Additive ICVI-v2 reevaluation of already fixed partitions and edge grid."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import pickle
import platform
import subprocess

import networkx as nx
import numpy as np
import pandas as pd
import sklearn
import yaml

from sbernet.clustering import louvain_labels
from sbernet.edge_sensitivity import knn_graph
from sbernet.icvi import (
    evaluate_partition,
    evaluate_partition_v2,
    flat_metrics,
    flat_metrics_v2,
)
from sbernet.metrics import partition_similarity
from sbernet.pipeline import _prepare
from sbernet.robustness.reproduction_gate import sha256


CANONICAL_COLUMNS = [
    "method", "K", "N", "SW", "CH", "CH_per_N", "S_Dbw", "AVI", "AVU",
    "ANUI", "MQ", "Q", "AVI_unweighted", "AVU_unweighted", "status", "notes",
]
EDGE_COLUMNS = [
    "edge_rule", "k", "edges", "density", "K", "N", "SW", "CH", "CH_per_N",
    "S_Dbw", "AVI", "AVU", "ANUI", "MQ", "Q", "AVI_unweighted",
    "AVU_unweighted", "ARI", "NMI", "status", "notes",
]


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return None


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )


def _assert_close(actual: object, expected: object, *, name: str, atol: float, rtol: float) -> None:
    if pd.isna(actual) and pd.isna(expected):
        return
    if isinstance(actual, (int, float, np.number)) and isinstance(expected, (int, float, np.number)):
        if not np.isclose(float(actual), float(expected), atol=atol, rtol=rtol):
            raise RuntimeError(f"historical gate mismatch for {name}: {actual!r} != {expected!r}")
        return
    if actual != expected:
        raise RuntimeError(f"historical gate mismatch for {name}: {actual!r} != {expected!r}")


def _graph_stats(graph: nx.Graph) -> dict[str, float | int]:
    return {"edges": graph.number_of_edges(), "density": float(nx.density(graph))}


def _markdown_table(frame: pd.DataFrame, columns: list[str], digits: int = 6) -> str:
    def value(item: object) -> str:
        if pd.isna(item):
            return "NA"
        if isinstance(item, (float, np.floating)):
            return f"{float(item):.{digits}f}"
        return str(item)

    rows = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    rows.extend("| " + " | ".join(value(row[column]) for column in columns) + " |" for _, row in frame.iterrows())
    return "\n".join(rows)


def run(config_path: str) -> None:
    cfg_path = Path(config_path)
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    exp = cfg["experiment"]
    output = Path(exp["output_dir"])
    if output.exists():
        raise FileExistsError(f"refusing to overwrite ICVI evidence: {output}")
    gate = json.loads(Path(exp["baseline_gate"]).read_text(encoding="utf-8"))
    if not gate.get("passed") or any(
        metric[value] != 1.0
        for metric in gate["metrics"].values()
        for value in ("ARI", "NMI")
    ):
        raise RuntimeError("baseline reproduction gate is not exact; ICVI-v2 is blocked")

    base_cfg, names, _, months, matrices = _prepare(cfg["source_config"])
    keys = [str(pd.Timestamp(month).date()) for month in months]
    if len(names) != 1904 or len(keys) != 24:
        raise RuntimeError("ICVI-v2 requires the exact 1,904 x 24 reference panel")
    period = cfg["fixed_partitions"]["input_period"]
    if period not in matrices:
        raise RuntimeError(f"fixed input period not found: {period}")
    x = matrices[period]
    with Path(exp["baseline_graphs"]).open("rb") as handle:
        graph = pickle.load(handle)["static"]
    if graph.number_of_nodes() != len(x):
        raise RuntimeError("stored static graph does not match the reference features")

    atol, rtol = float(exp["numeric_gate_atol"]), float(exp["numeric_gate_rtol"])
    old_canonical = pd.read_csv(exp["historical_canonical_csv"]).set_index("method")
    canonical_rows: list[dict] = []
    canonical_gate: list[dict] = []
    for method in cfg["fixed_partitions"]["methods"]:
        labels_path = Path(exp["fixed_method_labels_dir"]) / f"{method}_labels.csv"
        labels = pd.read_csv(labels_path).set_index("mo").loc[names, "community"].to_numpy()
        legacy = flat_metrics(evaluate_partition(x, labels, graph))
        for column in ("K", "N", "SW", "CH", "CH_per_N", "S_Dbw", "AVI", "AVU", "MQ"):
            _assert_close(
                legacy[column], old_canonical.loc[method, column],
                name=f"canonical/{method}/{column}", atol=atol, rtol=rtol,
            )
        canonical_gate.append({"method": method, "historical_v1_metrics_reproduced": True})
        canonical_rows.append({"method": method, **flat_metrics_v2(evaluate_partition_v2(x, labels, graph))})
    canonical = pd.DataFrame(canonical_rows)[CANONICAL_COLUMNS]

    reference = (
        pd.read_csv(exp["reference_static_labels"])
        .set_index("mo").loc[names, "community"].to_numpy()
    )
    old_edge = pd.read_csv(exp["historical_edge_csv"])
    edge_rows: list[dict] = []
    edge_gate: list[dict] = []
    for rule in cfg["edge_grid"]["rules"]:
        mutual = rule == "mutual"
        for k in cfg["edge_grid"]["k"]:
            candidate_graph = knn_graph(
                x, int(k), bool(cfg["edge_grid"]["isolate_fallback"]), mutual
            )
            labels = louvain_labels(
                candidate_graph,
                resolution=float(cfg["clustering_replay"]["resolution"]),
                seed=int(cfg["clustering_replay"]["seed"]),
            )
            similarity = partition_similarity(reference, labels)
            legacy = {
                **_graph_stats(candidate_graph),
                **flat_metrics(evaluate_partition(x, labels, candidate_graph)),
                **similarity,
            }
            expected = old_edge.loc[
                old_edge.edge_rule.eq(rule) & old_edge.k.eq(k)
            ].iloc[0]
            for column in (
                "edges", "density", "K", "N", "SW", "CH", "CH_per_N", "S_Dbw",
                "AVI", "AVU", "MQ", "ari", "nmi",
            ):
                _assert_close(
                    legacy[column], expected[column], name=f"edge/{rule}/{k}/{column}",
                    atol=atol, rtol=rtol,
                )
            if rule == "mutual" and int(k) == 20 and (
                similarity["ari"] != 1.0 or similarity["nmi"] != 1.0
            ):
                raise RuntimeError("reference mutual-k20 partition changed")
            edge_gate.append({
                "edge_rule": rule, "k": int(k),
                "historical_v1_row_reproduced": True,
                "reference_partition_exact": bool(rule == "mutual" and int(k) == 20),
            })
            edge_rows.append({
                "edge_rule": rule,
                "k": int(k),
                **_graph_stats(candidate_graph),
                **flat_metrics_v2(evaluate_partition_v2(x, labels, candidate_graph)),
                "ARI": similarity["ari"],
                "NMI": similarity["nmi"],
            })
    edge = pd.DataFrame(edge_rows)[EDGE_COLUMNS]

    output.mkdir(parents=True, exist_ok=False)
    canonical.to_csv(output / "canonical_icvi_v2.csv", index=False)
    edge.to_csv(output / "edge_icvi_v2.csv", index=False)
    definitions = {
        "schema_version": 2,
        "MQ": "TurboMQ=sum_i mu_i/(mu_i+0.5*epsilon_i)",
        "Q": "weighted Newman-Girvan modularity, resolution=1.0",
        "AVI": "mean_i S_ii/sum_j(S_ij); zero-strength community contributes 0",
        "AVU": "sum_i(sum_j!=i S_ij/(out_i+in_j-S_ij))/K; zero denominator contributes 0",
        "ANUI": "1/(AVU+1/AVI) when AVI!=0, otherwise 0",
        "AVI_unweighted": "historical unweighted block-count diagnostic",
        "AVU_unweighted": "historical unweighted block-count diagnostic",
        "S_Dbw": "repository Halkidi-Vazirgiannis 2001 Scat+Dens_bw population-std variant",
    }
    _write_json(output / "metric_definitions.json", definitions)

    report = (
        "# ICVI v2 report\n\n"
        "This is a diagnostic reevaluation of fixed partitions. It does not select a method, "
        "change a graph, or tune any parameter.\n\n"
        "## Canonical fixed partitions\n\n"
        + _markdown_table(canonical, ["method", "K", "SW", "CH", "S_Dbw", "AVI", "AVU", "ANUI", "MQ", "Q"])
        + "\n\nMQ is TurboMQ; Q is weighted Newman–Girvan modularity. Their scales are not comparable.\n\n"
        "## Edge grid\n\nSee `edge_icvi_v2.csv`. Every replayed v1 row passed the saved-table gate; "
        "mutual-k20 has ARI=NMI=1 against the unchanged static reference. The grid is not a tuning exercise.\n"
    )
    (output / "ICVI_REPORT.md").write_text(report, encoding="utf-8")
    audit = """# ICVI v2 audit

## Что обнаружено

Предыдущий canonical ICVI layer использовал поле MQ для weighted Newman–Girvan modularity. AVI/AVU считались по unweighted adjacency blocks.

## Почему это важно

MQ является неоднозначным сокращением. В reporting v2 MQ означает TurboMQ, Q означает weighted Newman–Girvan modularity, а AVI/AVU используют weighted adjacency.

## Что исправлено

Добавлены отдельные weighted block matrix, AVI, AVU, ANUI, TurboMQ и Q. Legacy AVI/AVU публикуются как `AVI_unweighted`/`AVU_unweighted`; историческое значение MQ доступно программно как `legacy_MQ_newman_girvan`. Все пять fixed method partitions прочитаны из сохранённых labels. Edge-grid был детерминированно воспроизведён, потому что его labels отдельно не сохранялись; каждая строка прошла gate против исторической v3-таблицы.

## Что НЕ изменено

Data, features, graph definitions, fixed labels, clustering methods, baseline, A–G, temporal model, omega=2, resolution=0.5 и scientific statuses не изменены. Новые метрики не использовались для выбора K, k, graph rule или метода.

## Historical compatibility

Старые CSV сохранены без изменений. В них `historical MQ column = Newman–Girvan Q`. Старый `evaluate_partition` оставлен как legacy v1 API; новый слой реализован отдельными `weighted_graph_icvi` и `evaluate_partition_v2`.

## S_Dbw

Формула не менялась: repository canonical variant — Halkidi–Vazirgiannis (2001) `Scat + Dens_bw`, coordinatewise population standard deviations, общий radius как среднее норм дисперсий, density в замкнутом евклидовом шаре и midpoint density только по двум рассматриваемым кластерам. Конвенция 0/0→0 и positive/0→undefined документирована в коде. Отдельного competition/rubric определения S_Dbw в репозитории не найдено; поэтому межреализационная численная эквивалентность не заявляется. Внутреннего unresolved discrepancy нет.

## Scientific consequence

Новые значения graph ICVI меняют обозначения и определения сетевых validity metrics, но не меняют partitions. TurboMQ и Q имеют разные шкалы; TurboMQ может превышать 1 и не сравнивается численно с Q.
"""
    (output / "ICVI_V2_AUDIT.md").write_text(audit, encoding="utf-8")

    inputs = [
        cfg_path, Path(cfg["source_config"]), Path(exp["baseline_gate"]),
        Path(exp["baseline_graphs"]), Path(exp["historical_canonical_csv"]),
        Path(exp["historical_edge_csv"]), Path(exp["reference_static_labels"]),
        Path(__file__), Path("src/sbernet/icvi.py"),
        *[
            Path(exp["fixed_method_labels_dir"]) / f"{method}_labels.csv"
            for method in cfg["fixed_partitions"]["methods"]
        ],
    ]
    manifest = {
        "experiment": cfg["experiment"]["id"],
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        "config_path": str(cfg_path),
        "config_sha256": sha256(cfg_path),
        "input_sha256": {str(path): sha256(path) for path in inputs},
        "packages": {
            "python": platform.python_version(), "numpy": np.__version__,
            "pandas": pd.__version__, "networkx": nx.__version__,
            "scikit_learn": sklearn.__version__, "PyYAML": yaml.__version__,
        },
        "seed": int(cfg["clustering_replay"]["seed"]),
        "baseline_gate": gate,
        "canonical_historical_gate": canonical_gate,
        "edge_historical_gate": edge_gate,
        "partitions_changed": False,
        "baseline_changed": False,
        "reference_k_changed": False,
        "reference_omega_changed": False,
        "status": "COMPLETED_ADDITIVE_ICVI_COMPATIBILITY_LAYER",
    }
    _write_json(output / "run_manifest.json", manifest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/icvi_v2.yaml")
    run(parser.parse_args().config)
