"""Run the preregistered small controlled temporal-network benchmark."""
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys
from pathlib import Path
import numpy as np
import pandas as pd
import yaml
from sbernet.synthetic_temporal import generate_panel, infer_labels, score


def aggregate(frame: pd.DataFrame, reps: int, seed: int) -> pd.DataFrame:
    rng=np.random.default_rng(seed); rows=[]
    metric_columns=[c for c in frame.columns if c not in {"scenario","seed","omega"}]
    for (scenario, omega), group in frame.groupby(["scenario","omega"], sort=True):
        for metric in metric_columns:
            value=group[metric].dropna().to_numpy(float)
            if not len(value): continue
            sampled=value[rng.integers(0,len(value),size=(reps,len(value)))].mean(axis=1)
            rows.append({"scenario":scenario,"omega":omega,"metric":metric,"mean":value.mean(),"std":value.std(ddof=1),"ci_low":np.quantile(sampled,.025),"ci_high":np.quantile(sampled,.975),"n":len(value)})
    return pd.DataFrame(rows)


def main(path: str) -> None:
    config_path=Path(path); cfg=yaml.safe_load(config_path.read_text(encoding="utf-8")); out=Path(cfg["experiment"]["output_dir"])
    if out.exists(): raise FileExistsError(f"Refusing to overwrite {out}")
    out.mkdir(parents=True)
    generator, model, experiment=cfg["generator"],cfg["model"],cfg["experiment"]
    rows=[]
    for scenario in generator["scenarios"]:
        for offset in range(experiment["seeds"]):
            seed=experiment["seed_start"]+offset
            panel=generate_panel(scenario, seed, **{k:v for k,v in generator.items() if k != "scenarios"})
            for omega in model["omega_grid"]:
                result=score(panel, infer_labels(panel, omega, model["k"], model["resolution"], model["louvain_seed"]))
                rows.append({"scenario":scenario,"seed":seed,"omega":omega,**result})
    seeds=pd.DataFrame(rows); seeds.to_csv(out/"seed_metrics.csv",index=False)
    pd.DataFrame([{**generator, "scenario":x} for x in generator["scenarios"]]).drop(columns="scenarios").to_csv(out/"scenario_parameters.csv",index=False)
    summary=aggregate(seeds,cfg["statistics"]["bootstrap_reps"],cfg["statistics"]["bootstrap_seed"]); summary.to_csv(out/"omega_aggregate.csv",index=False)
    seeds[["scenario","seed","omega","switch_precision","switch_recall","switch_f1","false_switches","missed_switches","false_switch_rate","false_persistence","false_instability"]].to_csv(out/"switch_detection.csv",index=False)
    seeds[["scenario","seed","omega","absolute_change_point_delay","signed_change_point_delay"]].to_csv(out/"change_point_delay.csv",index=False)
    wide=summary.pivot_table(index=["scenario","omega"],columns="metric",values="mean").reset_index()
    # Equal-weight transparent utility is a reporting aid, never a selected real-data parameter.
    for col, higher in [("ari",True),("switch_f1",True),("false_switch_rate",False),("absolute_change_point_delay",False)]:
        denom=wide.groupby("scenario")[col].transform(lambda x: max(x.max()-x.min(),1e-12))
        scaled=(wide[col]-wide.groupby("scenario")[col].transform("min"))/denom
        wide[f"utility_{col}"]=scaled if higher else 1-scaled
    wide["balanced_utility"]=wide[[c for c in wide if c.startswith("utility_")]].mean(axis=1)
    maxima=wide.groupby("scenario")["balanced_utility"].transform("max")
    wide["balanced_tradeoff_best"]=wide.balanced_utility.eq(maxima)
    wide.to_csv(out/"pareto_summary.csv",index=False)
    all_omega=wide.groupby("omega",as_index=False)[["ari","switch_f1","false_switch_rate","absolute_change_point_delay","balanced_utility"]].mean(numeric_only=True)
    role_note = ""
    if "mixed" in generator["scenarios"]:
        role_note = ("\nThe mixed scenario has disjoint node roles fixed before simulation: "
                     f"{generator['mixed_switch_fraction']:.0%} true switches, "
                     f"{generator['mixed_boundary_fraction']:.0%} boundary-only nodes, "
                     f"{generator['mixed_shock_fraction']:.0%} temporary-shock-only nodes, "
                     f"and {1-generator['mixed_switch_fraction']-generator['mixed_boundary_fraction']-generator['mixed_shock_fraction']:.0%} stable nodes. "
                     "Only true-switch nodes change latent truth.\n")
    report=f"""# Synthetic temporal benchmark\n\nA controlled benchmark used the reference-style composition (five centred composition coordinates) plus level block, mutual-kNN graphs, Louvain resolution .5, and a preregistered omega grid 0/.25/.5/1/2/4. It is not fitted to Russian data. Six scenarios and {experiment['seeds']} independently seeded panels per scenario are recorded in `seed_metrics.csv`.{role_note}\nAcross scenarios, maximum mean partition ARI occurs at omega={all_omega.loc[all_omega.ari.idxmax(),'omega']:.2g}; maximum switch F1 at omega={all_omega.loc[all_omega.switch_f1.idxmax(),'omega']:.2g}; and minimum false-switch rate at omega={all_omega.loc[all_omega.false_switch_rate.idxmin(),'omega']:.2g}. The transparent equal-weight balanced reporting utility is highest at omega={all_omega.loc[all_omega.balanced_utility.idxmax(),'omega']:.2g}. Scenario-specific results and CIs are in `omega_aggregate.csv` and `pareto_summary.csv`; a universal omega is not inferred.\n\nReference omega=2 is reported as one fixed trade-off specification. A calibrated specification is only reported where a scenario's preregistered utility is higher; it does not replace historical reference outputs.\n"""
    (out/"SYNTHETIC_TEMPORAL_REPORT.md").write_text(report,encoding="utf-8")
    manifest={"config_sha256":hashlib.sha256(config_path.read_bytes()).hexdigest(),"status":"COMPLETED","seeds":experiment["seeds"],"scenarios":generator["scenarios"],"omega_grid":model["omega_grid"],"git_commit":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),"python":sys.version}
    (out/"run_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")

if __name__ == "__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--config",default="configs/synthetic_temporal_benchmark.yaml"); main(parser.parse_args().config)
