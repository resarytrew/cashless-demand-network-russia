"""Build auditable, bounded human-readable labels from frozen evidence."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import pandas as pd
import yaml


def top_sectors(sectors: pd.DataFrame, profile: str) -> tuple[str,str]:
    value=sectors.loc[sectors.profile==profile, ["statistic", "median"]].dropna()
    if value.empty: return "", ""
    row=value.set_index("statistic")["median"].sort_values()
    return "; ".join(row.tail(3).index), "; ".join(row.head(3).index)


def main(path: str) -> None:
    config=Path(path); cfg=yaml.safe_load(config.read_text(encoding="utf-8")); exp=cfg["experiment"]; out=Path(exp["output_dir"])
    if out.exists(): raise FileExistsError(f"Refusing to overwrite {out}")
    out.mkdir(parents=True)
    typology=pd.read_csv(exp["typology_csv"]); ext=Path(exp["external_dir"]); summary=pd.read_csv(ext/"external_profile_summary.csv"); sectors=pd.read_csv(ext/"employment_sector_profile_summary.csv"); atlas=pd.read_csv(exp["atlas_csv"])
    rows=[]
    for profile in list("ABCDEFG"):
        policy=cfg["profiles"][profile]; base=typology.loc[typology.profile.eq(profile)].iloc[0]
        values=summary.loc[summary.profile.eq(profile)].set_index("variable")
        ranks={name:int(summary.loc[summary.variable.eq(name)].sort_values("median",ascending=False).reset_index(drop=True).query("profile == @profile").index[0]+1) for name in ["wage","population","employment_total"]}
        positive,negative=top_sectors(sectors,profile)
        group=atlas.loc[atlas.reference_profile.eq(profile)]
        rows.append({"technical_label":profile,"display_name":policy["display_name"],"status":policy["status"],"confidence":policy["confidence"],"n":int(base["size"]),"share":float(base.share_of_1904),"behavioural_total_median":float(base.median_Total),"behavioural_signature":f"positive: {base.top_positive_features}; negative: {base.top_negative_features}","wage_median":float(values.loc["wage","median"]),"wage_rank":ranks["wage"],"population_median":float(values.loc["population","median"]),"population_rank":ranks["population"],"employment_median":float(values.loc["employment_total","median"]),"employment_rank":ranks["employment_total"],"top_positive_okved_sector_shares":positive,"top_negative_okved_sector_shares":negative,"stability_class":group.stability_class.mode().iloc[0],"mean_temporal_switches":float(base.mean_temporal_switches),"representation_robustness":"material exact-boundary dependence; no status change","external_validation_strength":"national descriptive differences; exploratory and post-hoc"})
    table=pd.DataFrame(rows); table.to_csv(out/"profile_evidence_table.csv",index=False)
    lines=["# Profile naming audit", "", "Names describe observed local cashless consumer-demand profiles, not whole economies. They are derived from the evidence table below; no external statistic entered clustering.", ""]
    for row in table.itertuples(index=False):
        counter={"A":"overlapping/boundary-sensitive interpretation remains.","B":"federal-intracity subtype and B/E boundary dependence limit generalisation.","C":"beyond-context profile remains unresolved.","D":"exact D/F boundary is sensitive.","E":"nested/context-sensitive and B/E boundary dependence remain.","F":"exact membership is boundary-sensitive; this is a transition label.","G":"broad background/macroprofile caveat and contextual dependence remain."}[row.technical_label]
        lines.extend([f"## {row.technical_label} — {row.display_name}","",f"- technical_label: {row.technical_label}",f"- status / confidence: {row.status} / {row.confidence}",f"- evidence supporting name: total median {row.behavioural_total_median:.0f}; wage rank {row.wage_rank}/7; population rank {row.population_rank}/7; employment rank {row.employment_rank}/7; stability modal class {row.stability_class}.",f"- counterevidence: {counter}",""])
    Path("docs/PROFILE_NAMING_AUDIT.md").write_text("\n".join(lines),encoding="utf-8")
    (out/"run_manifest.json").write_text(json.dumps({"status":"COMPLETED","config_sha256":hashlib.sha256(config.read_bytes()).hexdigest(),"profiles":list("ABCDEFG")},indent=2),encoding="utf-8")

if __name__ == "__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--config",default="configs/profile_naming.yaml"); main(parser.parse_args().config)
