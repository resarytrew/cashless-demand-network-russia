"""Same-graph Leiden experiment, independently gated from historical perturbation."""
import argparse
from pathlib import Path

import leidenalg
import numpy as np
import pandas as pd

from sbernet.config import load_config
from .experiment_common import (load_baseline, make_manifest, save_json, profile_diagnostics,
                                temporal_diagnostics, validity_metrics, distribution)
from .pilot_gate import identical_igraph
from .reproduction_gate import similarity


def run(config_path):
    cfg = load_config(config_path)
    data = load_baseline(cfg)
    output = Path(cfg['paths']['output_dir'])
    output.mkdir(parents=True, exist_ok=False)
    save_json(output / 'run_manifest.json', make_manifest(config_path, cfg))
    labels = {}; checks = {}
    for scope in ['static', 'supra']:
        graph, checks[scope] = identical_igraph(data[scope])
        # Persist conversion proof before the algorithm is invoked.
        save_json(output / 'graph_identity.json', checks)
        print(f'Leiden {scope}: graph identity PASS; optimizing fixed resolution', flush=True)
        partition = leidenalg.find_partition(
            graph, leidenalg.RBConfigurationVertexPartition, weights='weight',
            resolution_parameter=cfg['clustering']['resolution'],
            seed=cfg['clustering']['seed'], n_iterations=cfg['clustering']['n_iterations'])
        labels[scope] = np.asarray(partition.membership, dtype=np.int64)
        np.save(output / f'{scope}_labels.npy', labels[scope])
        save_json(output / f'{scope}_raw.json', {'seed': cfg['clustering']['seed'],
                  'K': len(partition), 'quality_RBConfiguration': partition.quality(),
                  'iterations_setting': cfg['clustering']['n_iterations']})
    actual = labels['supra'].reshape(data['reference'].shape)
    pd.DataFrame(actual.T, index=data['names'], columns=data['keys']).to_csv(output / 'supra_labels.csv')
    pd.DataFrame({'mo': data['names'], 'community': labels['static']}).to_csv(output / 'static_dec2024_labels.csv', index=False)
    metrics = []
    for algorithm, lab in [('louvain', data['reference_static']), ('leiden', labels['static'])]:
        metrics.append({'algorithm': algorithm, **validity_metrics(data['static'], lab, data['matrices'][data['keys'][-1]]),
                        **similarity(data['reference_static'], lab)})
    pd.DataFrame(metrics).to_csv(output / 'leiden_static_metrics.csv', index=False)
    temporal, monthly = temporal_diagnostics(data['reference'], actual, data['keys'])
    temporal.update(validity_metrics(data['supra'], labels['supra']))
    pd.DataFrame([temporal]).to_csv(output / 'leiden_temporal_summary.csv', index=False)
    pd.DataFrame(monthly).to_csv(output / 'leiden_monthly_similarity.csv', index=False)
    profiles, pairs = profile_diagnostics(data['reference'][-1], actual[-1], cfg['experiment']['profiles'])
    pd.DataFrame(profiles).to_csv(output / 'leiden_archetype_retention.csv', index=False)
    pd.DataFrame(pairs).to_csv(output / 'leiden_pair_coassignment.csv', index=False)
    monthly_metrics = []
    for t, key in enumerate(data['keys']):
        for algorithm, lab in [('louvain', data['reference'][t]), ('leiden', actual[t])]:
            monthly_metrics.append({'month': key, 'algorithm': algorithm,
                **validity_metrics(data['monthly'][t], lab, data['matrices'][key])})
    pd.DataFrame(monthly_metrics).to_csv(output / 'leiden_monthly_metrics.csv', index=False)
    similarity_summary = []
    for key in ['ARI', 'NMI', 'adjacent_ARI', 'adjacent_NMI', 'same_label_share']:
        similarity_summary.append({'metric': key, **distribution([r[key] for r in monthly if key in r], cfg['experiment']['quantiles'])})
    pd.DataFrame(similarity_summary).to_csv(output / 'leiden_monthly_similarity_summary.csv', index=False)
    save_json(output / 'COMPLETED.json', {'completed': True, 'seed': cfg['clustering']['seed'],
                                        'algorithm': 'leiden', 'graph_identity_passed': True})
    print(pd.DataFrame(metrics).to_string(index=False), flush=True)
    print(pd.DataFrame([temporal]).to_string(index=False), flush=True)
    print(pd.DataFrame(profiles).to_string(index=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='configs/leiden.yaml')
    args = parser.parse_args()
    run(args.config)
