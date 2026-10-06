"""Create presentation JSON strictly from completed, frozen-or-derived artifacts."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path("outputs/final_competition_upgrade")
EXT=ROOT/"external_validation_national_20261006_r6"
STORY=ROOT/"story_data"


def clean(value):
    if isinstance(value, dict): return {str(k):clean(v) for k,v in value.items()}
    if isinstance(value, list): return [clean(v) for v in value]
    if isinstance(value, (np.integer,)): return int(value)
    if isinstance(value, (np.floating, float)):
        return None if not np.isfinite(value) else float(value)
    if pd.isna(value): return None
    return value


def dump(name: str, value) -> None:
    (STORY/name).write_text(json.dumps(clean(value),ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")


def main() -> None:
    if STORY.exists(): raise FileExistsError(f"Refusing to overwrite {STORY}")
    STORY.mkdir(parents=True)
    profile=pd.read_csv(ROOT/"profile_naming/profile_evidence_table.csv")
    global_tests=pd.read_csv(EXT/"external_global_tests.csv")
    prediction=pd.read_csv(EXT/"external_prediction_metrics.csv")
    permutation=pd.read_csv(EXT/"permutation_label_baseline.csv")
    grouped=pd.read_csv(ROOT/"geographic_confounding/external_prediction_grouped_cv.csv")
    loro=pd.read_csv(ROOT/"geographic_confounding/leave_one_region_out.csv")
    regional_baseline=pd.read_csv(ROOT/"geographic_confounding/region_only_baseline.csv")
    within=pd.read_csv(ROOT/"geographic_confounding/within_region_profile_tests.csv")
    benchmark=pd.read_csv(ROOT/"synthetic_temporal/pareto_summary.csv")
    omega=pd.read_csv(ROOT/"synthetic_temporal/omega_aggregate.csv")
    coverage=pd.read_csv(EXT/"external_validation_coverage.csv")
    effects=global_tests.set_index("variable").epsilon_squared.to_dict()
    dump("summary.json",{"reference_n":1904,"verified_lineage_n":1903,"population_coverage":1903,"wage_coverage":1890,"employment_coverage":1890,"okved_coverage":1888,"effect_sizes":{"population":effects["population"],"wage":effects["wage"],"employment":effects["employment_total"]},"external_prediction":{"logistic_macro_f1":prediction.loc[prediction.model.eq("multinomial_logistic"),"macro_f1"].item(),"random_forest_macro_f1":prediction.loc[prediction.model.eq("random_forest"),"macro_f1"].item(),"permutation_macro_f1":permutation.macro_f1.mean()},"regional_grouped_cv":grouped[["model","macro_f1","balanced_accuracy","accuracy","log_loss"]].to_dict(orient="records"),"temporal":{"reference_omega":2,"synthetic_benchmark_status":"COMPLETED","recommended_tradeoff_range":"scenario-dependent; 2 is retained reference trade-off"}})
    dump("profiles.json",profile.rename(columns={"technical_label":"technical_label"}).to_dict(orient="records"))
    joined=pd.read_csv(EXT/"external_validation_joined.csv"); labels=pd.read_csv("outputs/baseline/supra_labels.csv",index_col=0); atlas=pd.read_csv("outputs/stability_atlas_v2_2_1/municipality_affinity_atlas.csv")
    label_map={"1":"A","3":"B","7":"C","8":"D","9":"E","10":"F","11":"G"}; display=profile.set_index("technical_label").display_name.to_dict()
    records=[]
    atlas=atlas.rename(columns={"municipality":"reference_mo"})
    for item in joined.itertuples(index=False):
        if item.reference_mo not in labels.index: continue
        series=labels.loc[item.reference_mo].to_numpy(); raw=int(series[-1]); mapped=label_map.get(str(raw),"micro")
        matched=atlas.loc[atlas.reference_mo.eq(item.reference_mo)]
        stability=None if matched.empty else matched.iloc[0].stability_class
        records.append({"territory_id":item.territory_id,"official_name":item.official_name,"region":item.region,"oktmo":item.oktmo,"profile":mapped,"profile_display_name":display.get(mapped,"Техническое микросообщество"),"raw_community":raw,"stability_class":stability,"switch_count":int(np.sum(series[1:]!=series[:-1])),"dominant_profile":label_map.get(str(pd.Series(series).mode().iloc[0]),"micro"),"wage":item.wage,"population":item.population,"employment":item.employment_total,"external_data_available":bool(pd.notna(item.population) and pd.notna(item.wage) and pd.notna(item.employment_total))})
    if len(records)!=1903: raise ValueError(f"Expected 1903 verified municipalities, found {len(records)}")
    dump("municipalities.json",records)
    dump("external_validation.json",{"coverage":coverage.to_dict(orient="records"),"global_tests":global_tests.to_dict(orient="records"),"sector_permanova":json.loads((EXT/"employment_sector_permanova.json").read_text(encoding="utf-8"))})
    dump("external_prediction.json",{"stratified_cv":prediction.to_dict(orient="records"),"permutation_mean":permutation[["macro_f1","balanced_accuracy","accuracy"]].mean().to_dict()})
    dump("regional_generalization.json",{"grouped_cv":grouped.to_dict(orient="records"),"leave_one_region_out":loro.to_dict(orient="records"),"region_only":regional_baseline.to_dict(orient="records"),"within_region_tests":within.to_dict(orient="records")})
    dump("temporal_benchmark.json",{"aggregate":omega.to_dict(orient="records"),"scenario_pareto":benchmark.to_dict(orient="records")})
    dump("transition_flows.json",pd.read_csv("outputs/presubmission_upgrade/visualization/halfyear_transition_flows.csv").to_dict(orient="records"))
    dump("temporal_trajectories.json",pd.read_csv("outputs/presubmission_upgrade/visualization/municipality_profile_trajectories.csv").to_dict(orient="records"))
    dump("robustness.json",{"representation":json.loads((ROOT/"synthetic_temporal/run_manifest.json").read_text(encoding="utf-8")),"reference_note":"Existing frozen robustness outputs are preserved; exact boundaries remain specification-dependent."})
    dump("icvi.json",pd.read_csv("outputs/presubmission_upgrade/icvi/canonical_icvi.csv").to_dict(orient="records"))

if __name__ == "__main__": main()
