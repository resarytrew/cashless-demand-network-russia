"""Build new evidence versions from completed round 14 and protocol-v2 artifacts."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from sbernet.config import load_config
from sbernet.robustness.experiment_common import (load_baseline, temporal_diagnostics,
                                               validity_metrics, save_json)
from sbernet.robustness.reproduction_gate import sha256


def read(path):
    return pd.read_csv(path, float_precision='round_trip')


def table(frame):
    def fmt(v):
        if isinstance(v, (float, np.floating)):
            return 'unavailable' if pd.isna(v) else f'{v:.6f}'
        return str(v)
    lines = ['| ' + ' | '.join(frame.columns) + ' |', '| ' + ' | '.join(['---'] * len(frame.columns)) + ' |']
    lines += ['| ' + ' | '.join(fmt(v) for v in row) + ' |' for row in frame.itertuples(index=False, name=None)]
    return '\n'.join(lines)


def write_new(path, text):
    with Path(path).open('x', encoding='utf-8') as fh:
        fh.write(text.rstrip() + '\n')


def main():
    leiden = Path('outputs/leiden_robustness')
    pert = Path('outputs/perturbation_v2')
    evidence = Path('outputs/evidence_v2_2_0'); evidence.mkdir(exist_ok=False)
    assert json.loads((leiden / 'COMPLETED.json').read_text())['completed']
    assert json.loads((pert / 'COMPLETED.json').read_text())['n'] == 50
    runs = read(pert / 'perturbation_v2_50_runs.csv')
    pro = read(pert / 'perturbation_v2_50_archetype_retention.csv')
    pairs = read(pert / 'perturbation_v2_50_pair_coassignment.csv')
    summary = read(pert / 'perturbation_v2_50_summary.csv')
    assert set(runs.seed) == set(range(50)) and len(runs) == 50
    assert len(pro) == 350 and not pro.duplicated(['seed', 'archetype']).any()
    assert len(pairs) == 1050 and not pairs.duplicated(['seed', 'pair']).any()
    lp = read(leiden / 'leiden_archetype_retention.csv')
    lpair = read(leiden / 'leiden_pair_coassignment.csv')
    lt = read(leiden / 'leiden_temporal_summary.csv')
    ls = read(leiden / 'leiden_static_metrics.csv')
    prior = read('outputs/alpha_sensitivity/archetype_status_round13_alpha.csv')
    retained = summary.query("scope == 'archetype' and metric == 'retention'").set_index('group')
    precision = summary.query("scope == 'archetype' and metric == 'precision'").set_index('group')
    jaccard = summary.query("scope == 'archetype' and metric == 'Jaccard'").set_index('group')
    within = summary.query("scope == 'archetype' and metric == 'within_pair_coassignment'").set_index('group')
    ps = summary.query("scope == 'pair'").set_index('group')
    notes14 = {
        'A': 'Reference December core and boundary largely retained in this algorithm swap; overlapping/context caveats remain.',
        'B': 'B core retained inside merged B/E destination; nationwide independent-profile framing remains rejected.',
        'C': 'Only part of C retained; no rehabilitation of beyond-context profile claim.',
        'D': 'D core retained inside a larger D/F destination; exact-boundary stability weakened.',
        'E': 'B/E nearly coassign; nested/contextual interpretation strengthened.',
        'F': 'Splits substantially between D- and G-dominated destinations; weak refinement/boundary interpretation strengthened.',
        'G': 'Broad December core retained with additional members; broad macroprofile interpretation retained, exact boundary caveat remains.'}
    contextual = {
        'A': 'Overlapping regime; context and poor-separation caveats remain.',
        'B': 'Federal-intracity nested subtype; retention alone does not establish B/E separation.',
        'C': 'Rejected as standalone beyond-context profile; perturbation persistence cannot reverse context-control evidence.',
        'D': 'Compact candidate core; D/F and A/D mixing must be separated from core retention.',
        'E': 'Nested/context-sensitive profile; B/E cross-coassignment describes boundary merging.',
        'F': 'Weak refinement/boundary population; examine D/F and F/G jointly.',
        'G': 'Broad macroprofile; high retention can reflect absorption into an even broader destination.'}
    affected = {'A': ['A/D'], 'B': ['B/E'], 'C': [], 'D': ['A/D', 'D/F'],
                'E': ['B/E'], 'F': ['D/F', 'F/G'], 'G': ['F/G']}
    notes15 = {}
    for p in retained.index:
        boundaries = '; '.join(f'{pair} cross mean={ps.loc[pair,"mean"]:.6f}, q10={ps.loc[pair,"q10"]:.6f}, q90={ps.loc[pair,"q90"]:.6f}' for pair in affected[p])
        notes15[p] = contextual[p] + ' ' + boundaries
    status14 = prior[['archetype', 'round13_status']].merge(lp, on='archetype')
    status14['round14_status'] = status14['round13_status']
    status14['leiden_interpretation'] = status14.archetype.map(notes14)
    status14['historical_perturbation_pilot_status'] = 'SUPERSEDED_NON_REPRODUCIBLE'
    status14.to_csv(leiden / 'archetype_status_round14_leiden.csv', index=False)
    status15 = prior[['archetype', 'round13_status']].copy()
    status15['round15_status'] = status15['round13_status']
    status15['perturbation_v2_n'] = 50
    for metric, frame in [('retention', retained), ('precision', precision), ('Jaccard', jaccard), ('within_pair_coassignment', within)]:
        for stat in ['mean', 'median', 'SD', 'min', 'max', 'q05', 'q10', 'q25', 'q75', 'q90', 'q95']:
            status15[f'{metric}_{stat}'] = status15.archetype.map(frame[stat])
    status15['perturbation_v2_boundary_note'] = status15.archetype.map(notes15)
    status15['historical_perturbation_pilot_status'] = 'SUPERSEDED_NON_REPRODUCIBLE'
    status15.to_csv(pert / 'archetype_status_round15_perturbation_v2.csv', index=False)

    # Historical full master matrix is unavailable; never fabricate its omitted evidence columns.
    matrix14 = prior[['archetype', 'round13_status']].merge(
        lp[['archetype', 'retention', 'precision', 'Jaccard', 'within_pair_coassignment']].rename(
            columns={k: 'leiden_' + k for k in ['retention', 'precision', 'Jaccard', 'within_pair_coassignment']}), on='archetype')
    matrix14['evidence_version'] = '2.1.0'
    matrix14['matrix_scope'] = 'repository_round13_plus_new_rounds; full_historical_master_unavailable'
    matrix14['historical_perturbation_pilot_status'] = 'SUPERSEDED_NON_REPRODUCIBLE'
    matrix14['historical_pilot_quantitative_evidence_used'] = False
    matrix14['leiden_boundary_note'] = matrix14.archetype.map(notes14)
    matrix14['perturbation_v2_n'] = 0
    matrix14.to_csv(evidence / 'MASTER_PROFILE_EVIDENCE_MATRIX_v2.1.0.csv', index=False)
    final = matrix14.copy(); final['evidence_version'] = '2.2.0'; final['perturbation_v2_n'] = 50
    for stat in ['mean', 'q10', 'min']:
        final[f'perturbation_v2_{stat}_retention'] = final.archetype.map(retained[stat])
    final['perturbation_v2_mean_precision'] = final.archetype.map(precision['mean'])
    final['perturbation_v2_mean_Jaccard'] = final.archetype.map(jaccard['mean'])
    final['perturbation_v2_boundary_note'] = final.archetype.map(notes15)
    final.to_csv(evidence / 'MASTER_PROFILE_EVIDENCE_MATRIX_v2.2.0.csv', index=False)

    cfg = load_config('configs/leiden.yaml'); data = load_baseline(cfg)
    reference_stats, _ = temporal_diagnostics(data['reference'], data['reference'], data['keys'])
    reference_stats.update(validity_metrics(data['supra'], data['reference'].ravel()))
    temporal_compare = pd.DataFrame([{'algorithm': 'louvain', **reference_stats}, {'algorithm': 'leiden', **lt.iloc[0].to_dict()}])
    temporal_compare.to_csv(leiden / 'leiden_temporal_baseline_comparison.csv', index=False)
    lm = read(leiden / 'leiden_monthly_metrics.csv')
    metric_summary = lm.groupby('algorithm')[['SW', 'CHn', 'MQ', 'AVI', 'AVU']].mean().reset_index()
    metric_summary.to_csv(leiden / 'leiden_mean_monthly_metrics.csv', index=False)
    important_pairs = ['B/E', 'D/F', 'F/G', 'A/D']
    pair_table = ps.loc[important_pairs, ['mean', 'median', 'SD', 'min', 'q10', 'q90', 'max']].reset_index().rename(columns={'group': 'pair'})
    profile_table = pd.DataFrame({'archetype': list(retained.index), 'mean_retention': retained['mean'],
        'q10_retention': retained['q10'], 'min_retention': retained['min'],
        'mean_precision': precision['mean'], 'mean_Jaccard': jaccard['mean'],
        'mean_within_pair': within['mean']}).reset_index(drop=True)
    run_table = summary.query("scope == 'run' and metric in ['ARI_all_supra','NMI_all_supra','ARI_Dec2024','NMI_Dec2024','K_supra','K_Dec2024','mean_switches','share_le2_switches']")
    # Descriptive leave-one-out check; no seed is dropped from primary evidence.
    loo = []
    for pair in important_pairs:
        vals = pairs.loc[pairs.pair.eq(pair), 'cross_coassignment'].to_numpy()
        means = [(vals.sum() - v) / (len(vals) - 1) for v in vals]
        loo.append({'pair': pair, 'full_mean': vals.mean(), 'leave_one_out_mean_min': min(means),
                    'leave_one_out_mean_max': max(means), 'share_lt_0_1': np.mean(vals < 0.1),
                    'share_gt_0_5': np.mean(vals > 0.5), 'share_gt_0_9': np.mean(vals > 0.9)})
    pd.DataFrame(loo).to_csv(pert / 'perturbation_v2_boundary_tail_and_leave_one_out.csv', index=False)
    source_link = 'https://link.springer.com/article/10.1134/S1064562425700589'
    write_new(leiden / 'LEIDEN_ROBUSTNESS_AUDIT.md', f'''# Leiden robustness audit — Round 14

Independent same-graph algorithm swap authorized after baseline and graph-identity gates PASS. Historical perturbation failure does not block this test. Static December and full temporal supra graphs were loaded from the passed baseline reconstruction, checked against saved hashes, and passed exact NetworkX-to-igraph roundtrip checks immediately before optimization. Node/edge/weight/config evidence is in graph_identity.json and run_manifest.json. Historical evidence and baseline were not overwritten.

Algorithm: igraph 1.0.0 + leidenalg 0.12.0, RBConfigurationVertexPartition, weighted undirected graphs, resolution_parameter=0.5, seed=0, n_iterations=-1 (iterate until no improvement). No resolution or K tuning. Static isolate fallback ON, temporal fallback OFF; all feature and coupling parameters unchanged. Raw membership arrays and quality outputs were saved before derived metrics.

MQ is weighted Newman-Girvan modularity at resolution 1. Q_resolution_0_5 is also reported, separating the optimized objective from conventional MQ. Feature metrics are calculated on 1904-node monthly layers, not a dense supra distance matrix. SW and CH/N use scikit-learn. AVI and AVU use unweighted block adjacency counts following equations 18–21 in [Shalileh et al.]({source_link}); zero graph denominators contribute 0. The static Louvain SW/CH/AVI/AVU reproduce the unified alpha-audit values to reported precision.

S_Dbw is a newly explicit variant: elementwise population variances; radius=sqrt(sum cluster variance-vector norms)/K; counts inside or on radius around centers/midpoints; Scat plus mean between-density/max-center-density ratios. If a denominator is zero, return undefined, without epsilon or an invented finite value. Both static partitions hit this case. The literature page prints a reversed density indicator; this implementation explicitly uses inside-radius counts. No formula was changed after seeing results. This variant must not replace historical frozen S_Dbw tables. Monthly S_Dbw statuses are recorded per row; unavailable values are not evidence of an algorithm advantage.

All 24 monthly similarities and 23 adjacent-month similarities/persistence values are saved. A-G metrics refer to temporal December reference profiles, not static communities. Retention, precision, Jaccard, within-pair and all 21 cross-pair coassignments are label-invariant. No universal winning algorithm is selected.

Versioning: archetype_status_round14_leiden.csv and new master matrix v2.1.0. Full historical master is absent; the new repository matrix carries available Round 13 status, new numeric evidence and explicit provenance limitations. The historical n=5 is not quantitative evidence. Environment/source/config hashes and null git commit (no .git in supplied working copy) are recorded in the manifest.
''')
    write_new(leiden / 'LEIDEN_FINDINGS.md', f'''# Leiden findings — Round 14

The exact graph is preserved but the partition changes materially: full-supra ARI={lt.iloc[0].ARI_all_supra:.6f}, NMI={lt.iloc[0].NMI_all_supra:.6f}; December temporal ARI={lt.iloc[0].ARI_Dec2024:.6f}, NMI={lt.iloc[0].NMI_Dec2024:.6f}. Leiden gives {int(lt.iloc[0].K_supra)} supra communities and {int(lt.iloc[0].K_Dec2024)} December communities. The clean swap weakens exact algorithm-independence; it does not remove all broad structure.

Static comparison (one consistent metric implementation):

{table(ls[['algorithm','K','SW','CHn','MQ','Q_resolution_0_5','AVI','AVU']])}

Leiden improves some feature and optimized-objective metrics while conventional static MQ decreases. S_Dbw is undefined for both under the documented zero-denominator rule. No single ranking follows.

Temporal persistence:

{table(temporal_compare[['algorithm','mean_switches','median_switches','share_zero_switches','share_le2_switches','mean_adjacent_ARI','mean_adjacent_NMI']])}

Reference December profiles:

{table(lp[['archetype','retention','precision','Jaccard','within_pair_coassignment']])}

{table(lpair[lpair.pair.isin(important_pairs)])}

A's December membership remains close under this swap. B and E largely coassign, strengthening the nested/overlapping boundary caveat. D has high retention but low precision inside a larger D/F destination. F splits toward D and G; its exact-boundary claim remains weak. G retains a broad core with additional members. C is not rehabilitated: algorithmic retention cannot override failed context controls. Existing population/density, geography and causal-language caveats are unchanged. These are exploratory results for this reference specification and one fixed algorithm seed.
''')
    write_new(pert / 'PERTURBATION_HIGHREP_AUDIT.md', '''# Canonical perturbation robustness v2, n=50 — audit

This is a new protocol, not expanded historical pilot evidence. The user explicitly superseded the historical n=5 and authorized v2. See docs/PERTURBATION_PILOT_PROVENANCE_RESOLUTION.md and docs/PERTURBATION_V2_PROTOCOL.md. No historical seed 0..4 CSV values were used as reproduction targets, pooled observations, or evidence in Round 15.

Baseline is exactly reproduced in the prior accepted gate. Before this run the cached graphs, reference labels and baseline config hashes were rechecked. Protocol-v2 gate passed two same-process calls, a fresh process, and reversed insertion order for seed 0; all hashes compare exactly. Canonical edges, keep masks, jitter arrays, perturbed edges and final graphs are hashed with documented byte serialization. Temporal edge hashes are constant across all runs; coupling weights are never renormalized. Full node sets, including isolates, are preserved.

50 seeds (0..49) completed. Each worker saved raw labels first, then raw run/profile/pair/monthly diagnostics, then an atomic completion checkpoint with file hashes. Aggregate raw CSVs were written before summaries. No seed was excluded. Two worker processes executed independent seeds. Completed seeds must be hash-verified and skipped on rerun unless --force is explicit; forced reruns archive old completed seed directories. An incomplete seed is not accepted as evidence. run_manifest.json records source/config/package hashes and git commit=null because the supplied directory has no .git.

Per-seed diagnostics: full-supra/December ARI and NMI, K, switch statistics, all A-G retention/precision/Jaccard/within-pair coassignment and all 21 profile-pair cross-coassignments. Summaries use sample SD (ddof=1), NumPy linear quantiles q05/q10/q25/q75/q90/q95, mean/median/min/max. Retention threshold fractions >=.90/.80/.70/.50 are present. Boundary-tail and leave-one-out summaries are supplementary descriptions; all 50 seeds remain in primary evidence.

Interpretation: robustness to this fixed 5% deletion/2% log-jitter protocol with Louvain seed changing jointly. This does not separately identify edge-noise and algorithm-seed effects, establish universal boundaries, or provide population-sampling confidence intervals. High recall into a larger community can coexist with poor precision/Jaccard. No retuning, old-pilot matching or reference changes occurred.

Outputs: perturbation_v2_50_runs.csv (50 rows), perturbation_v2_50_archetype_retention.csv (350), perturbation_v2_50_pair_coassignment.csv (1050), perturbation_v2_50_summary.csv, plus raw seed checkpoints and monthly metrics. Status: archetype_status_round15_perturbation_v2.csv. New master matrix v2.2.0 explicitly marks historical_perturbation_pilot_status=SUPERSEDED_NON_REPRODUCIBLE and contains only available repository prior-status evidence plus the new rounds; missing historical master columns were not reconstructed from prose.
''')
    write_new(pert / 'PERTURBATION_HIGHREP_FINDINGS.md', f'''# Canonical perturbation robustness v2, n=50 — findings

All 50 seeds completed under the new canonical protocol after its reproducibility gate passed. The non-reproducible historical pilot contributes no quantitative evidence. These distributions characterize the fixed protocol, jointly varying intralayer perturbations and Louvain initialization.

Run-level distributions:

{table(run_table[['metric','mean','median','SD','min','q10','q90','max']])}

A-G distributions:

{table(profile_table)}

The distinction between retention and precision/Jaccard is essential: a preserved core can be absorbed into a larger destination. Existing substantive labels remain qualified; no profile is promoted to a universal archetype. C's rejection beyond context is unchanged even if it sometimes persists under this perturbation model.

Priority pair cross-coassignment distributions:

{table(pair_table)}

Tail proportions and leave-one-seed-out mean ranges:

{table(pd.DataFrame(loo))}

The full summaries also include q05/q25/q75/q95 and all retention-threshold fractions. Leave-one-out results describe sensitivity to individual runs; no observations are removed. The new distributions replace the former absence of reproducible perturbation evidence, rather than confirming or refuting the old n=5 numerical claims. Profile-specific interpretations and all contextual caveats are carried in Round 15 and master matrix v2.2.0.
''')
    claims = pd.DataFrame([
        {'claim':'H16 historical n=5 boundary evidence', 'new_status':'SUPERSEDED_NON_REPRODUCIBLE', 'change':'withdrawn as quantitative evidence', 'source':'docs/PERTURBATION_PILOT_PROVENANCE_RESOLUTION.md'},
        {'claim':'H17 exact Louvain algorithm independence', 'new_status':'not supported by fixed same-graph Leiden swap', 'change':'open question tested; exact invariance weakened', 'source':'outputs/leiden_robustness/leiden_temporal_summary.csv'},
        {'claim':'H8 F exact boundary stability', 'new_status':'weak refinement/boundary population', 'change':'Leiden and v2 distributions added; historical pilot excluded', 'source':'archetype_status_round15_perturbation_v2.csv'},
        {'claim':'H2 seven robust archetypes', 'new_status':'rejected', 'change':'unchanged', 'source':'docs/HYPOTHESIS_LEDGER.md'},
        {'claim':'H3-H5 optimal reference parameters', 'new_status':'rejected wording', 'change':'unchanged; no tuning', 'source':'configs/baseline.yaml'}])
    claims.to_csv(evidence / 'CLAIM_CHANGES_v2.2.0.csv', index=False)
    save_json(evidence / 'manifest.json', {'evidence_version':'2.2.0',
        'historical_master_available':False, 'prior_status_source':'outputs/alpha_sensitivity/archetype_status_round13_alpha.csv',
        'historical_pilot_quantitative_evidence_used':False,
        'files_sha256':{str(p):sha256(p) for directory in [leiden,pert,evidence] for p in directory.glob('*.csv')}})
    print(table(profile_table))
    print(table(pair_table))
    print(table(run_table[['metric','mean','q10','min','max']]))


if __name__ == '__main__':
    main()
