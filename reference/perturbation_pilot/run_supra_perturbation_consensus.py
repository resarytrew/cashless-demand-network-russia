#!/usr/bin/env python3
import argparse, zipfile, math, time, os, json
from pathlib import Path
import numpy as np, pandas as pd, networkx as nx
from sklearn.neighbors import NearestNeighbors
from scipy.spatial.distance import pdist
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
from multiprocessing import get_context

R=Path('/mnt/data')
GLOBAL={}

def build_shared():
    with zipfile.ZipFile(R/'potrebitelskie-beznalicnye-rashody-na-urovne-munizipalnyh-obrazovanij_ru_1764079373653.csv.zip') as zf:
        df=pd.read_csv(zf.open(zf.namelist()[0]),sep=';')
    df['period']=pd.to_datetime(df['period'])
    kc=df.groupby(['mo','category_15','period']).size(); dup=set(kc[kc>1].reset_index()['mo'])
    cnt=df.groupby(['mo','category_15'])['period'].nunique().unstack(fill_value=0)
    cats=list(df['category_15'].drop_duplicates())
    names=sorted([m for m,row in cnt.iterrows() if m not in dup and all(row.get(c,0)==24 for c in cats)])
    N=len(names)
    piv=df[df['mo'].isin(names)].pivot(index=['mo','period'],columns='category_15',values='value').reset_index()
    piv['Прочее']=piv['Все категории']-piv[['Здоровье','Маркетплейсы','Общественное питание','Продовольствие','Транспорт']].sum(axis=1)
    cc=['Продовольствие','Здоровье','Общественное питание','Маркетплейсы','Транспорт','Прочее']
    months=sorted(piv['period'].unique()); month_keys=[str(pd.Timestamp(m).date()) for m in months]; T=len(months)
    base=[]; weights=[]
    for t,(m,key) in enumerate(zip(months,month_keys)):
        d=piv[piv['period'].eq(m)].set_index('mo').loc[names]
        tot=d['Все категории'].to_numpy(float); comp=d[cc].to_numpy(float)/tot[:,None]
        lc=np.log(comp); clr=lc-lc.mean(axis=1,keepdims=True)
        lt=np.log(tot); med=np.median(lt); mad=np.median(np.abs(lt-med)); z=(lt-med)/(1.4826*mad)
        ms=np.median(pdist(clr)); ml=np.median(pdist(z[:,None]))
        X=np.c_[np.sqrt(.7)*clr/ms,np.sqrt(.3)*z[:,None]/ml]
        nn=NearestNeighbors(n_neighbors=21).fit(X); dist,idx=nn.kneighbors(X)
        neigh=idx[:,1:]; dd=dist[:,1:]; sig=dd[:,-1]; sets=[set(map(int,r)) for r in neigh]
        for i in range(N):
            for j in neigh[i]:
                j=int(j)
                if j<=i or i not in sets[j]: continue
                dij=float(np.linalg.norm(X[i]-X[j])); w=math.exp(-(dij*dij)/(sig[i]*sig[j]+1e-12))
                base.append((t*N+i,t*N+j,w)); weights.append(w)
    tw=2.0*float(np.median(weights))
    temporal=[(t*N+i,(t+1)*N+i,tw) for t in range(T-1) for i in range(N)]
    ref=pd.read_csv(R/'supra_labels_omega_2.0.csv',index_col=0).loc[names,month_keys]
    ref_flat=ref.to_numpy().T.reshape(-1); ref_dec=ref[month_keys[-1]].astype(int).to_numpy()
    arch=pd.read_csv(R/'dec2024_archetypes_final.csv'); major_ids=arch['cluster'].astype(int).tolist(); letters={cid:l for cid,l in zip(major_ids,list('ABCDEFG'))}
    return dict(names=names,N=N,T=T,base=base,temporal=temporal,ref_flat=ref_flat,ref_dec=ref_dec,major_ids=major_ids,letters=letters)

def init_worker(shared):
    GLOBAL.update(shared)

def within(lab,inds):
    vc=pd.Series(lab[inds]).value_counts().to_numpy(); den=len(inds)*(len(inds)-1)/2
    return float(np.sum(vc*(vc-1)/2)/den) if den else 1.0

def cross(lab,I,J):
    vi=pd.Series(lab[I]).value_counts(); vj=pd.Series(lab[J]).value_counts(); common=set(vi.index)&set(vj.index)
    return float(sum(int(vi[k])*int(vj[k]) for k in common)/(len(I)*len(J)))

