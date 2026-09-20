"""Non-destructive reference reproduction. Failure blocks downstream experiments."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import pickle
import struct
import sys

import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

from sbernet.pipeline import _prepare, _git_commit
from sbernet.graph import mutual_knn_graph
from sbernet.temporal import build_supra_graph
from sbernet.clustering import louvain_labels


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def graph_fingerprint(graph):
    """Canonical undirected endpoints and exact IEEE754 weights, little endian."""
    nodes = sorted(graph.nodes)
    edges = sorted((min(u, v), max(u, v), float(d['weight']))
                   for u, v, d in graph.edges(data=True))
    return {
        'node_count': len(nodes), 'edge_count': len(edges),
        'node_sha256': hashlib.sha256(b''.join(struct.pack('<q', n) for n in nodes)).hexdigest(),
        'edge_weight_sha256': hashlib.sha256(
            b''.join(struct.pack('<qqd', u, v, w) for u, v, w in edges)).hexdigest(),
    }


def similarity(reference, actual):
    return {'ARI': float(adjusted_rand_score(reference, actual)),
            'NMI': float(normalized_mutual_info_score(reference, actual))}


def baseline_passed(metrics):
    return all(value == 1.0 for scope in metrics.values() for value in scope.values())


def versions():
    result = {'python': sys.version, 'executable': sys.executable}
    for name in ['numpy', 'pandas', 'scipy', 'scikit-learn', 'networkx', 'PyYAML',
                 'igraph', 'leidenalg']:
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = None
    return result


def run(config_path, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'git_commit': _git_commit(), 'packages': versions(), 'seed': 0,
        'config_path': str(config_path), 'config_file_sha256': sha256(config_path),
        'reference_sha256': {str(p): sha256(p) for p in [
            Path('outputs/baseline/supra_labels.csv'),
            Path('outputs/baseline/static_dec2024_labels.csv')]},
    }
    (output / 'run_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('Preparing reference features', flush=True)
    cfg, names, audit, months, matrices = _prepare(config_path)
    keys = list(matrices)
    resolved = yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False)
    manifest['config_resolved_sha256'] = hashlib.sha256(resolved.encode()).hexdigest()
    manifest['seed'] = cfg['clustering']['seed']
    (output / 'resolved_config.yaml').write_text(resolved, encoding='utf-8')
    static = mutual_knn_graph(matrices[keys[-1]], cfg['network']['k'],
                              cfg['network']['static_isolate_fallback'])
    monthly = [mutual_knn_graph(matrices[k], cfg['network']['k'],
                                cfg['network']['temporal_isolate_fallback']) for k in keys]
    supra = build_supra_graph(monthly, len(names), cfg['temporal']['omega'])
    fingerprints = {'static': graph_fingerprint(static), 'supra': graph_fingerprint(supra),
                    'config_file_sha256': manifest['config_file_sha256'],
                    'config_resolved_sha256': manifest['config_resolved_sha256'],
                    'encoding': 'sorted nodes int64 LE; sorted (min(u,v),max(u,v),weight) int64,int64,float64 LE'}
    (output / 'graph_checksums.json').write_text(json.dumps(fingerprints, indent=2), encoding='utf-8')
    print('Graphs built: ' + json.dumps(fingerprints), flush=True)
    static_labels = louvain_labels(static, cfg['clustering']['resolution'], cfg['clustering']['seed'])
    pd.DataFrame({'mo': names, 'community': static_labels}).to_csv(output / 'static_dec2024_labels.csv', index=False)
    print('Running reference supra Louvain', flush=True)
    labels = louvain_labels(supra, cfg['clustering']['resolution'], cfg['clustering']['seed'])
    pd.DataFrame(labels.reshape(len(keys), len(names)).T, index=names, columns=keys).to_csv(output / 'supra_labels.csv')
    reference = pd.read_csv('outputs/baseline/supra_labels.csv', index_col=0).loc[names, keys]
    reference_static = pd.read_csv('outputs/baseline/static_dec2024_labels.csv').set_index('mo').loc[names, 'community']
    metrics = {
        'full_supra': similarity(reference.to_numpy().T.ravel(), labels),
        'temporal_Dec2024': similarity(reference.iloc[:, -1], labels.reshape(len(keys), len(names))[-1]),
        'static_Dec2024': similarity(reference_static, static_labels),
    }
    passed = baseline_passed(metrics) and len(names) == 1904 and len(keys) == 24
    result = {'passed': passed, 'metrics': metrics,
              'delta_from_required_one': {s: {k: v - 1 for k, v in m.items()} for s, m in metrics.items()},
              'panel_nodes': len(names), 'months': len(keys),
              'supra_K': len(np.unique(labels)), 'static_K': len(np.unique(static_labels))}
    (output / 'baseline_gate.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    manifest['baseline_config_unchanged'] = sha256(config_path) == manifest['config_file_sha256']
    manifest['status'] = 'passed' if passed else 'failed'
    (output / 'run_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2), flush=True)
    if not passed:
        report = ('# Reference reproduction failure\n\n'
                  'Baseline gate FAILED. No Leiden or perturbation pilot/high-rep runs were launched.\n\n'
                  'Required ARI=NMI=1 exactly; December temporal slice and standalone static partition are checked separately.\n\n'
                  '```json\n' + json.dumps(result, indent=2) + '\n```\n\n'
                  'Graph fingerprints are in graph_checksums.json. They record the reconstructed source graphs; '
                  'Leiden input identity has NOT been verified because the baseline gate failed.\n\n'
                  'Package versions and input hashes are in run_manifest.json. '
                  'igraph and leidenalg are not installed in this environment. '
                  'The cause of the mismatch is not established. No algorithm, seed, graph or stored reference was tuned or overwritten.\n')
        (output / 'REPRODUCIBILITY_FAILURE_REPORT.md').write_text(report, encoding='utf-8')
        return False
    with (output / 'baseline_graphs.pkl').open('wb') as fh:
        pickle.dump({'static': static, 'supra': supra, 'monthly': monthly,
                     'names': names, 'keys': keys, 'matrices': matrices}, fh)
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='configs/baseline.yaml')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    raise SystemExit(0 if run(args.config, args.output) else 1)
