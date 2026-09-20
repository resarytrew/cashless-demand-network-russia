import leidenalg
import networkx as nx
import numpy as np

from sbernet.robustness.pilot_gate import identical_igraph
from sbernet.robustness.experiment_common import validity_metrics


def test_leiden_fixed_seed_is_deterministic_on_identical_graph():
    graph = nx.karate_club_graph()
    converted, checks = identical_igraph(graph)
    kwargs = {'weights': 'weight', 'resolution_parameter': 0.5, 'seed': 0, 'n_iterations': -1}
    first = leidenalg.find_partition(converted, leidenalg.RBConfigurationVertexPartition, **kwargs)
    second = leidenalg.find_partition(converted, leidenalg.RBConfigurationVertexPartition, **kwargs)
    assert first.membership == second.membership
    assert checks['passed']


def test_network_indices_count_internal_edges_twice():
    graph = nx.Graph()
    graph.add_weighted_edges_from([(0, 1, 1.0), (0, 2, 1.0), (1, 2, 1.0),
                                   (3, 4, 1.0), (3, 5, 1.0), (4, 5, 1.0), (2, 3, 1.0)])
    result = validity_metrics(graph, np.array([0, 0, 0, 1, 1, 1]))
    assert np.isclose(result['AVI'], 6 / 7)
    assert result['AVU'] == 1.0
    assert np.isclose(result['MQ'], 6 / 7 - 0.5)
