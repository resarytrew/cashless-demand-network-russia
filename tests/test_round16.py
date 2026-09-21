import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
import yaml

from sbernet.io import build_strict_panel
from sbernet.pipeline import run
from sbernet.robustness.reproduction_gate import sha256
from scripts.round16_common import completed, seal
from scripts.build_competition_artifacts import individual_stability, choose_cases


def panel(months):
    return pd.DataFrame([{'mo': 'x', 'period': m, 'category_15': c, 'value': 1}
                         for m in months for c in ['total', 'food']])


def test_exact_calendar_rejects_shifted_24_months():
    with pytest.raises(ValueError, match='calendar'):
        build_strict_panel(panel(pd.date_range('2023-02-01', periods=24, freq='MS')), 24, ['total','food'])
    assert build_strict_panel(panel(pd.date_range('2023-01-01', periods=24, freq='MS')), 24, ['total','food'])[1] == ['x']


def test_calendar_rejects_midmonth_and_accepts_incomplete_exclusion():
    months = list(pd.date_range('2023-01-01', periods=24, freq='MS')); months[5] += pd.Timedelta(days=1)
    with pytest.raises(ValueError, match='calendar'):
        build_strict_panel(panel(months), 24, ['total','food'])
    raw = panel(pd.date_range('2023-01-01', periods=24, freq='MS'))
    raw = raw.drop(raw.index[-1])
    assert build_strict_panel(raw, 24, ['total','food'])[1] == []


def test_overwrite_rejected_before_feature_work(tmp_path):
    target=tmp_path/'out'; target.mkdir(); (target/'sentinel').write_text('keep')
    config=tmp_path/'config.yaml'; config.write_text(yaml.safe_dump({'paths':{'output_dir':str(target)}}))
    with patch('sbernet.pipeline._prepare', side_effect=AssertionError('must not run')):
        with pytest.raises(FileExistsError):
            run(config)
    assert (target/'sentinel').read_text() == 'keep'


def test_force_cannot_replace_frozen_baseline():
    with pytest.raises(ValueError, match='Frozen evidence'):
        run('configs/baseline.yaml', force=True)


def test_checkpoint_detects_corruption_and_incomplete(tmp_path):
    d=tmp_path/'run'; d.mkdir(); (d/'raw.json').write_text('{}')
    with pytest.raises(ValueError, match='Incomplete'):
        completed(d)
    seal(d); assert completed(d)
    (d/'raw.json').write_text('{"corrupted":true}')
    with pytest.raises(ValueError, match='Corrupt'):
        completed(d)


def test_collapsed_partition_has_high_peer_retention_but_low_precision():
    ref=np.array([1,1,3,3]); collapsed=np.zeros(4,dtype=int)
    co,precision,jaccard,_=individual_stability(ref,[collapsed],{'A':1,'B':3})
    assert np.all(co == 1)
    assert np.all(precision == .5)
    assert np.all(jaccard == .5)


def test_round16_output_schemas_and_reference_gamma():
    root=Path('outputs/round16_perturbation_decomposition')
    runs=pd.read_csv(root/'perturbation_decomposition_runs.csv')
    assert runs.groupby('mode').size().to_dict() == {'collapse_fixed':2,'combined':50,'graph_only':20,'optimizer_only':20}
    assert runs.loc[runs['mode'].eq('graph_only'),'louvain_seed'].eq(0).all()
    resolution=pd.read_csv('outputs/round16_resolution/resolution_sensitivity_summary.csv')
    assert set(resolution.gamma)=={.25,.5,.75,1.0}
    assert resolution.graph_topology_unchanged.all()
    ref=resolution[resolution.gamma.eq(.5)].iloc[0]
    assert ref.ARI_all_supra == ref.NMI_all_supra == ref.ARI_Dec2024 == ref.NMI_Dec2024 == 1
    cases=pd.read_csv(root/'perturbation_collapse_cases.csv')
    assert cases[cases['mode'].eq('combined')].set_index('seed').largest_community_n_Dec.to_dict()=={24:1864,39:1877}
    assert cases[cases['mode'].eq('collapse_fixed')].set_index('seed').largest_community_n_Dec.to_dict()=={24:1868,39:1874}


def test_benchmark_historical_families_never_reuse_old_numbers():
    b=pd.read_csv('outputs/round16_benchmark/canonical_method_benchmark.csv')
    unavailable=b[b.status.eq('UNREPRODUCIBLE_HISTORICAL_BENCHMARK_COMPONENT')]
    assert len(unavailable)==4
    assert unavailable[['SW','CHn','AVI','AVU','MQ']].isna().all().all()
    assert b[b.status.eq('CANONICAL_REBUILT')].S_Dbw.isna().all()
