"""Non-reference graph builders used only by explicit edge-rule sensitivity runs."""
from __future__ import annotations

import math

import networkx as nx
import numpy as np
from sklearn.neighbors import NearestNeighbors


def knn_graph(x: np.ndarray, k: int, isolate_fallback: bool, mutual: bool) -> nx.Graph:
    """Build a reciprocal or union kNN graph without losing one-sided edges."""
    if k >= len(x):
        raise ValueError("k must be smaller than number of observations.")
    distances, indices = NearestNeighbors(n_neighbors=k + 1).fit(x).kneighbors(x)
    neighbors, neighbour_distances = indices[:, 1:], distances[:, 1:]
    sigma = neighbour_distances[:, -1]
    neighbour_sets = [set(map(int, row)) for row in neighbors]
    graph = nx.Graph()
    graph.add_nodes_from(range(len(x)))
    for i in range(len(x)):
        for raw_j in neighbors[i]:
            j = int(raw_j)
            if mutual:
                if j <= i or i not in neighbour_sets[j]:
                    continue
            elif graph.has_edge(i, j):
                continue
            distance = float(np.linalg.norm(x[i] - x[j]))
            weight = math.exp(-(distance * distance) / (float(sigma[i] * sigma[j]) + 1e-12))
            graph.add_edge(i, j, weight=weight, distance=distance)
    if isolate_fallback:
        for i in list(nx.isolates(graph)):
            j = int(neighbors[i, 0])
            distance = float(np.linalg.norm(x[i] - x[j]))
            weight = math.exp(-(distance * distance) / (float(sigma[i] * sigma[j]) + 1e-12))
            graph.add_edge(i, j, weight=weight, distance=distance, fallback=True)
    return graph
