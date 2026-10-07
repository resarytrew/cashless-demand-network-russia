import numpy as np
import pandas as pd
import pytest

from sbernet.targeted_checks import (
    benjamini_hochberg,
    distance_contribution_table,
    optimal_label_alignment,
    residual_profile_test,
)


def test_distance_contributions_sum_to_one_for_pairs_and_edges():
    blocks = {
        "Demand": np.array([[0.0], [1.0], [3.0]]),
        "Wage": np.array([[0.0], [2.0], [2.0]]),
    }
    all_pairs = distance_contribution_table(blocks, scope="all")
    edges = distance_contribution_table(
        blocks, scope="edges", pairs=np.array([[0, 1], [1, 2]])
    )
    assert all_pairs.mean_share.sum() == pytest.approx(1.0)
    assert edges.mean_share.sum() == pytest.approx(1.0)
    assert set(all_pairs.block) == {"Demand", "Wage"}


def test_optimal_alignment_reports_actual_changed_share():
    reference = np.array([0, 0, 1, 1, 2])
    candidate = np.array([9, 9, 4, 4, 8])
    aligned, mapping, share = optimal_label_alignment(reference, candidate)
    assert share == 1.0
    assert aligned.tolist() == reference.tolist()
    assert mapping == {9: 0, 4: 1, 8: 2}


def test_benjamini_hochberg_is_monotone_in_rank():
    raw = np.array([0.04, 0.001, 0.02])
    adjusted = benjamini_hochberg(raw)
    order = np.argsort(raw)
    assert np.all(np.diff(adjusted[order]) >= 0)
    assert np.all(adjusted >= raw)


def test_residual_profile_test_detects_added_profile_signal():
    rng = np.random.default_rng(5)
    n = 180
    population = np.exp(rng.normal(10, 0.6, n))
    region = np.repeat(["r1", "r2", "r3"], n // 3)
    profile = np.tile(np.repeat(["A", "B", "C"], 20), 3)
    profile_effect = pd.Series(profile).map({"A": -0.3, "B": 0.0, "C": 0.3}).to_numpy()
    wage = np.exp(2.0 + 0.4 * np.log(population) + profile_effect + rng.normal(0, 0.05, n))
    frame = pd.DataFrame({"wage": wage, "population": population, "region": region, "profile": profile})
    residuals, diagnostics, summary, pairs = residual_profile_test(
        frame, outcome="wage", population="population", region="region", profile="profile",
        permutation_reps=99, seed=4,
    )
    assert len(residuals) == n
    assert diagnostics["partial_R2_profile"] > 0.8
    assert diagnostics["Freedman_Lane_within_region_p"] <= 0.02
    assert len(summary) == 3 and len(pairs) == 3
