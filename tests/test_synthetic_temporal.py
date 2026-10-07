import numpy as np
import pandas as pd
import pytest
from pathlib import Path
from sklearn.metrics import adjusted_rand_score

from scripts.run_synthetic_temporal_benchmark import build_tradeoff_summary
from sbernet.synthetic_temporal import (
    SyntheticPanel,
    generate_panel,
    monthly_partition_metrics,
    score,
)


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


def test_mixed_roles_are_disjoint_and_only_switch_nodes_change_truth():
    panel = generate_panel("mixed", 3, n_nodes=40, months=8, communities=4)
    assert panel.roles is not None
    roles = panel.roles
    sets = [set(roles[name]) for name in ("switch_nodes", "boundary_nodes", "shock_nodes", "stable_nodes")]
    assert sum(map(len, sets)) == 40
    assert not any(left.intersection(right) for index, left in enumerate(sets) for right in sets[index + 1:])
    changed = set(np.flatnonzero(panel.change_month >= 0))
    assert changed == set(roles["switch_nodes"])
    assert not np.any(panel.truth[:, roles["boundary_nodes"]] != panel.truth[0, roles["boundary_nodes"]])
    assert not np.any(panel.truth[:, roles["shock_nodes"]] != panel.truth[0, roles["shock_nodes"]])


def test_toy_perfect_labels_have_perfect_partition_and_events():
    truth = np.array([[0, 1], [0, 1], [1, 1]])
    panel = SyntheticPanel(np.zeros((3, 2, 6)), truth, np.array([2, -1]), "toy")
    metrics = score(panel, truth.copy())
    assert metrics["monthly_ari_mean"] == 1
    assert metrics["monthly_nmi_mean"] == 1
    assert metrics["switch_f1"] == 1


def test_independent_monthly_label_permutation_preserves_monthly_scores_not_legacy_flattened():
    truth = np.array([[0, 0, 1, 1], [0, 0, 1, 1]])
    original = truth.copy()
    independently_permuted = np.array([[0, 0, 1, 1], [1, 1, 0, 0]])

    before = monthly_partition_metrics(truth, original)
    after = monthly_partition_metrics(truth, independently_permuted)
    assert np.array_equal(before["monthly_ari"], after["monthly_ari"])
    assert np.array_equal(before["monthly_nmi"], after["monthly_nmi"])
    assert after["monthly_ari"].mean() == 1
    assert after["monthly_nmi"].mean() == 1
    assert adjusted_rand_score(truth.ravel(), original.ravel()) != adjusted_rand_score(
        truth.ravel(), independently_permuted.ravel()
    )


def test_transition_metrics_have_known_confusion_counts():
    truth = np.array(
        [[0, 0, 0, 1, 1, 1], [1, 0, 0, 1, 1, 1], [1, 1, 0, 1, 1, 1]]
    )
    inferred = np.array(
        [[0, 0, 0, 1, 1, 1], [1, 0, 1, 1, 1, 1], [1, 1, 0, 1, 1, 1]]
    )
    panel = SyntheticPanel(
        np.zeros((3, 6, 6)), truth, np.array([1, 2, -1, -1, -1, -1]), "toy"
    )
    metrics = score(panel, inferred)
    assert metrics["false_switches"] == 2
    assert metrics["missed_switches"] == 0
    assert metrics["switch_precision"] == pytest.approx(0.5)
    assert metrics["switch_recall"] == pytest.approx(1.0)
    assert metrics["switch_f1"] == pytest.approx(2 / 3)


def test_no_transition_has_no_fake_delay_and_stability_utility_is_defined():
    truth = np.array([[0, 0, 1, 1], [0, 0, 1, 1]])
    panel = SyntheticPanel(np.zeros((2, 4, 6)), truth, np.full(4, -1), "stable")
    metrics = score(panel, truth.copy())
    assert np.isnan(metrics["absolute_change_point_delay"])
    assert metrics["false_switch_rate"] == 0

    wide = pd.DataFrame(
        {
            "scenario": ["stable", "stable"],
            "omega": [0.0, 1.0],
            "monthly_ari_mean": [0.8, 0.9],
            "false_switch_rate": [0.1, 0.0],
            "switch_f1": [np.nan, np.nan],
            "absolute_change_point_delay": [np.nan, np.nan],
        }
    )
    result = build_tradeoff_summary(wide)
    assert result["stability_tradeoff_utility"].notna().all()
    assert result["transition_tradeoff_utility"].isna().all()


def test_transition_utility_requires_all_four_fixed_components():
    wide = pd.DataFrame(
        {
            "scenario": ["abrupt", "abrupt"],
            "omega": [0.0, 1.0],
            "monthly_ari_mean": [0.8, 0.9],
            "switch_f1": [0.9, 0.7],
            "false_switch_rate": [0.2, 0.1],
            "absolute_change_point_delay": [0.0, 1.0],
        }
    )
    result = build_tradeoff_summary(wide)
    component_columns = {
        "normalised_monthly_ari_mean",
        "normalised_switch_f1",
        "normalised_false_switch_rate",
        "normalised_absolute_change_point_delay",
    }
    assert component_columns.issubset(result.columns)
    expected = result[list(component_columns)].mean(axis=1)
    assert np.allclose(result["transition_tradeoff_utility"], expected)

    wide.loc[0, "absolute_change_point_delay"] = np.nan
    with pytest.raises(ValueError, match="Utility component is undefined"):
        build_tradeoff_summary(wide)


def test_v4_artifact_schemas():
    root = Path("outputs/final_competition_upgrade/synthetic_temporal_v4")
    seed_metrics = pd.read_csv(root / "seed_metrics.csv", nrows=1)
    assert {
        "monthly_ari_mean",
        "monthly_ari_std",
        "monthly_ari_min",
        "monthly_ari_median",
        "monthly_nmi_mean",
        "monthly_nmi_std",
        "monthly_nmi_min",
        "monthly_nmi_median",
        "legacy_flattened_ari",
        "legacy_flattened_nmi",
    }.issubset(seed_metrics.columns)
    monthly = pd.read_csv(root / "monthly_partition_metrics.csv", nrows=1)
    assert list(monthly.columns) == [
        "scenario",
        "seed",
        "omega",
        "month",
        "monthly_ari",
        "monthly_nmi",
    ]
    tradeoff = pd.read_csv(root / "tradeoff_summary.csv", nrows=1)
    assert {
        "transition_tradeoff_utility",
        "stability_tradeoff_utility",
        "pareto_efficient",
    }.issubset(tradeoff.columns)
