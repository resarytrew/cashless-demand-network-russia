from __future__ import annotations

import networkx as nx
import numpy as np
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score, silhouette_score


def partition_similarity(a: np.ndarray, b: np.ndarray) -> dict[str, float]:
    return {
        "ari": float(adjusted_rand_score(a, b)),
        "nmi": float(normalized_mutual_info_score(a, b)),
    }


def feature_silhouette(x: np.ndarray, labels: np.ndarray) -> float:
    return float(silhouette_score(x, labels))


def weighted_modularity(graph: nx.Graph, labels: np.ndarray) -> float:
    communities = [set(np.where(labels == c)[0].tolist()) for c in np.unique(labels)]
    return float(nx.community.modularity(graph, communities, weight="weight"))
