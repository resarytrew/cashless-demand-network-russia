import networkx as nx
import numpy as np
import pytest
from sklearn.metrics import calinski_harabasz_score, silhouette_score

from sbernet.features import monthly_feature_matrix
from sbernet.icvi import evaluate_partition, flat_metrics
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
