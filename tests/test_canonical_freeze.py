from pathlib import Path
import pandas as pd


def test_canonical_matrix_contains_verified_numbers_not_new_scientific_statuses():
    root=Path('outputs/evidence_freeze_v2_2_0')
    matrix=pd.read_csv(root/'MASTER_PROFILE_EVIDENCE_MATRIX_v2.2.0.csv')
    assert list(matrix.archetype)==list('ABCDEFG')
    assert matrix.perturbation_v2_n.eq(50).all()
    assert matrix.historical_pilot_quantitative_evidence_used.eq(False).all()
    assert matrix.historical_perturbation_pilot_status.eq('SUPERSEDED_NON_REPRODUCIBLE').all()
    assert 'round13_status' not in matrix and 'round15_status' not in matrix
    previous=pd.read_csv('outputs/perturbation_v2/archetype_status_round15_perturbation_v2.csv')
    registry=pd.read_csv(root/'SCIENTIFIC_STATUS_REGISTRY_UNCHANGED.csv')
    assert list(registry.scientific_status_unchanged)==list(previous.round15_status)
    checks=pd.read_csv(root/'EVIDENCE_NUMERIC_REPLAY_CHECKS.csv')
    assert checks.passed.all() and len(checks)==3748


def test_forensic_diagnostics_reproduce_undefined_without_replacing_old_outputs():
    root=Path('outputs/evidence_freeze_v2_2_0')
    checks=pd.read_csv(root/'ROUND14_S_DBW_REPLAY_CHECK.csv')
    assert len(checks)==50 and checks.passed.all()
    assert checks.stored_S_Dbw.isna().all()
    assert checks.recomputed_S_Dbw.isna().all()
    features=pd.read_csv(root/'FEATURE_REPRODUCTION_CHECK.csv')
    assert len(features)==24 and features.bitwise_equal.all()
