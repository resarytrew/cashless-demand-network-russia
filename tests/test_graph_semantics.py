import networkx as nx
import numpy as np
import pytest
from scipy.spatial.distance import pdist, squareform

from sbernet.graph_semantics import (
    dynamics_graph, epsilon_graph, graph_diagnostics, mean_delta_correlation, profile_overlap,
)


def test_epsilon_closed_threshold_includes_ties_and_no_fallback():
    x = np.array([[0.0], [1.0], [2.0], [20.0]])
    graph, calibration = epsilon_graph(x, target_edges=1, k=1, denominator_epsilon=1e-12)
    assert calibration["epsilon"] == 1
    assert calibration["actual_edges"] == 2
    assert calibration["excess_due_to_ties"] == 1
    assert set(graph.edges) == {(0, 1), (1, 2)}
    assert list(nx.isolates(graph)) == [3]
    assert all("fallback" not in data for _, _, data in graph.edges(data=True))


def test_epsilon_exact_budget_and_determinism():
    x = np.random.default_rng(20).normal(size=(25, 4))
    graph, calibration = epsilon_graph(x, 40, 3, 1e-12)
    replay, second = epsilon_graph(x, 40, 3, 1e-12)
    distances = squareform(pdist(x))
    assert calibration == second
    assert calibration["actual_edges"] == 40
    assert nx.utils.graphs_equal(graph, replay)
    for i in range(len(x)):
        for j in range(i + 1, len(x)):
            assert graph.has_edge(i, j) == (distances[i, j] <= calibration["epsilon"])


def test_component_correlations_match_direct_pearson_and_ignore_offsets():
    values = np.random.default_rng(1).normal(size=(24, 8, 6))
    similarity = mean_delta_correlation(values, 1e-12)
    delta = np.diff(values, axis=0)
    expected = np.mean([np.corrcoef(delta[:, :, p].T) for p in range(6)], axis=0)
    np.testing.assert_allclose(similarity, expected, atol=1e-14)
    shifted = values * np.arange(1, 7)[None, None, :] + np.arange(8)[None, :, None]
    np.testing.assert_allclose(similarity, mean_delta_correlation(shifted, 1e-12), atol=1e-14)


def test_constant_difference_fails_instead_of_silent_imputation():
    values = np.random.default_rng(1).normal(size=(24, 8, 6))
    values[:, 2, 4] = np.arange(24)
    with pytest.raises(ValueError, match="constant difference"):
        mean_delta_correlation(values, 1e-12)


def test_dynamics_ties_explicitly_exclude_self_and_negative_weights():
    similarity = np.full((4, 4), -0.5)
    np.fill_diagonal(similarity, 1)
    graph = dynamics_graph(similarity, 1, 1e-12)
    assert set(graph.edges) == {(0, 1)}
    assert list(nx.isolates(graph)) == [2, 3]
    assert graph[0][1]["weight"] > 0
    assert graph[0][1]["similarity"] == -0.5
    assert nx.utils.graphs_equal(graph, dynamics_graph(similarity, 1, 1e-12))


def test_output_schemas_and_retention_does_not_hide_mergers():
    overlap = profile_overlap([1, 1, 2, 2], [0, 0, 0, 0], {"A": 1})[0]
    assert overlap["retention"] == 1
    assert overlap["precision"] == 0.5
    assert overlap["Jaccard"] == 0.5
    graph = nx.path_graph(4)
    nx.set_edge_attributes(graph, 1, "weight")
    stats = graph_diagnostics(graph, graph)
    assert stats["reference_edge_jaccard"] == 1
    assert {"components", "isolates", "degree_max", "total_edge_weight"} <= stats.keys()