def one_run(seed):
    g=GLOBAL; rng=np.random.default_rng(20260918+seed)
    base=g['base']; keep=rng.random(len(base))>=0.05
    jitter=np.exp(rng.normal(0,0.02,keep.sum()))
    edges=[]; jj=0
    for keep_flag,(u,v,w) in zip(keep,base):
        if keep_flag:
            edges.append((u,v,float(w*jitter[jj]))); jj+=1
    H=nx.Graph(); H.add_nodes_from(range(g['N']*g['T'])); H.add_weighted_edges_from(edges); H.add_weighted_edges_from(g['temporal'])
    comms=nx.community.louvain_communities(H,weight='weight',resolution=.5,seed=seed)
    lab=np.empty(g['N']*g['T'],dtype=int)
    for c,nodes in enumerate(comms): lab[list(nodes)]=c
    dec=lab.reshape(g['T'],g['N'])[-1]
    out={'run':seed,'K_supra':len(comms),'K_Dec2024':len(np.unique(dec)),
         'ARI_all_supra':adjusted_rand_score(g['ref_flat'],lab),'NMI_all_supra':normalized_mutual_info_score(g['ref_flat'],lab),
         'ARI_Dec2024':adjusted_rand_score(g['ref_dec'],dec),'NMI_Dec2024':normalized_mutual_info_score(g['ref_dec'],dec)}
    ids={l:cid for cid,l in g['letters'].items()}; B=np.where(g['ref_dec']==ids['B'])[0]; E=np.where(g['ref_dec']==ids['E'])[0]
    out['BE_cross_coassignment']=cross(dec,B,E); out['B_within_pair_coassignment']=within(dec,B); out['E_within_pair_coassignment']=within(dec,E)
    pro=[]
    for cid in g['major_ids']:
        inds=np.where(g['ref_dec']==cid)[0]; vc=pd.Series(dec[inds]).value_counts()
        pro.append({'run':seed,'profile':g['letters'][cid],'n':len(inds),'best_destination_share':float(vc.iloc[0]/len(inds)),
                    'within_pair_coassignment':within(dec,inds),'n_destinations':int(len(vc))})
    return out,pro

def summarize(results):
    run_rows=[]; pro=[]
    for r,p in results: run_rows.append(r); pro.extend(p)
    runs=pd.DataFrame(run_rows).sort_values('run'); prof=pd.DataFrame(pro)
    runs.to_csv(R/'supra_perturbation_expanded_run_summary.csv',index=False); prof.to_csv(R/'supra_perturbation_expanded_profile_details.csv',index=False)
    be=runs.BE_cross_coassignment.to_numpy()
    beout=pd.DataFrame([{'n_runs':len(be),'mean':be.mean(),'sd':be.std(ddof=1),'median':np.median(be),'q10':np.quantile(be,.1),'q25':np.quantile(be,.25),'q75':np.quantile(be,.75),'q90':np.quantile(be,.9),'min':be.min(),'max':be.max(),'share_lt_0_1':(be<.1).mean(),'share_gt_0_5':(be>.5).mean(),'share_gt_0_9':(be>.9).mean()}])
    beout.to_csv(R/'BE_boundary_expanded_distribution.csv',index=False)
    agg=(prof.groupby('profile').agg(mean_retention=('best_destination_share','mean'),sd_retention=('best_destination_share','std'),q10_retention=('best_destination_share',lambda x:np.quantile(x,.1)),median_retention=('best_destination_share','median'),q90_retention=('best_destination_share',lambda x:np.quantile(x,.9)),min_retention=('best_destination_share','min'),mean_pair_coassignment=('within_pair_coassignment','mean'),min_pair_coassignment=('within_pair_coassignment','min')).reset_index())
    agg.to_csv(R/'supra_perturbation_expanded_profile_summary.csv',index=False)
    print('\nB/E distribution\n',beout.to_string(index=False),flush=True)
    print('\nARI summary\n',runs[['ARI_all_supra','ARI_Dec2024','K_supra','K_Dec2024']].describe().to_string(),flush=True)
    print('\nProfile summary\n',agg.to_string(index=False),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--runs',type=int,default=30); ap.add_argument('--workers',type=int,default=4); args=ap.parse_args()
    shared=build_shared(); print('built graph',shared['N'],shared['T'],len(shared['base']),flush=True)
    # Exact reconstruction check
    G=nx.Graph(); G.add_nodes_from(range(shared['N']*shared['T'])); G.add_weighted_edges_from(shared['base']); G.add_weighted_edges_from(shared['temporal'])
    comms=nx.community.louvain_communities(G,weight='weight',resolution=.5,seed=0); lab=np.empty(shared['N']*shared['T'],int)
    for c,nodes in enumerate(comms): lab[list(nodes)]=c
    print('reconstruction ARI',adjusted_rand_score(shared['ref_flat'],lab),flush=True); del G
    ctx=get_context('fork')
    results=[]
    with ctx.Pool(processes=args.workers,initializer=init_worker,initargs=(shared,)) as pool:
        for i,res in enumerate(pool.imap_unordered(one_run,range(args.runs)),1):
            results.append(res); print(f'{i}/{args.runs} complete',flush=True)
    summarize(results)
