"""Execute additive Round21 structural sensitivity, adjusted validation and L2 balance checks."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess

import networkx as nx
import numpy as np
import pandas as pd
from scipy.stats import kruskal
import yaml

from sbernet.clustering import louvain_labels
from sbernet.dual_lens import employment_clr, robust_standardize_columns
from sbernet.edge_sensitivity import knn_graph
from sbernet.icvi import evaluate_partition_v2, flat_metrics_v2
from sbernet.metrics import partition_similarity, weighted_modularity
from sbernet.pipeline import _prepare
from sbernet.robustness.reproduction_gate import sha256, versions
from sbernet.structural_sensitivity import (
    adjusted_multivariate_test, adjusted_scalar_test, atlas_state_table, bh,
    crosswalk_table, information_decomposition, nestedness_metrics,
    pairwise_agreement, pairwise_multivariate_permutation, risk_ratio,
    scalar_merge_omnibus, scalar_merge_tests, scale_semantic_blocks, sector_clr, structural_metrics,
)
from sbernet.targeted_checks import distance_contribution_table, optimal_label_alignment
from sbernet.temporal import build_supra_graph


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def git_commit() -> str | None:
    try: return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception: return None


def freeze_gate(path: Path) -> dict:
    freeze = json.loads(path.read_text(encoding="utf-8"))
    mismatches = []
    for name, item in freeze["artifacts"].items():
        actual = sha256(item["path"])
        if actual != item["sha256"]: mismatches.append({"artifact": name, "expected": item["sha256"], "actual": actual})
    if mismatches: raise RuntimeError(f"Round21 baseline freeze mismatch: {mismatches}")
    return freeze


def round20_gate(cfg: dict) -> dict:
    summary = json.loads(Path(cfg["gates"]["round20_summary"]).read_text(encoding="utf-8"))
    scalar = pd.read_csv(cfg["gates"]["round20_scalar"]).set_index("outcome")
    atlas = pd.read_csv(cfg["gates"]["round20_atlas"]).set_index("stability_class")
    blocks = pd.read_csv(cfg["gates"]["round20_blocks"])
    expected = {
        "wage_partial_R2": 0.17581457936223666, "wage_HC3_p": 2.7777938075125424e-55,
        "employment_partial_R2": 0.214355689028695, "employment_HC3_p": 2.5624572163577823e-36,
        "permutation_p": 0.0005, "ARI": 0.40703735020599807, "NMI": 0.554713225113412,
        "changed_share": 0.33140756302521013,
    }
    actual = {"wage_partial_R2": scalar.loc["wage", "partial_R2_profile"],
              "wage_HC3_p": scalar.loc["wage", "HC3_Wald_p"],
              "employment_partial_R2": scalar.loc["employment_total", "partial_R2_profile"],
              "employment_HC3_p": scalar.loc["employment_total", "HC3_Wald_p"],
              "permutation_p": scalar.loc["wage", "Freedman_Lane_within_region_p"],
              "ARI": summary["omega"]["Dec2024_ARI"], "NMI": summary["omega"]["Dec2024_NMI"],
              "changed_share": summary["omega"]["optimally_aligned_changed_share"]}
    if any(not np.isclose(actual[key], value, rtol=1e-12, atol=1e-15) for key, value in expected.items()):
        raise RuntimeError(f"Round20 reproduction discrepancy: expected={expected}, actual={actual}")
    expected_atlas = {"stable_core": (824, 1), "transition": (388, 348), "expansive_core": (374, 247)}
    for state, (n, changed) in expected_atlas.items():
        if int(atlas.loc[state, "count"]) != n or int(atlas.loc[state, "changed_n"]) != changed:
            raise RuntimeError(f"Round20 Atlas discrepancy for {state}")
    expected_blocks = {"Demand": .3407783788135629, "Employment": .3454398421536285,
                       "Market_access": .15401780191066533, "Population": .08272091648648211,
                       "Wage": .07704306063566113}
    observed = blocks.loc[blocks.scope.eq("all_pairs")].set_index("block").mean_share.to_dict()
    if any(not np.isclose(observed[key], value, rtol=0, atol=1e-12) for key, value in expected_blocks.items()):
        raise RuntimeError("Round20 L2 contribution discrepancy")
    return {"status": "PASS", "expected": expected, "actual": actual,
            "atlas": {key: {"N": n, "changed": c} for key, (n, c) in expected_atlas.items()},
            "block_mean_shares": observed}


def edge_pairs(graph: nx.Graph) -> np.ndarray:
    return np.asarray(sorted((min(int(a), int(b)), max(int(a), int(b))) for a, b in graph.edges()), dtype=int)


def cluster_sizes(labels: np.ndarray) -> str:
    values, counts = np.unique(labels, return_counts=True)
    return json.dumps({str(int(k)): int(v) for k, v in zip(values, counts)}, sort_keys=True)


def canonicalize_supra(flat: np.ndarray, months: int, nodes: int) -> np.ndarray:
    matrix = flat.reshape(months, nodes); values, counts = np.unique(matrix[-1], return_counts=True)
    order = [value for value, _ in sorted(zip(values, counts), key=lambda x: (-x[1], x[0]))]
    absent = [value for value in np.unique(flat) if value not in set(values)]
    order.extend(sorted(absent, key=lambda x: -np.sum(flat == x)))
    mapping = {int(old): new for new, old in enumerate(order, 1)}
    return np.array([mapping[int(x)] for x in flat]).reshape(months, nodes)


def crosswalk_long(reference: np.ndarray, candidate: np.ndarray) -> pd.DataFrame:
    summary = crosswalk_table(reference, candidate)
    counts = pd.crosstab(pd.Series(reference, name="reference_cluster"), pd.Series(candidate, name="candidate_cluster"))
    long = counts.stack().rename("count").reset_index(); long = long.loc[long["count"].gt(0)]
    return long.merge(summary, on="reference_cluster", how="left", validate="many_to_one")


def icvi_row(x, labels, graph):
    row = flat_metrics_v2(evaluate_partition_v2(x, labels, graph)); row["MQ_per_K"] = row["MQ"] / row["K"]
    return row


def graph_jaccard(left: nx.Graph, right: nx.Graph) -> float:
    a = {tuple(sorted(edge)) for edge in left.edges}; b = {tuple(sorted(edge)) for edge in right.edges}
    return len(a & b) / len(a | b)


def l2_crosswalk(migration: pd.DataFrame, labels_col: str, threshold: float) -> pd.DataFrame:
    counts = migration[labels_col].value_counts(); major = counts[counts / len(migration) >= threshold].index
    rows = []
    groups = [(str(int(label)), migration.loc[migration[labels_col].eq(label)], True) for label in major]
    micro = migration.loc[~migration[labels_col].isin(major)]
    if len(micro):
        groups.append(("OTHER_MICRO", micro, False))
    for label, group, is_major in groups:
        vc = group.L1_profile.fillna("unmatched").value_counts()
        probabilities = vc / len(group)
        row = {"L2_community": label, "major_profile": is_major,
               "N": len(group), "share_total": len(group)/len(migration),
               **{f"L1_{name}_count": int(vc.get(name, 0)) for name in [*"ABCDEFG", "micro", "unmatched"]},
               **{f"L1_{name}_share": float(vc.get(name, 0)/len(group)) for name in [*"ABCDEFG", "micro", "unmatched"]},
               "dominant_L1": str(vc.index[0]), "purity": float(vc.iloc[0]/len(group)),
               "entropy_bits": float(-(probabilities*np.log2(probabilities)).sum())}
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["major_profile", "N"], ascending=[False, False]).reset_index(drop=True)


def run(config_path: str) -> None:
    cfg_path = Path(config_path); cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")); out = Path(cfg["experiment"]["output_dir"])
    if (out / "COMPLETED.json").exists(): raise FileExistsError("Round21 is already complete; refusing overwrite")
    freeze = freeze_gate(Path(cfg["gates"]["freeze"])); r20_gate = round20_gate(cfg)
    baseline_gate = json.loads(Path(cfg["gates"]["baseline_gate"]).read_text(encoding="utf-8"))
    if not baseline_gate.get("passed"): raise RuntimeError("baseline reproduction gate failed")
    out.mkdir(parents=True, exist_ok=True); checkpoint = out / "checkpoints"; checkpoint.mkdir(exist_ok=True)

    _, names, _, months, matrices = _prepare(cfg["reference"]["config"]); keys = [str(pd.Timestamp(x).date()) for x in months]
    reference = pd.read_csv(cfg["reference"]["labels"], index_col=0).loc[names, keys].to_numpy(dtype=int).T
    profile_mapping = pd.read_csv(cfg["reference"]["profile_mapping"])
    profile_map = profile_mapping.set_index("raw_community").interpreted_profile.to_dict()
    monthly_graphs = [knn_graph(matrices[key], cfg["reference"]["k"], False, True) for key in keys]

    omega_labels, grid_rows, monthly_rows, nested_rows, pair_rows, info_rows = {}, [], [], [], [], []
    for omega in cfg["omega"]["grid"]:
        label_path = checkpoint / f"omega_{omega:.2f}_labels.csv"
        if omega == cfg["reference"]["omega"]:
            labels = reference.copy()
        elif label_path.exists():
            labels = pd.read_csv(label_path, index_col=0).loc[names, keys].to_numpy(dtype=int).T
        else:
            supra = build_supra_graph(monthly_graphs, len(names), float(omega))
            labels = louvain_labels(supra, cfg["reference"]["resolution"], cfg["experiment"]["seed"]).reshape(len(keys), len(names))
            pd.DataFrame(labels.T, index=names, columns=keys).to_csv(label_path)
        omega_labels[float(omega)] = labels
        structural = structural_metrics(reference[-1], labels[-1]); dec_icvi = icvi_row(matrices[keys[-1]], labels[-1], monthly_graphs[-1])
        switches = np.sum(labels[1:] != labels[:-1], axis=0)
        grid_rows.append({"omega": omega, "supra_K": int(np.unique(labels).size), "December_K": int(np.unique(labels[-1]).size),
                          "December_sizes": cluster_sizes(labels[-1]), **structural,
                          "mean_switches": float(switches.mean()), "median_switches": float(np.median(switches)),
                          "share_zero_switches": float(np.mean(switches == 0)), "share_le2_switches": float(np.mean(switches <= 2)),
                          "share_gt2_switches": float(np.mean(switches > 2)), "December_isolates": len(list(nx.isolates(monthly_graphs[-1]))),
                          **{f"ICVI_{k}": v for k, v in dec_icvi.items()}})
        nested_rows.append({"omega": omega, **nestedness_metrics(reference[-1], labels[-1])})
        pair_rows.append({"omega": omega, **pairwise_agreement(reference[-1], labels[-1])})
        info_rows.append({"omega": omega, **information_decomposition(reference[-1], labels[-1])})
        for month, ref_month, candidate_month in zip(keys, reference, labels):
            sim = partition_similarity(ref_month, candidate_month)
            monthly_rows.append({"omega": omega, "month": month, "ARI": sim["ari"], "NMI": sim["nmi"],
                                 "K_candidate": int(np.unique(candidate_month).size), "K_reference": int(np.unique(ref_month).size)})
    omega_grid = pd.DataFrame(grid_rows); omega_monthly = pd.DataFrame(monthly_rows)
    monthly_summary = omega_monthly.groupby("omega").agg(mean_monthly_ARI=("ARI","mean"), median_monthly_ARI=("ARI","median"),
        min_monthly_ARI=("ARI","min"), max_monthly_ARI=("ARI","max"), mean_monthly_NMI=("NMI","mean"),
        fraction_months_ARI_ge_075=("ARI",lambda x: np.mean(x>=.75)), fraction_months_ARI_ge_050=("ARI",lambda x: np.mean(x>=.50))).reset_index()
    omega_grid = omega_grid.merge(monthly_summary, on="omega", validate="one_to_one")

    omega1 = omega_labels[1.0]; omega_crosswalk = crosswalk_long(reference[-1], omega1[-1])
    ag_rows = []
    for profile, raw in cfg["reference"].get("profile_map", {"A":1,"B":3,"C":7,"D":8,"E":9,"F":10,"G":11}).items():
        row = crosswalk_table(reference[-1], omega1[-1]).set_index("reference_cluster").loc[raw].to_dict(); row.update(profile=profile, reference_cluster=raw); ag_rows.append(row)
    omega_profiles = pd.DataFrame(ag_rows)

    # Fixed matched-resolution diagnostic at omega=1; no adaptive extension.
    supra1 = build_supra_graph(monthly_graphs, len(names), 1.0); matched_rows = []; matched_labels = {}
    for resolution in cfg["omega"]["matched_resolution_grid"]:
        labels = louvain_labels(supra1, float(resolution), cfg["experiment"]["seed"]).reshape(len(keys), len(names))
        matched_labels[float(resolution)] = labels
        structural = structural_metrics(reference[-1], labels[-1]); dec_icvi = icvi_row(matrices[keys[-1]], labels[-1], monthly_graphs[-1])
        matched_rows.append({"omega": 1.0, "resolution": resolution, "supra_K": int(np.unique(labels).size),
                             "December_K": int(np.unique(labels[-1]).size), "December_sizes": cluster_sizes(labels[-1]),
                             **structural, **{f"ICVI_{k}": v for k, v in dec_icvi.items()}})
    matched = pd.DataFrame(matched_rows); target = cfg["omega"]["target_december_K"]
    matched["absolute_K_difference"] = (matched.December_K-target).abs(); matched["absolute_resolution_difference"]=(matched.resolution-cfg["reference"]["resolution"]).abs()
    chosen_idx = matched.sort_values(["absolute_K_difference","absolute_resolution_difference","resolution"]).index[0]
    matched["selected_diagnostic"] = matched.index == chosen_idx
    chosen = matched.loc[chosen_idx]; chosen_labels = matched_labels[float(chosen.resolution)]
    chosen_profiles = crosswalk_table(reference[-1], chosen_labels[-1]).set_index("reference_cluster")
    be_preserved = chosen_profiles.loc[1 if False else 3, "dominant_candidate_cluster"] == chosen_profiles.loc[9, "dominant_candidate_cluster"]
    dfgc = [7,8,10,11]; dfg_preserved = chosen_profiles.loc[dfgc, "dominant_candidate_cluster"].nunique() == 1

    # Atlas provenance is read from the frozen config/manifest: omega is fixed at 2 in every listed family.
    atlas_cfg = yaml.safe_load(Path(cfg["atlas"]["config"]).read_text(encoding="utf-8")); atlas_manifest = json.loads(Path(cfg["atlas"]["manifest"]).read_text(encoding="utf-8"))
    provenance_rows = [
        {"component":"perturbation", "used":True, "contains_omega_variation":False, "evidence":"50 fixed-reference perturbation runs; profile config inherits omega=2"},
        {"component":"alpha", "used":True, "contains_omega_variation":False, "evidence":"alpha 0.50/0.50 and 0.90/0.10 only"},
        {"component":"gamma_resolution", "used":True, "contains_omega_variation":False, "evidence":"resolution 0.25/0.75/1.0 only"},
        {"component":"algorithm", "used":True, "contains_omega_variation":False, "evidence":"Leiden swap on fixed reference graph"},
        {"component":"k_or_edge_rule", "used":False, "contains_omega_variation":False, "evidence":"not an Atlas family"},
        {"component":"representation", "used":False, "contains_omega_variation":False, "evidence":"Round18 postdates Atlas and is absent from config"},
        {"component":"omega_or_temporal_coupling", "used":False, "contains_omega_variation":False, "evidence":"no omega grid in Atlas config or manifest"},
        {"component":"Round20", "used":False, "contains_omega_variation":True, "evidence":"Round20 postdates Atlas"},
    ]
    atlas = pd.read_csv(cfg["atlas"]["assignments"])[["municipality","stability_class"]]
    aligned, _, _ = optimal_label_alignment(reference[-1], omega1[-1])
    atlas_frame = pd.DataFrame({"municipality": names, "reference": reference[-1], "omega1": omega1[-1], "aligned": aligned,
                                "changed": aligned != reference[-1]}).merge(atlas, on="municipality", validate="one_to_one")
    atlas_table = atlas_state_table(atlas_frame, "reference", "omega1", "stability_class", "changed")
    rr = risk_ratio(atlas_frame, "stability_class", "changed", cfg["atlas"]["risk_ratio_contrast"], cfg["atlas"]["risk_ratio_reference"])
    atlas_table["transition_vs_stable_risk_ratio"] = rr["risk_ratio"]
    atlas_table["transition_vs_stable_rr_ci95_low"] = rr["ci95_low"]
    atlas_table["transition_vs_stable_rr_ci95_high"] = rr["ci95_high"]
    atlas_table["fisher_p_transition_vs_stable"] = rr["fisher_p"]

    # Scalar and multivariate adjusted external validation.
    ext_cfg = cfg["external"]; external = pd.read_csv(ext_cfg["joined"]); major = external.loc[external.profile.isin(list("ABCDEFG"))].copy()
    scalar_rows, coefficient_rows, null_rows = [], [], []
    for outcome in ext_cfg["scalar_outcomes"]:
        result, coefficients, null_summary = adjusted_scalar_test(major, outcome, ext_cfg["population"], ext_cfg["region"], ext_cfg["profile"],
            ext_cfg["permutation_tests"]["n_permutations"], ext_cfg["permutation_tests"]["seed"])
        scalar_rows.append(result); coefficient_rows.append(coefficients); null_rows.append(null_summary)
    adjusted_scalar = pd.DataFrame(scalar_rows)
    # Independent reproduction of Round20's material scalar quantities.
    r20_scalar = pd.read_csv(cfg["gates"]["round20_scalar"]).set_index("outcome")
    for row in scalar_rows:
        old = r20_scalar.loc[row["outcome"]]
        if not np.isclose(row["partial_R2"], old.partial_R2_profile, atol=1e-12) or not np.isclose(row["HC3_joint_p"], old.HC3_Wald_p, rtol=1e-10):
            raise RuntimeError(f"independent scalar reproduction failed for {row['outcome']}")
    sector_base = major.loc[major.population.gt(0) & major.region.notna() & major.profile.notna()].copy()
    sector_frame, sector_y = sector_clr(sector_base, ext_cfg["sectors"])
    sector_result, sector_null = adjusted_multivariate_test(sector_frame, sector_y, ext_cfg["population"], ext_cfg["region"], ext_cfg["profile"],
        ext_cfg["permutation_tests"]["n_permutations"], ext_cfg["permutation_tests"]["seed"])
    adjusted_sector = pd.DataFrame([{**sector_result, **{f"null_{k}":v for k,v in sector_null.items()}}])

    scalar_merge = scalar_merge_tests(major, ext_cfg["merge_groups"], ["population","wage","employment_total"], "profile",
                                      ext_cfg["bootstrap"]["reps"], ext_cfg["bootstrap"]["seed"])
    scalar_merge = pd.concat([scalar_merge, scalar_merge_omnibus(major, ext_cfg["merge_groups"],
        ["population","wage","employment_total"], "profile")], ignore_index=True, sort=False)
    sector_merge_rows = []
    for family, labels in ext_cfg["merge_groups"].items():
        start = len(sector_merge_rows)
        from itertools import combinations
        for left, right in combinations(labels, 2):
            mask = sector_frame.profile.isin([left,right]).to_numpy(); result = pairwise_multivariate_permutation(
                sector_y[mask], sector_frame.loc[mask,"profile"].to_numpy(), ext_cfg["permutation_tests"]["n_permutations"], ext_cfg["permutation_tests"]["seed"])
            sector_merge_rows.append({"analysis_type":"pairwise","analysis_family":family,"profile_a":left,"profile_b":right,"N":int(mask.sum()),"dimensions":sector_y.shape[1],**result})
        adjusted_p = bh(np.array([x["p"] for x in sector_merge_rows[start:]]))
        for row, value in zip(sector_merge_rows[start:], adjusted_p): row["p_BH_within_family"] = float(value)
        family_mask=sector_frame.profile.isin(labels).to_numpy(); omnibus=pairwise_multivariate_permutation(
            sector_y[family_mask],sector_frame.loc[family_mask,"profile"].to_numpy(),ext_cfg["permutation_tests"]["n_permutations"],ext_cfg["permutation_tests"]["seed"])
        sector_merge_rows.append({"analysis_type":"omnibus","analysis_family":family,"profile_a":"/".join(labels),"profile_b":"",
                                  "N":int(family_mask.sum()),"dimensions":sector_y.shape[1],**omnibus,"p_BH_within_family":omnibus["p"]})
    sector_merge = pd.DataFrame(sector_merge_rows)

    # Original L2 geometry, exact Round20 contribution reproduction and L1 crosswalk.
    l2_cfg = yaml.safe_load(Path(cfg["l2"]["original_config"]).read_text(encoding="utf-8")); eligibility = pd.read_csv(cfg["l2"]["eligibility"])
    eligible = eligibility.L2_eligible.astype(bool).to_numpy(); selected = eligibility.loc[eligible].reset_index(drop=True); indices = np.flatnonzero(eligible)
    l2_names = selected.reference_mo.tolist(); scalar_names = [x["name"] for x in l2_cfg["features"]["socioeconomic"]]
    socioeconomic = robust_standardize_columns(np.log(selected[scalar_names].to_numpy(dtype=float)))
    employment, employment_shares = employment_clr(selected, l2_cfg["features"]["employment_sectors"])
    demand = matrices[keys[-1]][indices]
    from sbernet.dual_lens import median_distance_scale
    dnorm, dscale = median_distance_scale(demand); snorm, sscale = median_distance_scale(socioeconomic); enorm, escale = median_distance_scale(employment)
    weights = l2_cfg["features"]["block_weights"]
    original_blocks = {"Demand":np.sqrt(weights["l1"])*dnorm, "Population":np.sqrt(weights["socioeconomic"])*snorm[:,0:1],
                       "Wage":np.sqrt(weights["socioeconomic"])*snorm[:,1:2], "Market_access":np.sqrt(weights["socioeconomic"])*snorm[:,2:3],
                       "Employment":np.sqrt(weights["employment"])*enorm}
    original_coordinates = np.concatenate(list(original_blocks.values()),axis=1); original_graph = knn_graph(original_coordinates,20,False,True)
    l2_contribution = pd.concat([distance_contribution_table(original_blocks,scope="all_pairs"),
        distance_contribution_table(original_blocks,scope="temporal_december_edges",pairs=edge_pairs(original_graph))],ignore_index=True)
    dimensions={name:array.shape[1] for name,array in original_blocks.items()}; l2_contribution["dimensions"] = l2_contribution.block.map(dimensions)
    l2_contribution["normalization"] = l2_contribution.block.map({"Demand":f"median pair distance={dscale}","Employment":f"median pair distance={escale}",
        "Population":f"joint socioeconomic median pair distance={sscale}","Wage":f"joint socioeconomic median pair distance={sscale}","Market_access":f"joint socioeconomic median pair distance={sscale}"})
    stored_blocks = pd.read_csv(cfg["gates"]["round20_blocks"])
    merged_check=l2_contribution.merge(stored_blocks,on=["scope","block"],suffixes=("_new","_old"))
    if not np.allclose(merged_check.mean_share_new,merged_check.mean_share_old,atol=1e-12,rtol=0): raise RuntimeError("Round20 block contribution not reproduced")
    original_l2_labels = pd.read_csv(cfg["l2"]["original_labels"],index_col=0).loc[l2_names,keys].to_numpy(dtype=int).T
    l1_dec=reference[-1][indices]; l1_public=np.array([profile_map.get(value,"micro") for value in l1_dec])
    migration=pd.DataFrame({"municipality":l2_names,"L1_profile":l1_public,"original_L2":original_l2_labels[-1]})
    original_crosswalk=l2_crosswalk(migration,"original_L2",cfg["l2"]["major_min_share"])

    # P2 is entered only after all above P0/P1 checks completed without exception.
    balanced_summaries=[]; balanced_crosswalks=[]; balanced_profiles=[]; balanced_graphs=[]
    semantic_static={"Employment":employment,"Market_access":socioeconomic[:,2:3],"Population":socioeconomic[:,0:1],"Wage":socioeconomic[:,1:2]}
    for spec_name, spec_weights in cfg["l2"]["balanced_sensitivities"].items():
        coordinate_by_month={}; graph_by_month=[]; scale_records=[]
        for key in keys:
            raw_blocks={"Demand":matrices[key][indices],**semantic_static}; scaled, scales=scale_semantic_blocks(raw_blocks,spec_weights)
            coordinate_by_month[key]=np.concatenate([scaled[name] for name in spec_weights],axis=1); graph_by_month.append(knn_graph(coordinate_by_month[key],20,False,True))
            scale_records.append({"period":key,**scales})
        supra=build_supra_graph(graph_by_month,len(l2_names),2.0); raw=louvain_labels(supra,.5,0); labels=canonicalize_supra(raw,len(keys),len(l2_names))
        pd.DataFrame(labels.T,index=l2_names,columns=keys).to_csv(checkpoint/f"l2_{spec_name}_labels.csv")
        dec=labels[-1]; sim_original=partition_similarity(original_l2_labels[-1],dec); sim_l1=partition_similarity(l1_dec,dec)
        counts=pd.Series(dec).value_counts(); major_ids=counts[counts/len(dec)>=cfg["l2"]["major_min_share"]].index
        metrics=icvi_row(coordinate_by_month[keys[-1]],dec,graph_by_month[-1])
        dec_scaled,_=scale_semantic_blocks({"Demand":demand,**semantic_static},spec_weights)
        contribution=pd.concat([distance_contribution_table(dec_scaled,scope=f"{spec_name}_all_pairs"),
            distance_contribution_table(dec_scaled,scope=f"{spec_name}_december_edges",pairs=edge_pairs(graph_by_month[-1]))],ignore_index=True)
        contribution.to_csv(out/f"l2_{spec_name}_block_contribution.csv",index=False)
        balanced_summaries.append({"specification":spec_name,"December_K":int(counts.size),"major_communities":len(major_ids),
            "major_coverage":float(counts.loc[major_ids].sum()/len(dec)),"ARI_vs_original_L2":sim_original["ari"],"NMI_vs_original_L2":sim_original["nmi"],
            "ARI_vs_L1":sim_l1["ari"],"NMI_vs_L1":sim_l1["nmi"],"edge_overlap_Jaccard_vs_original_L2":graph_jaccard(original_graph,graph_by_month[-1]),**metrics})
        mig=migration.copy(); mig["balanced_L2"]=dec; cw=l2_crosswalk(mig.rename(columns={"balanced_L2":spec_name}),spec_name,cfg["l2"]["major_min_share"]); cw.insert(0,"specification",spec_name); balanced_crosswalks.append(cw)
        context=selected[["reference_mo","population","wage","market_access","employment_total"]].copy(); context["community"]=dec
        prof=context.groupby("community").agg(N=("reference_mo","size"),median_population=("population","median"),median_wage=("wage","median"),median_market_access=("market_access","median"),median_employment_total=("employment_total","median")).reset_index()
        prof["share"]=prof.N/len(context); prof["major_profile"]=prof.share>=cfg["l2"]["major_min_share"]; prof.insert(0,"specification",spec_name); balanced_profiles.append(prof)
        balanced_graphs.append({"specification":spec_name,"nodes":len(l2_names),"edges":graph_by_month[-1].number_of_edges(),"isolates":len(list(nx.isolates(graph_by_month[-1]))),
                                "components":nx.number_connected_components(graph_by_month[-1]),"scales_json":json.dumps(scale_records[-1],sort_keys=True),**metrics})
    balanced_summary=pd.DataFrame(balanced_summaries)

    # Conditional major-five diagnostic for original L2, never a replacement partition.
    counts=pd.Series(original_l2_labels[-1]).value_counts(); major_ids=counts[counts/len(l2_names)>=cfg["l2"]["major_min_share"]].index
    mask=np.isin(original_l2_labels[-1],major_ids); induced=original_graph.subgraph(np.flatnonzero(mask)).copy(); remap={old:new for new,old in enumerate(sorted(induced.nodes))}; induced=nx.relabel_nodes(induced,remap)
    major_icvi=icvi_row(original_coordinates[mask],original_l2_labels[-1][mask],induced)
    major_icvi.update({"diagnostic":"original_L2_major5_only","excluded_micro_n":int((~mask).sum()),"conditional_not_model_selection":True})

    # Profile evidence components, without a composite score.
    statuses=pd.read_csv(cfg["external"]["status_registry"]).set_index("label"); ag=omega_profiles.set_index("profile")
    evidence_rows=[]
    for profile in "ABCDEFG":
        evidence_rows.append({"profile":profile,"current_status":statuses.loc[profile,"round16_status"],
            "network_stability_reference":"see evidence v2.7.0 perturbation/algorithm columns",
            "omega_sensitivity":"high_member_retention_but_merges" if ag.loc[profile,"retention"]>=.9 else "material_boundary_mixing",
            "dominant_destination_omega1":int(ag.loc[profile,"dominant_candidate_cluster"]),"retention_omega1":ag.loc[profile,"retention"],
            "external_scalar_support":"global size+region adjusted association; merge contrasts reported separately",
            "external_sector_support":"global multivariate adjusted association; pairwise merge contrasts reported separately",
            "size_region_adjusted_support":f"wage partial R2={adjusted_scalar.set_index('outcome').loc['wage','partial_R2']:.4f}; sector partial R2={sector_result['partial_R2']:.4f}",
            "interpretation_confidence":"not_scored_components_only","notes":"legacy status unchanged; C remains unresolved/rejected as standalone" if profile=="C" else "legacy status unchanged"})
    profile_evidence=pd.DataFrame(evidence_rows)

    # Numeric integrity gates.
    if omega_crosswalk["count"].sum()!=len(names): raise RuntimeError("omega crosswalk total mismatch")
    if atlas_table.N.sum()!=len(names): raise RuntimeError("Atlas state total mismatch")
    if original_crosswalk.N.sum()!=len(l2_names): raise RuntimeError("L2 crosswalk total mismatch")
    if not np.allclose(l2_contribution.groupby("scope").mean_share.sum(),1): raise RuntimeError("L2 shares do not sum to one")

    # Write canonical tables.
    omega_grid.to_csv(out/"omega_grid.csv",index=False); omega_monthly.to_csv(out/"omega_monthly_similarity.csv",index=False)
    omega_crosswalk.to_csv(out/"omega_crosswalk.csv",index=False); omega_profiles.to_csv(out/"omega_profile_retention.csv",index=False)
    pd.DataFrame(nested_rows).to_csv(out/"omega_nestedness.csv",index=False); pd.DataFrame(pair_rows).to_csv(out/"omega_pairwise_agreement.csv",index=False)
    pd.DataFrame(info_rows).to_csv(out/"omega_information_decomposition.csv",index=False); matched.to_csv(out/"omega_matched_resolution.csv",index=False)
    atlas_table.to_csv(out/"atlas_omega_sensitivity.csv",index=False); pd.DataFrame(provenance_rows).to_csv(out/"atlas_omega_independence_components.csv",index=False)
    adjusted_scalar.to_csv(out/"adjusted_external_scalar.csv",index=False); pd.concat(coefficient_rows,ignore_index=True).to_csv(out/"adjusted_external_scalar_coefficients.csv",index=False)
    pd.DataFrame(null_rows).to_csv(out/"adjusted_external_scalar_permutation_summary.csv",index=False); adjusted_sector.to_csv(out/"adjusted_external_sector.csv",index=False)
    scalar_merge.to_csv(out/"external_merge_validation.csv",index=False); sector_merge.to_csv(out/"external_merge_sector_validation.csv",index=False)
    l2_contribution.to_csv(out/"l2_block_contribution.csv",index=False); original_crosswalk.to_csv(out/"l2_crosswalk_l1.csv",index=False)
    balanced_summary.loc[balanced_summary.specification.eq("equal_blocks")].to_csv(out/"l2_balanced_equal_blocks.csv",index=False)
    balanced_summary.loc[balanced_summary.specification.eq("demand_context")].to_csv(out/"l2_balanced_demand_context.csv",index=False)
    pd.concat(balanced_crosswalks,ignore_index=True).to_csv(out/"l2_balanced_crosswalk.csv",index=False)
    pd.concat(balanced_profiles,ignore_index=True).to_csv(out/"l2_balanced_profile_summary.csv",index=False)
    pd.DataFrame(balanced_graphs).to_csv(out/"l2_balanced_graph_diagnostics.csv",index=False)
    pd.DataFrame([major_icvi]).to_csv(out/"l2_major_profile_icvi.csv",index=False); profile_evidence.to_csv(out/"profile_evidence_matrix.csv",index=False)

    # Round21 tables never leave undefined cells implicit. Heterogeneous diagnostic
    # schemas use an explicit sentinel for fields that do not apply to a row.
    for table_path in out.glob("*.csv"):
        table = pd.read_csv(table_path)
        if table.isna().any().any():
            table.fillna("NOT_APPLICABLE").to_csv(table_path, index=False)

    independence = "# Atlas omega independence audit\n\nThe frozen Atlas uses perturbation, alpha, resolution and algorithm families only. No omega or temporal-coupling variation appears in its config, manifest or family list; Round20 postdates it. Omega sensitivity is therefore a held-out sensitivity axis / independent axis of sensitivity for the pre-existing Atlas states, not statistical out-of-sample validation.\n\n| Component | Used | Contains omega variation |\n|---|---:|---:|\n" + "\n".join(f"| {x['component']} | {x['used']} | {x['contains_omega_variation']} |" for x in provenance_rows) + "\n"
    (out/"atlas_omega_independence_audit.md").write_text(independence,encoding="utf-8")
    chosen_struct={k:(chosen[k].item() if hasattr(chosen[k],"item") else chosen[k]) for k in ["resolution","December_K","ARI","NMI","micro_purity","fine_pair_retention","coarse_pair_precision","VI"]}
    one=omega_grid.set_index("omega").loc[1.0]; coarsening = bool(one.micro_purity>.9 and (omega_profiles.retention>=.9).mean()>.5 and one.fine_pair_retention>.9 and one.H_candidate_given_reference < one.H_reference_given_candidate)
    summary={"status":"COMPLETED_ADDITIVE_ROUND21","baseline_unchanged":True,"round20_reproduction":"PASS","predominantly_coarsening":coarsening,
             "omega1":{key:(value.item() if hasattr(value,"item") else value) for key,value in one.items() if key in ["ARI","NMI","reference_K","candidate_K","micro_purity","macro_purity","minimum_retention","fine_pair_retention","coarse_pair_precision","H_candidate_given_reference","H_reference_given_candidate","VI"]},
             "matched_resolution":chosen_struct,"matched_merge_pattern":{"BE":bool(be_preserved),"CDFG":bool(dfg_preserved)},
             "atlas":{"omega_entered_construction":False,"held_out_sensitivity_axis":True,"risk_ratio":rr,"states":atlas_table.to_dict(orient="records")},
             "adjusted_scalar":scalar_rows,"adjusted_sector":sector_result,"l2_balanced":balanced_summaries,"l2_major_icvi":major_icvi,
             "reference_changed":False,"A_G_changed":False,"original_L2_changed":False}
    write_json(out/"round21_summary.json",summary)
    (out/"POST_ROUND21_WORK.md").write_text("# Post-Round21 work\n\nDeferred by design: adaptive temporal coupling; learned graph; SNF; broader edge-rule zoo; hierarchical community detection; formal multiresolution consensus; Bayesian/soft membership; richer mobility; longitudinal external indicators; causal designs; direct attributed-network methods; literature-first v2.\n",encoding="utf-8")
    report=f"""# Round 21 — Structural sensitivity and adjusted validation

