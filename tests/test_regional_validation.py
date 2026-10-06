import numpy as np
import pandas as pd
import pytest

from sbernet.regional_validation import assert_group_separation, within_region_residuals


def test_grouped_cv_rejects_region_leakage():
    groups = np.array(["a", "a", "b"])
    with pytest.raises(AssertionError):
        assert_group_separation(groups, np.array([0, 2]), np.array([1]))


def test_within_region_residualization_is_region_median_centered():
    frame = pd.DataFrame({"region": ["a", "a", "b", "b"], "population": [1., 3., 10., 14.]})
    result = within_region_residuals(frame, ["population"])
    assert result.population_within_region.tolist() == [-1., 1., -2., 2.]
