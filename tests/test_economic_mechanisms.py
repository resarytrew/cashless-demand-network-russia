import numpy as np

from sbernet.economic_mechanisms import (
    aitchison_rows,
    composition_change_volatility,
    greedy_unique_pairs,
    haversine_km,
    holm_adjust,
)


def test_holm_adjust_is_monotone_in_rank_and_restores_order():
    result = holm_adjust([0.04, 0.01, 0.03])
    assert np.allclose(result, [0.06, 0.03, 0.06])


def test_composition_volatility_is_zero_for_constant_clr_change():
    base = np.array([0.2, 0.3, 0.5])
    composition = np.stack([base, base, base, base])[None, :, :]
    assert np.allclose(composition_change_volatility(composition), 0)
    assert np.allclose(aitchison_rows(composition[:, 0], composition[:, -1]), 0)


def test_greedy_pairing_prefers_mutual_and_never_reuses_nodes():
    x = np.array([[0.0], [0.1], [1.0], [1.2]])
    eligible = np.ones((4, 4), dtype=bool)
    np.fill_diagonal(eligible, False)
    pairs = greedy_unique_pairs(x, eligible, caliper=0.5)
    assert {(i, j) for i, j, _, _ in pairs} == {(0, 1), (2, 3)}
    assert all(mutual for _, _, _, mutual in pairs)


def test_haversine_known_equator_distance():
    distance = haversine_km(0.0, 0.0, 1.0, 0.0)
    assert np.isclose(float(distance), 111.195, atol=0.01)
