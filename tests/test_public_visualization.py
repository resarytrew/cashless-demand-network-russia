import json
from pathlib import Path
import re

import numpy as np
import pandas as pd
import pytest
import yaml

from sbernet.visualization.public import build, digest
from sbernet.visualization.stability_landscape import FIELDS, PROFILES, field_grid, project

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def inputs():
    cfg = yaml.safe_load((ROOT/'configs/public_visual_style.yaml').read_text(encoding='utf-8'))
    frame = pd.read_csv(ROOT/cfg['atlas'])
    return cfg, frame


def test_direct_projection_preserves_all_1904_original_rows(inputs):
    cfg, frame = inputs
    original = frame.copy(deep=True)
    out = project(frame, cfg)
    pd.testing.assert_frame_equal(original, frame)
    pd.testing.assert_frame_equal(out[FIELDS], frame[FIELDS])
    assert len(out) == 1904 and set(PROFILES) <= set(out.reference_profile)
    assert out.reference_profile.eq('micro').sum() == 5
    expected = frame[[f'affinity_share_{p}' for p in PROFILES]].to_numpy() @ np.array(list(cfg['anchors'].values()))
    np.testing.assert_allclose(out[['x','y']], expected, atol=1e-12)
    assert np.isfinite(out[['x','y','hard_x','hard_y','uncertainty']]).all().all()
    assert out.uncertainty.between(0,1).all()


def test_invalid_affinities_are_rejected_not_renormalized(inputs):
    cfg, frame = inputs
    frame = frame.copy()
    frame.loc[0,'affinity_share_A'] = 2
    with pytest.raises(ValueError, match='affinity'):
        project(frame,cfg)


def test_visual_field_is_finite_deterministic_and_masked(inputs):
    cfg, frame = inputs
    points = project(frame,cfg)
    cells = field_grid(points,cfg)
    assert cells == field_grid(points,cfg)
    assert len(cells)>0 and np.isfinite(cells).all()
    assert all(0<=cell[2]<=1 for cell in cells)


def test_exports_share_inputs_and_do_not_change_scientific_files(inputs,tmp_path):
    cfg, _ = inputs
    paths=[ROOT/cfg[k] for k in ['atlas','external','statistics','gradient','matrix','family_matrices']]
    before={str(p):digest(p) for p in paths}
    first, second = tmp_path/'first',tmp_path/'second'
    build(ROOT,first/'site',first/'images')
    build(ROOT,second/'site',second/'images')
    assert before=={str(p):digest(p) for p in paths}
    a=json.loads((first/'site/data/municipalities.json').read_text(encoding='utf-8'))
    assert len(a['rows'])==1904
    page=(first/'site/index.html').read_text(encoding='utf-8')
    assert len(re.findall(r'class="point" data-id=',page))==1904
    assert '<script src=' not in page and 'NaN' not in page
    assert 'Object.freeze(rows)' in page
    for p in (first/'images').glob('*.svg'):
        assert p.read_bytes()==(second/'images'/p.name).read_bytes()
        assert p.read_bytes()==(first/'site/assets'/p.name).read_bytes()
    for p in (first/'images').glob('*.meta.json'):
        meta=json.loads(p.read_text(encoding='utf-8'))
        assert meta['inputs_sha256']==a['input_sha256']
        assert meta['fields_used']==FIELDS


def test_builder_refuses_scientific_destination(tmp_path):
    with pytest.raises(ValueError,match='writable'):
        build(ROOT,ROOT/'outputs/round16_evidence',tmp_path/'images')
