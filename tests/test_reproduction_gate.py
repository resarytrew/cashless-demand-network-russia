import networkx as nx

from sbernet.clustering import louvain_labels
from sbernet.config import load_config
from sbernet.robustness.reproduction_gate import (
    baseline_passed, graph_fingerprint, similarity,
)
from sbernet.robustness.pilot_gate import identical_igraph


def test_graph_checksum_ignores_insertion_order_but_detects_changes():
    graph = nx.Graph()
    graph.add_nodes_from(range(4))
    graph.add_weighted_edges_from([(0, 1, 0.5), (1, 2, 0.75)])
    other = nx.Graph()
    other.add_nodes_from(reversed(range(4)))
    other.add_weighted_edges_from([(2, 1, 0.75), (1, 0, 0.5)])
    assert graph_fingerprint(graph) == graph_fingerprint(other)
    other[0][1]['weight'] += 1e-15
    assert graph_fingerprint(graph) != graph_fingerprint(other)
    other[0][1]['weight'] = 0.5
    other.remove_node(3)
    assert graph_fingerprint(graph) != graph_fingerprint(other)


def test_gate_accepts_relabeling_but_rejects_nonexact_partition():
    exact = similarity([0, 0, 1, 1], [3, 3, 2, 2])
    assert baseline_passed({'full': exact})
    assert not baseline_passed({'full': exact, 'dec': similarity([0, 0, 1, 1], [0, 1, 1, 1])})
    assert not baseline_passed({'full': {'ARI': 1.0 - 1e-15, 'NMI': 1.0}})


def test_louvain_seed_is_deterministic():
    graph = nx.karate_club_graph()
    assert (louvain_labels(graph, 0.5, 0) == louvain_labels(graph, 0.5, 0)).all()


def test_igraph_conversion_preserves_weights_and_isolates():
    graph = nx.Graph()
    graph.add_nodes_from(range(5))
    graph.add_weighted_edges_from([(0, 2, 0.123456789012345), (3, 1, 0.8)])
    converted, report = identical_igraph(graph)
    assert report['passed']
    assert converted.vcount() == 5
    assert converted.ecount() == 2
    assert report['source'] == report['igraph_input']


def test_highrep_config_preserves_reference_and_declares_canonical_procedure():
    baseline = load_config('configs/baseline.yaml')
    highrep = load_config('configs/perturbation_highrep.yaml')
    assert baseline['robustness']['perturbation_runs_target'] == 30
    assert highrep['robustness']['n_repetitions'] == 50
    assert highrep['robustness']['seeds'] == list(range(50))
    assert highrep['robustness']['pilot_seeds'] == list(range(5))
    for key in ['features', 'network', 'temporal', 'clustering', 'panel']:
        assert highrep[key] == baseline[key]
    assert highrep['robustness']['perturbation']['rng_base_seed'] == 20260918