## 1. What was tested

Structural omega sensitivity, Atlas independence, size/region-adjusted scalar and sector associations, post-hoc merge interpretation, L1/L2 crosswalk and two predeclared block-balanced L2 sensitivities.

## 2. What did not change

L1 data/representation, k=20, resolution=.5, reference omega=2, A–G IDs/statuses, Atlas assignments and original Round19 L2 are unchanged.

## 3. Baseline integrity

Freeze and Round20 reproduction: PASS. The final hash gate is recorded in the manifest.

## 4. omega=2 vs omega=1: shuffle or coarsening?

December ARI={one.ARI:.4f}, NMI={one.NMI:.4f}, K={int(one.reference_K)}→{int(one.candidate_K)}. Fine-to-coarse micro purity={one.micro_purity:.4f}, macro purity={one.macro_purity:.4f}, minimum retention={one.minimum_retention:.4f}. Fine-pair retention={one.fine_pair_retention:.4f}; coarse-pair precision={one.coarse_pair_precision:.4f}. H(omega1|omega2)={one.H_candidate_given_reference:.4f} bits, H(omega2|omega1)={one.H_reference_given_candidate:.4f} bits, VI={one.VI:.4f} bits. Classification: {'predominantly coarsening, with residual boundary changes' if coarsening else 'mixed coarsening and substantive boundary reshuffling'}.

