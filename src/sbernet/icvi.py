"""Documented internal cluster-validity indices for fixed partitions.

The implementation deliberately evaluates a supplied partition; it never
selects a representation, graph, resolution, or number of communities.
"""
from __future__ import annotations

from itertools import combinations
from numbers import Real
from typing import Any

import networkx as nx
import numpy as np
from sklearn.metrics import calinski_harabasz_score, silhouette_score


def _invalid(reason: str) -> dict[str, Any]:
    return {"value": None, "status": f"undefined:{reason}"}


def _labels(labels: np.ndarray, n: int) -> tuple[np.ndarray, np.ndarray]:
    labels = np.asarray(labels)
    if labels.ndim != 1 or len(labels) != n:
        raise ValueError("labels must be one-dimensional and match X rows")
    if not np.isfinite(labels).all():
        raise ValueError("labels must be finite")
    _, inverse = np.unique(labels, return_inverse=True)
    return labels, inverse


def s_dbw(x: np.ndarray, inverse: np.ndarray) -> dict[str, Any]:
    """Compute the original S_Dbw validity index (lower is better).

    This implements the Scat + Dens_bw definition of Halkidi and
    Vazirgiannis, *Clustering Validity Assessment* (2001), with Euclidean
    density balls.  Let ``sigma(A)`` be the coordinatewise population standard
    deviation.  ``Scat = mean_i ||sigma(C_i)|| / ||sigma(X)||``.  The common
    radius is ``mean_i ||sigma(C_i)||`` and ``Dens_bw`` is the mean, over
    unordered cluster pairs, of the density at the two-centroid midpoint
    divided by the larger centroid density.  The midpoint density includes
    points from those two clusters only.

    A 0/0 pair means neither cluster has observations within its density ball;
    its between-density contribution is defined as zero (no observed bridge).
    A positive/zero ratio, zero global dispersion, or fewer than two clusters
    is undefined and returned with an explicit status.  This convention is
    fixed here and is not the historical forensic implementation.
    """
    k = int(inverse.max()) + 1
    if k < 2:
        return _invalid("requires_at_least_two_clusters")
    groups = [x[inverse == i] for i in range(k)]
    global_norm = float(np.linalg.norm(np.std(x, axis=0, ddof=0)))
    if global_norm == 0:
        return _invalid("zero_global_dispersion")
    dispersions = np.array([np.linalg.norm(np.std(g, axis=0, ddof=0)) for g in groups])
    radius = float(dispersions.mean())
    centers = [g.mean(axis=0) for g in groups]

    def density(points: np.ndarray, center: np.ndarray) -> int:
        return int(np.count_nonzero(np.linalg.norm(points - center, axis=1) <= radius))

    center_density = [density(group, center) for group, center in zip(groups, centers)]
    pair_scores: list[float] = []
    for i, j in combinations(range(k), 2):
        midpoint = (centers[i] + centers[j]) / 2.0
        numerator = density(groups[i], midpoint) + density(groups[j], midpoint)
        denominator = max(center_density[i], center_density[j])
        if denominator == 0 and numerator > 0:
            return _invalid("positive_midpoint_density_over_zero_center_density")
        pair_scores.append(0.0 if denominator == 0 else numerator / denominator)
    return {
        "value": float(dispersions.mean() / global_norm + np.mean(pair_scores)),
        "status": "defined:halkidi_vazirgiannis_2001_population_std",
    }


