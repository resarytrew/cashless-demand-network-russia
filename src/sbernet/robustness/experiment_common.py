"""Shared diagnostics and immutable input checks for rounds 14 and 15."""
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path
import pickle

import networkx as nx
import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import calinski_harabasz_score, silhouette_score

from sbernet.config import load_config
from sbernet.pipeline import _git_commit
from .reproduction_gate import graph_fingerprint, sha256, similarity, versions


def save_json(path, obj):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2, allow_nan=False), encoding='utf-8')
    tmp.replace(path)


def load_baseline(cfg):
    gate = Path(cfg['experiment']['baseline_gate_dir'])
    assert json.loads((gate / 'baseline_gate.json').read_text())['passed']
    manifest = json.loads((gate / 'run_manifest.json').read_text())
    assert sha256('configs/baseline.yaml') == manifest['config_file_sha256']
    for p, checksum in manifest['reference_sha256'].items():
        assert sha256(p) == checksum, f'Reference changed: {p}'
    with (gate / 'baseline_graphs.pkl').open('rb') as fh:
        data = pickle.load(fh)
    checks = json.loads((gate / 'graph_checksums.json').read_text())
    for name in ['static', 'supra']:
        assert graph_fingerprint(data[name]) == checks[name], f'Graph changed: {name}'
    baseline_cfg = load_config('configs/baseline.yaml')
    for key in ['features', 'network', 'temporal', 'panel']:
        assert cfg[key] == baseline_cfg[key], f'Reference specification changed: {key}'
    assert cfg['clustering']['resolution'] == baseline_cfg['clustering']['resolution']
    ref = pd.read_csv('outputs/baseline/supra_labels.csv', index_col=0).loc[data['names'], data['keys']]
    data['reference'] = ref.to_numpy(dtype=int).T
    data['reference_static'] = pd.read_csv('outputs/baseline/static_dec2024_labels.csv').set_index('mo').loc[data['names'], 'community'].to_numpy()
    return data


def make_manifest(config_path, cfg):
    source = {str(p): sha256(p) for p in Path('src/sbernet').rglob('*.py')}
    resolved = yaml.safe_dump(cfg, allow_unicode=True, sort_keys=True)
    return {'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'git_commit': _git_commit(),
            'packages': versions(), 'config_path': str(config_path), 'config_sha256': sha256(config_path),
            'resolved_config_sha256': hashlib.sha256(resolved.encode()).hexdigest(),
            'resolved_config': cfg, 'source_sha256': source,
            'baseline_config_sha256': sha256('configs/baseline.yaml')}


def profile_diagnostics(reference, actual, profiles):
    rows, pairrows = [], []
    masks = {p: np.where(reference == cid)[0] for p, cid in profiles.items()}
    for profile, indices in masks.items():
        destinations, counts = np.unique(actual[indices], return_counts=True)
        best = int(np.argmax(counts)); intersection = int(counts[best])
        destination = int(destinations[best]); n = len(indices)
        size = int(np.sum(actual == destination))
        rows.append({'archetype': profile, 'n_reference': n, 'destination': destination,
                     'destination_n': size, 'intersection': intersection,
                     'retention': intersection / n, 'precision': intersection / size,
                     'Jaccard': intersection / (n + size - intersection),
                     'within_pair_coassignment': float(np.sum(counts * (counts - 1)) / (n * (n - 1))) if n > 1 else 1.0,
                     'n_destinations': len(counts)})
    for a, b in itertools.combinations(profiles, 2):
        va, ca = np.unique(actual[masks[a]], return_counts=True)
        vb, cb = np.unique(actual[masks[b]], return_counts=True)
        da, db = dict(zip(va, ca)), dict(zip(vb, cb))
        value = sum(int(da[k]) * int(db.get(k, 0)) for k in da) / (len(masks[a]) * len(masks[b]))
        pairrows.append({'pair': f'{a}/{b}', 'cross_coassignment': value})
    return rows, pairrows