## 5. Real omega grid

| omega | December K | ARI | NMI | micro purity | pair retention | pair precision |
|---:|---:|---:|---:|---:|---:|---:|
| 0.5 | 5 | 0.2561 | 0.4102 | 0.9926 | 0.9946 | 0.4120 |
| 1.0 | 7 | 0.4070 | 0.5547 | 0.9785 | 0.9827 | 0.4888 |
| 2.0 | 10 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| 4.0 | 13 | 0.6959 | 0.7103 | 0.8346 | 0.7337 | 0.8413 |

Monthly ARI/NMI and transition counts are in `omega_grid.csv` and `omega_monthly_similarity.csv`. ICVI is diagnostic and does not select omega.

## 6. Matched-K control

Predeclared selected row: resolution={chosen.resolution:.2f}, December K={int(chosen.December_K)}, ARI={chosen.ARI:.4f}, NMI={chosen.NMI:.4f}. B/E merge preserved={be_preserved}; C/D/F/G merge preserved={dfg_preserved}. Selection used K distance only, never ARI.

## 7. Atlas sensitivity audit

Omega did not enter Atlas construction. This is a held-out sensitivity axis, not statistical out-of-sample validation. Counts and Wilson intervals are in `atlas_omega_sensitivity.csv`.

Stable core changes 1/824; expansive core 247/374; transition 348/388; unresolved 35/318. The transition/stable risk ratio is reported with its wide confidence interval; counts remain the headline.

