import numpy as np

from sbernet.synthetic_temporal import SyntheticPanel, generate_panel, score


def test_generator_is_deterministic_by_seed():
    first = generate_panel("mixed", 7, n_nodes=40, months=8, communities=4)
    second = generate_panel("mixed", 7, n_nodes=40, months=8, communities=4)
    assert np.array_equal(first.features, second.features)
    assert np.array_equal(first.truth, second.truth)


def test_abrupt_truth_switches_are_declared_at_change_month():
    panel = generate_panel("abrupt", 0, n_nodes=40, months=8, communities=4, switching_fraction=.25)
    changed = np.flatnonzero(panel.change_month >= 0)
    assert len(changed) == 10
    assert np.all(panel.truth[panel.change_month[changed] - 1, changed] != panel.truth[panel.change_month[changed], changed])


def test_temporary_shock_does_not_modify_latent_truth():
    panel = generate_panel("shock", 2, n_nodes=40, months=8, communities=4)
    assert (panel.change_month == -1).all()
    assert np.all(panel.truth == panel.truth[0])


def test_toy_perfect_labels_have_perfect_partition_and_events():
    truth = np.array([[0, 1], [0, 1], [1, 1]])
    panel = SyntheticPanel(np.zeros((3, 2, 6)), truth, np.array([2, -1]), "toy")
    metrics = score(panel, truth.copy())
    assert metrics["ari"] == 1
    assert metrics["switch_f1"] == 1
