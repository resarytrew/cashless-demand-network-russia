"""Run the post-lineage national BDMO interpretation layer.

The frozen A--G labels are read only after the OKTMO gate.  No result from this
script can enter graph construction, clustering, or profile mapping.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd
import yaml
from scipy.spatial.distance import pdist, squareform
from scipy.stats import chi2, kruskal, norm, rankdata
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, log_loss
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from sbernet.external_bdmo import municipality_oktmo11_to_8
from sbernet.sberindex_directory import read_directory, select_snapshot


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_member(path: Path) -> str:
    with ZipFile(path) as zf:
        members = [x for x in zf.namelist() if x.endswith('.csv') and '/' not in x]
    if len(members) != 1:
        raise ValueError(f"Expected one root CSV in {path}; got {members}")
    return members[0]


def read_bdmo(path: Path, years: set[int], spec: dict, sectors: bool = False) -> tuple[pd.DataFrame, dict]:
    """Filter BDMO deterministically, retaining current 8-character OKTMO text."""
    kept: list[pd.DataFrame] = []
    counts = {"source_rows": 0, "year_rows": 0, "period_rows": 0, "upper_level_rows": 0}
    member = csv_member(path)
    with ZipFile(path) as zf, zf.open(member) as raw:
        for chunk in pd.read_csv(raw, sep=";", chunksize=250_000, low_memory=False,
                                 dtype={"oktmo": "string", "year": "Int64", "okved2": "string"}):
            counts["source_rows"] += len(chunk)
            chunk = chunk.loc[chunk["year"].isin(years)].copy()
            counts["year_rows"] += len(chunk)
            if spec.get("period_value"):
                chunk = chunk.loc[chunk["indicator_period"].eq(spec["period_value"])]
            counts["period_rows"] += len(chunk)
            chunk = chunk.loc[chunk["mun_level"].fillna("").str.contains("верхнего уровня", regex=False)]
            counts["upper_level_rows"] += len(chunk)
            if sectors:
                code = chunk["okved2"].fillna("").str.extract(r"^Раздел\s+([A-U])", expand=False)
                chunk["okved_section"] = code
                chunk = chunk.loc[chunk["okved_section"].notna()]
            elif spec.get("dimension_column"):
                column = spec["dimension_column"]
                if "dimension_value" in spec:
                    chunk = chunk.loc[chunk[column].eq(spec["dimension_value"])]
                else:
                    chunk = chunk.loc[chunk[column].fillna("").str.startswith(spec["dimension_prefix"])]
            kept.append(chunk)
    frame = pd.concat(kept, ignore_index=True) if kept else pd.DataFrame()
    counts["csv_member"] = member
    counts["retained_rows"] = len(frame)
    return frame, counts


def unique_values(frame: pd.DataFrame, variable: str, group: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, conflicts = [], []
    for keys, part in frame.groupby(group, dropna=False, sort=True):
        values = pd.to_numeric(part["indicator_value"], errors="coerce").dropna().unique()
        if len(values) == 1 and pd.notna(part["oktmo"].iloc[0]):
            record = dict(zip(group, keys if isinstance(keys, tuple) else (keys,), strict=True))
            record[variable] = float(values[0]); rows.append(record)
        else:
            record = dict(zip(group, keys if isinstance(keys, tuple) else (keys,), strict=True))
            record.update({"variable": variable, "n_rows": len(part), "n_values": len(values)})
            conflicts.append(record)
    return pd.DataFrame(rows), pd.DataFrame(conflicts)


def bh(pvals: list[float]) -> list[float]:
    values = np.asarray(pvals, dtype=float); order = np.argsort(values); out = np.empty(len(values))
    adjusted = values[order] * len(values) / np.arange(1, len(values) + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    out[order] = np.minimum(adjusted, 1.0)
    return out.tolist()


def cliff(a: np.ndarray, b: np.ndarray) -> float:
    return float((np.greater.outer(a, b).sum() - np.less.outer(a, b).sum()) / (len(a) * len(b)))


def dunn(frame: pd.DataFrame, value: str) -> pd.DataFrame:
    data = frame[["profile", value]].dropna(); groups = sorted(data.profile.unique())
    if len(groups) < 2: return pd.DataFrame()
    ranks = rankdata(data[value]); data = data.assign(_rank=ranks)
    n = len(data); tie = 1 - sum((x**3 - x) for x in data[value].value_counts()) / (n**3 - n)
    rows, pvals = [], []
    for i, first in enumerate(groups):
        a = data.loc[data.profile.eq(first)]
        for second in groups[i + 1:]:
            b = data.loc[data.profile.eq(second)]
            se = np.sqrt((n * (n + 1) / 12) * tie * (1 / len(a) + 1 / len(b)))
            z = (a._rank.mean() - b._rank.mean()) / se
            p = float(2 * norm.sf(abs(z)))
            rows.append({"variable": value, "profile_a": first, "profile_b": second, "n_a": len(a), "n_b": len(b), "z": z, "p_raw": p, "cliff_delta_a_minus_b": cliff(a[value].to_numpy(), b[value].to_numpy())}); pvals.append(p)
    out = pd.DataFrame(rows); out["p_fdr_bh"] = bh(pvals); return out


def summaries(frame: pd.DataFrame, variables: list[str], reps: int, seed: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed); rows, global_rows, pairwise = [], [], []
    for variable in variables:
        data = frame[["profile", variable]].dropna(); grouped = [x[variable].to_numpy() for _, x in data.groupby("profile", sort=True)]
        if len(grouped) >= 2 and min(map(len, grouped)) > 0:
            stat, p = kruskal(*grouped); n, k = len(data), len(grouped)
            eps2 = max(0.0, (stat - k + 1) / (n - k)) if n > k else np.nan
            global_rows.append({"variable": variable, "n": n, "groups": k, "kruskal_h": stat, "p_value": p, "epsilon_squared": eps2})
            pairwise.append(dunn(data, variable))
        for profile, part in data.groupby("profile", sort=True):
            values = part[variable].to_numpy(); sampled = values[rng.integers(0, len(values), size=(reps, len(values)))]
            rows.append({"variable": variable, "profile": profile, "n": len(values), "mean": values.mean(), "median": np.median(values), "q25": np.quantile(values, .25), "q75": np.quantile(values, .75), "mean_ci_low": np.quantile(sampled.mean(1), .025), "mean_ci_high": np.quantile(sampled.mean(1), .975), "median_ci_low": np.quantile(np.median(sampled, axis=1), .025), "median_ci_high": np.quantile(np.median(sampled, axis=1), .975)})
    return pd.DataFrame(rows), pd.DataFrame(global_rows), pd.concat(pairwise, ignore_index=True) if pairwise else pd.DataFrame()


def permanova(clr: pd.DataFrame, reps: int, seed: int) -> dict:
    x = clr.drop(columns="profile").to_numpy(); labels = clr.profile.to_numpy(); groups = np.unique(labels)
    d2 = squareform(pdist(x, metric="sqeuclidean")); n, k = len(x), len(groups)
    total = d2.sum() / n
    def pseudo_f(y: np.ndarray) -> float:
        within = sum(d2[np.ix_(y == g, y == g)].sum() / (y == g).sum() for g in np.unique(y))
        return ((total - within) / (k - 1)) / (within / (n - k))
    observed = pseudo_f(labels); rng = np.random.default_rng(seed)
    null = np.array([pseudo_f(rng.permutation(labels)) for _ in range(reps)])
    return {"method": "PERMANOVA_on_CLR_Euclidean_distance", "n": n, "groups": k, "pseudo_f": observed, "permutations": reps, "p_value": float((1 + (null >= observed).sum()) / (reps + 1)), "seed": seed}


def prediction(frame: pd.DataFrame, features: list[str], folds: int, seed: int) -> pd.DataFrame:
    data = frame.loc[frame.profile.isin(list("ABCDEFG")), ["profile", *features]].copy()
    y = data.pop("profile").to_numpy(); x = data.to_numpy(); cv = StratifiedKFold(folds, shuffle=True, random_state=seed)
    models = {"multinomial_logistic": Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler()), ("model", LogisticRegression(max_iter=3000, class_weight="balanced"))]), "random_forest": Pipeline([("impute", SimpleImputer(strategy="median")), ("model", RandomForestClassifier(n_estimators=400, min_samples_leaf=3, class_weight="balanced", random_state=seed, n_jobs=-1))])}
    rows = []
    for name, model in models.items():
        actual, predicted, probs = [], [], []
        for train, test in cv.split(x, y):
            model.fit(x[train], y[train]); actual.extend(y[test]); predicted.extend(model.predict(x[test])); probs.append(model.predict_proba(x[test]))
        probability = np.vstack(probs); classes = model.classes_
        rows.append({"model": name, "n": len(y), "folds": folds, "macro_f1": f1_score(actual, predicted, average="macro"), "balanced_accuracy": balanced_accuracy_score(actual, predicted), "accuracy": accuracy_score(actual, predicted), "log_loss": log_loss(actual, probability, labels=classes), "features": ";".join(features)})
    return pd.DataFrame(rows)


def permutation_label_baseline(frame: pd.DataFrame, features: list[str], folds: int, seed: int, reps: int = 20) -> pd.DataFrame:
    """A feature-independent diagnostic baseline using the identical CV recipe."""
    data = frame.loc[frame.profile.isin(list("ABCDEFG")), ["profile", *features]].copy()
    y = data.pop("profile").to_numpy(); x = data.to_numpy(); rng = np.random.default_rng(seed)
    cv = StratifiedKFold(folds, shuffle=True, random_state=seed)
    rows = []
    for rep in range(reps):
        shuffled = rng.permutation(y); actual, predicted = [], []
        for train, test in cv.split(x, shuffled):
            model = Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler()), ("model", LogisticRegression(max_iter=3000, class_weight="balanced"))])
            model.fit(x[train], shuffled[train]); actual.extend(shuffled[test]); predicted.extend(model.predict(x[test]))
        rows.append({"replicate": rep, "macro_f1": f1_score(actual, predicted, average="macro"), "balanced_accuracy": balanced_accuracy_score(actual, predicted), "accuracy": accuracy_score(actual, predicted)})
    return pd.DataFrame(rows)


def main(config_path: str) -> None:
    cfg_path = Path(config_path); cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")); exp, specs, stats = cfg["experiment"], cfg["sources"], cfg["statistics"]
    out = Path(exp["output_dir"])
    if out.exists(): raise FileExistsError(f"Refusing to overwrite evidence directory: {out}")
    out.mkdir(parents=True); (out / "story_data").mkdir()
    lineage = pd.read_csv(exp["lineage_csv"], dtype={"territory_id": "Int64"})
    directory = select_snapshot(read_directory(exp["directory_workbook"]), exp["target_year"])
    # Read independent BDMO code universe before authorising any 11->8 mapping.
    raw, audits, all_codes = {}, {}, set()
    for key in ("population", "wage", "employment_total", "employment_by_okved", "investment_per_capita"):
        spec = specs[key]; years = set(spec.get("years", [spec.get("year")]))
        raw[key], audits[key] = read_bdmo(Path(spec["raw_file"]), years, spec, sectors=key == "employment_by_okved")
        all_codes.update(raw[key]["oktmo"].dropna().astype(str).str.zfill(8))
    oktmo = municipality_oktmo11_to_8(lineage, directory, all_codes)
    oktmo.to_csv(out / "oktmo_11_to_8_audit.csv", index=False)
    valid = oktmo.loc[oktmo.transform_allowed].copy()
    if len(valid) != 1903: raise RuntimeError(f"OKTMO gate expected 1903 valid rows, got {len(valid)}")
    # strict scalar joins
    scalar = valid[["territory_id", "official_name", "region", "candidate_oktmo8"]].rename(columns={"candidate_oktmo8": "oktmo"}).copy()
    conflicts = []
    for key in ("population", "wage", "employment_total", "investment_per_capita"):
        variable = specs[key]["variable"]; values, bad = unique_values(raw[key], variable, ["oktmo", "year"])
        conflicts.append(bad); values["oktmo"] = values.oktmo.astype(str).str.zfill(8)
        # core target uses the declared annual scalar; investment keeps separate yearly columns below.
        if key != "investment_per_capita":
            values = values.loc[values.year.eq(exp["target_year"]), ["oktmo", variable]]
            scalar = scalar.merge(values, on="oktmo", how="left", validate="one_to_one")
    # sector rows and deterministic section aggregation
    section, sector_bad = unique_values(raw["employment_by_okved"], "employment", ["oktmo", "year", "okved_section"])
    conflicts.append(sector_bad); section["oktmo"] = section.oktmo.astype(str).str.zfill(8)
    section = section.loc[section.year.eq(exp["target_year"])]
    sector_map = {"A":"agriculture", "B":"mining", "C":"manufacturing", "D":"utilities", "E":"utilities", "F":"construction", "G":"trade", "H":"transport", "I":"hospitality", "J":"information", "K":"finance", "L":"real_estate", "M":"professional", "N":"administrative", "O":"public_administration", "P":"education", "Q":"health", "R":"arts", "S":"other_services", "T":"other_services", "U":"other_services"}
    section["sector"] = section.okved_section.map(sector_map); sector = section.groupby(["oktmo", "sector"], as_index=False).employment.sum()
    sector_wide = sector.pivot(index="oktmo", columns="sector", values="employment").reset_index(); sector_columns = [x for x in sector_wide.columns if x != "oktmo"]
    scalar = scalar.merge(sector_wide, on="oktmo", how="left", validate="one_to_one")
    labels = pd.read_csv(exp["reference_labels"], index_col=0); dec = labels.columns[-1]
    mapping = pd.read_csv(exp["profile_mapping"]); profile_map = mapping.set_index("raw_community")["interpreted_profile"].to_dict()
    lookup = lineage.loc[lineage.status.eq("VERIFIED_DATA_LINEAGE_MATCH"), ["territory_id", "reference_mo"]].copy(); lookup["raw_community"] = lookup.reference_mo.map(labels[dec]).astype("Int64")
    lookup["profile"] = lookup.raw_community.map(profile_map)
    scalar = scalar.merge(lookup[["territory_id", "reference_mo", "profile"]], on="territory_id", how="left", validate="one_to_one")
    coverage_rows = []
    for variable in ["population", "wage", "employment_total"]:
        n = int(scalar[variable].notna().sum()); coverage_rows.append({"indicator": variable, "year": exp["target_year"], "eligible_reference_n": len(valid), "matched_n": n, "coverage_pct": 100*n/len(valid), "source": Path(specs["population" if variable == "population" else "wage" if variable == "wage" else "employment_total"]["raw_file"]).name, "status": "CORE" if n / len(valid) >= .80 else "LIMITED"})
    n_sector = int(scalar[sector_columns].notna().any(axis=1).sum()); coverage_rows.append({"indicator":"employment_by_okved", "year":exp["target_year"], "eligible_reference_n":len(valid), "matched_n":n_sector, "coverage_pct":100*n_sector/len(valid), "source":Path(specs["employment_by_okved"]["raw_file"]).name, "status":"CORE" if n_sector/len(valid)>=.80 else "LIMITED"})
    coverage = pd.DataFrame(coverage_rows); coverage.to_csv(out / "external_validation_coverage.csv", index=False)
    join_audit = []
    for row in coverage_rows:
        variable = row["indicator"]
        available = (
            scalar.loc[scalar[variable].notna(), "oktmo"]
            if variable in scalar
            else sector_wide.loc[sector_wide[sector_columns].notna().any(axis=1), "oktmo"]
        )
        missing = sorted(set(valid.candidate_oktmo8) - set(available))
        duplicate_n = int(sum(len(x) for x in conflicts if not x.empty and "variable" in x and x.variable.eq(variable).any()))
        join_audit.append({**row, "duplicate_keys": duplicate_n, "missing_key_count": len(missing), "missing_keys": ";".join(missing)})
    pd.DataFrame(join_audit).to_csv(out / "bdmo_join_audit.csv", index=False)
    investment_values, investment_bad = unique_values(raw["investment_per_capita"], "investment_per_capita", ["oktmo", "year"]); conflicts.append(investment_bad); investment_values.oktmo = investment_values.oktmo.astype(str).str.zfill(8)
    inv_rows=[]
    for year in specs["investment_per_capita"]["years"]:
        n=int(valid.oktmo11.str[:8].isin(set(investment_values.loc[investment_values.year.eq(year),"oktmo"])).sum())
        inv_rows.append({"indicator":"investment_per_capita", "year":year, "eligible_reference_n":len(valid), "matched_n":n, "coverage_pct":100*n/len(valid), "status":"CANDIDATE" if n/len(valid)>=.5 else "LIMITED"})
    investment_coverage=pd.DataFrame(inv_rows); investment_coverage.to_csv(out / "investment_year_coverage.csv", index=False)
    scalar.to_csv(out / "external_validation_joined.csv", index=False); pd.concat([x for x in conflicts if not x.empty], ignore_index=True).to_csv(out / "bdmo_duplicate_or_conflict_keys.csv", index=False) if any(not x.empty for x in conflicts) else pd.DataFrame(columns=["variable"]).to_csv(out / "bdmo_duplicate_or_conflict_keys.csv", index=False)
    major=scalar.loc[scalar.profile.isin(list("ABCDEFG"))].copy(); summary, global_tests, pairs = summaries(major, ["population", "wage", "employment_total"], stats["bootstrap_reps"], stats["seed"])
    summary.to_csv(out / "external_profile_summary.csv", index=False); global_tests.to_csv(out / "external_global_tests.csv", index=False); pairs.to_csv(out / "external_pairwise_dunn_bh.csv", index=False)
    comp=major.dropna(subset=sector_columns, how="all").copy(); comp[sector_columns]=comp[sector_columns].fillna(0); totals=comp[sector_columns].sum(axis=1); comp=comp.loc[totals.gt(0)].copy(); comp[sector_columns]=comp[sector_columns].div(comp[sector_columns].sum(axis=1), axis=0)
    positive=comp[sector_columns].where(comp[sector_columns].gt(0)).min(axis=1); replaced=comp[sector_columns].mask(comp[sector_columns].eq(0), positive.mul(.5), axis=0); replaced=replaced.div(replaced.sum(axis=1),axis=0); clr=np.log(replaced).sub(np.log(replaced).mean(axis=1),axis=0); clr.insert(0,"profile",comp.profile.to_numpy()); perm=permanova(clr, stats["permutation_reps"],stats["seed"]); (out / "employment_sector_permanova.json").write_text(json.dumps(perm,indent=2),encoding="utf-8")
    sector_summary = comp.groupby("profile", sort=True)[sector_columns].agg(["mean", "median"]).stack(level=0).reset_index().rename(columns={"level_1": "statistic"})
    sector_summary.to_csv(out / "employment_sector_profile_summary.csv", index=False)
    med=summary.loc[summary.profile.isin(["D","F","G"])].pivot(index="variable",columns="profile",values="median").reset_index(); med["monotonic_status"]=np.where((med.D>med.F)&(med.F>med.G),"D>F>G",np.where((med.G>med.F)&(med.F>med.D),"G>F>D","not_monotonic"))
    sector_dfg = comp.loc[comp.profile.isin(["D", "F", "G"])].groupby("profile")[sector_columns].median().T.reset_index().rename(columns={"index": "variable"})
    sector_dfg["variable"] = "employment_share_" + sector_dfg["variable"].astype(str)
    sector_dfg["monotonic_status"] = np.where((sector_dfg.D > sector_dfg.F) & (sector_dfg.F > sector_dfg.G), "D>F>G", np.where((sector_dfg.G > sector_dfg.F) & (sector_dfg.F > sector_dfg.D), "G>F>D", "not_monotonic"))
    med = pd.concat([med, sector_dfg], ignore_index=True); med.to_csv(out / "dfg_transition.csv", index=False)
    feature_cols=["population","wage","employment_total",*sector_columns]; metrics=prediction(major,feature_cols,stats["cv_folds"],stats["seed"]); metrics.to_csv(out / "external_prediction_metrics.csv",index=False)
    baseline = permutation_label_baseline(major, feature_cols, stats["cv_folds"], stats["seed"]); baseline.to_csv(out / "permutation_label_baseline.csv", index=False)
    # Selection-bias output is descriptive: all external availability versus nonavailability by frozen profile.
    scalar["core_complete"]=scalar[["population","wage","employment_total"]].notna().all(axis=1); selection=scalar.groupby(["profile","core_complete"],dropna=False).size().reset_index(name="n"); selection.to_csv(out / "selection_bias_profile_counts.csv",index=False)
    scalar.groupby(["region", "core_complete"], dropna=False).size().reset_index(name="n").to_csv(out / "selection_bias_region_counts.csv", index=False)
    (out / "OKVED_AGGREGATION.md").write_text("# OKVED aggregation\n\nRows are restricted to BDMO upper-level municipalities and the annual period. Only `Раздел A` through `Раздел U` records are used; the declared total is excluded. A→agriculture, B→mining, C→manufacturing, D/E→utilities, F→construction, G→trade, H→transport, I→hospitality, J→information, K→finance, L→real_estate, M→professional, N→administrative, O→public_administration, P→education, Q→health, R→arts, and S/T/U→other_services. Each municipality's sector values are divided by the sum of these observed sections; analysis uses a documented multiplicative zero replacement followed by CLR and PERMANOVA.\n",encoding="utf-8")
    (out / "OKTMO_TRANSFORMATION_AUDIT.md").write_text(f"# OKTMO 11→8 transformation audit\n\nReference universe: 1,904. Verified lineage: 1,903. Excluded unresolved lineage: 1. Validated OKTMO8: {int(oktmo.transform_allowed.sum())}.\n\nThe directory code is held as text, hyphens are formatting only, and leading zeroes remain strings. A candidate is permitted only when the verified SberIndex municipality record has 11 digits, suffix `000`, and its first eight digits occur in the independently ingested upper-level BDMO municipal-code universe. Duplicate candidates are rejected as many-to-one conflicts. No names are used as a join key.\n\nOfficial semantic references: {cfg['experiment']['references'][0]['url']} and {cfg['experiment']['references'][1]['url']}. Rosstat describes digits 1–8 as identifying a municipality and digits 9–11 as identifying a locality; municipality reporting can use the 11-digit representation ending `000`.\n",encoding="utf-8")
    for name, file in {"external_profile_summary":summary,"wage_by_profile":summary.query("variable == 'wage'"),"population_by_profile":summary.query("variable == 'population'"),"employment_by_profile":summary.query("variable == 'employment_total'"),"employment_sector_by_profile":sector_summary,"dfg_transition":med,"external_prediction_metrics":metrics,"external_coverage":coverage}.items(): file.to_csv(out / "story_data" / f"{name}.csv",index=False)
    report = f"""# National external validation\n\nThis is an external interpretation layer using frozen A–G labels; it neither constructs nor tunes the network or clustering. Reference universe: 1,904; verified data lineage: 1,903; unresolved lineage excluded: 1; valid gated OKTMO8: {int(oktmo.transform_allowed.sum())}.\n\nCore coverage is population {coverage_rows[0]['matched_n']}/{len(valid)} ({coverage_rows[0]['coverage_pct']:.2f}%), wage {coverage_rows[1]['matched_n']}/{len(valid)} ({coverage_rows[1]['coverage_pct']:.2f}%), total employment {coverage_rows[2]['matched_n']}/{len(valid)} ({coverage_rows[2]['coverage_pct']:.2f}%), and sector employment {coverage_rows[3]['matched_n']}/{len(valid)} ({coverage_rows[3]['coverage_pct']:.2f}%). Investment is limited: the largest tested annual coverage is {investment_coverage.coverage_pct.max():.2f}%, so investment is excluded from the central national analysis.\n\nGlobal profile differences are in `external_global_tests.csv`; their epsilon-squared effects are {', '.join(f"{x.variable}={x.epsilon_squared:.3f}" for x in global_tests.itertuples())}. Sector composition PERMANOVA on CLR Euclidean distances has pseudo-F={perm['pseudo_f']:.3f}, p={perm['p_value']:.3g}, n={perm['n']}. D/F/G medians and monotonic checks are in `dfg_transition.csv`; they are descriptive external consistency checks, not a claim of stable exact boundaries.\n\nPrediction uses pipeline-contained imputation/scaling and stratified CV. Metrics are in `external_prediction_metrics.csv`; `permutation_label_baseline.csv` is the deliberately label-shuffled diagnostic. All inferential results are exploratory and susceptible to coverage/selection effects documented in the selection-bias tables.\n"""
    (out / "NATIONAL_EXTERNAL_VALIDATION.md").write_text(report, encoding="utf-8")
    audit = {"reference_total":1904,"verified_lineage":1903,"excluded_unresolved":1,"valid_oktmo8":int(oktmo.transform_allowed.sum()),"coverage":coverage.to_dict(orient="records"),"investment":investment_coverage.to_dict(orient="records"),"external_features_do_not_enter_clustering":True}
    (out / "run_manifest.json").write_text(json.dumps({"config_sha256":digest(cfg_path),"input_sha256":{str(p):digest(Path(p)) for p in [exp['lineage_csv'],exp['directory_workbook'],exp['reference_labels'],exp['profile_mapping'],*[x['raw_file'] for x in specs.values()]]},"audit":audit},ensure_ascii=False,indent=2),encoding="utf-8")
    (out / "COMPLETED.json").write_text(json.dumps({"status":"COMPLETED_NATIONAL_EXTERNAL_INTERPRETATION","audit":audit},ensure_ascii=False,indent=2),encoding="utf-8")

if __name__ == "__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--config",default="configs/external_validation_national_20261006.yaml"); main(parser.parse_args().config)
