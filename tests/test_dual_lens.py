import numpy as np
import pandas as pd
import pytest

from sbernet.dual_lens import (
    canonicalize_partition,
    combine_lenses,
    cross_lens_migration,
    employment_clr,
    robust_standardize_columns,
)


def test_employment_clr_zero_replacement_is_finite_and_centered():
    frame = pd.DataFrame({"a": [2.0, 0.0], "b": [0.0, 3.0], "c": [2.0, 1.0]})
    clr, shares = employment_clr(frame, ["a", "b", "c"])
    assert np.isfinite(clr).all()
    assert clr.mean(axis=1) == pytest.approx([0.0, 0.0])
    assert shares.sum(axis=1).to_numpy() == pytest.approx([1.0, 1.0])


def test_combine_lenses_has_declared_blocks_and_is_deterministic():
    base = np.arange(12, dtype=float).reshape(4, 3)
    socio = robust_standardize_columns(np.array([[1., 2.], [2., 4.], [4., 8.], [8., 16.]]))
    employment = np.array([[0., 1.], [1., 0.], [2., -1.], [3., -2.]])
    weights = {"l1": .4, "socioeconomic": .3, "employment": .3}
    first, scales = combine_lenses(base, socio, employment, weights)
    second, _ = combine_lenses(base, socio, employment, weights)
    assert first.shape == (4, 7)
    assert first == pytest.approx(second)
    assert all(value > 0 for value in scales.values())


def test_canonical_labels_and_cross_lens_migration_are_label_invariant():
    raw = np.array([9, 9, 4, 4, 4])
    canonical, mapping = canonicalize_partition(raw)
    assert mapping == {4: 1, 9: 2}
    assert canonical.tolist() == [2, 2, 1, 1, 1]
    contingency, migration = cross_lens_migration(
        ["a", "b", "c", "d", "e"],
        np.array([1, 1, 2, 2, 3]),
        canonical,
        np.array(["A", "A", "B", "B", "C"]),
    )
    assert contingency.set_index("L1_profile").loc["A", 2] == 2
    assert migration.cross_lens_reassigned.sum() == 1


def test_bad_block_weights_and_empty_employment_fail_explicitly():
    block = np.arange(8, dtype=float).reshape(4, 2)
    with pytest.raises(ValueError, match="sum to one"):
        combine_lenses(block, block, block, {"l1": .5, "socioeconomic": .5, "employment": .5})
    with pytest.raises(ValueError, match="at least one positive"):
        employment_clr(pd.DataFrame({"a": [0.0], "b": [0.0]}), ["a", "b"])