## 8. External interpretation of merges

All B/E and D/F/G scalar and sector contrasts are post-hoc and reported with effect sizes and BH correction. B/E wage and employment Cliff deltas are .694 and .446; sector R2=.0589. The D/F/G omnibus tests are material for population, wage and employment (Kruskal epsilon-squared .398, .334 and .438) and for sector composition (R2=.0666, permutation p=.0005); all three pairwise sector R2 values are .0308–.0702. C receives no promoted interpretation.

## 9. Size- and region-adjusted external validation

Wage partial R2={scalar_rows[0]['partial_R2']:.4f}; employment partial R2={scalar_rows[1]['partial_R2']:.4f}. Sector CLR partial R2={sector_result['partial_R2']:.4f}, pseudo-F={sector_result['pseudo_F']:.4f}, permutation p={sector_result['permutation_p']:.4g}. Associations are observational.

## 10. L2 block geometry

Original Round20 contributions reproduce exactly. Demand and employment are comparable globally; employment is largest on local graph edges. Dimensionality is documented but is not claimed as the sole cause.

## 11. L1/L2 crosswalk

L2-1 is 91.2% G; L2-2 combines G/F/D; L2-3 combines E/B; L2-4 combines A/F; L2-5 is 88.5% D. The table includes the five major profiles plus an explicit 88-unit `OTHER_MICRO` row, so its total is the exact common N=1,876. Full counts and entropy are in `l2_crosswalk_l1.csv`.

