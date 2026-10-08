import networkx as nx
import numpy as np

from sbernet.benchmarks.kefrin import (
    fit_kefrinc,
    weighted_modularity_residual,
    zscore_columns,
)
from sbernet.kefrin_benchmark import comparison_metrics


def toy_inputs():
    rng = np.random.default_rng(4)
    features = np.vstack([
        rng.normal([-3, 0], .15, size=(12, 2)),
        rng.normal([0, 3], .15, size=(12, 2)),
        rng.normal([3, 0], .15, size=(12, 2)),
    ])
    graph = nx.Graph()
    graph.add_nodes_from(range(len(features)))
    for start in (0, 12, 24):
        for i in range(start, start + 12):
            for j in range(i + 1, start + 12):
                graph.add_edge(i, j, weight=1.0)
    return zscore_columns(features), weighted_modularity_residual(graph, len(features))


def test_clean_room_kefrinc_is_deterministic_and_returns_exact_k():
    features, network = toy_inputs()
    first = fit_kefrinc(features, network, k_clusters=3, seed=0)
    second = fit_kefrinc(features, network, k_clusters=3, seed=0)
    assert first.converged and first.objective >= 0
    assert np.array_equal(first.labels, second.labels)
    assert np.unique(first.labels).size == 3
    assert np.isfinite(first.labels).all()


def test_modularity_residual_has_zero_row_sums():
    _, network = toy_inputs()
    assert np.allclose(network.sum(axis=1), 0, atol=1e-12)


def test_comparison_is_label_permutation_invariant():
    reference = np.array([0, 0, 1, 1, 2, 2])
    candidate = np.array([9, 9, 4, 4, 7, 7])
    result = comparison_metrics(reference, candidate)
    assert result["ARI"] == result["NMI"] == 1
    assert result["hungarian_aligned_accuracy"] == 1


def test_input_validation_rejects_constant_feature_and_bad_graph_order():
    with np.testing.assert_raises(ValueError):
        zscore_columns(np.ones((4, 2)))
    graph = nx.Graph()
    graph.add_edge(1, 2, weight=1.0)
    with np.testing.assert_raises(ValueError):
        weighted_modularity_residual(graph, 2)
