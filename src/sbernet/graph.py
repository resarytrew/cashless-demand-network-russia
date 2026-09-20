from __future__ import annotations

import math

import networkx as nx
import numpy as np
from sklearn.neighbors import NearestNeighbors


def mutual_knn_graph(x: np.ndarray, k: int, isolate_fallback: bool) -> nx.Graph:
    if k >= len(x):
        raise ValueError("k must be smaller than number of observations.")

    nn = NearestNeighbors(n_neighbors=k + 1).fit(x)
    distances, indices = nn.kneighbors(x)

    neighbors = indices[:, 1:]
    neighbor_distances = distances[:, 1:]
    sigma = neighbor_distances[:, -1]
    neighbor_sets = [set(map(int, row)) for row in neighbors]

    graph = nx.Graph()
    graph.add_nodes_from(range(len(x)))

    for i in range(len(x)):
        for j_raw in neighbors[i]:
            j = int(j_raw)
            if j <= i or i not in neighbor_sets[j]:
                continue
            d = float(np.linalg.norm(x[i] - x[j]))
            denom = float(sigma[i] * sigma[j]) + 1e-12
            weight = math.exp(-(d * d) / denom)
            graph.add_edge(i, j, weight=weight, distance=d)

    if isolate_fallback:
        for i in list(nx.isolates(graph)):
            j = int(neighbors[i, 0])
            d = float(np.linalg.norm(x[i] - x[j]))
            denom = float(sigma[i] * sigma[j]) + 1e-12
            weight = math.exp(-(d * d) / denom)
            graph.add_edge(i, j, weight=weight, distance=d, fallback=True)

    return graph
