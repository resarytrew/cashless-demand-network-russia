"""Run the preserved historical pilot without changing its numerical procedure."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import pickle
import shutil

import networkx as nx
import numpy as np
import pandas as pd

from sbernet.config import load_config
from sbernet.clustering import louvain_labels
from .reproduction_gate import graph_fingerprint, sha256, similarity, baseline_passed, versions


def import_historical(path):
    spec = importlib.util.spec_from_file_location('canonical_pilot', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def identical_igraph(source):
    import igraph as ig
    edges = list(source.edges(data=True))
    target = ig.Graph(n=source.number_of_nodes(),
                      edges=[(u, v) for u, v, _ in edges], directed=False)
    target.es['weight'] = [float(d['weight']) for _, _, d in edges]
    roundtrip = nx.Graph()
    roundtrip.add_nodes_from(range(target.vcount()))
    roundtrip.add_weighted_edges_from((u, v, w) for (u, v), w in
                                      zip(target.get_edgelist(), target.es['weight']))
    expected, actual = graph_fingerprint(source), graph_fingerprint(roundtrip)
    if expected != actual:
        raise ValueError('Leiden graph conversion changed nodes/edges/weights')
    return target, {'passed': True, 'source': expected, 'igraph_input': actual}


def run(gate_dir, config_path):
    gate_dir = Path(gate_dir)
    if not json.loads((gate_dir / 'baseline_gate.json').read_text())['passed']:
        raise ValueError('Baseline gate did not pass')
    cfg = load_config(config_path)
    settings = cfg['robustness']['perturbation']
    output = gate_dir / 'pilot'
    output.mkdir(exist_ok=False)
    refdir = Path(settings['reference_dir'])
    inputs = [refdir / f for f in ['supra_same_object_stability_run_summary.csv',
                                  'supra_same_object_stability_archetype_details.csv',
                                  'BE_boundary_instability_by_perturbation.csv']]
    runner = Path(settings['historical_runner'])
    manifest = {'packages': versions(), 'config_sha256': sha256(config_path),
                'inputs_sha256': {str(p): sha256(p) for p in inputs + [runner]},
                'atol': settings['comparison_atol'], 'rtol': settings['comparison_rtol'],
                'adaptation': 'Unmodified runner imported; only module R points to staged input aliases. '
                              'Profile IDs [1,3,7,8,9,10,11] from RESEARCH_STATE section 9. '
                              'Historical fork-based main is not invoked; build_shared and one_run are called directly.'}
    (output / 'run_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    with (gate_dir / 'baseline_graphs.pkl').open('rb') as fh:
        baseline = pickle.load(fh)
    graph_check = {}
    for key in ['static', 'supra']:
        _, graph_check[key] = identical_igraph(baseline[key])
    graph_check['packages'] = versions()
    graph_check['config_sha256'] = sha256('configs/baseline.yaml')
    (gate_dir / 'leiden_graph_identity_gate.json').write_text(json.dumps(graph_check, indent=2), encoding='utf-8')
    print('Leiden graph identity gate passed for static and supra', flush=True)

    stage = output / 'historical_input_aliases'
    stage.mkdir()
    shutil.copyfile(cfg['paths']['spending_zip'], stage / 'potrebitelskie-beznalicnye-rashody-na-urovne-munizipalnyh-obrazovanij_ru_1764079373653.csv.zip')
    shutil.copyfile('outputs/baseline/supra_labels.csv', stage / 'supra_labels_omega_2.0.csv')
    pd.DataFrame({'cluster': [1, 3, 7, 8, 9, 10, 11]}).to_csv(stage / 'dec2024_archetypes_final.csv', index=False)
    historical = import_historical(runner)
    historical.R = stage
    print('Building canonical pilot graph with unmodified historical build_shared', flush=True)
    shared = historical.build_shared()
    graph = nx.Graph()
    graph.add_nodes_from(range(shared['N'] * shared['T']))
    graph.add_weighted_edges_from(shared['base'])
    graph.add_weighted_edges_from(shared['temporal'])
    lab = louvain_labels(graph, cfg['clustering']['resolution'], cfg['clustering']['seed'])
    metrics = {'full_supra': similarity(shared['ref_flat'], lab),
               'temporal_Dec2024': similarity(shared['ref_dec'], lab.reshape(shared['T'], shared['N'])[-1])}
    canonical = {'metrics': metrics, 'passed': baseline_passed(metrics),
                 'graph_fingerprint': graph_fingerprint(graph),
                 'same_graph_as_repository': graph_fingerprint(graph) == graph_fingerprint(baseline['supra'])}
    (output / 'canonical_baseline_gate.json').write_text(json.dumps(canonical, indent=2), encoding='utf-8')
    print('Canonical runner baseline: ' + json.dumps(canonical), flush=True)
    if not canonical['passed']:
        (output / 'PERTURBATION_PILOT_REPRODUCIBILITY_FAILURE.md').write_text(
            '# Canonical pilot reconstruction failure\n\nHistorical runner baseline did not reproduce. '
            'No perturbation seeds, Leiden or high-rep experiment launched.\n\n```json\n' +
            json.dumps(canonical, indent=2) + '\n```\n', encoding='utf-8')
        return False
    with (output / 'canonical_shared.pkl').open('wb') as fh:
        pickle.dump(shared, fh)
    historical.init_worker(shared)
    ref_runs = pd.read_csv(inputs[0]).query("mode == 'perturb'").set_index('seed')
    ref_profiles = pd.read_csv(inputs[1]).query("mode == 'perturb'").set_index(['seed', 'archetype'])
    ref_be = pd.read_csv(inputs[2]).set_index('perturb_seed')
    comparisons = []
    def compare(seed, scope, name, actual, expected):
        comparisons.append({'seed': seed, 'scope': scope, 'metric': name,
                            'actual': float(actual), 'expected': float(expected),
                            'delta': float(actual - expected),
                            'passed': bool(np.isclose(actual, expected,
                                                     atol=settings['comparison_atol'],
                                                     rtol=settings['comparison_rtol']))})
    for seed in cfg['robustness']['pilot_seeds']:
        print(f'Canonical pilot seed {seed} started', flush=True)
        result, profiles = historical.one_run(seed)
        # Raw seed output is durable before comparisons and before any summary.
        (output / f'seed_{seed:02d}_raw.json').write_text(
            json.dumps({'run': result, 'profiles': profiles}, indent=2), encoding='utf-8')
        pd.DataFrame([result]).to_csv(output / f'seed_{seed:02d}_run.csv', index=False)
        pd.DataFrame(profiles).to_csv(output / f'seed_{seed:02d}_profiles.csv', index=False)
        for metric in ['K_supra', 'ARI_all_supra', 'NMI_all_supra', 'ARI_Dec2024', 'NMI_Dec2024']:
            ref_name = metric if metric == 'K_supra' else metric + '_vs_reference'
            compare(seed, 'run', metric, result[metric], ref_runs.loc[seed, ref_name])
        for metric, ref_name in [('K_Dec2024', 'K_Dec2024'), ('BE_cross_coassignment', 'B_E_cross_coassignment'),
                                 ('B_within_pair_coassignment', 'B_within_pair_coassignment'),
                                 ('E_within_pair_coassignment', 'E_within_pair_coassignment')]:
            compare(seed, 'BE', metric, result[metric], ref_be.loc[seed, ref_name])
        for p in profiles:
            ref = ref_profiles.loc[(seed, p['profile'])]
            for metric, ref_name in [('n', 'n_reference'), ('best_destination_share', 'best_destination_share'),
                                     ('within_pair_coassignment', 'within_reference_pair_coassignment'),
                                     ('n_destinations', 'n_destinations')]:
                compare(seed, p['profile'], metric, p[metric], ref[ref_name])
        pd.DataFrame(comparisons).to_csv(output / 'pilot_comparisons.csv', index=False)
        failed = [r for r in comparisons if not r['passed']]
        print(f'Seed {seed}: {len(failed)} failed comparisons', flush=True)
        if failed:
            (output / 'PERTURBATION_PILOT_REPRODUCIBILITY_FAILURE.md').write_text(
                '# Canonical perturbation pilot reproduction failure\n\n'
                f'Stopped after seed {seed}. No later pilot seeds, Leiden or high-rep experiment launched. '
                'The historical runner and reference CSVs were not modified. '
                'Raw results saved before comparisons.\n\n'
                f'Declared tolerance: atol={settings["comparison_atol"]}, rtol={settings["comparison_rtol"]}. '
                'Exact differences are in pilot_comparisons.csv.\n\n```json\n' +
                json.dumps(failed, indent=2) + '\n```\n', encoding='utf-8')
            return False
    (output / 'pilot_gate.json').write_text(json.dumps({'passed': True,
        'seeds': cfg['robustness']['pilot_seeds'], 'max_absolute_delta': max(abs(r['delta']) for r in comparisons)}, indent=2), encoding='utf-8')
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--gate-dir', required=True)
    parser.add_argument('--config', default='configs/perturbation_highrep.yaml')
    args = parser.parse_args()
    raise SystemExit(0 if run(args.gate_dir, args.config) else 1)
