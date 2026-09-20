import itertools
import numpy as np
from scipy.spatial.distance import squareform, pdist

from sbernet.robustness.spatial_block import exact_matched_mean_distance


def test_exact_matched_mean_distance_matches_enumeration():
    x = np.array([[0.0], [1.0], [3.0], [10.0], [12.0]])
    d = squareform(pdist(x))
    strata = np.array(["a", "a", "a", "b", "b"], dtype=object)
    # draw 2 of a and 1 of b
    sample_mask = np.array([True, True, False, True, False])
    expected = exact_matched_mean_distance(d, strata, sample_mask)

    values = []
    for a_pick in itertools.combinations([0, 1, 2], 2):
        for b_pick in itertools.combinations([3, 4], 1):
            idx = np.array(a_pick + b_pick)
            values.append(d[np.ix_(idx, idx)][np.triu_indices(3, 1)].mean())

    assert np.isclose(expected, np.mean(values))
