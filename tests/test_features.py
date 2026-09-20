import numpy as np

from sbernet.features import clr, robust_z


def test_clr_rows_sum_to_zero():
    x = np.array([[0.2, 0.3, 0.5], [0.4, 0.4, 0.2]])
    transformed = clr(x)
    assert np.allclose(transformed.sum(axis=1), 0.0)


def test_robust_z_median_is_zero():
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    assert np.isclose(np.median(robust_z(x)), 0.0)