def temporal_diagnostics(reference, actual, keys):
    switch = np.sum(actual[1:] != actual[:-1], axis=0)
    monthly = []
    for i, key in enumerate(keys):
        row = {'month': key, **similarity(reference[i], actual[i]), 'K': len(np.unique(actual[i]))}
        if i:
            row.update({f'adjacent_{k}': v for k, v in similarity(actual[i - 1], actual[i]).items()})
            row['same_label_share'] = float(np.mean(actual[i - 1] == actual[i]))
        monthly.append(row)
    stats = {**{f'{k}_all_supra': v for k, v in similarity(reference.ravel(), actual.ravel()).items()},
             **{f'{k}_Dec2024': v for k, v in similarity(reference[-1], actual[-1]).items()},
             'K_supra': len(np.unique(actual)), 'K_Dec2024': len(np.unique(actual[-1])),
             'mean_switches': float(np.mean(switch)), 'median_switches': float(np.median(switch)),
             'share_zero_switches': float(np.mean(switch == 0)), 'share_le2_switches': float(np.mean(switch <= 2)),
             'mean_adjacent_ARI': float(np.mean([r['adjacent_ARI'] for r in monthly[1:]])),
             'mean_adjacent_NMI': float(np.mean([r['adjacent_NMI'] for r in monthly[1:]]))}
    return stats, monthly


def validity_metrics(graph, labels, x=None):
    groups = [set(np.where(labels == c)[0].tolist()) for c in np.unique(labels)]
    row = {'K': len(groups), 'MQ': float(nx.community.modularity(graph, groups, weight='weight')),
           'Q_resolution_0_5': float(nx.community.modularity(graph, groups, weight='weight', resolution=0.5))}
    # Eq.18-21 of Shalileh et al. (2026): unweighted adjacency counts.
    _, mapped = np.unique(labels, return_inverse=True)
    block = np.zeros((len(groups), len(groups)), dtype=np.int64)
    for u, v in graph.edges:
        block[mapped[u], mapped[v]] += 1
        block[mapped[v], mapped[u]] += 1
    internal = np.diag(block); external = block.sum(axis=1) - internal
    iso = np.divide(internal, internal + external, out=np.zeros(len(groups)), where=(internal + external) != 0)
    denom = external[:, None] + external[None, :] - block
    cross = block.copy(); np.fill_diagonal(cross, 0)
    uni = np.divide(cross, denom, out=np.zeros_like(denom, dtype=float), where=denom > 0)
    row.update(AVI=float(iso.mean()), AVU=float(uni.sum() / len(groups)))
    if x is not None:
        clusters = [x[sorted(g)] for g in groups]
        centers = [a.mean(axis=0) for a in clusters]
        norms = np.array([np.linalg.norm(a.var(axis=0)) for a in clusters])
        radius = np.sqrt(norms.sum()) / len(groups)
        density = [int(np.sum(np.linalg.norm(a - c, axis=1) <= radius)) for a, c in zip(clusters, centers)]
        between = []
        for i, j in itertools.combinations(range(len(groups)), 2):
            midpoint = (centers[i] + centers[j]) / 2
            count = sum(int(np.sum(np.linalg.norm(clusters[k] - midpoint, axis=1) <= radius)) for k in [i, j])
            den = max(density[i], density[j])
            if den == 0:
                row['S_Dbw'] = None
                row['S_Dbw_status'] = 'undefined_zero_density_denominator'
                break
            between.append(count / den)
        else:
            row['S_Dbw'] = float(norms.mean() / np.linalg.norm(x.var(axis=0)) + np.mean(between))
            row['S_Dbw_status'] = 'inside_radius_density_variant'
        row.update(SW=float(silhouette_score(x, labels)), CHn=float(calinski_harabasz_score(x, labels) / len(x)))
    return row


def distribution(values, quantiles):
    x = np.asarray(values, dtype=float)
    return {'n': len(x), 'mean': float(x.mean()), 'median': float(np.median(x)),
            'SD': float(x.std(ddof=1)) if len(x) > 1 else 0.0,
            'min': float(x.min()), 'max': float(x.max()),
            **{f'q{round(q * 100):02d}': float(np.quantile(x, q, method='linear')) for q in quantiles}}
