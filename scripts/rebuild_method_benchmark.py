"""Single-geometry canonical benchmark with explicit unavailable historical families."""
import argparse
import json
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans, SpectralClustering, AgglomerativeClustering

from sbernet.config import load_config
from sbernet.clustering import louvain_labels
from sbernet.robustness.experiment_common import load_baseline, validity_metrics, make_manifest, save_json
from sbernet.robustness.reproduction_gate import sha256, graph_fingerprint
from round16_common import require_fresh, array_hash

UNAVAILABLE = 'UNREPRODUCIBLE_HISTORICAL_BENCHMARK_COMPONENT'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='configs/benchmark_canonical.yaml')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    cfg = load_config(args.config); data = load_baseline(cfg)
    out = require_fresh(cfg['paths']['output_dir'], args.force)
    ex = cfg['experiment']; x = data['matrices'][ex['input_month']]; graph = data['static']
    seed = cfg['clustering']['seed']; gamma = cfg['clustering']['resolution']; k = ex['requested_k']
    rows, meta = [], []
    manifest = make_manifest(args.config, cfg)
    manifest.update(script_sha256=sha256(__file__), feature_sha256=array_hash(x), graph=graph_fingerprint(graph),
                    historical_source_sha256=sha256(ex['historical_tables']))
    save_json(out / 'run_manifest.json', manifest)
    for method in ex['algorithms']:
        params = {}
        if method == 'Louvain':
            params = {'resolution': gamma, 'seed': seed}
            labels = louvain_labels(graph, gamma, seed)
        elif method == 'Greedy':
            params = {'resolution': gamma, 'weight': 'weight', 'cutoff': 1, 'best_n': None}
            groups = nx.community.greedy_modularity_communities(graph, **params)
            labels = np.empty(len(x), dtype=int)
            for i, group in enumerate(groups):
                labels[list(group)] = i
        elif method == 'Spectral':
            params = {**ex['spectral'], 'n_clusters': k, 'random_state': seed}
            affinity = nx.to_scipy_sparse_array(graph, nodelist=range(len(x)), weight='weight', format='csr', dtype=float)
            affinity.indices = affinity.indices.astype(np.int32)
            affinity.indptr = affinity.indptr.astype(np.int32)
            labels = SpectralClustering(**params).fit_predict(affinity)
        elif method == 'KMeans':
            params = {**ex['kmeans'], 'n_clusters': k, 'random_state': seed}
            labels = KMeans(**params).fit_predict(x)
        elif method == 'Ward':
            params = {'n_clusters': k, 'linkage': 'ward', 'metric': 'euclidean'}
            labels = AgglomerativeClustering(**params).fit_predict(x)
        else:
            raise ValueError(method)
        pd.DataFrame({'mo': data['names'], 'community': labels}).to_csv(out / f'{method}_labels.csv', index=False)
        metrics = validity_metrics(graph, labels, x)
        if metrics['S_Dbw'] is None:
            metrics['S_Dbw_status'] = 'S_Dbw undefined under the fixed Round-14 implementation'
        rows.append({'method': method, 'family': 'Aitchison+level', 'status': 'CANONICAL_REBUILT', **metrics})
        meta.append({'method': method, 'input_period': ex['input_month'], 'municipalities': len(x),
            'feature_geometry': 'sqrt(.70)*CLR/median_pair_distance + sqrt(.30)*robust_z(log(Total))/median_pair_distance; 7D',
            'feature_sha256': array_hash(x), 'distance_metric': 'Euclidean in the fixed 7D reference geometry',
            'graph_construction': 'undirected mutual-kNN adaptive RBF; same graph for all network metrics',
            'k': cfg['network']['k'], 'isolate_handling': 'static nearest-neighbor fallback enabled',
            'algorithm': method, 'algorithm_parameters': json.dumps(params, sort_keys=True),
            'requested_K': k if method in ['Spectral', 'KMeans', 'Ward'] else None,
            'resulting_K': metrics['K'], 'random_seed': seed if method in ['Louvain', 'Spectral', 'KMeans'] else None,
            'silhouette_geometry': 'Euclidean fixed reference December 7D features',
            'CH_geometry': 'fixed reference December 7D features; CH divided by N',
            'AVI_definition': 'mean_c internal ordered adjacency count/(internal+external); unweighted',
            'AVU_definition': 'sum_c sum_d!=c block_cd/(external_c+external_d-block_cd)/K; unweighted; zero denominators=0',
            'MQ_definition': 'weighted Newman-Girvan modularity on same reference static graph, resolution=1',
            'S_Dbw_status': metrics['S_Dbw_status'],
            'historical_parameter_identity': 'UNESTABLISHED; explicit Round16 specification, not a reconstruction of undocumented old settings'})
        print(method, {m: metrics[m] for m in ['K','SW','CHn','AVI','AVU','MQ']}, flush=True)
    for family in ex['unavailable_historical_families']:
        reason = ('No historical generator/config/labels in repository or supplied DOCX: '
                  'trajectory representation, normalization, lag/window/DTW constraint and graph tie rules unestablished. No guessed reconstruction.')
        rows.append({'method': family, 'family': family, 'status': UNAVAILABLE, 'reason': reason})
        meta.append({'method': family, 'algorithm': 'Louvain (historical table context)', 'status': UNAVAILABLE,
                     'input_period': 'UNESTABLISHED', 'feature_geometry': 'UNESTABLISHED', 'reason': reason})
    benchmark = pd.DataFrame(rows); benchmark.to_csv(out / 'canonical_method_benchmark.csv', index=False)
    pd.DataFrame(meta).to_csv(out / 'canonical_method_benchmark_metadata.csv', index=False)
    tables = json.loads(Path(ex['historical_tables']).read_text(encoding='utf-8'))
    diff = []
    for table_id in [2, 3]:
        headers = tables[table_id][0]
        for row in tables[table_id][1:]:
            method = 'Louvain' if row[0] == 'Aitchison+level' else row[0]
            new = benchmark.set_index('method').loc[method]
            for name in ['SW', 'CH/N', 'AVI', 'AVU', 'MQ']:
                old = float(row[headers.index(name)])
                value = new.get('CHn' if name == 'CH/N' else name, np.nan)
                diff.append({'method': method, 'metric': name, 'historical_value': old, 'canonical_value': value,
                             'absolute_delta': abs(value - old), 'relative_delta': (value - old) / abs(old) if old else np.nan,
                             'status': new['status'],
                             'historical_source': f'reference/round16/competition_source.docx; document table {table_id+1}; row {row[0]}'})
    pd.DataFrame(diff).to_csv(out / 'benchmark_old_vs_canonical_diff.csv', index=False)
    (out / 'CANONICAL_BENCHMARK_AUDIT.md').write_text(
        '# Canonical benchmark — Round 16\n\n'
        '`canonical_method_benchmark.csv` is the only admissible source of method-comparison numbers. '
        'Five algorithms use the same reconstructed December geometry and the same graph for network evaluation. '
        'K=9 is fixed from reference static K, not selected using metrics. Explicit Round16 algorithm parameters are in the metadata. '
        'Their identity to undocumented historical algorithm settings is not claimed.\n\n'
        'Four historical distance/trajectory families are UNREPRODUCIBLE_HISTORICAL_BENCHMARK_COMPONENT. '
        'The supplied DOCX contains rounded scores but no executable provenance. No alternative trajectory experiment was invented. '
        'Those rows must not appear with old numeric scores in competition comparisons.\n\n'
        'S_Dbw uses exactly Round14; undefined means a zero center-density denominator under that implementation. '
        'It does not rule out all other definitions. No audit variant or old finite score is used for ranking.\n\n'
        'Diff: absolute_delta=abs(new-old); relative_delta=(new-old)/abs(old). Historical inputs are rounded DOCX values. '
        'A difference cannot by itself identify its historical cause; historical features/parameters/metric scripts are unavailable.\n', encoding='utf-8')


if __name__ == '__main__':
    main()
