"""Build descriptive competition CSVs/figures from raw data and frozen labels, without clustering."""
import argparse
import json
from pathlib import Path
import textwrap

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist

from sbernet.config import load_config
from sbernet.features import robust_z
from sbernet.io import read_semicolon_zip, build_strict_panel
from sbernet.robustness.experiment_common import load_baseline, save_json, make_manifest
from sbernet.robustness.region_null import admin_form
from sbernet.robustness.reproduction_gate import sha256
from round16_common import require_fresh, seal

PARTS = ['Food', 'Health', 'Catering', 'Marketplace', 'Transport', 'Other']


def feature_table(cfg, data):
    cats = cfg['panel']['selected_categories']; total = cfg['panel']['total_category']
    raw = read_semicolon_zip(cfg['paths']['spending_zip'])
    panel, names, _ = build_strict_panel(raw, 24, [total] + cats)
    assert names == data['names']
    rows = []
    for key in data['keys']:
        p = panel[panel.period.eq(pd.Timestamp(key))].pivot(index='mo', columns='category_15', values='value').loc[names]
        f = pd.DataFrame({'municipality': names, 'month': key, 'Total': p[total].to_numpy(),
                          'level_z': robust_z(np.log(p[total].to_numpy()))})
        for english, russian in zip(PARTS[:-1], cats):
            f[english] = p[russian].to_numpy() / p[total].to_numpy()
        f['Other'] = 1 - f[PARTS[:-1]].sum(axis=1)
        rows.append(f)
    return pd.concat(rows, ignore_index=True)


def individual_stability(ref, labels, profiles):
    """Per-node peer coassignment excludes self; Jaccard penalizes global collapse."""
    n = len(ref); co = np.zeros(n); precision = np.zeros(n); jac = np.zeros(n)
    assignments = []
    masks = [ref == c for c in profiles.values()]
    for actual in labels:
        _, inv, counts = np.unique(actual, return_inverse=True, return_counts=True)
        scores = np.zeros((n, len(masks)))
        for col, mask in enumerate(masks):
            overlap = np.bincount(inv[mask], minlength=len(counts))[inv]
            size = int(mask.sum())
            scores[:, col] = overlap / (size + counts[inv] - overlap)
            co[mask] += (overlap[mask] - 1) / (size - 1)
            precision[mask] += overlap[mask] / counts[inv[mask]]
            jac[mask] += scores[mask, col]
        assignments.append(np.argmax(scores, axis=1))
    return co / len(labels), precision / len(labels), jac / len(labels), np.array(assignments)


def choose_cases(x, ref, profiles, co, assignments, rules):
    names = list(profiles); centers = np.array([np.median(x[ref == cid], axis=0) for cid in profiles.values()])
    dist = cdist(x, centers)
    index = {cid: j for j, cid in enumerate(profiles.values())}
    own = np.array([index.get(c, -1) for c in ref]); valid = own >= 0
    own_dist = dist[np.arange(len(ref)), np.maximum(own, 0)]
    stable = np.flatnonzero(valid & (co >= rules['stable_min_within_coassignment']))
    if not len(stable):
        raise ValueError('No stable-core candidate passes the declared threshold')
    stable_id = int(stable[np.argmin(own_dist[stable])])
    boundary = np.flatnonzero(ref == profiles['F'])
    allowed = [names.index(p) for p in rules['boundary_profiles']]
    probs = np.stack([(assignments[:, boundary] == j).mean(axis=0) for j in allowed], axis=1)
    # Entropy includes an explicit outside-D/F/G category, so it does not discard inconvenient runs.
    probs = np.column_stack([probs, 1 - probs.sum(axis=1)])
    entropy = -(probs * np.log(np.maximum(probs, np.finfo(float).tiny))).sum(axis=1)
    boundary_id = int(boundary[np.argmax(entropy)])
    context_col = names.index(rules['context_profile'])
    other_dist = dist.copy(); other_dist[:, context_col] = np.inf
    margin = other_dist.min(axis=1) - dist[:, context_col]
    context = np.flatnonzero((ref == profiles[rules['context_profile']]) & (margin > 0))
    if not len(context):
        raise ValueError('No positive-margin contextual candidate')
    context_id = int(context[np.argmin(dist[context, context_col])])
    return [('stable_core', stable_id), ('boundary', boundary_id), ('context_candidate_unverified', context_id)]


