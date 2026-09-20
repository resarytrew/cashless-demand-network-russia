import numpy as np

from sbernet.robustness.region_null import expected_mean_distance_stratified


def test_exact_stratified_null_mean_simple_case():
    # Four points, two strata. Sampling one point from each stratum means
    # the expected pair distance is the mean of the four cross-stratum distances.
    d = np.array(
        [
            [0.0, 1.0, 2.0, 4.0],
            [1.0, 0.0, 3.0, 5.0],
            [2.0, 3.0, 0.0, 1.0],
            [4.0, 5.0, 1.0, 0.0],
        ]
    )
    strata = np.array(["a", "a", "b", "b"])
    sample = np.array([0, 2])
    expected = (2.0 + 4.0 + 3.0 + 5.0) / 4.0
    got = expected_mean_distance_stratified(d, strata, sample)
    assert np.isclose(got, expected)
