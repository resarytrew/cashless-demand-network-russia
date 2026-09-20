from pathlib import Path
import json, zipfile
import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist, squareform

ROOT=Path('/mnt/data')
SEED=20260919
BLOCK_SIZES_KM=[300,500,750,1000]
SHIFTS=[(0.0,0.0),(0.5,0.0),(0.0,0.5),(0.5,0.5)]
SUBSAMPLE_REPS=1000
SUBSAMPLE_SHARE=0.80
ARCH_MAP={1:'A',3:'B',7:'C',8:'D',9:'E',10:'F',11:'G'}
ARCHS=list('ABCDEFG')


def load_feature_matrix(names):
    p=ROOT/'potrebitelskie-beznalicnye-rashody-na-urovne-munizipalnyh-obrazovanij_ru_1764079373653.csv.zip'
    with zipfile.ZipFile(p) as z:
        df=pd.read_csv(z.open(z.namelist()[0]),sep=';')
    df['period']=pd.to_datetime(df['period'])
    dec=df[df['period'].eq(pd.Timestamp('2024-12-01')) & df['mo'].isin(names)].copy()
    pivot=dec.pivot(index='mo',columns='category_15',values='value').loc[names].copy()
    cats=['Продовольствие','Здоровье','Общественное питание','Маркетплейсы','Транспорт']
    pivot['Прочее']=pivot['Все категории']-pivot[cats].sum(axis=1)
    parts=cats+['Прочее']
    comp=pivot[parts].div(pivot['Все категории'],axis=0).to_numpy(float)
    logc=np.log(comp); clr=logc-logc.mean(axis=1,keepdims=True)
    lt=np.log(pivot['Все категории'].to_numpy(float)); med=np.median(lt); mad=np.median(np.abs(lt-med))
    z=(lt-med)/(1.4826*mad)
    ms=np.median(pdist(clr)); ml=np.median(pdist(z[:,None]))
    X=np.column_stack([np.sqrt(.7)*clr/ms,np.sqrt(.3)*z[:,None]/ml])
    return X


def grouped_distance_sums(D, group_ids, K):
    """KxK ordered distance sums: S[h,g] = sum_{i in h,j in g} D_ij."""
    n=D.shape[0]
    tmp=np.empty((n,K),dtype=float)
    members=[np.where(group_ids==g)[0] for g in range(K)]
    for g,idx in enumerate(members):
        tmp[:,g]=D[:,idx].sum(axis=1)
    S=np.empty((K,K),dtype=float)
    for h,idx in enumerate(members):
        S[h,:]=tmp[idx,:].sum(axis=0)
    return S, members


def expected_total(S,N,m):
    p=np.divide(m,N,out=np.zeros_like(m,dtype=float),where=N>0)
    q=np.zeros_like(p)
    ok=N>1
    q[ok]=m[ok]*(m[ok]-1)/(N[ok]*(N[ok]-1))
    M=np.outer(p,p)*S
    np.fill_diagonal(M,q*np.diag(S))
    return 0.5*M.sum(), M


def aggregate_matrix_by_blocks(M, stratum_block, B):
    out=np.zeros((B,B),dtype=float)
    # bincount each row to destination blocks, then accumulate rows by source block
    for h in range(M.shape[0]):
        rowagg=np.bincount(stratum_block,weights=M[h],minlength=B)
        out[stratum_block[h]] += rowagg
    return out


def block_matrix_for_observed(D,target_mask,block_codes,B):
    idx=np.where(target_mask)[0]
    if len(idx)==0:
        return np.zeros((B,B)),np.zeros(B,dtype=int)
    Dt=D[np.ix_(idx,idx)]
    tb=block_codes[idx]
    counts=np.bincount(tb,minlength=B)
    # aggregate ordered matrix by target blocks
    K=B
    tmp=np.empty((len(idx),K),dtype=float)
    members=[np.where(tb==b)[0] for b in range(B)]
    for b,inds in enumerate(members):
        if len(inds): tmp[:,b]=Dt[:,inds].sum(axis=1)
        else: tmp[:,b]=0.0
    out=np.zeros((B,B),dtype=float)
    for b,inds in enumerate(members):
        if len(inds): out[b,:]=tmp[inds,:].sum(axis=0)
    return out,counts


