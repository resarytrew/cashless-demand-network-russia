"""Read-only forensic verification, or explicit creation of a new Round16 verification record."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import pickle
import subprocess
import sys

import numpy as np
import pandas as pd

from sbernet.config import load_config
from sbernet.pipeline import _prepare
from sbernet.robustness.reproduction_gate import sha256, graph_fingerprint
from sbernet.robustness.experiment_common import temporal_diagnostics, profile_diagnostics, save_json, validity_metrics
from round16_common import completed, array_hash

ROOT=Path('outputs/round16_evidence')


def verify_old_freeze():
    root=Path('outputs/evidence_freeze_v2_2_0')
    path=root/'EVIDENCE_FREEZE_MANIFEST.json'
    assert sha256(path)==(root/'EVIDENCE_FREEZE_MANIFEST.sha256').read_text().split()[0]
    m=json.loads(path.read_text()); assert sha256(m['inventory_path'])==m['inventory_sha256']
    entries=pd.read_csv(m['inventory_path']); redirected=[]
    mapping={f'src/sbernet/{name}.py':Path('reference/round16/pre_hardening')/f'{name}.py' for name in ['io','pipeline','cli']}
    for r in entries.itertuples():
        p=Path(r.path)
        if sha256(p)!=r.sha256 and r.path in mapping:
            p=mapping[r.path]; redirected.append({'original':r.path,'preserved_source':str(p)})
        assert p.stat().st_size==r.bytes and sha256(p)==r.sha256,r.path
    return {'passed':True,'files':len(entries),'source_snapshots_used':redirected,
            'scope':'Frozen outputs verified in place; exactly three intentionally hardened source dependencies verified against preserved original bytes'}


def compare_numeric(actual, expected):
    count=0
    for key,value in actual.items():
        if isinstance(value,(int,float,np.integer,np.floating)) and key in expected:
            assert np.isclose(value,expected[key],rtol=0,atol=1e-12),(key,value,expected[key])
            count+=1
    return count


def verify():
    freeze=verify_old_freeze()
    gate=Path('outputs/round16_reproducibility')
    assert json.loads((gate/'baseline_gate.json').read_text())['passed']
    data=pickle.load((gate/'baseline_graphs.pkl').open('rb'))
    ref=pd.read_csv('outputs/baseline/supra_labels.csv',index_col=0).loc[data['names'],data['keys']].to_numpy().T
    cfg=load_config('configs/round16_decomposition.yaml')
    _,names,_,_,matrices=_prepare('configs/baseline.yaml')
    assert names==data['names']
    assert all(array_hash(matrices[k])==array_hash(data['matrices'][k]) for k in data['keys'])
    checks=json.loads((gate/'graph_checksums.json').read_text())
    for key in ['static','supra']:
        assert graph_fingerprint(data[key])==checks[key]
    comparisons=0; runs=0
    for directory in ['outputs/round16_perturbation_decomposition','outputs/round16_resolution']:
        root=Path(directory); assert completed(root/'aggregate')
        for p in (root/'runs').iterdir():
            assert completed(p)
            raw=json.loads((p/'raw_results.json').read_text())
            actual=np.load(p/'supra_labels.npy').reshape(ref.shape)
            stats,monthly=temporal_diagnostics(ref,actual,data['keys'])
            comparisons+=compare_numeric(stats,raw['run'])
            largest=np.unique(actual[-1],return_counts=True)[1].max()
            assert largest==raw['run']['largest_community_n_Dec']
            pro,pairs=profile_diagnostics(ref[-1],actual[-1],cfg['experiment']['profiles'])
            for left,right in zip(pro,raw['profiles']):
                assert left['archetype']==right['archetype']; comparisons+=compare_numeric(left,right)
            for left,right in zip(pairs,raw['pairs']):
                assert left['pair']==right['pair']; comparisons+=compare_numeric(left,right)
            for left,right in zip(monthly,raw['monthly']):
                comparisons+=compare_numeric(left,right)
            runs+=1
    # Fresh metric replay for each rebuilt algorithm, not clustering.
    bpath=Path('outputs/round16_benchmark'); benchmark=pd.read_csv(bpath/'canonical_method_benchmark.csv').set_index('method')
    for method in ['Louvain','Greedy','Spectral','KMeans','Ward']:
        labels=pd.read_csv(bpath/f'{method}_labels.csv').set_index('mo').loc[names,'community'].to_numpy()
        actual=validity_metrics(data['static'],labels,matrices[data['keys'][-1]])
        comparisons+=compare_numeric(actual,benchmark.loc[method].to_dict())
    old=pd.read_csv('outputs/perturbation_v2/archetype_status_round15_perturbation_v2.csv')
    new=pd.read_csv(ROOT/'archetype_status_round16.csv')
    assert list(old.round15_status)==list(new.round16_status) and not new.changed.any()
    assert completed('outputs/round16_competition')
    return {'passed':True,'old_freeze':freeze,'raw_new_runs_verified':runs,
            'numeric_comparisons':comparisons,'reconstructed_feature_months_bitwise_equal':24,
            'scientific_status_changes':0,'scope':'forensic label/metric replay, not repeated optimization'}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--record',action='store_true');args=parser.parse_args()
    record=ROOT/'ROUND16_VERIFICATION.json'
    if args.record and record.exists():
        raise FileExistsError('Verification record already exists; use read-only verification')
    result=verify()
    # Existing new freeze is checked before any optional recording.
    inventory=ROOT/'ROUND16_FILES_SHA256.csv'; manifest=ROOT/'ROUND16_FREEZE_MANIFEST.json'
    if inventory.exists():
        m=json.loads(manifest.read_text())
        assert sha256(manifest)==(ROOT/'ROUND16_FREEZE_MANIFEST.sha256').read_text().split()[0]
        assert sha256(inventory)==m['inventory_sha256']
        for r in pd.read_csv(inventory).itertuples():
            assert sha256(r.path)==r.sha256,r.path
        result['round16_freeze']='PASS'
    if args.record:
        test=subprocess.run([sys.executable,'-m','pytest','-q'],capture_output=True,text=True,check=False)
        (ROOT/'tests.log').write_text(test.stdout+test.stderr,encoding='utf-8')
        assert test.returncode==0,test.stdout+test.stderr
        result.update(timestamp_utc=datetime.now(timezone.utc).isoformat(),tests=test.stdout.strip(),tests_passed=True,
                      all_acceptance_criteria_met=False,limitation='Case3 individual contextual evidence and verified regional/covariate joins missing')
        acceptance=pd.read_csv(ROOT/'ACCEPTANCE_CRITERIA.csv')
        acceptance.loc[acceptance.criterion.eq(15),'status']='PASS'
        acceptance.loc[acceptance.criterion.eq(15),'note']=test.stdout.strip().splitlines()[-1]
        acceptance.to_csv(ROOT/'ACCEPTANCE_CRITERIA.csv',index=False)
        save_json(record,result)
        paths=[]
        for directory in ['configs','scripts','src','tests','docs','reference/round16',
                          'outputs/round16_reproducibility','outputs/round16_protocol_gate',
                          'outputs/round16_perturbation_decomposition','outputs/round16_resolution',
                          'outputs/round16_benchmark','outputs/round16_competition','outputs/round16_evidence']:
            paths.extend(p for p in Path(directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
        pd.DataFrame([{'path':p.as_posix(),'bytes':p.stat().st_size,'sha256':sha256(p)} for p in sorted(set(paths))]).to_csv(inventory,index=False)
        save_json(manifest,{'version':'2.3.0','inventory_sha256':sha256(inventory),'files':len(set(paths)),
                           'complete_acceptance':False,'old_outputs_unchanged':True,'source_hardening_snapshots':result['old_freeze']['source_snapshots_used']})
        (ROOT/'ROUND16_FREEZE_MANIFEST.sha256').write_text(sha256(manifest)+'  ROUND16_FREEZE_MANIFEST.json\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
