"""Explicit non-reference graph constructions for Round24.

Only municipality-sized distance matrices are used; no supra adjacency is dense.
"""
from __future__ import annotations

import math

import networkx as nx
import numpy as np
from scipy.spatial.distance import pdist
from sklearn.neighbors import NearestNeighbors


def epsilon_graph(x, target_edges, k, denominator_epsilon):
    """Closed global threshold, edge-count calibrated without partition labels."""
    x = np.asarray(x, dtype=float)
    if x.ndim != 2 or not np.isfinite(x).all() or not 0 < k < len(x):
        raise ValueError("finite feature matrix and 0 < k < N required")
    distances = pdist(x, metric="euclidean")
    if not 1 <= target_edges <= len(distances):
        raise ValueError("target_edges outside unordered-pair count")
    threshold = float(np.partition(distances, target_edges - 1)[target_edges - 1])
    # Same estimator/bandwidth as reference; no change to the reference builder.
    knn_distances, _ = NearestNeighbors(n_neighbors=k + 1).fit(x).kneighbors(x)
    sigma = knn_distances[:, -1]
    left, right = np.triu_indices(len(x), 1)
    selected = np.flatnonzero(distances <= threshold)
    graph = nx.Graph()
    graph.add_nodes_from(range(len(x)))
    for index in selected:
        i, j = int(left[index]), int(right[index])
        distance = float(distances[index])
        weight = math.exp(-distance**2 / (float(sigma[i] * sigma[j]) + denominator_epsilon))
        graph.add_edge(i, j, distance=distance, weight=weight)
    calibration = {
        "epsilon": threshold, "target_edges": int(target_edges),
        "actual_edges": graph.number_of_edges(),
        "pairs_strictly_below": int(np.sum(distances < threshold)),
        "pairs_at_threshold": int(np.sum(distances == threshold)),
        "excess_due_to_ties": graph.number_of_edges() - int(target_edges),
        "unordered_pair_count": len(distances),
        "threshold_uses_partition_labels": False,
    }
    return graph, calibration


def mean_delta_correlation(features, centered_norm_tolerance):
    """Equal component Pearson mean; input has shape (time, municipality, part)."""
    values = np.asarray(features, dtype=float)
    if values.ndim != 3 or values.shape[0] < 4 or not np.isfinite(values).all():
        raise ValueError("finite (T>=4, N, P) feature tensor required")
    delta = np.diff(values, axis=0)
    centered = delta - delta.mean(axis=0, keepdims=True)
    norms = np.linalg.norm(centered, axis=0)
    invalid = np.argwhere(norms <= centered_norm_tolerance)
    if invalid.size:
        raise ValueError(f"undefined constant difference correlations (node,part): {invalid.tolist()}")
    unit = centered / norms[None, :, :]
    similarity = np.einsum("tip,tjp->ij", unit, unit, optimize=True) / values.shape[2]
    similarity = np.clip((similarity + similarity.T) / 2, -1, 1)
    np.fill_diagonal(similarity, 1.0)
    return similarity


def dynamics_graph(similarity, k, denominator_epsilon):
    """Mutual kNN on correlation distance, deterministic ties, no fallback."""
    similarity = np.asarray(similarity, dtype=float)
    n = len(similarity)
    if (similarity.shape != (n, n) or not np.isfinite(similarity).all()
            or not np.allclose(similarity, similarity.T)
            or np.any(np.abs(similarity) > 1) or not 0 < k < n):
        raise ValueError("finite symmetric [-1,1] similarity and 0 < k < N required")
    distance = np.sqrt(2 * np.maximum(0, 1 - similarity))
    np.fill_diagonal(distance, np.inf)
    # Stable sort breaks equal distances by frozen panel index, excludes self.
    neighbors = np.argsort(distance, axis=1, kind="stable")[:, :k]
    sigma = distance[np.arange(n), neighbors[:, -1]]
    sets = [set(row.tolist()) for row in neighbors]
    graph = nx.Graph()
    graph.add_nodes_from(range(n))
    for i in range(n):
        for raw_j in neighbors[i]:
            j = int(raw_j)
            if j <= i or i not in sets[j]:
                continue
            d = float(distance[i, j])
            weight = math.exp(-d*d / (float(sigma[i]*sigma[j]) + denominator_epsilon))
            graph.add_edge(i, j, distance=d, similarity=float(similarity[i, j]), weight=weight)
    return graph


def graph_diagnostics(graph, reference):
    degrees = np.array([graph.degree(i) for i in graph.nodes], dtype=int)
    edges = {tuple(sorted(edge)) for edge in graph.edges}
    ref_edges = {tuple(sorted(edge)) for edge in reference.edges}
    components = sorted(map(len, nx.connected_components(graph)), reverse=True)
    return {
        "N": graph.number_of_nodes(), "edges": len(edges), "density": nx.density(graph),
        "components": len(components), "isolates": int(np.sum(degrees == 0)),
        "largest_component_n": components[0],
        "degree_min": int(degrees.min()), "degree_median": float(np.median(degrees)),
        "degree_max": int(degrees.max()), "degree_mean": float(degrees.mean()),
        "total_edge_weight": float(graph.size(weight="weight")),
        "reference_edge_intersection": len(edges & ref_edges),
        "reference_edge_jaccard": len(edges & ref_edges) / len(edges | ref_edges),
        "fallback_edges": sum(bool(d.get("fallback", False)) for _, _, d in graph.edges(data=True)),
        "negative_similarity_edges": sum(d.get("similarity", 0) < 0 for _, _, d in graph.edges(data=True)),
    }


def profile_overlap(reference, candidate, profile_map):
    rows = []
    reference, candidate = np.asarray(reference), np.asarray(candidate)
    for profile, label in profile_map.items():
        mask = reference == label
        destinations, counts = np.unique(candidate[mask], return_counts=True)
        if not len(counts):
            raise ValueError(f"missing reference profile {profile}")
        winner = int(np.argmax(counts))
        intersection = int(counts[winner])
        destination = int(destinations[winner])
        size, destination_size = int(mask.sum()), int(np.sum(candidate == destination))
        rows.append({
            "profile": profile, "reference_n": size, "destination": destination,
            "destination_n": destination_size, "intersection_n": intersection,
            "retention": intersection / size, "precision": intersection / destination_size,
            "Jaccard": intersection / (size + destination_size - intersection),
            "within_pair_coassignment": float(np.sum(counts * (counts - 1)) / (size * (size - 1))) if size > 1 else 1.0,
        })
    return rows
