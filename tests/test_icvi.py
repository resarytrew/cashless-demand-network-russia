import networkx as nx
import numpy as np
import pytest
from sklearn.metrics import calinski_harabasz_score, silhouette_score

from sbernet.features import monthly_feature_matrix
from sbernet.icvi import (
    adjacency_block_matrix,
    evaluate_partition,
    evaluate_partition_v2,
    flat_metrics,
    flat_metrics_v2,
    weighted_graph_icvi,
)
from sbernet.metrics import weighted_modularity


def graph(n: int) -> nx.Graph:
    value = nx.path_graph(n)
    nx.set_edge_attributes(value, 1.0, "weight")
    return value


def test_matches_sklearn_and_is_label_permutation_invariant():
    x = np.array([[0., 0.], [.1, 0.], [5., 5.], [5.1, 5.]])
    labels = np.array([0, 0, 1, 1])
    base = evaluate_partition(x, labels, graph(4))
    renamed = evaluate_partition(x, np.array([9, 9, 4, 4]), graph(4))
    assert base == renamed
    assert base["CH"]["value"] == pytest.approx(calinski_harabasz_score(x, labels))
    assert base["SW"]["value"] == pytest.approx(silhouette_score(x, labels))
    assert base["MQ"]["value"] == pytest.approx(weighted_modularity(graph(4), labels))


def test_well_separated_partition_beats_mixed_partition():
    x = np.array([[0.0], [0.1], [0.2], [5.0], [5.1], [5.2]])
    good = evaluate_partition(x, np.array([0, 0, 0, 1, 1, 1]), graph(6))
    bad = evaluate_partition(x, np.array([0, 1, 0, 1, 0, 1]), graph(6))
    assert good["SW"]["value"] > bad["SW"]["value"]
    assert good["CH"]["value"] > bad["CH"]["value"]
    assert good["S_Dbw"]["value"] < bad["S_Dbw"]["value"]
    assert all(value["value"] is not None for value in good.values() if isinstance(value, dict))


def test_degenerate_partition_is_explicitly_undefined():
    result = evaluate_partition(np.array([[0.0], [1.0], [2.0]]), np.array([0, 0, 0]), graph(3))
    row = flat_metrics(result)
    assert result["SW"]["value"] is None
    assert result["CH"]["value"] is None
    assert row["status"] == "partially_undefined"


def test_reference_representation_retains_six_part_clr_block():
    rows = []
    for name, total, values in [("a", 100., [10., 15., 20., 25., 5.]), ("b", 150., [20., 20., 25., 30., 15.])]:
        rows.append({"mo": name, "category_15": "Total", "value": total})
        for category, value in zip(["f", "h", "c", "m", "t"], values):
            rows.append({"mo": name, "category_15": category, "value": value})
    # Duplicate rows to avoid the two-row robust-scale degeneracy in this unit test.
    month = __import__("pandas").DataFrame(rows + [{**row, "mo": row["mo"] + "2", "value": row["value"] * 1.1} for row in rows])
    args = dict(month_df=month, municipality_order=["a", "a2", "b", "b2"], total_category="Total",
                selected_categories=["f", "h", "c", "m", "t"], other_category="Other", structure_weight=.7, level_weight=.3)
    default, _ = monthly_feature_matrix(**args)
    assert default.shape == (4, 7)


def weighted_example() -> tuple[nx.Graph, np.ndarray]:
    value = nx.Graph()
    value.add_nodes_from(range(4))
    value.add_weighted_edges_from([(0, 1, 4.0), (2, 3, 2.0), (1, 2, 1.0)])
    return value, np.array([10, 10, 20, 20])


def test_weighted_block_sums_and_manual_avi_avu_anui():
    value, labels = weighted_example()
    block = adjacency_block_matrix(value, labels)
    assert block == pytest.approx(np.array([[8.0, 1.0], [1.0, 4.0]]))
    result = weighted_graph_icvi(value, labels)
    manual_avi = ((8.0 / 9.0) + (4.0 / 5.0)) / 2.0
    # For either ordered off-diagonal term: 1 / (1 + 1 - 1) = 1.
    manual_avu = (1.0 + 1.0) / 2.0
    assert result["AVI"]["value"] == pytest.approx(manual_avi)
    assert result["AVU"]["value"] == pytest.approx(manual_avu)
    assert result["ANUI"]["value"] == pytest.approx(
        1.0 / (manual_avu + 1.0 / manual_avi)
    )


def test_turbomq_perfect_separation_and_cross_edge_degradation():
    separated = nx.Graph()
    separated.add_nodes_from(range(6))
    separated.add_weighted_edges_from([(0, 1, 1.0), (2, 3, 2.0), (4, 5, 3.0)])
    labels = np.array([0, 0, 1, 1, 2, 2])
    perfect = weighted_graph_icvi(separated, labels)
    assert perfect["MQ"]["value"] == pytest.approx(3.0)
    connected = separated.copy()
    connected.add_weighted_edges_from([(1, 2, 0.5), (3, 4, 0.5)])
    degraded = weighted_graph_icvi(connected, labels)
    assert degraded["MQ"]["value"] < perfect["MQ"]["value"]


def test_q_matches_networkx_and_all_graph_metrics_ignore_label_names():
    value, labels = weighted_example()
    result = weighted_graph_icvi(value, labels)
    expected = nx.community.modularity(
        value, [{0, 1}, {2, 3}], weight="weight", resolution=1.0
    )
    assert result["Q"]["value"] == pytest.approx(expected)
    renamed = weighted_graph_icvi(value, np.array([7, 7, -3, -3]))
    for name in (
        "AVI", "AVU", "ANUI", "MQ", "Q", "AVI_unweighted", "AVU_unweighted"
    ):
        assert renamed[name]["value"] == pytest.approx(result[name]["value"])


def test_weighted_equals_unweighted_for_unit_weights_and_can_differ_otherwise():
    unit = graph(4)
    labels = np.array([0, 0, 1, 1])
    equal = weighted_graph_icvi(unit, labels)
    assert equal["AVI"]["value"] == pytest.approx(equal["AVI_unweighted"]["value"])
    assert equal["AVU"]["value"] == pytest.approx(equal["AVU_unweighted"]["value"])
    unequal = weighted_graph_icvi(*weighted_example())
    assert unequal["AVI"]["value"] != pytest.approx(unequal["AVI_unweighted"]["value"])


def test_invalid_weights_and_zero_weight_q_are_explicit():
    value = nx.Graph()
    value.add_nodes_from(range(2))
    value.add_edge(0, 1, weight=0.0)
    result = weighted_graph_icvi(value, np.array([0, 1]))
    assert result["Q"]["value"] is None
    assert result["Q"]["status"] == "undefined:zero_total_graph_weight"
    assert np.isfinite(result["MQ"]["value"])
    invalid = value.copy()
    invalid[0][1]["weight"] = np.nan
    with pytest.raises(ValueError, match="finite and non-negative"):
        weighted_graph_icvi(invalid, np.array([0, 1]))
    invalid[0][1]["weight"] = "1.0"
    with pytest.raises(ValueError, match="not coerced"):
        weighted_graph_icvi(invalid, np.array([0, 1]))


def test_v2_flattening_never_silently_emits_nan():
    value = graph(3)
    result = evaluate_partition_v2(
        np.array([[0.0], [1.0], [2.0]]), np.array([0, 0, 0]), value
    )
    row = flat_metrics_v2(result)
    assert row["SW"] is None
    assert row["status"] == "partially_undefined"
    for metric in ("AVI", "AVU", "ANUI", "MQ", "Q"):
        assert row[metric] is None or np.isfinite(row[metric])
