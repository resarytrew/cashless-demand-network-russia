"""Canonical sorted-edge perturbation, exact process gates, per-seed checkpoints."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import networkx as nx
import numpy as np
import pandas as pd

from sbernet.clustering import louvain_labels
from sbernet.config import load_config
from .experiment_common import (load_baseline, make_manifest, save_json, profile_diagnostics,
                                temporal_diagnostics, distribution)
from .reproduction_gate import sha256, versions

EDGE_DTYPE = np.dtype([('u', '<i8'), ('v', '<i8'), ('weight', '<f8')], align=False)
WORKER = {}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical_edges(graph, kind=None):
    rows = []
    for u, v, d in graph.edges(data=True):
        if kind is None or d.get('kind') == kind:
            if u == v:
                raise ValueError('Protocol v2 does not accept self loops')
            rows.append((min(u, v), max(u, v), float(d['weight'])))
    rows.sort(key=lambda row: (row[0], row[1]))
    return np.array(rows, dtype=EDGE_DTYPE)


def perturb(graph, seed, settings):
    if graph.is_directed() or graph.is_multigraph():
        raise ValueError('Expected a simple undirected graph')
    if any(d.get('kind') not in {'intralayer', 'temporal'} for _, _, d in graph.edges(data=True)):
        raise ValueError('Every source edge requires an explicit kind')
    base = canonical_edges(graph, 'intralayer')
    temporal = canonical_edges(graph, 'temporal')
    rng = np.random.default_rng(settings['rng_base_seed'] + seed)
    keep = rng.random(len(base)) >= settings['intralayer_drop_probability']
    jitter = np.exp(rng.normal(settings['retained_weight_log_jitter_mean'],
                               settings['retained_weight_log_jitter_sd'], int(keep.sum())))
    retained = base[keep].copy()
    retained['weight'] *= jitter
    result = nx.Graph()
    nodes = np.array(sorted(graph.nodes), dtype='<i8')
    result.add_nodes_from(int(n) for n in nodes)
    result.add_edges_from((int(e['u']), int(e['v']), {'weight': float(e['weight']), 'kind': 'intralayer'}) for e in retained)
    result.add_edges_from((int(e['u']), int(e['v']), {'weight': float(e['weight']), 'kind': 'temporal'}) for e in temporal)
    final_edges = canonical_edges(result)
    assert np.array_equal(canonical_edges(result, 'temporal'), temporal)
    hashes = {'seed': int(seed), 'canonical_base_edge_sha256': digest(base.tobytes()),
              'keep_mask_sha256': digest(keep.astype('u1').tobytes()),
              'jitter_array_sha256': digest(jitter.astype('<f8').tobytes()),
              'perturbed_intralayer_edge_sha256': digest(retained.tobytes()),
              'temporal_edge_sha256': digest(temporal.tobytes()),
              'final_supra_edge_weight_sha256': digest(final_edges.tobytes()),
              'final_supra_graph_sha256': digest(nodes.tobytes() + final_edges.tobytes()),
              'node_count': len(nodes), 'base_intralayer_count': len(base),
              'retained_intralayer_count': len(retained), 'temporal_edge_count': len(temporal),
              'edge_count': len(final_edges)}
    return result, hashes


def fresh_hash(config_path, destination):
    cfg = load_config(config_path)
    data = load_baseline(cfg)
    _, hashes = perturb(data['supra'], cfg['robustness']['gate_seed'], cfg['robustness']['perturbation'])
    save_json(destination, hashes)


def gate(config_path):
    cfg = load_config(config_path)
    data = load_baseline(cfg)
    output = Path(cfg['paths']['output_dir']); output.mkdir(parents=True, exist_ok=True)
    gate_dir = output / 'gate'; gate_dir.mkdir(exist_ok=False)
    manifest = make_manifest(config_path, cfg)
    save_json(gate_dir / 'run_manifest.json', manifest)
    seed = cfg['robustness']['gate_seed']
    _, first = perturb(data['supra'], seed, cfg['robustness']['perturbation'])
    save_json(gate_dir / 'same_process_first.json', first)
    _, second = perturb(data['supra'], seed, cfg['robustness']['perturbation'])
    save_json(gate_dir / 'same_process_second.json', second)
    env = os.environ.copy()
    env['PYTHONPATH'] = str(Path('src').resolve())
    subprocess.run([sys.executable, '-m', 'sbernet.robustness.perturbation_v2', 'fresh-hash',
                    '--config', str(config_path), '--hash-output', str(gate_dir / 'fresh_process.json')],
                   check=True, env=env, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    fresh = json.loads((gate_dir / 'fresh_process.json').read_text())
    reversed_graph = nx.Graph()
    reversed_graph.add_nodes_from(reversed(list(data['supra'].nodes)))
    reversed_graph.add_edges_from((v, u, dict(d)) for u, v, d in reversed(list(data['supra'].edges(data=True))))
    _, reverse = perturb(reversed_graph, seed, cfg['robustness']['perturbation'])
    save_json(gate_dir / 'reversed_insertion.json', reverse)
    passed = first == second == fresh == reverse
    report = {'passed': passed, 'same_process_equal': first == second,
              'fresh_process_equal': first == fresh, 'reversed_insertion_equal': first == reverse,
              'config_sha256': sha256(config_path), 'packages': versions(), 'hashes': first}
    save_json(gate_dir / 'gate.json', report)
    lines = ['# Perturbation v2 reproducibility gate', '', f'Status: {"PASS" if passed else "FAIL"}.', '',
             'Seed 0: two calls in the same process, one fresh Python process, and one reversed node/edge insertion order. '
             'All saved hashes and counts are compared exactly, without numerical tolerance. '
             'No historical pilot CSV comparisons are used.', '', '```json', json.dumps(report, indent=2), '```', '',
             'The gate verifies perturbation graph determinism; Louvain uses the run seed separately.']
    (output / 'PERTURBATION_V2_REPRODUCIBILITY_GATE.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    if not passed:
        (output / 'PERTURBATION_V2_REPRODUCIBILITY_FAILURE.md').write_text('\n'.join(lines), encoding='utf-8')
        raise RuntimeError('Protocol v2 gate failed; n=50 prohibited')
    print(json.dumps(report, indent=2), flush=True)


def init_worker(config_path):
    cfg = load_config(config_path)
    WORKER.update(cfg=cfg, data=load_baseline(cfg), config_sha256=sha256(config_path))


def seed_run(seed):
    start = time.monotonic()
    cfg, data = WORKER['cfg'], WORKER['data']
    seed_dir = Path(cfg['paths']['output_dir']) / 'seeds' / f'{seed:02d}'
    seed_dir.mkdir(parents=True, exist_ok=True)
    graph, hashes = perturb(data['supra'], seed, cfg['robustness']['perturbation'])
    save_json(seed_dir / 'graph_hashes.json', hashes)
    labels = louvain_labels(graph, cfg['clustering']['resolution'], seed)
    # Raw labels before any derived diagnostics or summary.
    np.save(seed_dir / 'supra_labels.npy', labels)
    actual = labels.reshape(data['reference'].shape)
    stats, monthly = temporal_diagnostics(data['reference'], actual, data['keys'])
    stats.update(seed=seed, **{k: v for k, v in hashes.items() if k != 'seed'})
    profiles, pairs = profile_diagnostics(data['reference'][-1], actual[-1], cfg['experiment']['profiles'])
    for rows in [profiles, pairs, monthly]:
        for row in rows:
            row['seed'] = seed
    raw = {'run': stats, 'profiles': profiles, 'pairs': pairs, 'monthly': monthly}
    save_json(seed_dir / 'raw_results.json', raw)
    manifest = {'seed': seed, 'config_sha256': WORKER['config_sha256'], 'packages': versions(),
                'elapsed_seconds': time.monotonic() - start,
                'timestamp_utc': datetime.now(timezone.utc).isoformat(),
                'files_sha256': {name: sha256(seed_dir / name) for name in
                    ['supra_labels.npy', 'graph_hashes.json', 'raw_results.json']}}
    save_json(seed_dir / 'COMPLETED.json', manifest)
    return {'seed': seed, 'seconds': manifest['elapsed_seconds'], 'ARI': stats['ARI_all_supra'],
            'Dec_ARI': stats['ARI_Dec2024']}


def checkpoint_valid(seed_dir, config_hash):
    checkpoint = seed_dir / 'COMPLETED.json'
    if not checkpoint.exists():
        return False
    saved = json.loads(checkpoint.read_text())
    if saved['config_sha256'] != config_hash or saved['packages'] != versions():
        raise ValueError(f'Checkpoint config/environment mismatch: {seed_dir}')
    if not all(sha256(seed_dir / name) == checksum for name, checksum in saved['files_sha256'].items()):
        raise ValueError(f'Checkpoint integrity mismatch: {seed_dir}')
    return True


def summarize(cfg):
    output = Path(cfg['paths']['output_dir'])
    raw = [json.loads((output / 'seeds' / f'{s:02d}' / 'raw_results.json').read_text()) for s in cfg['robustness']['seeds']]
    runs = pd.DataFrame([r['run'] for r in raw])
    profiles = pd.DataFrame([p for r in raw for p in r['profiles']])
    pairs = pd.DataFrame([p for r in raw for p in r['pairs']])
    # Combined per-run tables are saved before distribution summaries.
    runs.to_csv(output / 'perturbation_v2_50_runs.csv', index=False)
    profiles.to_csv(output / 'perturbation_v2_50_archetype_retention.csv', index=False)
    pairs.to_csv(output / 'perturbation_v2_50_pair_coassignment.csv', index=False)
    pd.DataFrame([p for r in raw for p in r['monthly']]).to_csv(output / 'perturbation_v2_50_monthly_similarity.csv', index=False)
    summaries = []
    quantiles = cfg['experiment']['quantiles']
    for metric in runs.select_dtypes(include='number').columns:
        if metric != 'seed':
            summaries.append({'scope': 'run', 'group': 'all', 'metric': metric, **distribution(runs[metric], quantiles)})
    for profile, group in profiles.groupby('archetype'):
        for metric in ['retention', 'precision', 'Jaccard', 'within_pair_coassignment', 'n_destinations']:
            row = {'scope': 'archetype', 'group': profile, 'metric': metric, **distribution(group[metric], quantiles)}
            if metric == 'retention':
                row.update({f'share_ge_{threshold:.2f}': float(np.mean(group[metric] >= threshold)) for threshold in cfg['experiment']['retention_thresholds']})
            summaries.append(row)
    for pair, group in pairs.groupby('pair'):
        summaries.append({'scope': 'pair', 'group': pair, 'metric': 'cross_coassignment', **distribution(group.cross_coassignment, quantiles)})
    pd.DataFrame(summaries).to_csv(output / 'perturbation_v2_50_summary.csv', index=False)
    return runs, profiles, pairs


def run(config_path, force=False):
    cfg = load_config(config_path); output = Path(cfg['paths']['output_dir'])
    gate_report = json.loads((output / 'gate/gate.json').read_text())
    if not (gate_report['passed'] and gate_report['config_sha256'] == sha256(config_path)
            and gate_report['packages'] == versions()):
        raise ValueError('v2 gate missing, failed, or stale')
    if not json.loads((Path(cfg['experiment']['leiden_output_dir']) / 'COMPLETED.json').read_text())['completed']:
        raise ValueError('Leiden must complete before v2 n=50')
    data = load_baseline(cfg)
    base_hash = digest(canonical_edges(data['supra'], 'intralayer').tobytes())
    assert base_hash == gate_report['hashes']['canonical_base_edge_sha256']
    del data
    manifest_path = output / 'run_manifest.json'
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text())
        assert old['config_sha256'] == sha256(config_path)
        assert old['source_sha256'] == make_manifest(config_path, cfg)['source_sha256'], 'Source changed since experiment start'
    else:
        save_json(manifest_path, make_manifest(config_path, cfg))
    pending = []
    for seed in cfg['robustness']['seeds']:
        seed_dir = output / 'seeds' / f'{seed:02d}'
        if checkpoint_valid(seed_dir, sha256(config_path)) and not force:
            print(f'Skip completed seed {seed}', flush=True)
        else:
            if force and (seed_dir / 'COMPLETED.json').exists():
                # Preserve previous completed evidence on explicit force.
                archive = seed_dir.with_name(seed_dir.name + '_before_force_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f'))
                seed_dir.rename(archive)
            pending.append(seed)
    with ProcessPoolExecutor(max_workers=cfg['experiment']['workers'], initializer=init_worker,
                             initargs=(str(config_path),)) as executor:
        futures = [executor.submit(seed_run, seed) for seed in pending]
        for future in as_completed(futures):
            print(json.dumps(future.result()), flush=True)
    for seed in cfg['robustness']['seeds']:
        assert checkpoint_valid(output / 'seeds' / f'{seed:02d}', sha256(config_path))
    runs, profiles, pairs = summarize(cfg)
    save_json(output / 'COMPLETED.json', {'completed': True, 'n': len(runs),
                                        'protocol_version': cfg['experiment']['protocol_version'],
                                        'config_sha256': sha256(config_path)})
    print('Completed canonical perturbation robustness v2, n=' + str(len(runs)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['gate', 'fresh-hash', 'run'])
    parser.add_argument('--config', default='configs/perturbation_v2.yaml')
    parser.add_argument('--hash-output')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    if args.mode == 'gate':
        gate(args.config)
    elif args.mode == 'fresh-hash':
        fresh_hash(args.config, args.hash_output)
    else:
        run(args.config, args.force)
