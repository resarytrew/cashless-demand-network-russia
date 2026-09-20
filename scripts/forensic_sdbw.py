"""Metric-only forensic replay. Never invoke graph clustering or edit prior artifacts."""
import argparse
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path
import pickle
from unittest.mock import patch

import numpy as np
import pandas as pd
import yaml

from sbernet.pipeline import _prepare
from sbernet.robustness.reproduction_gate import sha256, versions


def sdbw_trace(x, labels, variant, ddof=0):
    ids = np.unique(labels)
    clusters = [x[labels == cid] for cid in ids]
    centers = [points.mean(axis=0) for points in clusters]
    norms = np.array([np.linalg.norm(points.var(axis=0, ddof=ddof)) for points in clusters])
    if variant['radius'] == 'sqrt_sum_over_k':
        radius = float(np.sqrt(norms.sum()) / len(ids))
    elif variant['radius'] == 'sqrt_mean':
        radius = float(np.sqrt(norms.mean()))
    else:
        raise ValueError('Undeclared radius variant')
    def count(points, center):
        distance = np.linalg.norm(points - center, axis=1)
        return int(np.count_nonzero(distance <= radius if variant['indicator'] == 'inside' else distance > radius))
    densities = [count(points, center) for points, center in zip(clusters, centers)]
    cluster_rows = [{'cluster_id': int(cid), 'n': len(points), 'variance_norm': float(norm),
                     'radius': radius, 'center_density': density,
                     'min_center_distance': float(np.min(np.linalg.norm(points - center, axis=1)))}
                    for cid, points, center, norm, density in zip(ids, clusters, centers, norms, densities)]
    pair_rows, ratios = [], []
    undefined = False
    for i, j in itertools.combinations(range(len(ids)), 2):
        midpoint = (centers[i] + centers[j]) / 2
        numerator = count(clusters[i], midpoint) + count(clusters[j], midpoint)
        denominator = max(densities[i], densities[j])
        if denominator:
            ratio = numerator / denominator
        elif variant['zero_policy'] == 'floor_one':
            ratio = float(numerator)
        elif variant['zero_policy'] == 'zero_only_for_zero_numerator' and numerator == 0:
            ratio = 0.0
        else:
            ratio = None; undefined = True
        if ratio is not None:
            ratios.append(ratio)
        pair_rows.append({'cluster_i': int(ids[i]), 'cluster_j': int(ids[j]),
                          'density_i': densities[i], 'density_j': densities[j],
                          'midpoint_density': numerator, 'denominator': denominator,
                          'zero_over_zero': denominator == 0 and numerator == 0,
                          'positive_over_zero': denominator == 0 and numerator > 0,
                          'ratio': ratio})
    global_norm = float(np.linalg.norm(x.var(axis=0, ddof=ddof)))
    scatter = float(norms.mean() / global_norm) if global_norm else None
    density_between = float(np.mean(ratios)) if not undefined and ratios else None
    score = scatter + density_between if scatter is not None and density_between is not None else None
    summary = {'variant': variant['id'], 'K': len(ids), 'radius': radius,
               'scatter': scatter, 'density_between': density_between, 'S_Dbw': score,
               'status': 'undefined' if score is None else 'finite',
               'zero_density_clusters': sum(d == 0 for d in densities),
               'zero_over_zero_pairs': sum(r['zero_over_zero'] for r in pair_rows),
               'positive_over_zero_pairs': sum(r['positive_over_zero'] for r in pair_rows)}
    return summary, cluster_rows, pair_rows