def main():
    spatial=pd.read_csv(ROOT/'municipality_spatial_join_1904.csv')
    spatial=spatial[spatial['centroid_lon'].notna() & spatial['centroid_lat'].notna()].copy().reset_index(drop=True)
    labels=pd.read_csv(ROOT/'supra_labels_admin_residual_base.csv').rename(columns={'Unnamed: 0':'sber_name','2024-12-01':'community_id'})
    labels['archetype']=labels['community_id'].map(ARCH_MAP)
    spatial=spatial.drop(columns=['community_id','archetype'],errors='ignore').merge(labels[['sber_name','community_id','archetype']],on='sber_name',how='left',validate='one_to_one')
    # Preserve the baseline feature geometry: compute scaling on the full strict 1904 panel,
    # then subset to the 1903 municipalities that have geometry.
    full_names=pd.read_csv(ROOT/'municipality_crosswalk_final_1904.csv')['sber_name'].tolist()
    X_full=load_feature_matrix(full_names)
    pos={name:i for i,name in enumerate(full_names)}
    X=X_full[[pos[name] for name in spatial['sber_name']]]
    D=squareform(pdist(X))
    archetype=spatial['archetype'].to_numpy(object)
    admin=spatial['sber_type_2023_24'].astype(str).to_numpy(object)

    # Equal-area coordinates.
    pts=gpd.GeoDataFrame(geometry=gpd.points_from_xy(spatial['centroid_lon'],spatial['centroid_lat']),crs=4326).to_crs(6933)
    xx=pts.geometry.x.to_numpy(); yy=pts.geometry.y.to_numpy()

    # Reference observed distances for audit.
    obs_ref={}
    for a in ARCHS:
        idx=np.where(archetype==a)[0]
        sub=D[np.ix_(idx,idx)]
        obs_ref[a]=sub[np.triu_indices(len(idx),1)].mean()

    rng=np.random.default_rng(SEED)
    spec_rows=[]; subs_rows=[]; loo_rows=[]

    for size_km in BLOCK_SIZES_KM:
        size=size_km*1000.0
        for sx,sy in SHIFTS:
            bx=np.floor((xx-sx*size)/size).astype(int); by=np.floor((yy-sy*size)/size).astype(int)
            block_label=np.array([f'{a}:{b}' for a,b in zip(bx,by)],dtype=object)
            block_codes,block_uniques=pd.factorize(block_label,sort=True)
            B=len(block_uniques)
            str_label=np.array([f'{b}|{ad}' for b,ad in zip(block_label,admin)],dtype=object)
            str_codes,str_uniques=pd.factorize(str_label,sort=True)
            K=len(str_uniques)
            N=np.bincount(str_codes,minlength=K)
            S,_=grouped_distance_sums(D,str_codes,K)
            # map stratum to block code via first occurrence
            stratum_block=np.empty(K,dtype=int)
            for h in range(K):
                stratum_block[h]=block_codes[np.where(str_codes==h)[0][0]]

            for a in ARCHS:
                mask=archetype==a
                m=np.bincount(str_codes[mask],minlength=K)
                n=int(mask.sum())
                Etot,M=expected_total(S,N,m)
                Emean=Etot/(n*(n-1)/2)
                ratio=obs_ref[a]/Emean
                spec_rows.append(dict(block_size_km=size_km,shift_x_fraction=sx,shift_y_fraction=sy,n_blocks=B,n_strata=K,
                                      archetype=a,n=n,observed_mean_distance=obs_ref[a],spatial_block_admin_null_mean=Emean,
                                      ratio_spatial_block_admin=ratio,null_definition='exact counts by equal-area block × Sber admin form'))

                if (sx,sy)==(0.0,0.0):
                    Eblock=aggregate_matrix_by_blocks(M,stratum_block,B)
                    Oblock,counts=block_matrix_for_observed(D,mask,block_codes,B)
                    full_ratio=Oblock.sum()/Eblock.sum()
                    keep_n=max(2,int(round(SUBSAMPLE_SHARE*B)))
                    # Generate block selection matrix once per profile for deterministic but independent draws.
                    Z=np.zeros((SUBSAMPLE_REPS,B),dtype=float)
                    for r in range(SUBSAMPLE_REPS):
                        chosen=rng.choice(B,size=keep_n,replace=False)
                        Z[r,chosen]=1.0
                    Os=0.5*np.einsum('bi,ij,bj->b',Z,Oblock,Z,optimize=True)
                    Es=0.5*np.einsum('bi,ij,bj->b',Z,Eblock,Z,optimize=True)
                    ratios=np.divide(Os,Es,out=np.full_like(Os,np.nan),where=Es>0)
                    ns=Z@counts
                    good=np.isfinite(ratios)&(ns>=2)
                    ratios=ratios[good]; ns=ns[good]
                    subs_rows.append(dict(block_size_km=size_km,archetype=a,full_ratio=full_ratio,full_n=n,n_blocks=B,
                                          subsample_share_blocks=SUBSAMPLE_SHARE,reps=len(ratios),ratio_median=np.median(ratios),
                                          ratio_q05=np.quantile(ratios,.05),ratio_q25=np.quantile(ratios,.25),ratio_q75=np.quantile(ratios,.75),
                                          ratio_q95=np.quantile(ratios,.95),share_ratio_lt_1=np.mean(ratios<1),share_ratio_lt_0_9=np.mean(ratios<.9),
                                          median_profile_n_in_subsample=np.median(ns),method_note='80% blocks without replacement'))

                    if size_km==500:
                        # leave one block out via total minus row/column
                        Ototal=0.5*Oblock.sum(); Etotal=0.5*Eblock.sum()
                        o_row=Oblock.sum(axis=1); e_row=Eblock.sum(axis=1)
                        o_diag=np.diag(Oblock); e_diag=np.diag(Eblock)
                        Oloo=Ototal-o_row+0.5*o_diag
                        Eloo=Etotal-e_row+0.5*e_diag
                        nloo=n-counts
                        vals=np.divide(Oloo,Eloo,out=np.full(B,np.nan),where=(Eloo>0)&(nloo>=2))
                        vals=vals[np.isfinite(vals)]
                        loo_rows.append(dict(block_size_km=500,archetype=a,full_ratio=full_ratio,n_blocks=B,
                                             loo_min=np.min(vals),loo_q05=np.quantile(vals,.05),loo_median=np.median(vals),
                                             loo_q95=np.quantile(vals,.95),loo_max=np.max(vals),loo_all_lt_1=bool(np.all(vals<1)),
                                             max_abs_change_from_full=np.max(np.abs(vals-full_ratio)),min_profile_n_after_drop=int(np.min(nloo[nloo>=2]))))

    specs=pd.DataFrame(spec_rows); subs=pd.DataFrame(subs_rows); loo=pd.DataFrame(loo_rows)
    grp=specs.groupby('archetype')['ratio_spatial_block_admin']
    summary=grp.agg(['min','median','max']).reset_index()
    qs=grp.quantile([.05,.25,.75,.95]).unstack(); qs.columns=['q05','q25','q75','q95']
    summary=summary.merge(qs.reset_index(),on='archetype')
    summary['specifications_n']=grp.size().values
    summary['share_specs_ratio_lt_1']=grp.apply(lambda s:float((s<1).mean())).values
    summary['share_specs_ratio_lt_0_9']=grp.apply(lambda s:float((s<.9).mean())).values
    prev=pd.read_csv(ROOT/'region_admin_stratified_null_dec2024.csv')[['archetype','ratio_admin','ratio_region_admin']]
    summary=summary.merge(prev,on='archetype',how='left')

    specs.to_csv(ROOT/'spatial_block_admin_null_all_specs.csv',index=False)
    summary.to_csv(ROOT/'spatial_block_admin_null_summary.csv',index=False)
    subs.to_csv(ROOT/'spatial_block_subsampling_80pct.csv',index=False)
    loo.to_csv(ROOT/'spatial_block_leave_one_out_500km.csv',index=False)
    manifest=dict(seed=SEED,geometry_n=len(spatial),block_sizes_km=BLOCK_SIZES_KM,shift_fractions=SHIFTS,
                  subsample_reps=SUBSAMPLE_REPS,subsample_share=SUBSAMPLE_SHARE,
                  method='exact spatial-block x admin matched null + 80% block subsampling + 500km leave-one-block-out')
    (ROOT/'spatial_block_robustness_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    with open(ROOT/'SPATIAL_BLOCK_ROBUSTNESS_AUDIT.md','w',encoding='utf-8') as f:
        f.write('# Spatial block robustness audit\n\n')
        f.write('## Design\n\n')
        f.write('- Geometry coverage: 1903/1904. The supplied layer has no polygon for Pervomaisk, Luhansk People’s Republic.\n')
        f.write('- Feature space: December 2024 reference CLR + relative spending level, weights 70/30.\n')
        f.write('- Equal-area square blocks: 300, 500, 750, 1000 km; four grid origins each.\n')
        f.write('- Null preserves exact profile counts within spatial block × Sber administrative form.\n')
        f.write('- Primary effect size R = observed mean within-profile distance / exact matched-null expected distance. R<1 means residual compactness.\n')
        f.write('- 80% block subsampling is without replacement. This is deliberate: with-replacement cluster bootstrap duplicates municipalities and creates artificial zero pair distances for a pairwise-distance statistic.\n')
        f.write('- A 500-km leave-one-block-out analysis checks whether one geographic block dominates a result.\n\n')
        f.write('## Across all 16 spatial-block specifications\n\n'+summary.to_markdown(index=False,floatfmt='.4f')+'\n\n')
        f.write('## 80% spatial-block subsampling\n\n'+subs.to_markdown(index=False,floatfmt='.4f')+'\n\n')
        f.write('## 500-km leave-one-block-out\n\n'+loo.to_markdown(index=False,floatfmt='.4f')+'\n')

    print('OBSERVED',obs_ref)
    print('\nSUMMARY\n',summary.to_string(index=False))
    print('\nSUBSAMPLE\n',subs.to_string(index=False))
    print('\nLOO\n',loo.to_string(index=False))

if __name__=='__main__': main()
