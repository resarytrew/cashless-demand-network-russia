from __future__ import annotations

import networkx as nx
import numpy as np


def build_supra_graph(monthly_graphs: list[nx.Graph], n_nodes: int, omega: float) -> nx.Graph:
    supra = nx.Graph()
    supra.add_nodes_from(range(len(monthly_graphs) * n_nodes))
    intralayer_weights: list[float] = []

    for t, graph in enumerate(monthly_graphs):
        offset = t * n_nodes
        for u, v, data in graph.edges(data=True):
            weight = float(data["weight"])
            intralayer_weights.append(weight)
            supra.add_edge(offset + u, offset + v, weight=weight, kind="intralayer")

    if not intralayer_weights:
        raise ValueError("No intralayer edges found.")

    reference_weight = float(np.median(intralayer_weights))
    temporal_weight = omega * reference_weight

    for t in range(len(monthly_graphs) - 1):
        left = t * n_nodes
        right = (t + 1) * n_nodes
        for node in range(n_nodes):
            supra.add_edge(left + node, right + node, weight=temporal_weight, kind="temporal")

    supra.graph["temporal_weight"] = temporal_weight
    supra.graph["reference_intralayer_weight"] = reference_weight
    return supra