def savefig(out, name, fig):
    fig.savefig(out / f'{name}.png', dpi=220, bbox_inches='tight')
    fig.savefig(out / f'{name}.svg', bbox_inches='tight')
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='configs/competition_artifacts.yaml')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args(); cfg = load_config(args.config); data = load_baseline(cfg)
    out = require_fresh(cfg['paths']['output_dir'], args.force)
    profiles = cfg['experiment']['profiles']; ref = data['reference'][-1]; names = data['names']
    inv = {v: k for k, v in profiles.items()}
    manifest = make_manifest(args.config, cfg); manifest['script_sha256'] = sha256(__file__)
    manifest['case_rule_recorded_before_name_selection'] = cfg['experiment']['case_selection']
    manifest['input_sha256'] = {}
    series = []
    for seed in range(50):
        p = Path(cfg['experiment']['combined_dir']) / 'seeds' / f'{seed:02d}'
        cp = json.loads((p / 'COMPLETED.json').read_text())
        for fname, h in cp['files_sha256'].items():
            assert sha256(p / fname) == h
            manifest['input_sha256'][str(p / fname)] = h
        series.append(np.load(p / 'supra_labels.npy').reshape(data['reference'].shape)[-1])
    save_json(out / 'run_manifest.json', manifest)
    allfeatures = feature_table(cfg, data)
    dec = allfeatures[allfeatures.month.eq(data['keys'][-1])].copy().reset_index(drop=True)
    dec['profile'] = [inv.get(c, 'micro') for c in ref]
    dec['admin_form'] = [admin_form(s) for s in names]
    dec.to_csv(out / 'december_municipality_features.csv', index=False)
    status = pd.read_csv('outputs/perturbation_v2/archetype_status_round15_perturbation_v2.csv').set_index('archetype')
    prof = dec[dec.profile.ne('micro')].groupby('profile')[['Total', 'level_z'] + PARTS].median()
    prof['n'] = dec.groupby('profile').size(); prof['status'] = status.round15_status
    prof.to_csv(out / 'figure_A_profile_matrix.csv')

    # Descriptive within-stratum recovery; no replacement for missing historical inferential test.
    b = dec.profile.eq('B'); other = dec.admin_form.eq('federal_intracity') & ~b
    assert dec.loc[b, 'admin_form'].eq('federal_intracity').all()
    brows = []
    for metric in ['level_z'] + PARTS:
        left = dec.loc[b, metric].to_numpy(); right = dec.loc[other, metric].to_numpy()
        delta = float(np.sign(left[:, None] - right).mean())
        negligible = abs(delta) < cfg['experiment']['negligible_cliff_delta_threshold']
        brows.append({'metric': metric, 'n_B': len(left), 'n_other_federal': len(right),
            'B_median': float(np.median(left)), 'other_federal_median': float(np.median(right)),
            'effect_size': delta, 'effect_definition': 'Cliff delta B minus other federal',
            'median_difference': float(np.median(left) - np.median(right)),
            'p_value': None, 'uncertainty': 'historical inferential output unavailable; no new inference',
            'multiplicity_correction': 'not applicable to descriptive effect; historical correction unavailable',
            'direction': 'no meaningful separation under declared |delta|<.147 convention' if negligible else ('B higher' if delta > 0 else 'B lower'),
            'provenance': 'Round16 descriptive recomputation from fixed December features and existing admin_form parser'})
    btable = pd.DataFrame(brows); btable.to_csv(out / 'B_WITHIN_FEDERAL_INTRACITY_PROFILE.csv', index=False)
    transport = btable.set_index('metric').loc['Transport']
    (out / 'B_WITHIN_FEDERAL_INTRACITY_PROFILE.md').write_text(
        '# B within federal-intracity stratum\n\n'
        f'B is not simply “federal-city territory”: {int(b.sum())} reference B municipalities are compared with '
        f'{int(other.sum())} other federal-intracity territories using the existing text-based administrative parser. '
        'Within the same administrative stratum it shows a distinct descriptive demand profile. '
        f'Transport: Cliff delta={transport.effect_size:.6f}; {transport.direction}. '
        'The |delta|<.147 descriptive convention is declared in config, not a significance test or equivalence proof. '
        'Historical p-values, uncertainty and multiplicity correction were not supplied and have not been fabricated. '
        'This is a fixed-profile descriptive reconstruction, not reproduction of the missing historical inferential audit. '
        'Do not interpret the profile as affluent/premium or as income evidence.\n', encoding='utf-8')

    co, precision, jac, assignment = individual_stability(ref, series, profiles)
    x = data['matrices'][data['keys'][-1]]
    selected = choose_cases(x, ref, profiles, co, assignment, cfg['experiment']['case_selection'])
    cases, trajectories, analogrows = [], [], []
    individual = pd.DataFrame({'panel_index': range(len(names)), 'municipality': names,
        'profile': dec.profile, 'mean_peer_coassignment': co, 'mean_destination_precision': precision,
        'mean_destination_Jaccard': jac})
    individual.to_csv(out / 'municipality_perturbation_stability.csv', index=False)
    for kind, i in selected:
        neighbors = list(data['static'].neighbors(i))
        neighbors.sort(key=lambda j: (float(np.linalg.norm(x[i] - x[j])), j))
        analogs = neighbors[:cfg['experiment']['case_selection']['analog_count']]
        for rank, j in enumerate(analogs, 1):
            analogrows.append({'case': kind, 'municipality': names[i], 'rank': rank, 'analog': names[j],
                              'reference_distance': float(np.linalg.norm(x[i]-x[j])),
                              'combined_coassignment': float(np.mean([a[i] == a[j] for a in series])),
                              'qualification': 'reference static neighbor; pair coassignment can be inflated by collapse'})
        row = dec.iloc[i].to_dict()
        row.update(case=kind, panel_index=i, region='UNAVAILABLE_WITHOUT_VERIFIED_CROSSWALK',
                   mean_peer_coassignment=float(co[i]), mean_destination_precision=float(precision[i]),
                   mean_destination_Jaccard=float(jac[i]),
                   closest_network_analogs=json.dumps([names[j] for j in analogs], ensure_ascii=False),
                   population=None, density=None, contextual_attenuation=None,
                   contextual_evidence_status='UNAVAILABLE_INDIVIDUAL_CONTROLS',
                   caveat='context candidate only; no individual attenuation claim' if kind.startswith('context') else 'selected illustration; not population inference or causal explanation')
        cases.append(row)
        trajectory = allfeatures[allfeatures.municipality.eq(names[i])].copy()
        trajectory['case'] = kind; trajectory['temporal_community_id'] = data['reference'][:, i]
        trajectories.append(trajectory)
    cases = pd.DataFrame(cases); cases.to_csv(out / 'case_studies_3_municipalities.csv', index=False)
    trajectory = pd.concat(trajectories, ignore_index=True); trajectory.to_csv(out / 'case_studies_temporal_trajectories.csv', index=False)
    pd.DataFrame(analogrows).to_csv(out / 'case_studies_network_analogs.csv', index=False)
    (out / 'THREE_MUNICIPAL_CASE_STUDIES.md').write_text(
        '# Three municipal illustrations\n\nSelection rules were recorded in configs/competition_artifacts.yaml before names were selected. '
        'Stable core: mean peer coassignment >=.90, then minimum distance to profile componentwise median. '
        'Boundary: baseline F with maximum entropy of Jaccard-matched destinations D/F/G/other over all 50 seeds. '
        'Context candidate: representative positive-margin E member. All ties use panel index. No seed is removed.\n\n'
        + '\n\n'.join(f'## {r.case}: {r.municipality}\nReference {r.profile}; published Total={r.Total:.0f}; '
                       f'peer coassignment={r.mean_peer_coassignment:.3f}; destination precision={r.mean_destination_precision:.3f}; '
                       f'Jaccard={r.mean_destination_Jaccard:.3f}. {r.caveat}.' for r in cases.itertuples())
        + '\n\nThe third selection is explicitly provisional: historical group-level attenuation cannot establish '
        'individual context sensitivity. Verified region/population/density and individual residual evidence are missing. '
        'The full requested context-sensitive case is NOT established. No region was guessed from municipality names. '
        'CSV companions contain all six shares, Total, 24-month features/labels and nearest network analogs.\n', encoding='utf-8')

    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, ax = plt.subplots(figsize=(12, 6))
    cols = ['level_z'] + PARTS
    # Column scaling only for color; each cell retains its original median value.
    values = prof[cols].to_numpy(); color = (values-values.mean(axis=0))/values.std(axis=0)
    im = ax.imshow(color, cmap='RdBu_r', vmin=-2, vmax=2, aspect='auto')
    ax.set_xticks(range(7), cols); ax.set_yticks(range(7), [f'{p} · n={prof.loc[p,"n"]}' for p in prof.index])
    for i in range(7):
        for j in range(7):
            ax.text(j, i, f'{values[i,j]:.3f}', ha='center', va='center', color='white' if abs(color[i,j])>1.25 else '#17242b')
    ax.set_title('A–G: median reference profiles · December 2024', loc='left', pad=15)
    fig.colorbar(im, ax=ax, label='Column-standardized color; values are original medians')
    fig.text(.08, -.02, 'Statuses preserved from Round 15: A overlapping · B nested · C unsupported beyond context\nD boundary caveat · E contextual · F boundary population · G broad macroprofile', fontsize=9)
    savefig(out, 'figure_A_profile_matrix', fig)
    ret = pd.read_csv(Path(cfg['experiment']['combined_dir']) / 'perturbation_v2_50_archetype_retention.csv')
    ret.to_csv(out / 'figure_B_core_boundary_distributions.csv', index=False)
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharey=True)
    for ax, metric in zip(axes, ['retention','precision','Jaccard']):
        ax.boxplot([ret.loc[ret.archetype.eq(p),metric] for p in profiles], tick_labels=list(profiles), showfliers=True)
        ax.set_title(metric); ax.set_ylim(-.03,1.03)
    fig.suptitle('Core and boundary · all 50 combined runs'); savefig(out,'figure_B_core_boundary',fig)
    runs = pd.read_csv(Path(cfg['experiment']['combined_dir']) / 'perturbation_v2_50_runs.csv')
    runs['largest_community_share_Dec'] = [np.unique(a,return_counts=True)[1].max()/len(names) for a in series]
    runs.to_csv(out / 'figure_C_perturbation_stability.csv',index=False)
    fig, axes = plt.subplots(2,1,figsize=(11,6),sharex=True)
    for ax, metric, label in zip(axes,['ARI_Dec2024','largest_community_share_Dec'],['December ARI','Largest December community share']):
        ax.plot(runs.seed,runs[metric],'.-',color='#236b77',lw=.8)
        for seed in [24,39]:
            val = runs.set_index('seed').loc[seed,metric]; ax.scatter(seed,val,color='#bc392f',zorder=4)
            ax.annotate(f'  {seed}: {val:.3f}',(seed,val),fontsize=9)
        ax.set_ylabel(label); ax.set_ylim(-.06,1.08)
    axes[-1].set_xlabel('Perturbation / Louvain seed'); fig.suptitle('Combined perturbation v2 · no runs excluded')
    savefig(out,'figure_C_perturbation_stability',fig)
    pair = pd.read_csv(Path(cfg['experiment']['combined_dir']) / 'perturbation_v2_50_pair_coassignment.csv')
    pnames=['B/E','D/F','F/G','A/D']; pair = pair[pair.pair.isin(pnames)]
    pair.to_csv(out / 'figure_D_pair_instability.csv',index=False)
    fig,ax=plt.subplots(figsize=(9,4)); ax.boxplot([pair.loc[pair.pair.eq(p),'cross_coassignment'] for p in pnames],tick_labels=pnames)
    ax.set_ylim(-.03,1.03); ax.set_ylabel('Cross-coassignment'); ax.set_title('Boundary mixing · all 50 combined runs',loc='left')
    savefig(out,'figure_D_pair_instability',fig)
    fig,axes=plt.subplots(2,3,figsize=(14,8))
    for col,row in enumerate(cases.itertuples()):
        t=trajectory[trajectory['case'].eq(row.case)]
        axes[0,col].plot(range(24),t.Total,color='#236b77'); axes[0,col].set_title('\n'.join(textwrap.wrap(row.municipality,34)),fontsize=9)
        axes[0,col].set_ylabel('Published Total, rubles'); axes[0,col].set_xticks([0,12,23],['Jan 2023','Jan 2024','Dec 2024'])
        axes[1,col].bar(range(6),[getattr(row,p) for p in PARTS],color='#5f8f97')
        axes[1,col].set_xticks(range(6),PARTS,rotation=45,ha='right'); axes[1,col].set_ylim(0,.6)
        axes[1,col].set_title(f'{row.case}\npeer={row.mean_peer_coassignment:.2f}; Jaccard={row.mean_destination_Jaccard:.2f}',fontsize=9)
    fig.suptitle('Transparent municipal selections · third case provisional'); fig.tight_layout(rect=(0,.03,1,.96))
    fig.text(.05,.005,'Total denominator unestablished; region and individual contextual attenuation unavailable. No causal interpretation.',fontsize=9)
    savefig(out,'figure_E_municipal_cases',fig)
    seal(out)
    print('Competition artifacts built; three descriptive selections, contextual case explicitly provisional',flush=True)


if __name__ == '__main__':
    main()
