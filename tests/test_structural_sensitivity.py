import itertools

import numpy as np
import pandas as pd

from sbernet.structural_sensitivity import (
    adjusted_multivariate_test,
    adjusted_scalar_test,
    information_decomposition,
    nestedness_metrics,
    pairwise_agreement,
    sector_clr,
    scale_semantic_blocks,
    multivariate_permutation,
    structural_metrics,
)


def brute_pairs(a, b):
    same_a = same_b = both = 0
    for i, j in itertools.combinations(range(len(a)), 2):
        same_a += a[i] == a[j]
        same_b += b[i] == b[j]
        both += a[i] == a[j] and b[i] == b[j]
    return both / same_a, both / same_b


def test_pure_coarsening_nestedness_pairwise_and_entropy():
    fine = np.array([0, 0, 1, 1, 2, 2])
    coarse = np.array([7, 7, 7, 7, 8, 8])
    nested = nestedness_metrics(fine, coarse)
    pair = pairwise_agreement(fine, coarse)
    info = information_decomposition(fine, coarse)
    assert nested["micro_purity"] == nested["macro_purity"] == 1
    assert pair["fine_pair_retention"] == 1
    assert pair["coarse_pair_precision"] < 1
    assert np.isclose(info["H_candidate_given_reference"], 0)
    assert info["H_reference_given_candidate"] > 0


def test_pairwise_combinatorics_matches_bruteforce():
    a = np.array([0, 0, 0, 1, 1, 2, 2, 2])
    b = np.array([4, 4, 5, 5, 5, 6, 4, 6])
    expected_retention, expected_precision = brute_pairs(a, b)
    result = pairwise_agreement(a, b)
    assert np.isclose(result["fine_pair_retention"], expected_retention)
    assert np.isclose(result["coarse_pair_precision"], expected_precision)


def test_metrics_are_label_permutation_invariant_and_identical_case():
    a = np.array([0, 0, 1, 1, 2, 2, 2])
    renamed = np.array([99, 99, -2, -2, 8, 8, 8])
    identical = structural_metrics(a, renamed)
    assert identical["ARI"] == identical["NMI"] == 1
    assert identical["micro_purity"] == 1
    assert identical["fine_pair_retention"] == identical["coarse_pair_precision"] == 1
    assert np.isclose(identical["VI"], 0)
    assert np.isclose(identical["H_candidate_given_reference"], 0)
    assert np.isclose(identical["H_reference_given_candidate"], 0)
    shuffled_names = structural_metrics(np.array([10, 10, 3, 3, 7, 7, 7]), renamed)
    for key in ("ARI", "NMI", "micro_purity", "fine_pair_retention", "VI"):
        assert np.isclose(identical[key], shuffled_names[key])


def test_shuffled_toy_is_not_misclassified_as_coarsening():
    fine = np.repeat(np.arange(4), 8)
    shuffled = np.tile(np.arange(4), 8)
    result = structural_metrics(fine, shuffled)
    assert result["micro_purity"] < .5
    assert result["fine_pair_retention"] < .5
    assert result["H_candidate_given_reference"] > 1


def synthetic_frame(seed=11, signal=True):
    rng = np.random.default_rng(seed); n = 180
    region = np.repeat(np.arange(6), n // 6); profile = np.tile(np.repeat(list("ABC"), 10), 6)
    log_pop = rng.normal(size=n); profile_signal = np.array([{"A": -1, "B": 0, "C": 1}[x] for x in profile])
    value = .7 * log_pop + .3 * region + (1.2 * profile_signal if signal else 0) + rng.normal(scale=.4, size=n)
    return pd.DataFrame({"population": np.exp(log_pop + 8), "region": region, "profile": profile,
                         "outcome": np.exp(value + 10)})


def test_partial_r2_and_freedman_lane_are_deterministic():
    frame = synthetic_frame()
    first, _, null1 = adjusted_scalar_test(frame, "outcome", "population", "region", "profile", 99, 44)
    second, _, null2 = adjusted_scalar_test(frame, "outcome", "population", "region", "profile", 99, 44)
    assert first == second and null1 == null2
    assert first["partial_R2"] > .5
    assert first["Freedman_Lane_p"] <= .02


def test_constrained_permutation_does_not_invent_systematic_signal():
    frame = synthetic_frame(signal=False)
    result, _, _ = adjusted_scalar_test(frame, "outcome", "population", "region", "profile", 199, 4)
    assert result["partial_R2"] < .05
    assert result["Freedman_Lane_p"] > .05


def test_multivariate_sector_adjustment_signal_and_determinism():
    frame = synthetic_frame(); rng = np.random.default_rng(4)
    code = frame.profile.map({"A": -1, "B": 0, "C": 1}).to_numpy()
    raw = np.exp(np.column_stack([code + rng.normal(scale=.3, size=len(frame)),
                                  -code + rng.normal(scale=.3, size=len(frame)),
                                  rng.normal(scale=.3, size=len(frame))]))
    frame[["s1", "s2", "s3"]] = raw
    clean, clr = sector_clr(frame, ["s1", "s2", "s3"])
    first, null1 = adjusted_multivariate_test(clean, clr, "population", "region", "profile", 99, 7)
    second, null2 = adjusted_multivariate_test(clean, clr, "population", "region", "profile", 99, 7)
    assert first == second and null1 == null2
    assert np.isfinite([first[key] for key in ("SSE_trace_reduced", "SSE_trace_full",
                                                "incremental_explained_SS", "partial_R2", "pseudo_F")]).all()
    assert first["partial_R2"] > .5 and first["permutation_p"] <= .02


def test_freedman_lane_permutation_groups_are_region_constrained():
    frame = synthetic_frame(); original = np.arange(len(frame)); rng = np.random.default_rng(3)
    permuted = original.copy()
    for indices in frame.groupby("region").indices.values():
        permuted[indices] = rng.permutation(permuted[indices])
    assert np.array_equal(frame.region.to_numpy(), frame.region.to_numpy()[permuted])


def test_semantic_block_weighting_scales_median_squared_distance_to_weight():
    from scipy.spatial.distance import pdist
    blocks = {"a": np.array([[0.], [1.], [3.], [8.]]),
              "b": np.array([[0., 1.], [2., 0.], [3., 4.], [9., 1.]])}
    weights = {"a": .2, "b": .8}
    coordinates, _ = scale_semantic_blocks(blocks, weights)
    for name, values in coordinates.items():
        assert np.isclose(np.median(pdist(values)) ** 2, weights[name])


def test_multivariate_omnibus_accepts_three_groups_deterministically():
    rng=np.random.default_rng(9); labels=np.repeat(list("ABC"),20)
    y=np.column_stack([np.repeat([-1.,0.,1.],20)+rng.normal(scale=.2,size=60),rng.normal(size=60)])
    first=multivariate_permutation(y,labels,99,12); second=multivariate_permutation(y,labels,99,12)
    assert first==second
    assert first["R2"]>.3 and first["p"]<=.02