def _adjacency_validity(graph: nx.Graph, inverse: np.ndarray) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return AVI (higher) and AVU (lower) from unweighted adjacency blocks.

    ``AVI = mean_i m_ii / (m_ii + sum_{j!=i}m_ij)``.  ``AVU`` is the mean
    off-diagonal block overlap ``m_ij/(e_i + e_j - m_ij)`` across ordered
    communities, following the repository's canonical Round16 definition.
    Isolated communities contribute zero to both quantities.
    """
    k = int(inverse.max()) + 1
    block = np.zeros((k, k), dtype=np.int64)
    for u, v in graph.edges:
        block[inverse[u], inverse[v]] += 1
        block[inverse[v], inverse[u]] += 1
    internal = np.diag(block)
    external = block.sum(axis=1) - internal
    avi = np.divide(internal, internal + external, out=np.zeros(k), where=(internal + external) > 0)
    denom = external[:, None] + external[None, :] - block
    cross = block.astype(float)
    np.fill_diagonal(cross, 0.0)
    avu = np.divide(cross, denom, out=np.zeros_like(cross), where=denom > 0)
    return ({"value": float(avi.mean()), "status": "defined"},
            {"value": float(avu.sum() / k), "status": "defined"})


def adjacency_block_matrix(
    graph: nx.Graph,
    labels: np.ndarray,
    *,
    weighted: bool = True,
) -> np.ndarray:
    """Return the symmetric community adjacency block matrix.

    Each undirected edge contributes once to both ``S[i, j]`` and ``S[j, i]``.
    Consequently a within-community edge contributes twice to ``S[i, i]``.
    The function deliberately rejects directed/multi graphs, non-canonical node
    sets and invalid weights instead of silently coercing them.
    """
    if graph.is_directed() or graph.is_multigraph():
        raise ValueError("graph must be a simple undirected graph")
    original, inverse = _labels(labels, graph.number_of_nodes())
    del original
    n = len(inverse)
    if set(graph.nodes) != set(range(n)):
        raise ValueError("graph nodes must be exactly 0..N-1")
    k = int(inverse.max()) + 1
    block = np.zeros((k, k), dtype=float)
    for u, v, data in graph.edges(data=True):
        raw_weight = data.get("weight", 1.0) if weighted else 1.0
        if isinstance(raw_weight, (bool, np.bool_)) or not isinstance(raw_weight, Real):
            raise ValueError("graph weights must be numeric, not coerced from another type")
        weight = float(raw_weight)
        if not np.isfinite(weight) or weight < 0:
            raise ValueError("graph weights must be finite and non-negative")
        i, j = int(inverse[u]), int(inverse[v])
        block[i, j] += weight
        block[j, i] += weight
    return block


def _block_graph_icvi(block: np.ndarray) -> dict[str, dict[str, Any]]:
    """Compute weighted AVI, AVU, ANUI and TurboMQ from one block matrix."""
    k = len(block)
    internal = np.diag(block)
    row_sum = block.sum(axis=1)
    external = row_sum - internal
    avi_by_cluster = np.divide(
        internal, row_sum, out=np.zeros(k, dtype=float), where=row_sum > 0
    )
    avi = float(avi_by_cluster.mean())

    denominator = external[:, None] + external[None, :] - block
    numerator = block.copy()
    np.fill_diagonal(numerator, 0.0)
    valid = denominator != 0
    overlap = np.divide(
        numerator,
        denominator,
        out=np.zeros_like(numerator, dtype=float),
        where=valid,
    )
    np.fill_diagonal(overlap, 0.0)
    avu = float(overlap.sum() / k)
    anui = 0.0 if avi == 0 else float(1.0 / (avu + 1.0 / avi))

    mu = internal / 2.0
    cf_denominator = mu + 0.5 * external
    cf = np.divide(
        mu,
        cf_denominator,
        out=np.zeros(k, dtype=float),
        where=cf_denominator > 0,
    )
    mq = float(cf.sum())
    return {
        "AVI": {"value": avi, "status": "defined:weighted_adjacency"},
        "AVU": {"value": avu, "status": "defined:weighted_adjacency_pattern"},
        "ANUI": {"value": anui, "status": "defined:weighted_adjacency"},
        "MQ": {"value": mq, "status": "defined:turbomq"},
    }


def weighted_graph_icvi(graph: nx.Graph, labels: np.ndarray) -> dict[str, dict[str, Any]]:
    """Evaluate canonical ICVI-v2 graph metrics for a fixed partition.

    ``MQ`` is TurboMQ and ``Q`` is weighted Newman--Girvan modularity at
    resolution one.  Weighted AVI/AVU are accompanied by their unweighted
    legacy diagnostics.  A graph without positive total weight has no defined
    Newman--Girvan null model; Q is then explicitly undefined while all block
    metrics remain defined under their documented zero conventions.
    """
    weighted = adjacency_block_matrix(graph, labels, weighted=True)
    unweighted = adjacency_block_matrix(graph, labels, weighted=False)
    result = _block_graph_icvi(weighted)
    legacy = _block_graph_icvi(unweighted)
    result["AVI_unweighted"] = {
        "value": legacy["AVI"]["value"],
        "status": "defined:legacy_unweighted_adjacency",
    }
    result["AVU_unweighted"] = {
        "value": legacy["AVU"]["value"],
        "status": "defined:legacy_unweighted_adjacency_pattern",
    }
    inverse = _labels(labels, graph.number_of_nodes())[1]
    communities = [set(np.where(inverse == cluster)[0]) for cluster in range(len(weighted))]
    total_weight = float(weighted.sum() / 2.0)
    if total_weight <= 0:
        result["Q"] = _invalid("zero_total_graph_weight")
        result["legacy_MQ_newman_girvan"] = _invalid("zero_total_graph_weight")
    else:
        q = float(
            nx.community.modularity(
                graph, communities, weight="weight", resolution=1.0
            )
        )
        result["Q"] = {"value": q, "status": "defined:weighted_newman_girvan"}
        result["legacy_MQ_newman_girvan"] = {
            "value": q,
            "status": "defined:historical_name_only",
        }
    return result


def evaluate_partition_v2(
    x: np.ndarray,
    labels: np.ndarray,
    graph: nx.Graph | None = None,
) -> dict[str, Any]:
    """Evaluate a fixed partition using the canonical ICVI-v2 definitions.

    This function is additive.  :func:`evaluate_partition` remains the legacy
    v1 evaluator so historical artifacts and callers retain their exact
    definitions.
    """
    x = np.asarray(x, dtype=float)
    if x.ndim != 2 or x.shape[0] < 1 or x.shape[1] < 1 or not np.isfinite(x).all():
        raise ValueError("X must be a non-empty finite 2D array")
    original, inverse = _labels(labels, len(x))
    n = len(x)
    k = int(inverse.max()) + 1
    result: dict[str, Any] = {"N": n, "K": k}
    if 2 <= k < n:
        result["SW"] = {"value": float(silhouette_score(x, original)), "status": "defined"}
        ch = float(calinski_harabasz_score(x, original))
        result["CH"] = {"value": ch, "status": "defined"}
        result["CH_per_N"] = {"value": ch / n, "status": "defined"}
    else:
        reason = "requires_two_to_N_minus_one_clusters"
        result["SW"] = _invalid(reason)
        result["CH"] = _invalid(reason)
        result["CH_per_N"] = _invalid(reason)
    result["S_Dbw"] = s_dbw(x, inverse)
    graph_metrics = (
        weighted_graph_icvi(graph, original)
        if graph is not None
        else {
            name: _invalid("graph_not_supplied")
            for name in (
                "AVI", "AVU", "ANUI", "MQ", "Q", "AVI_unweighted",
                "AVU_unweighted", "legacy_MQ_newman_girvan",
            )
        }
    )
    result.update(graph_metrics)
    return result


def flat_metrics_v2(result: dict[str, Any]) -> dict[str, Any]:
    """Flatten canonical v2 metrics for CSV output with explicit statuses."""
    metrics = (
        "SW", "CH", "CH_per_N", "S_Dbw", "AVI", "AVU", "ANUI", "MQ", "Q",
        "AVI_unweighted", "AVU_unweighted",
    )
    values = {name: result[name]["value"] for name in metrics}
    statuses = {name: result[name]["status"] for name in metrics}
    notes = "; ".join(
        f"{name}={status}"
        for name, status in statuses.items()
        if not status.startswith("defined")
    )
    return {
        "K": result["K"],
        "N": result["N"],
        **values,
        "status": "defined" if not notes else "partially_undefined",
        "notes": notes,
    }


def evaluate_partition(x: np.ndarray, labels: np.ndarray, graph: nx.Graph | None = None) -> dict[str, Any]:
    """Evaluate one fixed partition with SW↑, CH↑, S_Dbw↓, AVI↑, AVU↓, MQ↑.

    ``SW`` is the mean silhouette coefficient using Euclidean distances.  ``CH``
    is the raw Calinski--Harabasz variance ratio; ``CH_per_N = CH / N`` is only
    a scale diagnostic.  ``MQ`` is weighted Newman--Girvan modularity at
    resolution one.  Graph indices assume nodes ``0..N-1``; disconnected graphs
    are valid and are evaluated without synthetic edges.

    Undefined metrics are returned as ``None`` together with a metric-specific
    status.  Invalid numeric input raises rather than silently coercing data.
    """
    x = np.asarray(x, dtype=float)
    if x.ndim != 2 or x.shape[0] < 1 or x.shape[1] < 1 or not np.isfinite(x).all():
        raise ValueError("X must be a non-empty finite 2D array")
    original, inverse = _labels(labels, len(x))
    n = len(x)
    k = int(inverse.max()) + 1
    result: dict[str, Any] = {"N": n, "K": k}
    if 2 <= k < n:
        result["SW"] = {"value": float(silhouette_score(x, original)), "status": "defined"}
        ch = float(calinski_harabasz_score(x, original))
        result["CH"] = {"value": ch, "status": "defined"}
        result["CH_per_N"] = {"value": ch / n, "status": "defined"}
    else:
        reason = "requires_two_to_N_minus_one_clusters"
        result["SW"] = _invalid(reason)
        result["CH"] = _invalid(reason)
        result["CH_per_N"] = _invalid(reason)
    result["S_Dbw"] = s_dbw(x, inverse)
    if graph is None:
        result["AVI"] = _invalid("graph_not_supplied")
        result["AVU"] = _invalid("graph_not_supplied")
        result["MQ"] = _invalid("graph_not_supplied")
    else:
        if set(graph.nodes) != set(range(n)):
            raise ValueError("graph nodes must be exactly 0..N-1")
        weights = [float(data.get("weight", 1.0)) for _, _, data in graph.edges(data=True)]
        if not np.isfinite(weights).all() or any(weight < 0 for weight in weights):
            raise ValueError("graph weights must be finite and non-negative")
        result["AVI"], result["AVU"] = _adjacency_validity(graph, inverse)
        communities = [set(np.where(inverse == cluster)[0]) for cluster in range(k)]
        result["MQ"] = {"value": float(nx.community.modularity(graph, communities, weight="weight")), "status": "defined"}
    return result


def flat_metrics(result: dict[str, Any]) -> dict[str, Any]:
    """Flatten :func:`evaluate_partition` for CSV rows, retaining status notes."""
    metrics = ("SW", "CH", "CH_per_N", "S_Dbw", "AVI", "AVU", "MQ")
    values = {name: result[name]["value"] for name in metrics}
    statuses = {name: result[name]["status"] for name in metrics}
    notes = "; ".join(
        f"{name}={status}" for name, status in statuses.items()
        if not status.startswith("defined")
    )
    return {"K": result["K"], "N": result["N"], **values,
            "status": "defined" if not notes else "partially_undefined", "notes": notes}
