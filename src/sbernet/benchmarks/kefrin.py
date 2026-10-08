"""Clean-room KEFRiNc implementation from Shalileh & Mirkin (2022).

No upstream source code is imported or copied.  The implementation follows the
published alternating-minimisation equations, equal data-source weights, cosine
distance, and random-first/max-sum seed initialisation.
"""
from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
import numpy as np


@dataclass(frozen=True)
class KEFRiNResult:
    labels: np.ndarray
    objective: float
    iterations: int
    converged: bool
    seed_indices: tuple[int, ...]


def zscore_columns(values: np.ndarray) -> np.ndarray:
    """Paper option Z: column centring and population-standard-deviation scaling."""
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 2 or not np.isfinite(values).all():
        raise ValueError("feature matrix must be a finite two-dimensional array")
    scale = values.std(axis=0, ddof=0)
    if np.any(scale <= 0):
        raise ValueError("KEFRiN Z preprocessing requires nonconstant columns")
    return (values - values.mean(axis=0)) / scale


def weighted_modularity_residual(graph: nx.Graph, n_nodes: int) -> np.ndarray:
    """Paper option M: P_ij <- P_ij - P_i+ P_+j / P_++."""
    if graph.is_directed():
        raise ValueError("Round22 requires the undirected reference graph")
    expected_nodes = list(range(n_nodes))
    if list(sorted(graph.nodes())) != expected_nodes:
        raise ValueError("graph nodes must be consecutive integers in feature-row order")
    adjacency = nx.to_numpy_array(
        graph, nodelist=expected_nodes, weight="weight", dtype=np.float64
    )
    if not np.isfinite(adjacency).all() or np.any(adjacency < 0):
        raise ValueError("reference adjacency must contain finite nonnegative weights")
    row_sum = adjacency.sum(axis=1)
    total = float(row_sum.sum())
    if total <= 0:
        raise ValueError("reference graph must have positive total weight")
    return adjacency - np.outer(row_sum, row_sum) / total


def cosine_distances(values: np.ndarray, centers: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    centers = np.asarray(centers, dtype=np.float64)
    value_norm = np.linalg.norm(values, axis=1)
    center_norm = np.linalg.norm(centers, axis=1)
    if np.any(value_norm <= 0) or np.any(center_norm <= 0):
        raise ValueError("cosine KEFRiN requires nonzero node and center vectors")
    similarity = (values @ centers.T) / np.outer(value_norm, center_norm)
    return 1.0 - np.clip(similarity, -1.0, 1.0)


def _combined_distance(
    features: np.ndarray,
    network: np.ndarray,
    feature_centers: np.ndarray,
    network_centers: np.ndarray,
    rho: float,
    xi: float,
) -> np.ndarray:
    return rho * cosine_distances(features, feature_centers) + xi * cosine_distances(
        network, network_centers
    )


def seed_indices_max_sum(
    features: np.ndarray,
    network: np.ndarray,
    k_clusters: int,
    seed: int,
    rho: float = 1.0,
    xi: float = 1.0,
) -> tuple[int, ...]:
    """Paper seed rule: random first node, then maximum summed distance to seeds."""
    n = len(features)
    if not 1 < k_clusters <= n:
        raise ValueError("k_clusters must be between 2 and N")
    rng = np.random.default_rng(seed)
    selected = [int(rng.integers(0, n))]
    while len(selected) < k_clusters:
        distance = _combined_distance(
            features,
            network,
            features[selected],
            network[selected],
            rho,
            xi,
        ).sum(axis=1)
        distance[np.asarray(selected, dtype=int)] = -np.inf
        selected.append(int(np.argmax(distance)))
    return tuple(selected)


def fit_kefrinc(
    features: np.ndarray,
    network: np.ndarray,
    *,
    k_clusters: int,
    seed: int,
    rho: float = 1.0,
    xi: float = 1.0,
    max_iterations: int = 1000,
) -> KEFRiNResult:
    """Fit one KEFRiNc initialisation; empty clusters and cap hits fail explicitly."""
    features = np.asarray(features, dtype=np.float64)
    network = np.asarray(network, dtype=np.float64)
    if features.ndim != 2 or network.ndim != 2 or len(features) != len(network):
        raise ValueError("feature and network matrices must be 2D with the same N")
    if not np.isfinite(features).all() or not np.isfinite(network).all():
        raise ValueError("KEFRiN inputs must be finite")
    if rho <= 0 or xi <= 0:
        raise ValueError("rho and xi must be positive")
    seeds = seed_indices_max_sum(features, network, k_clusters, seed, rho, xi)
    feature_centers = features[list(seeds)].copy()
    network_centers = network[list(seeds)].copy()
    previous: np.ndarray | None = None
    for iteration in range(1, max_iterations + 1):
        distances = _combined_distance(
            features, network, feature_centers, network_centers, rho, xi
        )
        labels = np.argmin(distances, axis=1).astype(np.int64)
        counts = np.bincount(labels, minlength=k_clusters)
        if np.any(counts == 0):
            raise RuntimeError(
                f"KEFRiN returned an empty cluster at iteration {iteration}: {counts.tolist()}"
            )
        if previous is not None and np.array_equal(labels, previous):
            objective = float(distances[np.arange(len(labels)), labels].sum())
            return KEFRiNResult(labels, objective, iteration, True, seeds)
        previous = labels.copy()
        feature_centers = np.vstack([features[labels == k].mean(axis=0) for k in range(k_clusters)])
        network_centers = np.vstack([network[labels == k].mean(axis=0) for k in range(k_clusters)])
    raise RuntimeError(f"KEFRiN did not converge within {max_iterations} iterations")

