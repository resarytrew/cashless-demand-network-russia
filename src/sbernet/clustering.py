from __future__ import annotations

import networkx as nx
import numpy as np


def louvain_labels(graph: nx.Graph, resolution: float, seed: int) -> np.ndarray:
    communities = nx.community.louvain_communities(
        graph,
        weight="weight",
        resolution=resolution,
        seed=seed,
    )
    labels = np.empty(graph.number_of_nodes(), dtype=int)
    for community_id, nodes in enumerate(communities):
        labels[list(nodes)] = community_id
    return labels
