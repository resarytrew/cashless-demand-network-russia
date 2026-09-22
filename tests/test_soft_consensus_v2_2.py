import numpy as np

from sbernet.robustness.soft_consensus_v2_2 import (
    affinities_to_members,
    balanced_consensus_subset,
    select_consensus_core_anchors,
    transition_direction,
)


def test_subset_consensus_equal_weights_only_included_families():
    same = np.ones((3, 3), dtype=np.float32)
    separate = np.eye(3, dtype=np.float32)
    matrices = {
        "perturbation": same,
        "alpha": separate,
        "gamma": separate,
        "algorithm": separate,
    }
    out = balanced_consensus_subset(matrices, ["perturbation", "alpha"])
    assert np.isclose(out[0, 1], 0.5)
    out_without_perturbation = balanced_consensus_subset(
        matrices, ["alpha", "gamma", "algorithm"]
    )
    assert np.isclose(out_without_perturbation[0, 1], 0.0)


def test_anchor_affinity_excludes_self_when_node_is_anchor():
    consensus = np.array(
        [
            [1.0, 0.8, 0.1, 0.1],
            [0.8, 1.0, 0.2, 0.2],
            [0.1, 0.2, 1.0, 0.9],
            [0.1, 0.2, 0.9, 1.0],
        ]
    )
    raw, shares = affinities_to_members(
        consensus,
        ["A", "B"],
        {"A": np.array([0, 1]), "B": np.array([2, 3])},
    )
    assert np.isclose(raw[0, 0], 0.8)
    assert np.isclose(raw[0, 1], 0.1)
    assert np.isclose(shares[0].sum(), 1.0)


def test_consensus_core_anchor_selection_is_exact_and_deterministic():
    ref = np.array(["A"] * 8 + ["B"] * 4, dtype=object)
    names = ["A", "B"]
    raw = np.zeros((12, 2), dtype=float)
    raw[:8, 0] = np.arange(8)
    raw[8:, 1] = [0.1, 0.4, 0.3, 0.2]
    anchors = select_consensus_core_anchors(ref, names, raw, fraction=0.25)
    assert anchors["A"].tolist() == [6, 7]
    # minimum two anchors is enforced even though ceil(4 * .25) == 1
    assert anchors["B"].tolist() == [9, 10]


def test_transition_direction_is_not_a_consensus_class():
    left = np.array([4, 3, 2, 1, 0])
    right = np.array([0, 1, 2, 3, 4])
    out = transition_direction(left, right, "D", "G")
    assert out.tolist() == [
        "D-leaning",
        "D-leaning",
        "mixed",
        "G-leaning",
        "G-leaning",
    ]
