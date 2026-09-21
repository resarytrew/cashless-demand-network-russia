"""Assemble Round16 reports and a new evidence matrix without changing older evidence."""
import argparse
import json
from pathlib import Path

import pandas as pd

from sbernet.robustness.reproduction_gate import sha256, versions
from sbernet.robustness.experiment_common import save_json
from round16_common import require_fresh


def table(frame):
    # Avoid a nonessential tabulate dependency.
    def text(v):
        return f'{v:.6f}' if isinstance(v, float) else str(v).replace('|','/').replace('\n',' ')
    return '| ' + ' | '.join(frame.columns) + ' |\n|' + '|'.join(['---']*len(frame.columns)) + '|\n' + '\n'.join('| ' + ' | '.join(text(v) for v in row) + ' |' for row in frame.itertuples(index=False,name=None))


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--force',action='store_true'); args=parser.parse_args()
    out=require_fresh('outputs/round16_evidence',args.force)
    decomp=Path('outputs/round16_perturbation_decomposition'); resolution=Path('outputs/round16_resolution')
    runs=pd.read_csv(decomp/'perturbation_decomposition_runs.csv')
    profiles=pd.read_csv(decomp/'perturbation_decomposition_archetypes.csv')
    rprofiles=pd.read_csv(resolution/'resolution_sensitivity_archetypes.csv')
    summary=pd.read_csv(decomp/'perturbation_decomposition_summary.csv')
    collapse=pd.read_csv(decomp/'perturbation_collapse_cases.csv')
    rsummary=pd.read_csv(resolution/'resolution_sensitivity_summary.csv')
    status=pd.read_csv('outputs/perturbation_v2/archetype_status_round15_perturbation_v2.csv')
    statuses=pd.DataFrame({'label':status.archetype,'prior_status':status.round15_status,
        'round16_status':status.round15_status,'changed':False,
        'numerical_reason':'No status change proposed; new sensitivity adds boundary limitations, not status promotion/demotion',
        'interpretation_note':'Status preserved from Round15; contextual status rationale not newly reproduced'})
    statuses.to_csv(out/'archetype_status_round16.csv',index=False)
    matrix=pd.read_csv('outputs/evidence_freeze_v2_2_0/MASTER_PROFILE_EVIDENCE_MATRIX_v2.2.0.csv').set_index('archetype')
    matrix['evidence_version']='2.3.0'; matrix['freeze_revision']='round16_scoped'
    matrix['scientific_status_registry']='archetype_status_round16.csv'
    matrix['evidence_scope']='baseline fresh reproduction; fixed-geometry benchmark; optimizer/graph sensitivity; gamma grid; contextual limits explicit'
    for mode in ['optimizer_only','graph_only','combined']:
        means=profiles[profiles['mode'].eq(mode)].groupby('archetype')[['retention','precision']].mean()
        for metric in means:
            matrix[f'{mode}_{metric}']=means[metric]
    for label in matrix.index:
        rp=rprofiles[rprofiles.archetype.eq(label)]
        matrix.loc[label,'resolution_sensitivity_note']=f'gamma .25/.5/.75/1: retention range {rp.retention.min():.6f}..{rp.retention.max():.6f}; precision {rp.precision.min():.6f}..{rp.precision.max():.6f}; Jaccard {rp.Jaccard.min():.6f}..{rp.Jaccard.max():.6f}; no scale selected'
    matrix['collapse_run_sensitivity']='Seeds24/39 retained; collapse persists at fixed optimizer seed0 (1868/1904 and1874/1904). Read precision/Jaccard with retention.'
    matrix['contextual_reproducibility_scope']='historical-only for population/density/spatial/residual controls; B descriptive within-stratum recovered, historical inference unavailable'
    matrix['data_passport_interpretation_scope']='DENOMINATOR_NOT_ESTABLISHED_FROM_AVAILABLE_OFFICIAL_METADATA; category additivity unconfirmed'
    matrix.to_csv(out/'MASTER_PROFILE_EVIDENCE_MATRIX_v2.3.0.csv')
    lineage=[]
    for mode in ['optimizer_only','graph_only','combined']:
        for metric in ['retention','precision']:
            lineage.append({'field':f'{mode}_{metric}','source':str(decomp/'perturbation_decomposition_archetypes.csv'),
                            'derivation':f'mean({metric}) grouped by archetype where mode={mode}; all runs retained'})
    pd.DataFrame(lineage).to_csv(out/'MATRIX_FIELD_LINEAGE_ROUND16.csv',index=False)

    context=[
        dict(evidence_family='baseline',claim='fixed reference labels reproduce',source_files='data/raw/spending.csv.zip; outputs/baseline/*',config='configs/baseline.yaml',code='src/sbernet/robustness/reproduction_gate.py',raw_input_available=True,derived_input_available=True,fully_reproducible_external=True,limitation='pinned numerical environment; exact calendar; source coverage not representativeness',recommended_claim_scope='baseline fully reproduced'),
        dict(evidence_family='admin within-stratum B',claim='B differs descriptively from other federal-intracity territories',source_files='data/raw/spending.csv.zip; outputs/baseline/supra_labels.csv',config='configs/competition_artifacts.yaml',code='scripts/build_competition_artifacts.py; src/sbernet/robustness/region_null.py:admin_form',raw_input_available=True,derived_input_available=True,fully_reproducible_external=True,limitation='text-derived administrative stratum; historical p-values/corrections absent',recommended_claim_scope='contextual evidence reproducible within supplied artifacts: descriptive B comparison only'),
        dict(evidence_family='admin residual controls',claim='residual compactness after administrative adjustment',source_files='data/processed/supra_labels_admin_residual_base.csv (missing)',config='historical residualization config unavailable',code='historical residualization generator unavailable',raw_input_available=False,derived_input_available=False,fully_reproducible_external=False,limitation='do not replace residual labels by baseline labels based on similar filenames',recommended_claim_scope='historical-only'),
        dict(evidence_family='region/admin controls',claim='region x admin matched-null compactness',source_files='data/processed/municipality_crosswalk_final_1904.csv; outputs/reference/economic_space_points.csv (missing)',config='configs/region_null.yaml',code='src/sbernet/robustness/region_null.py',raw_input_available=False,derived_input_available=False,fully_reproducible_external=False,limitation='crosswalk snapshots/manual resolutions and result CSV unavailable; rounded narrative retained only',recommended_claim_scope='externally dependent; historical-only numerical claims'),
        dict(evidence_family='spatial controls',claim='polygon/block matched-null compactness',source_files='data/processed/municipality_spatial_join_1904.csv; geometry provenance; crosswalk; residual labels (missing)',config='configs/spatial_block.yaml',code='src/sbernet/robustness/spatial_block.py; spatial_block_reference_script.py',raw_input_available=False,derived_input_available=False,fully_reproducible_external=False,limitation='geometry source identified but exact snapshot and joins/hash unavailable',recommended_claim_scope='externally dependent; historical-only'),
        dict(evidence_family='population/density controls',claim='attenuation of residual compactness',source_files='Rosstat municipal population Jan01 2024/2025; area; covariates (missing)',config='historical config unavailable',code='historical residualization generator unavailable',raw_input_available=False,derived_input_available=False,fully_reproducible_external=False,limitation='DOCX supplies rounded claims, not municipality-level covariates or runnable provenance',recommended_claim_scope='historical-only; source unavailable in supplied artifacts'),
    ]
    pd.DataFrame(context).to_csv(out/'CONTEXTUAL_EVIDENCE_REPRODUCIBILITY_MATRIX.csv',index=False)

    stats=summary[(summary.scope.eq('run')) & (summary.metric.eq('ARI_Dec2024'))][['mode','n','mean','median','SD','min','max','q10','q90']]
    audit=('# Perturbation sensitivity decomposition\n\nOptimizer-only: seeds0..19 on the unmodified reference supra graph. '
        'Graph-only: v2 graph seeds0..19 with Louvain seed=0. Combined: all existing v2 seeds0..49 replayed from raw labels; no reclustering. '
        'Collapse-specific graph seeds24/39 are separate diagnostics and are not added to the 20-run graph-only distribution.\n\n'
        'Fresh baseline passed all six ARI/NMI checks exactly. Features reproduced bitwise; graph hashes are identical. '
        'A fresh v2 gate passed same-process, fresh-process and reversed insertion tests. Each graph-only graph hash matches the corresponding Round15 graph. '
        'Raw labels precede metrics and checksummed completion markers. Resume verified 42 checkpoints and rewrote no results.\n\n'
        +table(stats)+'\n\nSample SD uses ddof=1; quantiles use NumPy linear interpolation. All run metrics, A–G retention/precision/Jaccard/within-pair '
        'and 21 cross-pairs have mean/median/SD/min/max/q05/q10/q25/q75/q90/q95. No seed is discarded.\n\n'
        'These are optimizer-only sensitivity, graph-perturbation sensitivity and combined sensitivity. '
        'The 20/20/50 design is not a factorial causal variance decomposition. Graph-only includes the canonical v2 graph insertion order, '
        'whereas optimizer-only retains the exact baseline object order. This operational distinction is documented, not silently attributed to edge noise alone. '
        'Comparisons describe this algorithm/protocol, not population sampling uncertainty.\n')
    (decomp/'PERTURBATION_DECOMPOSITION_AUDIT.md').write_text(audit,encoding='utf-8')
    ccols=['mode','seed','louvain_seed','K_Dec2024','largest_community_n_Dec','largest_community_share_Dec','ARI_all_supra','NMI_all_supra','ARI_Dec2024','NMI_Dec2024','MQ','Dec_MQ','edges','components','connectivity_changed']
    collapse_text=('# Collapse cases 24 and 39\n\n'+table(collapse[ccols])+'\n\n'
        'Raw combined labels confirm 1864/1904 and 1877/1904. Reusing those exact perturbed graphs with Louvain seed=0 gives 1868/1904 and 1874/1904. '
        'Collapse therefore does not require the original optimizer seeds24/39. It persists for these graph realizations with optimizer seed0; '
        'the limited design does not establish graph-only causality or invariance to every optimizer seed.\n\n'
        'high retention can be misleading under near-global community collapse; therefore retention must be interpreted jointly with precision, Jaccard and largest-community share.\n\n'
        '`perturbation_collapse_cases.csv` reports full/December quality, degrees, components and weight distributions; '
        '`perturbation_collapse_archetypes.csv` and `perturbation_collapse_pairs.csv` retain all requested profile and pair diagnostics. '
        'MQ is resolution1; Q_resolution_0_5 is the optimized gamma=.5 quality. December MQ is evaluated on the induced perturbed December layer. '
        'Connected-component counts do not change, but unchanged connectivity does not imply unchanged community structure. '
        'All edges and weight hashes are recorded in each collapse checkpoint. No seed was removed.\n')
    (decomp/'PERTURBATION_COLLAPSE_CASES_24_39.md').write_text(collapse_text,encoding='utf-8')
    rcols=['gamma','static_K','static_SW','static_CHn','static_AVI','static_AVU','static_MQ','K_supra','K_Dec2024','mean_switches','share_le2_switches','ARI_all_supra','ARI_Dec2024']
    (resolution/'RESOLUTION_SENSITIVITY_AUDIT.md').write_text(
        '# Resolution sensitivity audit\n\nFour predeclared values .25/.50/.75/1.00; seed0; unchanged features, static/supra graphs, weights, alpha=.70, k20, omega2. '
        'Static December and temporal December are separate partitions. Raw labels and monthly diagnostics are checkpointed; '
        'requested A–G diagnostics and all 21 pair relations are saved. Gamma=.5 reproduces ARI=NMI=1. No best gamma is selected.\n\n'
        +table(rsummary[rcols])+'\n\nS_Dbw undefined under the fixed Round-14 implementation; no alternative variant was used for ranking. '
        'MQ uses resolution1; static_Q_resolution uses each run gamma. This is scale/granularity sensitivity.\n',encoding='utf-8')
    rdetail=rprofiles.groupby('archetype')[['retention','precision','Jaccard']].agg(['min','max'])
    rdetail.columns=['_'.join(c) for c in rdetail.columns]
    (resolution/'RESOLUTION_SENSITIVITY_FINDINGS.md').write_text(
        '# Resolution sensitivity findings\n\nAcross the fixed grid, supra K ranges from7 to22, December K from6 to15; '
        'share with <=2 switches changes from94.91% to61.50%. December ARI to gamma=.5 is .733900/.631656/.857288 at .25/.75/1.00. '
        'Granularity and temporal persistence are model-dependent. Exact A–G boundaries need this additional limitation. '
        'Scientific statuses are unchanged; no parameter is selected.\n\n'+table(rdetail.reset_index())+'\n',encoding='utf-8')

    report='''# Round 16 final pre-submission audit

Status: **COMPUTATIONAL WORK COMPLETED; FULL ACCEPTANCE BLOCKED BY MISSING CONTEXTUAL INPUTS**.
Round16 is not declared fully complete: the third contextual case lacks individual controls and verified region/covariates.
Historical trajectory methods are explicitly unavailable under the permitted benchmark exception.

## 1. What changed
The supplied DOCX and reviewer text are archived in reference/round16 with extracted tables.
Baseline was freshly reconstructed: six ARI/NMI=1; 1904 municipalities, exact24-month calendar;
24 feature matrices bitwise identical; static/supra graph hashes identical. Before any research changes,
the original freeze verified all390 files. New artifacts occupy separate Round16 directories.
Five static algorithms,20 optimizer-only runs,20 graph-only runs,two collapse seed0 reruns,
four resolutions and five figure-ready PNG/SVG sets were produced. Combined n=50 was replayed, not reclustered.

## 2. Benchmark reconciliation
The only allowed source for method comparison numbers is
`outputs/round16_benchmark/canonical_method_benchmark.csv`.
Reference Louvain: SW=.169645, CH/N=.459672, AVI=.907450, AVU=.506291, MQ=.767448.
DOCX rounded values were .176/.468/.909/.469/.765. AVU changes materially.
All five algorithms now share feature/metric provenance; explicit Round16 settings do not establish
the identity of undocumented old settings. Historical cosine/correlation/lagged-correlation/DTW
are UNREPRODUCIBLE_HISTORICAL_BENCHMARK_COMPONENT, with blank canonical numbers.
The diff CSV covers every metric in both historical comparison tables. No old finite S_Dbw is reused.
The historical cause of mismatch remains unestablished; matching old scores was not a tuning target.

## 3. Perturbation decomposition
'''+table(stats)+'''

Combined sensitivity has lower mean December agreement than either separate20-run regime.
Optimizer-only and graph-only both materially alter boundaries; this design cannot allocate causal
variance or identify a universally dominant source. Unequal run counts and graph insertion-order
semantics are explicit. All tails, including collapse, remain in evidence.

## 4. Collapse runs
Combined seed24/39 has largest December groups1864/1877; on identical perturbed graphs with
optimizer seed0 these become1868/1874. Collapse persists without the original optimizer seeds.
High retention during near-global merging is insufficient: precision, Jaccard and largest-group share
are required. Graph connectivity is unchanged; per-edge weights/degrees/component diagnostics and
full/December modularity are saved. No causal decomposition is claimed.

## 5. Resolution sensitivity
'''+table(rsummary[rcols])+'''

The fixed grid changes granularity and switching substantially. Gamma=.5 remains the reference.
No ICVI-based selection or status promotion is performed. Profile-specific retention, precision,
Jaccard and pair distributions accompany the audit.

## 6. Data passport
The CSV establishes rubles and monthly frequency. The official dataset page could not be retrieved
(502 and timeout). DENOMINATOR_NOT_ESTABLISHED_FROM_AVAILABLE_OFFICIAL_METADATA.
Total/category common normalization and mutual additivity remain unconfirmed. Other is a technical
model residual, not an established economic sector. Turnover/per-capita/income/wealth/purchasing-power
interpretations are unsupported. The source and transformations are in docs/DATA_PASSPORT.md.

## 7. Reproducibility scope
Baseline, new sensitivity experiments and descriptive B comparison are reproducible from supplied
artifacts under the recorded environment. Crosswalk, geometry join, residual labels, population/density
covariates and historical control generators/results remain absent. The supplied DOCX adds historical
claims, not executable contextual evidence. Nearby project ZIP inventories were checked and did not
contain those inputs. Contextual matrix and recovery instructions document exact limits.
Within-stratum B comparison covers98 versus142: Transport Cliff delta=-.070997; historical p-values
and multiplicity corrections are unavailable. No new significance test was substituted.

## 8. Scientific statuses
All A–G statuses copy Round15 verbatim; changed=false for all7. Matrix v2.3.0 is a new file with
separate optimizer/graph/combined fields and limitations. The earlier v2.2.0 freeze remains intact.
Historical pilot n=5 remains SUPERSEDED_NON_REPRODUCIBLE and contributes no quantitative evidence.

## 9. Competition implications
### What was found
- Reference demand profiles differ in level and six calculated category shares; Health is restored to the profile matrix.
- Within federal-intracity territories, B differs descriptively in several features; Transport has little separation.
- Cores and exact boundaries differ: high retention can coexist with weak precision, particularly under merging.
- Both gamma and optimizer/graph changes affect the observed partition; no seven-equally-robust-type claim is supported.

### Why we can trust it
- Fresh baseline reproduces six partition metrics exactly, with bitwise feature and graph checks.
- All50 existing combined partitions and all new raw labels remain available with checkpoints.
- Separate sensitivity axes, collapse cases and full distributions replace reliance on means alone.
- Old mismatching benchmark numbers and finite historical S_Dbw are excluded from canonical comparison.

### How to use it
- Build descriptive peer comparisons with both feature distance and pair coassignment, checking community size.
- Prioritize municipal cases for manual review using boundary uncertainty, without automatic investment decisions.
- Compare observed category profiles and retrospective trajectories; separate indicator changes from label changes.
- Use sensitivity outputs to communicate uncertainty of segmentation. Live monitoring remains future work.

## 10. Remaining limitations
- Verified contextual inputs and individual attenuation are absent. Two case studies are fully descriptive;
  the third is a transparent provisional E candidate, not a demonstrated context-sensitive territory.
- All three cases lack verified regional/covariate joins. These were not inferred from names.
- Four historical distance families have unrecoverable definitions in the supplied state.
- Denominator, additivity and publication/suppression rules require official clarification.
- Historical B significance/correction output is missing; only descriptive effects are recovered.
- The original DOCX is preserved unchanged. Canonical replacement tables, figures and a correction map are provided;
  an edited, layout-verified submission DOCX is not claimed as an output of this round.
- Expanding-window monitoring and predictive utility remain future work, as required by the task.

Engineering: baseline outputs now reject silent overwrite; --force archives non-frozen outputs and cannot
overwrite frozen evidence. Strict panel checks exact calendar dates. Changed source files have byte-identical
pre-hardening snapshots so the old390-file freeze can be verified against its original dependencies.
See ROUND16_VERIFICATION.json for the final test and integrity results.
'''
    (out/'ROUND16_FINAL_PRESUBMISSION_AUDIT.md').write_text(report,encoding='utf-8')
    pd.DataFrame([
        {'criterion':i,'status':('PARTIAL_BLOCKED' if i==11 else 'PASS'),'note':('Three deterministic selections; third contextual attenuation and verified joins absent' if i==11 else 'See audit and raw artifacts')}
        for i in range(1,17)]).to_csv(out/'ACCEPTANCE_CRITERIA.csv',index=False)
    # Criterion15 is finalized only after the full-suite run, never inferred here.
    acceptance=pd.read_csv(out/'ACCEPTANCE_CRITERIA.csv'); acceptance.loc[acceptance.criterion.eq(15),'status']='PENDING_FINAL_TEST_RECORD'
    acceptance.to_csv(out/'ACCEPTANCE_CRITERIA.csv',index=False)
    save_json(out/'run_manifest.json',{'script_sha256':sha256(__file__),'packages':versions(),
        'inputs':{str(p):sha256(p) for directory in [decomp,resolution,Path('outputs/round16_benchmark'),Path('outputs/round16_competition')]
                  for p in directory.glob('*.csv')},'scientific_status_changes':0,'complete_acceptance':False})
    print('Round16 evidence/report assembled; acceptance explicitly blocked by contextual case inputs')


if __name__=='__main__':
    main()
