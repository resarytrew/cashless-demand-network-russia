"""Verify persisted evidence, checkpoint integrity and independent saved-label counts."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

from sbernet.config import load_config
from sbernet.robustness.experiment_common import save_json
from sbernet.robustness.perturbation_v2 import checkpoint_valid
from sbernet.robustness.reproduction_gate import sha256


def main():
    root = Path('outputs/perturbation_v2')
    cfg = load_config('configs/perturbation_v2.yaml')
    ref = pd.read_csv('outputs/baseline/supra_labels.csv', index_col=0).to_numpy(dtype=int).T
    profiles = cfg['experiment']['profiles']
    gate = json.loads((root / 'gate/gate.json').read_text())
    rows = []
    for seed in range(50):
        directory = root / 'seeds' / f'{seed:02d}'
        assert checkpoint_valid(directory, sha256('configs/perturbation_v2.yaml'))
        raw = json.loads((directory / 'raw_results.json').read_text())
        hashes = json.loads((directory / 'graph_hashes.json').read_text())
        assert hashes['canonical_base_edge_sha256'] == gate['hashes']['canonical_base_edge_sha256']
        assert hashes['temporal_edge_sha256'] == gate['hashes']['temporal_edge_sha256']
        assert hashes['node_count'] == 45696 and hashes['temporal_edge_count'] == 43792
        assert raw['run']['seed'] == seed
        labels = np.load(directory / 'supra_labels.npy', allow_pickle=False).reshape(ref.shape)
        assert len(raw['profiles']) == 7 and len(raw['pairs']) == 21 and len(raw['monthly']) == 24
        assert adjusted_rand_score(ref.ravel(), labels.ravel()) == raw['run']['ARI_all_supra']
        assert normalized_mutual_info_score(ref[-1], labels[-1]) == raw['run']['NMI_Dec2024']
        for row in raw['profiles']:
            mask = ref[-1] == profiles[row['archetype']]
            counts = np.bincount(labels[-1][mask])
            intersection = int(counts.max())
            destination = int(np.argmax(counts))
            alternative_n = int(np.count_nonzero(labels[-1] == destination))
            assert row['intersection'] == intersection
            assert row['retention'] == intersection / int(mask.sum())
            assert row['precision'] == intersection / alternative_n
            assert row['Jaccard'] == intersection / (int(mask.sum()) + alternative_n - intersection)
        rows.append({'seed': seed, 'checkpoint_and_raw_labels_verified': True})
    runs = pd.read_csv(root / 'perturbation_v2_50_runs.csv')
    summary = pd.read_csv(root / 'perturbation_v2_50_summary.csv')
    pro = pd.read_csv(root / 'perturbation_v2_50_archetype_retention.csv')
    pairs = pd.read_csv(root / 'perturbation_v2_50_pair_coassignment.csv')
    assert len(runs) == 50 and len(pro) == 350 and len(pairs) == 1050
    assert {'mean','median','SD','min','max','q05','q10','q25','q75','q90','q95'} <= set(summary.columns)
    assert not summary[['mean','median','SD','min','max','q05','q10','q25','q75','q90','q95']].isna().any().any()
    numeric = pro[['retention','precision','Jaccard','within_pair_coassignment']]
    assert ((numeric >= 0) & (numeric <= 1)).all().all()
    assert pairs.cross_coassignment.between(0,1).all()
    old_gate = Path(cfg['experiment']['baseline_gate_dir'])
    manifest = json.loads((old_gate / 'run_manifest.json').read_text())
    assert sha256('configs/baseline.yaml') == manifest['config_file_sha256']
    for file, checksum in manifest['reference_sha256'].items():
        assert sha256(file) == checksum
    for row in pd.read_csv('outputs/perturbation_pilot_reference/SHA256_MANIFEST.csv').to_dict('records'):
        assert sha256(row['path']) == row['sha256']
    matrix = pd.read_csv('outputs/evidence_v2_2_0/MASTER_PROFILE_EVIDENCE_MATRIX_v2.2.0.csv')
    assert matrix.historical_perturbation_pilot_status.eq('SUPERSEDED_NON_REPRODUCIBLE').all()
    assert matrix.perturbation_v2_n.eq(50).all()
    result = {'passed': True, 'seeds_verified': 50, 'raw_run_rows': 50, 'profile_rows':350,
              'pair_rows':1050, 'baseline_and_historical_pack_unchanged': True,
              'reference_shape': list(ref.shape), 'checks':rows}
    save_json(root / 'ARTIFACT_VERIFICATION.json', result)
    print('Artifact verification PASS: 50 seed checkpoints, saved-label metrics, schemas, immutable reference pack.')


if __name__ == '__main__':
    main()
