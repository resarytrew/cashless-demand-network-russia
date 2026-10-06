"""Run prespecified region-held-out checks on the frozen external interpretation layer."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import pandas as pd
import yaml
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sbernet.regional_validation import grouped_prediction, region_only_baseline, within_region_residuals, within_region_tests


def main(path: str) -> None:
    config=Path(path); cfg=yaml.safe_load(config.read_text(encoding="utf-8")); exp=cfg["experiment"]; out=Path(exp["output_dir"])
    if out.exists(): raise FileExistsError(f"Refusing to overwrite {out}")
    out.mkdir(parents=True)
    frame=pd.read_csv(exp["input_csv"],dtype={"region":"string"}); frame=frame.loc[frame.profile.isin(list("ABCDEFG"))].copy()
    features=["population","wage","employment_total"]+[x for x in frame if x in {"administrative","arts","construction","education","finance","health","hospitality","information","manufacturing","other_services","professional","public_administration","real_estate","trade","utilities"}]
    grouped=grouped_prediction(frame,features,exp["folds"],exp["seed"]); grouped.to_csv(out/"external_prediction_grouped_cv.csv",index=False)
    region_only=region_only_baseline(frame,exp["folds"]); region_only.to_csv(out/"region_only_baseline.csv",index=False)
    residual=within_region_residuals(frame,["population","wage","employment_total"])
    tests=within_region_tests(residual,["population_within_region","wage_within_region","employment_total_within_region"]); tests.to_csv(out/"within_region_profile_tests.csv",index=False)
    rows=[]
    for region, held in frame.groupby("region",sort=True):
        if len(held)<exp["min_leave_one_region_n"]: continue
        train=frame.loc[frame.region.ne(region)]; test=held; y=train.profile.to_numpy(); x=train[features].to_numpy(); x_test=test[features].to_numpy()
        for name,model in {"multinomial_logistic":Pipeline([("impute",SimpleImputer(strategy="median")),("scale",StandardScaler()),("model",LogisticRegression(max_iter=3000,class_weight="balanced",random_state=exp["seed"]))]),"random_forest":Pipeline([("impute",SimpleImputer(strategy="median")),("model",RandomForestClassifier(n_estimators=400,min_samples_leaf=3,class_weight="balanced",random_state=exp["seed"],n_jobs=-1))])}.items():
            model.fit(x,y); pred=model.predict(x_test); prob=model.predict_proba(x_test); majority=pd.Series(y).value_counts().sort_index().idxmax()
            rows.append({"region":region,"model":name,"n":len(test),"macro_f1":f1_score(test.profile,pred,average="macro",zero_division=0),"balanced_accuracy":balanced_accuracy_score(test.profile,pred),"accuracy":accuracy_score(test.profile,pred),"log_loss":log_loss(test.profile,prob,labels=model.classes_),"majority_baseline":float((test.profile==majority).mean()),"coverage":1.0})
    loro=pd.DataFrame(rows); loro.to_csv(out/"leave_one_region_out.csv",index=False)
    report=f"""# Geographic confounding and regional generalisation\n\nAll analyses use frozen A–G labels and post-hoc external variables; no output returns to clustering. GroupKFold holds entire `region` values out, with a runtime disjointness assertion. Regional prediction metrics: {grouped[['model','macro_f1','balanced_accuracy']].to_dict(orient='records')}. The region-only diagnostic is explicitly an unseen-region training-majority baseline, because a one-hot region model cannot identify an unobserved subject.\n\nWithin-region centring subtracts the observed regional median before Kruskal–Wallis testing. Results are associations and do not make a causal geography claim. Leave-one-region-out rows below the minimum n are intentionally omitted.\n"""
    (out/"GEOGRAPHIC_CONFOUNDING_REPORT.md").write_text(report,encoding="utf-8")
    (out/"run_manifest.json").write_text(json.dumps({"status":"COMPLETED","config_sha256":hashlib.sha256(config.read_bytes()).hexdigest(),"input_sha256":hashlib.sha256(Path(exp["input_csv"]).read_bytes()).hexdigest(),"features":features},indent=2),encoding="utf-8")

if __name__ == "__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--config",default="configs/geographic_confounding.yaml"); main(parser.parse_args().config)
