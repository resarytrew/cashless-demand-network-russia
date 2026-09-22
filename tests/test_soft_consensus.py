import numpy as np

from sbernet.robustness.soft_consensus import (
    balanced_consensus,
    classify_f_transition,
    coassignment_matrix,
    normalized_entropy,
    profile_affinities,
)


def test_coassignment_is_invariant_to_label_permutation():
    a = np.array([1, 1, 2, 2, 3])
    b = np.array([9, 9, 4, 4, 7])
    assert np.array_equal(coassignment_matrix([a]), coassignment_matrix([b]))


def test_balanced_consensus_weights_families_not_run_counts():
    all_same = coassignment_matrix([np.array([0, 0, 0])])
    all_separate = coassignment_matrix([np.array([0, 1, 2])])
    families = {
        "perturbation": all_same,
        "alpha": all_separate,
        "gamma": all_separate,
        "algorithm": all_separate,
    }
    out = balanced_consensus(families)
    assert np.isclose(out[0, 1], 0.25)
    assert np.allclose(np.diag(out), 1.0)


def test_profile_affinity_is_size_normalized_and_excludes_self_pair():
    consensus = np.array(
        [
            [1.0, 1.0, 0.2, 0.2],
            [1.0, 1.0, 0.2, 0.2],
            [0.2, 0.2, 1.0, 1.0],
            [0.2, 0.2, 1.0, 1.0],
        ],
        dtype=float,
    )
    names, raw, weights = profile_affinities(
        consensus, np.array([1, 1, 2, 2]), {"A": 1, "B": 2}
    )
    assert names == ["A", "B"]
    assert np.isclose(raw[0, 0], 1.0)
    assert np.isclose(raw[0, 1], 0.2)
    assert np.isclose(weights[0].sum(), 1.0)


def test_entropy_limits():
    certain = normalized_entropy(np.array([[1.0, 0.0, 0.0]]))[0]
    uniform = normalized_entropy(np.array([[1 / 3, 1 / 3, 1 / 3]]))[0]
    assert np.isclose(certain, 0.0)
    assert np.isclose(uniform, 1.0)


def test_f_transition_requires_three_of_four_family_votes():
    left = np.array([4, 3, 2, 1, 0])
    right = np.array([0, 1, 2, 3, 4])
    assert classify_f_transition(left, right).tolist() == [
        "F→D",
        "F→D",
        "F-middle",
        "F→G",
        "F→G",
    ]
