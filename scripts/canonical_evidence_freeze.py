"""Freeze verified saved-label evidence, without executing clustering algorithms."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import yaml

from sbernet.config import load_config
from sbernet.robustness.experiment_common import load_baseline, profile_diagnostics, temporal_diagnostics, distribution
from sbernet.robustness.reproduction_gate import sha256, versions


def read(path):
    return pd.read_csv(path, float_precision='round_trip')


def build(config):
    cfg = yaml.safe_load(Path(config).read_text(encoding='utf-8'))
    out = Path(cfg['output_dir'])
    if (out / 'MASTER_PROFILE_EVIDENCE_MATRIX_v2.2.0.csv').exists():
        raise FileExistsError('Canonical matrix already exists; do not overwrite frozen evidence')
    data = load_baseline(load_config('configs/perturbation_v2.yaml'))
    comparisons, lineage = [], []
    def check(scope, key, actual, expected):
        passed = bool(np.isclose(actual,expected,atol=cfg['comparison_atol'],rtol=0,equal_nan=True))
        comparisons.append({'scope':scope,'key':key,'actual':actual,'stored':expected,
                            'delta':float(actual-expected),'passed':passed})
        if not passed:
            pd.DataFrame(comparisons).to_csv(out/'EVIDENCE_VERIFICATION_FAILURE.csv',index=False)
            raise ValueError(f'Evidence mismatch {scope}/{key}')
    def compare_rows(scope, actual, stored, idkey, metrics):
        index = stored.set_index(idkey)
        for row in actual:
            for metric in metrics:
                check(scope,f'{row[idkey]}/{metric}',row[metric],index.loc[row[idkey],metric])
    lp = Path(cfg['leiden_dir']); pp = Path(cfg['perturbation_dir'])
    labels = np.load(lp/'supra_labels.npy',allow_pickle=False).reshape(data['reference'].shape)
    lpro, lpair = profile_diagnostics(data['reference'][-1],labels[-1],cfg['profiles'])
    metric_names = ['retention','precision','Jaccard','within_pair_coassignment']
    compare_rows('leiden_profiles',lpro,read(lp/'leiden_archetype_retention.csv'),'archetype',metric_names)
    compare_rows('leiden_pairs',lpair,read(lp/'leiden_pair_coassignment.csv'),'pair',['cross_coassignment'])
    lt, _ = temporal_diagnostics(data['reference'],labels,data['keys'])
    stored_lt = read(lp/'leiden_temporal_summary.csv').iloc[0]
    for k,v in lt.items(): check('leiden_run',k,v,stored_lt[k])
    allpro, allpair, allruns = [], [], []
    for seed in cfg['seeds']:
        folder = pp/'seeds'/f'{seed:02d}'
        checkpoint = json.loads((folder/'COMPLETED.json').read_text())
        assert checkpoint['seed']==seed
        assert checkpoint['config_sha256']==sha256('configs/perturbation_v2.yaml')
        for name,h in checkpoint['files_sha256'].items(): assert sha256(folder/name)==h
        raw = json.loads((folder/'raw_results.json').read_text())
        lab = np.load(folder/'supra_labels.npy',allow_pickle=False).reshape(data['reference'].shape)
        pro,pairs = profile_diagnostics(data['reference'][-1],lab[-1],cfg['profiles'])
        compare_rows(f'seed{seed}_profiles',pro,pd.DataFrame(raw['profiles']),'archetype',metric_names)
        compare_rows(f'seed{seed}_pairs',pairs,pd.DataFrame(raw['pairs']),'pair',['cross_coassignment'])
        stats,_ = temporal_diagnostics(data['reference'],lab,data['keys'])
        for k,v in stats.items(): check(f'seed{seed}_run',k,v,raw['run'][k])
        for row in pro: row['seed']=seed
        for row in pairs: row['seed']=seed
        allpro.extend(pro); allpair.extend(pairs); allruns.append({'seed':seed,**stats})
    pro=pd.DataFrame(allpro); pairs=pd.DataFrame(allpair)
    stored_summary=read(pp/'perturbation_v2_50_summary.csv').set_index(['scope','group','metric'])
    summaries=[]
    for scope,frame,group_col,metrics in [('archetype',pro,'archetype',metric_names),('pair',pairs,'pair',['cross_coassignment'])]:
        for group,df in frame.groupby(group_col):
            for metric in metrics:
                stats=distribution(df[metric],cfg['quantiles'])
                for name,value in stats.items(): check('summary',f'{scope}/{group}/{metric}/{name}',value,stored_summary.loc[(scope,group,metric),name])
                summaries.append({'scope':scope,'group':group,'metric':metric,**stats})
    pd.DataFrame(summaries).to_csv(out/'CANONICAL_DISTRIBUTIONS.csv',index=False)
    pro.to_csv(out/'VERIFIED_PROFILE_RESULTS.csv',index=False)
    pairs.to_csv(out/'VERIFIED_PAIR_RESULTS.csv',index=False)
    pd.DataFrame(allruns).to_csv(out/'VERIFIED_RUN_RESULTS.csv',index=False)
    # Metadata status is retained separately, never asserted as newly reproduced context evidence.
    old_status=read(pp/'archetype_status_round15_perturbation_v2.csv')
    registry=old_status[['archetype','round15_status']].rename(columns={'round15_status':'scientific_status_unchanged'})
    registry['status_source']=(pp/'archetype_status_round15_perturbation_v2.csv').as_posix()
    registry['status_source_sha256']=sha256(pp/'archetype_status_round15_perturbation_v2.csv')
    registry['role']='governance_annotation_not_reproduced_context_evidence'
    registry.to_csv(out/'SCIENTIFIC_STATUS_REGISTRY_UNCHANGED.csv',index=False)
    records=[]
    lindex=pd.DataFrame(lpro).set_index('archetype')
    priority={'A':['A/D'],'B':['B/E'],'C':[],'D':['A/D','D/F'],'E':['B/E'],'F':['D/F','F/G'],'G':['F/G']}
    for profile in cfg['profiles']:
        row={'archetype':profile,'evidence_version':cfg['evidence_version'],
             'freeze_revision':cfg['freeze_revision'],'reference_n':int(lindex.loc[profile,'n_reference']),
             'evidence_scope':'saved_label_replay_verified; not new clustering reproduction',
             'historical_perturbation_pilot_status':'SUPERSEDED_NON_REPRODUCIBLE',
             'historical_pilot_quantitative_evidence_used':False,'perturbation_v2_n':len(cfg['seeds']),
             'S_Dbw_evidence_status':'EXCLUDED_UNRESOLVED_HISTORICAL_PROVENANCE_AND_UNDEFINED_ROUND14',
             'scientific_status_registry':'SCIENTIFIC_STATUS_REGISTRY_UNCHANGED.csv'}
        for metric in metric_names:
            row['leiden_'+metric]=float(lindex.loc[profile,metric])
            values=pro.loc[pro.archetype.eq(profile),metric]
            for stat,val in distribution(values,cfg['quantiles']).items():
                if stat!='n': row[f'perturbation_v2_{stat}_{metric}']=val
            if metric=='retention':
                for threshold in cfg['retention_thresholds']:
                    row[f'perturbation_v2_retention_share_ge_{threshold:.2f}']=float(np.mean(values>=threshold))
        notes=[]
        for pair in priority[profile]:
            d=distribution(pairs.loc[pairs.pair.eq(pair),'cross_coassignment'],cfg['quantiles'])
            notes.append(f'{pair}: mean={d["mean"]:.9f}, q10={d["q10"]:.9f}, q90={d["q90"]:.9f}')
        row['perturbation_v2_boundary_note']='; '.join(notes) or 'All pair distributions recorded separately; no status inference'
        records.append(row)
        lineage.append({'archetype':profile,'field_family':'leiden_*','source':(lp/'supra_labels.npy').as_posix(),
                        'source_sha256':sha256(lp/'supra_labels.npy'),'derivation':'December best-match overlap and pair counts against saved reference'})
        lineage.append({'archetype':profile,'field_family':'perturbation_v2_*','source':'outputs/perturbation_v2/seeds/00..49/supra_labels.npy',
                        'source_sha256':'per-file hashes in EVIDENCE_FREEZE_FILES_SHA256.csv','derivation':'all 50 saved partitions; sample SD, linear quantiles; no excluded runs'})
    matrix=pd.DataFrame(records)
    matrix.to_csv(out/'MASTER_PROFILE_EVIDENCE_MATRIX_v2.2.0.csv',index=False)
    pd.DataFrame(lineage).to_csv(out/'MATRIX_FIELD_LINEAGE.csv',index=False)
    previous=read(cfg['previous_matrix']).set_index('archetype')
    for row in records:
        for metric in ['leiden_retention','leiden_precision','leiden_Jaccard','leiden_within_pair_coassignment',
                       'perturbation_v2_mean_retention','perturbation_v2_q10_retention','perturbation_v2_min_retention']:
            check('previous_matrix_verified_numeric',f'{row["archetype"]}/{metric}',row[metric],previous.loc[row['archetype'],metric])
    pd.DataFrame(comparisons).to_csv(out/'EVIDENCE_NUMERIC_REPLAY_CHECKS.csv',index=False)
    exclusions=[
        ('historical perturbation n=5','SUPERSEDED_NON_REPRODUCIBLE','No numerical use'),
        ('historical S_Dbw alpha and older static tables','UNVERIFIED_IMPLEMENTATION_PROVENANCE','Excluded; diagnostics do not establish historical code'),
        ('Round14 S_Dbw','UNDEFINED_OR_VARIANT_SPECIFIC','Diagnostic audit only; no ranking or profile evidence'),
        ('population/density/admin/spatial/mobility/transition claims','UNDERLYING_ARTIFACTS_NOT_AVAILABLE_IN_FREEZE','No reconstructed numerical fields; statuses unchanged separately'),
        ('Round13 alpha sensitivity','OUTSIDE_THIS_CANONICAL_REPLAY_SCOPE','Available historical outputs retained, not silently promoted to full rerun evidence'),
        ('previous mixed matrix narrative columns','GOVERNANCE_NOT_QUANTITATIVE_EVIDENCE','Moved to unchanged status registry or omitted; old file untouched')]
    pd.DataFrame(exclusions,columns=['evidence_family','disposition','reason']).to_csv(out/'EVIDENCE_ADMISSIBILITY.csv',index=False)
    (out/'CANONICAL_MATRIX_BUILD_MANIFEST.json').write_text(json.dumps({'passed':True,'checks':len(comparisons),
        'clustering_calls':0,'scientific_status_changes':0,'matrix_rows':len(matrix),'packages':versions(),
        'config_sha256':sha256(config),'script_sha256':sha256(__file__)},indent=2),encoding='utf-8')
    print(f'Canonical matrix built: {len(matrix)} profiles; {len(comparisons)} numerical checks passed; no clustering.')


def seal(config):
    cfg=yaml.safe_load(Path(config).read_text(encoding='utf-8')); out=Path(cfg['output_dir'])
    protected=read(out/'PRE_AUDIT_PROTECTED_FILES_SHA256.csv')
    assert all(sha256(r.path)==r.sha256 for r in protected.itertuples()),'Pre-existing file changed'
    entries=[]
    for directory in ['configs','src','scripts','tests','docs','reference','data/raw','outputs']:
        for p in Path(directory).rglob('*'):
            if not p.is_file() or '__pycache__' in p.parts: continue
            if p.name in {'EVIDENCE_FREEZE_MANIFEST.json','EVIDENCE_FREEZE_MANIFEST.sha256','EVIDENCE_FREEZE_FILES_SHA256.csv','FREEZE_VERIFICATION.json'}: continue
            role='context_or_historical_not_admitted'
            if out in p.parents: role='canonical_audit_and_derived_evidence'
            elif 'seeds' in p.parts and 'perturbation_v2' in p.parts: role='admitted_raw_partition_and_checkpoint'
            elif p.as_posix() in ['outputs/leiden_robustness/supra_labels.npy','outputs/baseline/supra_labels.csv']: role='admitted_partition_input'
            elif directory in ['configs','src','scripts','tests','data/raw']: role='reproduction_dependency'
            entries.append({'path':p.as_posix(),'bytes':p.stat().st_size,'sha256':sha256(p),'role':role})
    inventory=out/'EVIDENCE_FREEZE_FILES_SHA256.csv'
    pd.DataFrame(entries).sort_values('path').to_csv(inventory,index=False)
    manifest={'evidence_version':'2.2.0','freeze_revision':cfg['freeze_revision'],
              'timestamp_utc':datetime.now(timezone.utc).isoformat(),'status':'FROZEN_SCOPED_REPRODUCIBLE_EVIDENCE',
              'inventory_path':inventory.as_posix(),'inventory_sha256':sha256(inventory),'file_count':len(entries),
              'canonical_matrix':(out/'MASTER_PROFILE_EVIDENCE_MATRIX_v2.2.0.csv').as_posix(),
              'canonical_matrix_sha256':sha256(out/'MASTER_PROFILE_EVIDENCE_MATRIX_v2.2.0.csv'),
              'scientific_status_changes':0,'new_clustering_experiments':0,
              'preexisting_files_unchanged':True,'git_commit':None,'git_note':'supplied working copy has no .git',
              'reproducibility_scope':'metric replay from saved raw partitions; previous gates retained; no fresh clustering claimed',
              'limitations':['historical full master and external control evidence unavailable','historical S_Dbw provenance unresolved','old pilot excluded'],
              'verification_command':'python scripts/canonical_evidence_freeze.py verify',
              'packages':versions()}
    path=out/'EVIDENCE_FREEZE_MANIFEST.json'
    with path.open('x',encoding='utf-8') as f: json.dump(manifest,f,indent=2)
    (out/'EVIDENCE_FREEZE_MANIFEST.sha256').write_text(sha256(path)+'  EVIDENCE_FREEZE_MANIFEST.json\n',encoding='utf-8')
    verify(config)


def verify(config):
    cfg=yaml.safe_load(Path(config).read_text(encoding='utf-8')); out=Path(cfg['output_dir'])
    path=out/'EVIDENCE_FREEZE_MANIFEST.json'
    assert sha256(path)==(out/'EVIDENCE_FREEZE_MANIFEST.sha256').read_text().split()[0]
    m=json.loads(path.read_text()); assert sha256(m['inventory_path'])==m['inventory_sha256']
    entries=read(m['inventory_path'])
    for r in entries.itertuples():
        assert Path(r.path).stat().st_size==r.bytes and sha256(r.path)==r.sha256,r.path
    print(f'Freeze verification PASS: {len(entries)} files, inventory and manifest hashes intact.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['build','seal','verify'])
    parser.add_argument('--config',default='configs/evidence_freeze_v2_2_0.yaml');args=parser.parse_args()
    import leidenalg
    with patch('networkx.community.louvain_communities',side_effect=RuntimeError('Clustering prohibited')), \
         patch.object(leidenalg,'find_partition',side_effect=RuntimeError('Clustering prohibited')):
        {'build':build,'seal':seal,'verify':verify}[args.mode](args.config)