def audit(config_path):
    cfg = yaml.safe_load(Path(config_path).read_text(encoding='utf-8'))
    output = Path(cfg['output_dir']); output.mkdir(parents=True, exist_ok=False)
    # Snapshot all pre-existing research outputs/config/status/code before any audit writes.
    protected = []
    for directory in ['outputs', 'configs', 'docs', 'src', 'reference']:
        for p in Path(directory).rglob('*'):
            if p.is_file() and output not in p.parents and '__pycache__' not in p.parts:
                protected.append({'path': p.as_posix(), 'sha256': sha256(p), 'bytes': p.stat().st_size})
    pd.DataFrame(protected).to_csv(output / 'PRE_AUDIT_PROTECTED_FILES_SHA256.csv', index=False)
    gate = Path(cfg['baseline_gate_dir'])
    with (gate / 'baseline_graphs.pkl').open('rb') as fh:
        cache = pickle.load(fh)
    meta = json.loads((gate / 'run_manifest.json').read_text())
    assert sha256(cfg['baseline_config']) == meta['config_file_sha256']
    for p, checksum in meta['reference_sha256'].items():
        assert sha256(p) == checksum
    # Fresh feature reconstruction is not a new clustering experiment.
    _, names, _, _, matrices = _prepare(cfg['baseline_config'])
    assert names == cache['names']
    features_checks = []
    for key in cache['keys']:
        old, fresh = cache['matrices'][key], matrices[key]
        equal = np.array_equal(old, fresh)
        features_checks.append({'month': key, 'bitwise_equal': equal,
            'max_abs_delta': float(np.max(np.abs(old-fresh))),
            'matrix_sha256': hashlib.sha256(fresh.astype('<f8').tobytes()).hexdigest()})
        assert equal, f'Cached feature mismatch {key}'
    pd.DataFrame(features_checks).to_csv(output / 'FEATURE_REPRODUCTION_CHECK.csv', index=False)
    keys = cache['keys']; ref = pd.read_csv('outputs/baseline/supra_labels.csv', index_col=0).loc[names, keys].to_numpy().T
    static_ref = pd.read_csv('outputs/baseline/static_dec2024_labels.csv').set_index('mo').loc[names, 'community'].to_numpy()
    leiden = Path(cfg['leiden_dir'])
    static_leiden = np.load(leiden / 'static_labels.npy', allow_pickle=False)
    supra_leiden = np.load(leiden / 'supra_labels.npy', allow_pickle=False).reshape(ref.shape)
    targets = [('static_louvain_alpha70', matrices[keys[-1]], static_ref, 'static', keys[-1]),
               ('static_leiden_alpha70', matrices[keys[-1]], static_leiden, 'static', keys[-1])]
    for t, key in enumerate(keys):
        targets += [('temporal_louvain_alpha70', matrices[key], ref[t], 'temporal', key),
                    ('temporal_leiden_alpha70', matrices[key], supra_leiden[t], 'temporal', key)]
    for entry in cfg['sdbw']['alpha_static_diagnostics']:
        _, anames, _, _, amatrices = _prepare(entry['config'])
        assert anames == names
        alab = pd.read_csv(entry['labels']).set_index('mo').loc[names, 'community'].to_numpy()
        targets.append((f'static_louvain_alpha{round(entry["alpha"]*100)}', amatrices[keys[-1]], alab, 'static', keys[-1]))
    summaries, clusters, pairs = [], [], []
    for target, x, lab, scope, month in targets:
        for variant in cfg['sdbw']['variants']:
            result, cr, pr = sdbw_trace(x, lab, variant, cfg['sdbw']['variance_ddof'])
            context = {'target': target, 'scope': scope, 'month': month}
            summaries.append({**context, **result})
            # Full cluster/pair diagnostics for strict executed variant; alternative summaries retained separately.
            if variant['id'] == 'round14_strict':
                clusters.extend([{**context, **r} for r in cr])
                pairs.extend([{**context, **r} for r in pr])
    result = pd.DataFrame(summaries)
    result.to_csv(output / 'S_DBW_VARIANT_DIAGNOSTICS.csv', index=False)
    pd.DataFrame(clusters).to_csv(output / 'S_DBW_CLUSTER_DIAGNOSTICS.csv', index=False)
    pd.DataFrame(pairs).to_csv(output / 'S_DBW_PAIR_DIAGNOSTICS.csv', index=False)
    historical = pd.read_csv('outputs/alpha_sensitivity/alpha_sensitivity_static_metrics.csv', float_precision='round_trip')
    comparisons = []
    for row in historical.to_dict('records'):
        for current in result.query('scope == "static"').to_dict('records'):
            if current['target'] == f'static_louvain_alpha{round(row["alpha"]*100)}':
                comparisons.append({'alpha': row['alpha'], 'variant': current['variant'],
                                    'historical_S_Dbw': row['S_Dbw'], 'diagnostic_S_Dbw': current['S_Dbw'],
                                    'delta': current['S_Dbw'] - row['S_Dbw'],
                                    'admissible_as_historical_provenance': False})
    pd.DataFrame(comparisons).to_csv(output / 'HISTORICAL_S_DBW_COMPARISON.csv', index=False)
    old_static = pd.read_csv(leiden / 'leiden_static_metrics.csv')
    old_monthly = pd.read_csv(leiden / 'leiden_monthly_metrics.csv')
    checks = []
    for r in result.query('variant == "round14_strict"').to_dict('records'):
        if r['target'].endswith(('alpha50','alpha90')):
            continue
        algorithm = 'leiden' if 'leiden' in r['target'] else 'louvain'
        if r['scope'] == 'static':
            old = old_static[old_static.algorithm == algorithm]
        else:
            old = old_monthly[(old_monthly.algorithm == algorithm) & (old_monthly.month == r['month'])]
        stored = old.iloc[0].S_Dbw
        reproduced = (pd.isna(stored) and pd.isna(r['S_Dbw'])) or np.isclose(stored, r['S_Dbw'], atol=cfg['comparison_atol'], rtol=0)
        checks.append({'target':r['target'],'month':r['month'],'stored_S_Dbw':stored,'recomputed_S_Dbw':r['S_Dbw'],'passed':bool(reproduced)})
    pd.DataFrame(checks).to_csv(output / 'ROUND14_S_DBW_REPLAY_CHECK.csv', index=False)
    assert all(c['passed'] for c in checks)
    manifest = {'timestamp_utc':datetime.now(timezone.utc).isoformat(), 'config_sha256':sha256(config_path),
                'audit_script_sha256':sha256(__file__), 'packages':versions(), 'clustering_calls':0,
                'fixed_partitions_evaluated':len(targets),'diagnostic_variants':len(cfg['sdbw']['variants']),
                'round14_metric_replay_passed':True, 'scientific_status_changes':0}
    (output / 'FORENSIC_RUN_MANIFEST.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(result.query('scope == "static"').to_string(index=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--config',default='configs/evidence_freeze_v2_2_0.yaml')
    args = parser.parse_args()
    import leidenalg
    with patch('networkx.community.louvain_communities', side_effect=RuntimeError('Clustering prohibited in forensic audit')), \
         patch.object(leidenalg, 'find_partition', side_effect=RuntimeError('Clustering prohibited in forensic audit')):
        audit(args.config)
