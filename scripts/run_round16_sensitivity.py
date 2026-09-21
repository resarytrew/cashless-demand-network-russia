"""Optimizer/graph sensitivity and fixed-grid resolution; no model selection."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

from sbernet.config import load_config
from sbernet.clustering import louvain_labels
from sbernet.robustness.experiment_common import (
    load_baseline, save_json, profile_diagnostics, temporal_diagnostics, validity_metrics, distribution)
from sbernet.robustness.perturbation_v2 import perturb
from sbernet.robustness.reproduction_gate import graph_fingerprint, sha256
from round16_common import start_run, completed, seal

STATE = {}


def initialize(config):
    cfg = load_config(config)
    STATE.update(cfg=cfg, data=load_baseline(cfg))


def topology(graph):
    weights = np.array([d['weight'] for _, _, d in graph.edges(data=True)])
    degree = np.array([d for _, d in graph.degree()])
    components = sorted((len(c) for c in nx.connected_components(graph)), reverse=True)
    return {'edges': graph.number_of_edges(), 'components': len(components),
            'largest_component_n': components[0], 'isolates': int(np.sum(degree == 0)),
            **{f'degree_{k}': v for k, v in distribution(degree, [.05, .5, .95]).items()},
            **{f'weight_{k}': v for k, v in distribution(weights, [.05, .5, .95]).items()}}


def diagnostics(data, graph, labels, cfg, tags):
    actual = labels.reshape(data['reference'].shape)
    stats, monthly = temporal_diagnostics(data['reference'], actual, data['keys'])
    largest = int(np.unique(actual[-1], return_counts=True)[1].max())
    stats.update(largest_community_n_Dec=largest, largest_community_share_Dec=largest / len(data['names']), **tags)
    profiles, pairs = profile_diagnostics(data['reference'][-1], actual[-1], cfg['experiment']['profiles'])
    for rows in [profiles, pairs, monthly]:
        for row in rows:
            row.update(tags)
    return {'run': stats, 'profiles': profiles, 'pairs': pairs, 'monthly': monthly}


def job(task):
    mode, value = task
    cfg, data = STATE['cfg'], STATE['data']
    directory = Path(cfg['paths']['output_dir']) / 'runs' / f'{mode}_{value}'
    directory.mkdir(parents=True, exist_ok=False)
    graph = data['supra']
    gamma = cfg['clustering']['resolution']
    seed = cfg['clustering']['seed']
    hashes = {}
    if mode in ['graph_only', 'collapse_fixed']:
        protocol = load_config(cfg['experiment']['protocol_config'])
        graph, hashes = perturb(graph, value, protocol['robustness']['perturbation'])
        old = json.loads((Path(cfg['experiment']['combined_dir']) / 'seeds' / f'{value:02d}' / 'graph_hashes.json').read_text())
        if hashes != old:
            raise ValueError(f'Perturbed graph does not reproduce v2 seed {value}')
        seed = cfg['experiment']['fixed_louvain_seed']
    elif mode == 'optimizer_only':
        seed = value
    elif mode == 'resolution':
        gamma = value
    else:
        raise ValueError(mode)
    before = graph_fingerprint(graph)
    labels = louvain_labels(graph, gamma, seed)
    np.save(directory / 'supra_labels.npy', labels)
    tags = {'mode': mode, 'seed': int(value) if mode != 'resolution' else seed,
            'louvain_seed': seed, 'gamma': gamma}
    raw = diagnostics(data, graph, labels, cfg, tags)
    if mode == 'resolution':
        sl = louvain_labels(data['static'], gamma, seed)
        np.save(directory / 'static_labels.npy', sl)
        sm = validity_metrics(data['static'], sl, data['matrices'][data['keys'][-1]])
        sm['Q_resolution'] = nx.community.modularity(data['static'],
            [set(np.where(sl == c)[0]) for c in np.unique(sl)], weight='weight', resolution=gamma)
        raw['run'].update({f'static_{k}': v for k, v in sm.items()})
        raw['run']['mean_communities_per_month'] = float(np.mean([r['K'] for r in raw['monthly']]))
        raw['run']['graph_topology_unchanged'] = graph_fingerprint(graph) == before
    if mode == 'collapse_fixed':
        raw['graph_diagnostics'] = topology(graph)
        raw['graph_diagnostics']['reference_components'] = nx.number_connected_components(data['supra'])
        raw['graph_diagnostics']['connectivity_changed'] = raw['graph_diagnostics']['components'] != raw['graph_diagnostics']['reference_components']
        raw['run'].update(validity_metrics(graph, labels))
        oldlabels = np.load(Path(cfg['experiment']['combined_dir']) / 'seeds' / f'{value:02d}' / 'supra_labels.npy')
        oldraw = diagnostics(data, graph, oldlabels, cfg, {**tags, 'mode': 'combined', 'louvain_seed': value})
        oldraw['run'].update(validity_metrics(graph, oldlabels))
        raw['combined'] = oldraw
        # December induced graph quality is distinct from full-supra quality.
        n = len(data['names']); offset = (len(data['keys']) - 1) * n
        decgraph = nx.relabel_nodes(graph.subgraph(range(offset, offset + n)), lambda v: v - offset)
        for target, lab in [(raw, labels), (oldraw, oldlabels)]:
            target['run'].update({f'Dec_{k}': v for k, v in validity_metrics(decgraph, lab.reshape(-1, n)[-1]).items()})
    save_json(directory / 'graph_identity.json', {'fingerprint': before, 'perturbation': hashes})
    save_json(directory / 'raw_results.json', raw)
    seal(directory)
    return {'task': task, 'Dec_ARI': raw['run']['ARI_Dec2024'], 'largest_share': raw['run']['largest_community_share_Dec']}


def aggregate(cfg, out, tasks, kind):
    raw = [json.loads((out / 'runs' / f'{m}_{v}' / 'raw_results.json').read_text()) for m, v in tasks]
    if kind == 'decomposition':
        data = load_baseline(cfg)
        for seed in range(50):
            path = Path(cfg['experiment']['combined_dir']) / 'seeds' / f'{seed:02d}'
            cp = json.loads((path / 'COMPLETED.json').read_text())
            for name, h in cp['files_sha256'].items():
                if sha256(path / name) != h:
                    raise ValueError(f'Corrupt combined run {seed}: {name}')
            labels = np.load(path / 'supra_labels.npy')
            raw.append(diagnostics(data, data['supra'], labels, cfg, {'mode': 'combined', 'seed': seed, 'louvain_seed': seed, 'gamma': .5}))
    prefix = 'perturbation_decomposition' if kind == 'decomposition' else 'resolution_sensitivity'
    tables = {}
    for field, suffix in [('run', 'summary' if kind == 'resolution' else 'runs'),
                          ('profiles', 'archetypes'), ('pairs', 'pairs'), ('monthly', 'monthly')]:
        rows = [r[field] for r in raw] if field == 'run' else [v for r in raw for v in r[field]]
        tables[field] = pd.DataFrame(rows)
        tables[field].to_csv(out / f'{prefix}_{suffix}.csv', index=False)
    if kind == 'decomposition':
        summaries = []
        for field, idcol, metrics in [
            ('run', None, ['ARI_all_supra', 'NMI_all_supra', 'ARI_Dec2024', 'NMI_Dec2024',
                          'K_supra', 'K_Dec2024', 'largest_community_n_Dec', 'largest_community_share_Dec',
                          'mean_switches', 'median_switches', 'share_le2_switches']),
            ('profiles', 'archetype', ['retention', 'precision', 'Jaccard', 'within_pair_coassignment']),
            ('pairs', 'pair', ['cross_coassignment'])]:
            table = tables[field]
            table = table[table['mode'].isin(['optimizer_only', 'graph_only', 'combined'])]
            for keys, group in table.groupby(['mode'] + ([idcol] if idcol else [])):
                for metric in metrics:
                    summaries.append({'mode': keys[0], 'scope': field, 'group': keys[1] if idcol else 'all',
                                      'metric': metric, **distribution(group[metric], cfg['experiment']['quantiles'])})
        pd.DataFrame(summaries).to_csv(out / 'perturbation_decomposition_summary.csv', index=False)
        collapse, profiles, pairs = [], [], []
        for r in raw:
            if r['run']['mode'] == 'collapse_fixed':
                for case in [r, r['combined']]:
                    collapse.append({**case['run'], **r['graph_diagnostics']})
                    profiles.extend(case['profiles']); pairs.extend(case['pairs'])
        pd.DataFrame(collapse).to_csv(out / 'perturbation_collapse_cases.csv', index=False)
        pd.DataFrame(profiles).to_csv(out / 'perturbation_collapse_archetypes.csv', index=False)
        pd.DataFrame(pairs).to_csv(out / 'perturbation_collapse_pairs.csv', index=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('kind', choices=['decomposition', 'resolution'])
    parser.add_argument('--config', required=True)
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    cfg = load_config(args.config)
    load_baseline(cfg)  # Fail before output creation if the baseline gate is missing/stale.
    if args.kind == 'decomposition':
        pg = json.loads((Path(cfg['experiment']['protocol_gate_dir']) / 'gate/gate.json').read_text())
        if not pg['passed'] or pg['config_sha256'] != sha256(cfg['experiment']['protocol_gate_config']):
            raise ValueError('Fresh protocol v2 gate missing, failed or stale')
    out = start_run(args.config, cfg, args.force)
    if args.kind == 'decomposition':
        tasks = [(mode, seed) for mode in ['optimizer_only', 'graph_only'] for seed in cfg['experiment']['seeds']]
        tasks += [('collapse_fixed', s) for s in cfg['experiment']['collapse_seeds']]
    else:
        tasks = [('resolution', g) for g in cfg['experiment']['gammas']]
    pending = [t for t in tasks if not completed(out / 'runs' / f'{t[0]}_{t[1]}')]
    print(f'{len(pending)} pending; {len(tasks)-len(pending)} verified checkpoints skipped', flush=True)
    if not pending and completed(out / 'aggregate'):
        print('Verified complete run; no files rewritten', flush=True)
        return
    with ProcessPoolExecutor(max_workers=cfg['experiment']['workers'], initializer=initialize, initargs=(args.config,)) as pool:
        for future in as_completed([pool.submit(job, t) for t in pending]):
            print(json.dumps(future.result()), flush=True)
    aggregate(cfg, out, tasks, args.kind)
    marker = out / 'aggregate'; marker.mkdir(exist_ok=False)
    save_json(marker / 'COMPLETED.json', {'files_sha256': {f'../{p.name}': sha256(p) for p in out.glob('*.csv')}})


if __name__ == '__main__':
    main()
