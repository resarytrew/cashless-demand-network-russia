#!/usr/bin/env python3
import csv, json, math, statistics, sys
from pathlib import Path
import numpy as np
from scipy import stats
import statsmodels.api as sm

ROOT=Path(__file__).resolve().parent
def num(v):
    if v is None or v=="": return None
    return float(v)
rows=[]
with open(ROOT/"external_validation_58.csv",encoding="utf-8-sig",newline="") as f:
    for r in csv.DictReader(f):
        for k in ["population_2024","urban_population_2024","urban_share_2024","salary_2024","salary_2025","investment_per_capita_2024","workers_2024"]:
            r[k]=num(r[k])
        rows.append(r)

def spear(x,y):
    z=stats.spearmanr(x,y)
    return float(z.statistic),float(z.pvalue)
def cliffs_delta(x,y):
    gt=sum(a>b for a in x for b in y); lt=sum(a<b for a in x for b in y)
    return (gt-lt)/(len(x)*len(y))

actual={}
yak=[r for r in rows if r["region"]=="Республика Саха (Якутия)" and r["profile"]=="A"]
actual["A_YAK_WAGE_INVEST"]=dict(zip(["value","p_value"],spear([r["salary_2024"] for r in yak],[r["investment_per_capita_2024"] for r in yak])))
actual["A_YAK_WAGE_POP"]=dict(zip(["value","p_value"],spear([r["salary_2024"] for r in yak],[r["population_2024"] for r in yak])))
actual["A_YAK_WAGE_URBAN"]=dict(zip(["value","p_value"],spear([r["salary_2024"] for r in yak],[r["urban_share_2024"] for r in yak])))
X=np.column_stack([np.log([r["investment_per_capita_2024"] for r in yak]),np.log([r["population_2024"] for r in yak]),[r["urban_share_2024"] for r in yak]])
fit=sm.OLS(np.log([r["salary_2024"] for r in yak]),sm.add_constant(X)).fit(cov_type="HC3")
actual["A_YAK_HC3_LOGINVEST"]={"value":float(fit.params[1]),"p_value":float(fit.pvalues[1])}
actual["A_YAK_WAGE_2024_2025"]=dict(zip(["value","p_value"],spear([r["salary_2024"] for r in yak],[r["salary_2025"] for r in yak])))

rank={"G":1,"F":2,"D":3}
alt=[r for r in rows if r["region"]=="Республика Алтай" and r["profile"] in rank]
actual["ALT_DFG_WAGE_GRADIENT"]=dict(zip(["value","p_value"],spear([rank[r["profile"]] for r in alt],[r["salary_2024"] for r in alt])))
X=np.column_stack([[rank[r["profile"]] for r in alt],np.log([r["population_2024"] for r in alt]),[r["urban_share_2024"] for r in alt]])
fit=sm.OLS(np.log([r["salary_2024"] for r in alt]),sm.add_constant(X)).fit()
actual["ALT_DFG_ADJUSTED"]={"value":float(fit.params[1]),"p_value":float(fit.pvalues[1])}

kh=[r for r in rows if r["region"]=="Хабаровский край"]
A=[r["salary_2024"] for r in kh if r["profile"]=="A"]; G=[r["salary_2024"] for r in kh if r["profile"]=="G"]
actual["KHAB_A_G_WAGE"]={"value":cliffs_delta(A,G),"p_value":float(stats.mannwhitneyu(A,G,alternative="two-sided").pvalue)}
chu=[r for r in rows if r["region"]=="Чукотский АО"]
actual["CHU_A_WAGE_2024"]={"value":statistics.median([r["salary_2024"] for r in chu]),"p_value":None}
actual["CHU_A_WAGE_2025"]={"value":statistics.median([r["salary_2025"] for r in chu]),"p_value":None}

exp=json.loads((ROOT/"expected_results.json").read_text(encoding="utf-8"))
failed=[]
for k,e in exp["tests"].items():
    a=actual[k]
    for field in ("value","p_value"):
        ev=e[field]; av=a[field]
        if ev is None and av is None: continue
        tol=1e-10*max(1.0,abs(float(ev)))
        if abs(float(av)-float(ev))>tol:
            failed.append((k,field,av,ev))
profiles={p:sum(r["profile"]==p for r in rows) for p in sorted(set(r["profile"] for r in rows))}
regions={p:sum(r["region"]==p for r in rows) for p in sorted(set(r["region"] for r in rows))}
print(f"rows={len(rows)}; profiles={profiles}; regions={regions}")
for k,a in actual.items(): print(k,a)
if failed:
    print("FAIL",failed,file=sys.stderr); sys.exit(1)
print("PASS: all restored tests reproduce expected values within numerical tolerance.")