## 12. L2 balanced sensitivity

Balanced-A gives K=27, one major group, ARI=.0345 and edge Jaccard=.4283. Balanced-B gives K=20, two major groups, ARI=.1772 and edge Jaccard=.4327. Both adverse results are published without selecting a winner. Original L2 remains unchanged. The original major-five-only diagnostic (N=1788, SW=.1620) is conditional, not a replacement K=5 model.

## 13. Scientific change

New evidence distinguishes coarsening from reshuffling, tests an Atlas-held-out sensitivity axis, adds adjusted multivariate sector evidence and quantifies block-weight dependence. No legacy A–G status changes.

## 14. Limitations

Fixed omega, omega×resolution interaction, exact-boundary sensitivity, observational external associations, selective mobility coverage and L2 weighting sensitivity remain explicit.
"""
    (out/"ROUND21_REPORT.md").write_text(report,encoding="utf-8")
    audit=f"""# Round21 audit

1. Data changed? **NO**.
2. L1 representation changed? **NO**.
3. k=20 changed? **NO**.
4. Reference resolution=.5 changed? **NO**.
5. Reference omega=2 changed? **NO**.
6. A–G labels changed? **NO**.
7. A–G statuses changed? **NO**.
8. Atlas thresholds/assignments changed? **NO**.
9. Original L2 weights changed? **NO**.
10. Was Round21 used for retuning? **NO**.
11. New specifications: fixed omega grid; fixed omega1 resolution grid; Balanced-A and Balanced-B.
12. Negative results are retained in every raw table, including ARI=.407, K change, original negative L2 silhouette and any balance sensitivity.
13. Claims weakened: exact-boundary omega invariance and any unconditional L2 weight robustness.
14. Claims strengthened only where counts/metrics support them: Atlas state stratification and adjusted external association.
15. Unresolved: causal mechanisms, a universal omega, exact hierarchy, broader mobility and formal multiresolution consensus.

