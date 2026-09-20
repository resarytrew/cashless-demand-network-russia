import numpy as np
from scripts.forensic_sdbw import sdbw_trace


def variant(radius='sqrt_sum_over_k', zero='undefined'):
    return {'id':'test','radius':radius,'indicator':'inside','zero_policy':zero}


def test_zero_over_zero_is_explained_not_silently_regularized():
    x = np.array([[-1.], [1.], [9.], [11.]])
    labels = np.array([0,0,1,1])
    score, clusters, pairs = sdbw_trace(x, labels, variant())
    assert score['S_Dbw'] is None
    assert score['zero_over_zero_pairs'] == 1
    assert score['positive_over_zero_pairs'] == 0
    assert all(c['center_density'] == 0 for c in clusters)
    zero_score, _, _ = sdbw_trace(x, labels, variant(zero='zero_only_for_zero_numerator'))
    assert np.isclose(zero_score['S_Dbw'], 1/26)
    rms_score, _, _ = sdbw_trace(x, labels, variant(radius='sqrt_mean'))
    assert np.isclose(rms_score['S_Dbw'], 1/26)


def test_positive_over_zero_is_not_resolved_by_zero_zero_convention():
    x = np.array([[-2.],[2.],[1.],[5.]])
    labels = np.array([0,0,1,1])
    score, _, pairs = sdbw_trace(x, labels, variant(zero='zero_only_for_zero_numerator'))
    assert score['S_Dbw'] is None
    assert score['positive_over_zero_pairs'] == 1
    assert pairs[0]['midpoint_density'] == 2
    assert pairs[0]['denominator'] == 0


def test_trace_invariant_to_label_names_and_global_scale():
    x = np.array([[-1.],[1.],[9.],[11.]])
    a, _, _ = sdbw_trace(x, np.array([0,0,1,1]), variant(radius='sqrt_mean'))
    b, _, _ = sdbw_trace(x*10, np.array([99,99,-2,-2]), variant(radius='sqrt_mean'))
    assert np.isclose(a['S_Dbw'],b['S_Dbw'])
    assert np.isclose(b['radius'],10*a['radius'])
