import networkx as nx
import numpy as np

from sbernet.graph import knn_graph


def test_union_knn_keeps_one_sided_nominations_and_contains_mutual_edges():
    # For k=1, 0 nominates 1 and 3 nominates 2, but neither nomination is
    # reciprocal.  A union graph must retain both directed nominations.
    values = np.array([[0.0], [1.1], [2.0], [10.0]])
    mutual = knn_graph(values, k=1, isolate_fallback=False, mutual=True)
    union = knn_graph(values, k=1, isolate_fallback=False, mutual=False)
    assert set(mutual.edges).issubset(set(union.edges))
    assert union.has_edge(0, 1)
    assert union.has_edge(2, 3)
    assert nx.is_empty(mutual) is False