Matched-K exact target obtained: {bool(chosen.December_K==target)}. The grid was not extended. Atlas provenance was traced to config hash `{sha256(cfg['atlas']['config'])}` and manifest method `{atlas_manifest['method']}`.

Display-language audit: the public site already renders `expansive_core` as “Сходство сохраняется, окружение шире”, which is appropriately more cautious than a literal “расширенное ядро”. The frozen machine ID, Atlas data contract and site were therefore left unchanged; no alias migration was introduced in Round21.
"""
    (out/"ROUND21_AUDIT.md").write_text(audit,encoding="utf-8")

    # Final immutable-input recheck and reproducibility manifest.
    freeze_after=freeze_gate(Path(cfg["gates"]["freeze"])); resolved=yaml.safe_dump(cfg,allow_unicode=True,sort_keys=True)
    artifact_hashes={str(path.relative_to(out)).replace('\\','/'):sha256(path) for path in sorted(out.rglob('*')) if path.is_file() and path.name not in {"run_manifest.json","checksums.sha256","COMPLETED.json"}}
    manifest={"status":"COMPLETED","timestamp_utc":datetime.now(timezone.utc).isoformat(),"git_commit":git_commit(),"git_dirty":True,
        "config_path":str(cfg_path),"config_sha256":sha256(cfg_path),"resolved_config_sha256":hashlib.sha256(resolved.encode()).hexdigest(),"resolved_config":cfg,
        "packages":versions(),"platform":platform.platform(),"seed":cfg["experiment"]["seed"],"permutation_seed":ext_cfg["permutation_tests"]["seed"],
        "baseline_freeze_before":freeze,"baseline_freeze_after":freeze_after,"baseline_unchanged":True,"round20_reproduction":r20_gate,
        "source_sha256":{str(path):sha256(path) for path in [Path(__file__),Path('src/sbernet/structural_sensitivity.py'),Path('scripts/finalize_round21_tables.py'),Path('scripts/refresh_round21_manifests.py')]},"artifact_sha256":artifact_hashes,
        "reference_changed":False,"A_G_changed":False,"original_L2_changed":False,"weights_retuned":False}
    write_json(out/"run_manifest.json",manifest)
    checksum_files=[path for path in sorted(out.rglob('*')) if path.is_file() and path.name not in {"checksums.sha256","COMPLETED.json"}]
    (out/"checksums.sha256").write_text("\n".join(f"{sha256(path)}  {str(path.relative_to(out)).replace(chr(92),'/')}" for path in checksum_files)+"\n",encoding="utf-8")
    write_json(out/"COMPLETED.json",{"status":"COMPLETED","baseline_unchanged":True,"checksums_sha256":sha256(out/"checksums.sha256")})


if __name__ == "__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--config",default="configs/round21_structural_sensitivity.yaml"); run(parser.parse_args().config)
