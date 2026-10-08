"""Run frozen exploratory tests of seven economic-mechanism hypotheses."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import pickle
import platform
import subprocess
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
import scipy
from scipy.stats import kruskal, linregress, mannwhitneyu, spearmanr, theilslopes, wilcoxon
import sklearn
import yaml

from sbernet.economic_mechanisms import (
    aitchison_rows,
    composition_change_volatility,
    greedy_unique_pairs,
    haversine_km,
    holm_adjust,
    partial_r2,
    robust_z_matrix,
)
from sbernet.io import build_strict_panel, read_semicolon_zip


PROFILE_ORDER = list("ABCDEFG")
STATE_ORDER = ["stable_core", "expansive_core", "transition", "unresolved"]
COLORS = {
    "A": "#355C7D", "B": "#6C5B7B", "C": "#C06C84", "D": "#F67280",
    "E": "#F8B195", "F": "#2A9D8F", "G": "#264653",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    def convert(item: object) -> object:
        if isinstance(item, (np.integer,)): return int(item)
        if isinstance(item, (np.floating,)): return float(item)
        if isinstance(item, np.ndarray): return item.tolist()
        if isinstance(item, pd.Timestamp): return item.isoformat()
        raise TypeError(type(item).__name__)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False, default=convert), encoding="utf-8")


def git_output(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True, encoding="utf-8").strip()


def snapshot(paths: list[Path]) -> dict[str, dict[str, int | str]]:
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing frozen Round23 input: {missing}")
    return {
        str(path).replace("\\", "/"): {"sha256": sha256(path), "bytes": path.stat().st_size}
        for path in paths
    }


def markdown_table(frame: pd.DataFrame, columns: list[str], digits: int = 4) -> str:
    def render(value: object) -> str:
        if pd.isna(value): return "NA"
        if isinstance(value, (float, np.floating)): return f"{float(value):.{digits}f}"
        return str(value)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    lines += ["| " + " | ".join(render(row[column]) for column in columns) + " |" for _, row in frame.iterrows()]
    return "\n".join(lines)


def design_dummies(frame: pd.DataFrame, numeric: list[str], categorical: list[str]) -> np.ndarray:
    blocks = [np.ones((len(frame), 1), dtype=float)]
    for column in numeric:
        blocks.append(frame[[column]].to_numpy(float))
    if categorical:
        encoded = pd.get_dummies(frame[categorical].astype(str), drop_first=True, dtype=float)
        blocks.append(encoded.to_numpy(float))
    return np.column_stack(blocks)


def freedman_lane_partial_r2(
    y: np.ndarray,
    reduced: np.ndarray,
    added: np.ndarray,
    strata: np.ndarray,
    reps: int,
    seed: int,
) -> tuple[float, float]:
    """Partial R2 with reduced-model residual permutations within strata."""
    y = np.asarray(y, dtype=float)
    q, _ = np.linalg.qr(np.asarray(reduced, dtype=float), mode="reduced")
    y_res = y - q @ (q.T @ y)
    z = np.asarray(added, dtype=float)
    z_res = z - q @ (q.T @ z)
    gram_inv = np.linalg.pinv(z_res.T @ z_res)

    def score(residual: np.ndarray) -> np.ndarray:
        if residual.ndim == 1: residual = residual[:, None]
        residual = residual - q @ (q.T @ residual)
        rss = np.sum(residual * residual, axis=0)
        cross = z_res.T @ residual
        explained = np.sum(cross * (gram_inv @ cross), axis=0)
        return np.clip(explained / rss, 0.0, 1.0)

    observed = float(score(y_res)[0])
    rng = np.random.default_rng(seed)
    groups = [np.flatnonzero(strata == value) for value in pd.unique(strata)]
    exceed = 0
    batch = 100
    for start in range(0, reps, batch):
        width = min(batch, reps - start)
        permutations = np.empty((len(y), width), dtype=float)
        for column in range(width):
            order = np.arange(len(y))
            for indices in groups:
                order[indices] = rng.permutation(indices)
            permutations[:, column] = y_res[order]
        exceed += int(np.count_nonzero(score(permutations) >= observed - 1e-15))
    return observed, (exceed + 1) / (reps + 1)


def hc3_ols(y: np.ndarray, x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    y, x = np.asarray(y, float), np.asarray(x, float)
    xtx_inv = np.linalg.pinv(x.T @ x)
    beta = xtx_inv @ x.T @ y
    residual = y - x @ beta
    leverage = np.sum((x @ xtx_inv) * x, axis=1)
    scaled = residual / np.maximum(1e-12, 1 - leverage)
    meat = x.T @ ((scaled * scaled)[:, None] * x)
    covariance = xtx_inv @ meat @ xtx_inv
    se = np.sqrt(np.maximum(0.0, np.diag(covariance)))
    t_value = beta / se
    p_value = 2 * scipy.stats.t.sf(np.abs(t_value), max(1, len(y) - x.shape[1]))
    return beta, se, p_value


def theil_sen_batch(series: np.ndarray) -> np.ndarray:
    values = np.asarray(series, dtype=float)
    if values.ndim == 1: values = values[None, :]
    left, right = np.triu_indices(values.shape[1], k=1)
    slopes = (values[:, right] - values[:, left]) / (right - left)[None, :]
    return np.median(slopes, axis=1)


def bootstrap_profile_dispersion(
    values: np.ndarray,
    profiles: np.ndarray,
    reps: int,
    rng: np.random.Generator,
) -> np.ndarray:
    result = np.empty((reps, len(PROFILE_ORDER), values.shape[1]), dtype=float)
    for profile_index, profile in enumerate(PROFILE_ORDER):
        group = values[profiles == profile]
        probability = np.full(len(group), 1 / len(group))
        for start in range(0, reps, 100):
            width = min(100, reps - start)
            weights = rng.multinomial(len(group), probability, size=width)
            result[start:start + width, profile_index, :] = weights @ group / len(group)
    return np.std(result, axis=1, ddof=1)


def save_figure(fig: plt.Figure, stem: Path) -> None:
    fig.savefig(stem.with_suffix(".png"), dpi=180, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight")
    plt.close(fig)


def load_panel(cfg: dict) -> tuple[list[str], list[str], np.ndarray, np.ndarray, np.ndarray]:
    raw = read_semicolon_zip(cfg["inputs"]["spending"])
    required = [cfg["composition"]["total"]] + cfg["composition"]["parts"][:-1]
    panel, names, audit = build_strict_panel(raw, cfg["inputs"]["months"], required)
    if audit.strict_panel_names != cfg["inputs"]["panel_n"]:
        raise RuntimeError("Round23 strict-panel size differs from frozen contract")
    panel["period"] = pd.to_datetime(panel["period"])
    months = sorted(panel["period"].unique())
    totals = np.empty((len(names), len(months)), dtype=float)
    compositions = np.empty((len(names), len(months), len(cfg["composition"]["parts"])), dtype=float)
    selected = cfg["composition"]["parts"][:-1]
    for month_index, month in enumerate(months):
        pivot = panel.loc[panel.period.eq(month)].pivot(index="mo", columns="category_15", values="value").loc[names]
        total = pivot[cfg["composition"]["total"]].to_numpy(float)
        observed = pivot[selected].to_numpy(float)
        other = total - observed.sum(axis=1)
        parts = np.column_stack([observed, other])
        if np.any(total <= 0) or np.any(parts <= 0):
            raise RuntimeError(f"non-positive total/composition part in {pd.Timestamp(month).date()}")
        totals[:, month_index] = total
        compositions[:, month_index, :] = parts / total[:, None]
    return names, [str(pd.Timestamp(month).date()) for month in months], totals, compositions, panel


def profile_labels(names: list[str], cfg: dict) -> np.ndarray:
    temporal = pd.read_csv(cfg["inputs"]["temporal_labels"], index_col=0).loc[names]
    raw = temporal[cfg["inputs"]["reference_month"]].to_numpy(int)
    mapping = {int(key): value for key, value in cfg["profiles"]["raw_to_public"].items()}
    return np.asarray([mapping.get(int(value), "micro") for value in raw], dtype=object)


def main(config_path: str) -> None:
    started = time.perf_counter()
    cfg_path = Path(config_path)
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    output = Path(cfg["experiment"]["output_dir"])
    output.mkdir(parents=True, exist_ok=True)
    if (output / cfg["outputs"]["checksums"]).exists():
        raise FileExistsError("Round23 is complete; refusing to overwrite without a new config/run")
    gate_path = output / "baseline_gate" / "baseline_gate.json"
    if not gate_path.is_file():
        raise RuntimeError("Round23 baseline replay gate is missing")
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    if not gate.get("passed") or any(value != 1.0 for metric in gate["metrics"].values() for value in metric.values()):
        raise RuntimeError("Round23 baseline replay gate failed; downstream tests are blocked")

    frozen_paths = [cfg_path] + [Path(value) for key, value in cfg["inputs"].items() if key not in {"reference_month", "panel_n", "months"}]
    before = snapshot(frozen_paths)
    freeze = {
        "status": "FROZEN_BEFORE_ROUND23_COMPUTATION", "created_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_output("rev-parse", "HEAD"), "before": before, "after": None,
        "baseline_reproduction": "PASS", "final_hash_gate": "PENDING",
    }
    write_json(output / "BASELINE_FREEZE.json", freeze)

    names, months, totals, compositions, _ = load_panel(cfg)
    profiles = profile_labels(names, cfg)
    ag = np.isin(profiles, PROFILE_ORDER)
    month_index = {month: index for index, month in enumerate(months)}
    required_months = ["2023-01-01", "2023-12-01", "2024-01-01", "2024-12-01"]
    if any(month not in month_index for month in required_months):
        raise RuntimeError("required Round23 endpoint is absent")
    jan23, dec23, jan24, dec24 = [month_index[value] for value in required_months]
    shares = {part: compositions[:, :, index] for index, part in enumerate(cfg["composition"]["parts"])}
    market = shares["Маркетплейсы"]
    food = shares["Продовольствие"]

    atlas = pd.read_csv(cfg["inputs"]["atlas"]).set_index("municipality").loc[names]
    if not np.array_equal(atlas["reference_profile"].to_numpy(str), profiles):
        raise RuntimeError("Atlas/profile alignment differs from frozen reference")
    external = pd.read_csv(cfg["inputs"]["external"]).set_index("reference_mo").reindex(names)
    external["profile_check"] = profiles
    if external.index.has_duplicates:
        raise RuntimeError("external covariate join is duplicated")
    if int(external["region"].notna().sum()) != 1903:
        raise RuntimeError("external region coverage differs from the audited 1903/1904 contract")
    states = atlas["stability_class"].to_numpy(str)
    reps = int(cfg["inference"]["permutation_reps"])
    boots = int(cfg["inference"]["bootstrap_reps"])
    seed = int(cfg["inference"]["seed"])
    rng = np.random.default_rng(seed)

    # H24: Atlas uncertainty and observed economic volatility.
    total_volatility = np.std(np.diff(np.log(totals), axis=1), axis=1, ddof=1)
    composition_volatility = composition_change_volatility(compositions)
    municipality = pd.DataFrame({
        "municipality": names, "profile": profiles, "atlas_state": states,
        "mean_log_total": np.mean(np.log(totals), axis=1),
        "total_volatility": total_volatility,
        "composition_volatility": composition_volatility,
        "region": external["region"].to_numpy(),
    })
    municipality.to_csv(output / "municipality_volatility.csv", index=False)
    volatility_rows = []
    for metric in ("total_volatility", "composition_volatility"):
        for state in STATE_ORDER:
            values = municipality.loc[municipality.atlas_state.eq(state), metric].to_numpy(float)
            volatility_rows.append({
                "metric": metric, "atlas_state": state, "N": len(values), "mean": values.mean(),
                "median": np.median(values), "q25": np.quantile(values, .25), "q75": np.quantile(values, .75),
            })
    volatility_summary = pd.DataFrame(volatility_rows)
    volatility_summary.to_csv(output / "uncertainty_volatility_summary.csv", index=False)
    omnibus_rows, pair_rows = [], []
    primary_states = cfg["h24_uncertainty_volatility"]["states_primary"]
    for metric_index, metric in enumerate(("total_volatility", "composition_volatility")):
        groups = [municipality.loc[municipality.atlas_state.eq(state), metric].to_numpy(float) for state in primary_states]
        statistic, p_value = kruskal(*groups)
        omnibus_rows.append({"metric": metric, "test": "kruskal_wallis", "statistic": statistic, "p_raw": p_value})
        for left_index, left in enumerate(primary_states):
            for right in primary_states[left_index + 1:]:
                x = municipality.loc[municipality.atlas_state.eq(left), metric].to_numpy(float)
                y = municipality.loc[municipality.atlas_state.eq(right), metric].to_numpy(float)
                statistic, p_value = mannwhitneyu(x, y, alternative="two-sided")
                pair_rows.append({"metric": metric, "state_a": left, "state_b": right, "median_a": np.median(x), "median_b": np.median(y), "U": statistic, "p_raw": p_value})
    pairwise = pd.DataFrame(pair_rows)
    pairwise["p_holm"] = holm_adjust(pairwise.p_raw)
    pairwise.to_csv(output / "uncertainty_volatility_pairwise.csv", index=False)
    pd.DataFrame(omnibus_rows).to_csv(output / "uncertainty_volatility_omnibus.csv", index=False)
    adjusted_rows = []
    valid_h24 = ag & np.isin(states, STATE_ORDER) & external["region"].notna().to_numpy()
    adjusted_frame = municipality.loc[valid_h24].reset_index(drop=True)
    reduced = design_dummies(adjusted_frame, ["mean_log_total"], ["profile", "region"])
    state_added = pd.get_dummies(adjusted_frame.atlas_state, dtype=float).reindex(columns=STATE_ORDER[1:], fill_value=0).to_numpy(float)
    for metric_index, metric in enumerate(("total_volatility", "composition_volatility")):
        effect, p_value = freedman_lane_partial_r2(
            np.log1p(adjusted_frame[metric].to_numpy(float)), reduced, state_added,
            adjusted_frame.profile.to_numpy(), reps, seed + metric_index,
        )
        adjusted_rows.append({"metric": metric, "N": len(adjusted_frame), "partial_R2_atlas_state": effect, "permutation_p": p_value, "controls": "mean_log_total+profile+region"})
    adjusted_h24 = pd.DataFrame(adjusted_rows)
    adjusted_h24.to_csv(output / "uncertainty_volatility_adjusted.csv", index=False)

    # H25: Marketplace/Food co-movement by profile and pooled profile families.
    change_specs = {
        "primary_dec24_minus_dec23": (dec24, dec23),
        "requested_dec24_minus_jan23": (dec24, jan23),
        "replication_jan24_minus_jan23": (jan24, jan23),
    }
    substitution_rows = []
    group_masks = {
        "FG": np.isin(profiles, ["F", "G"]), "BD": np.isin(profiles, ["B", "D"]),
        **{profile: profiles == profile for profile in ["B", "D", "F", "G"]},
    }
    for change_name, (end, start) in change_specs.items():
        delta_market, delta_food = market[:, end] - market[:, start], food[:, end] - food[:, start]
        delta_log_ratio = np.log(market[:, end] / food[:, end]) - np.log(market[:, start] / food[:, start])
        for group, take in group_masks.items():
            rho, p_value = spearmanr(delta_market[take], delta_food[take])
            substitution_rows.append({
                "change": change_name, "group": group, "N": int(take.sum()), "spearman_rho": rho,
                "p_raw": p_value, "mean_delta_marketplace_share": delta_market[take].mean(),
                "mean_delta_food_share": delta_food[take].mean(), "mean_delta_log_marketplace_food_ratio": delta_log_ratio[take].mean(),
            })
    substitution = pd.DataFrame(substitution_rows)
    substitution["p_holm"] = holm_adjust(substitution.p_raw)
    substitution.to_csv(output / "marketplace_food_correlations.csv", index=False)
    primary_market = market[:, dec24] - market[:, dec23]
    primary_food = food[:, dec24] - food[:, dec23]
    combined = np.flatnonzero(np.isin(profiles, ["B", "D", "F", "G"]))
    fg_n = int(np.isin(profiles[combined], ["F", "G"]).sum())
    observed_contrast = float(spearmanr(primary_market[np.isin(profiles, ["F", "G"])], primary_food[np.isin(profiles, ["F", "G"])])[0] - spearmanr(primary_market[np.isin(profiles, ["B", "D"])], primary_food[np.isin(profiles, ["B", "D"])])[0])
    null = np.empty(reps)
    for rep in range(reps):
        permuted = rng.permutation(combined)
        fg_take, bd_take = permuted[:fg_n], permuted[fg_n:]
        null[rep] = spearmanr(primary_market[fg_take], primary_food[fg_take])[0] - spearmanr(primary_market[bd_take], primary_food[bd_take])[0]
    contrast_p = (np.count_nonzero(null <= observed_contrast) + 1) / (reps + 1)
    substitution_contrast = pd.DataFrame([{"change": "primary_dec24_minus_dec23", "rho_FG_minus_rho_BD": observed_contrast, "one_sided_permutation_p": contrast_p, "reps": reps}])
    substitution_contrast.to_csv(output / "marketplace_food_group_contrast.csv", index=False)

    # H26: initial Total and subsequent marketplace-share growth.
    baseline_log_total = np.log(totals[:, dec23])
    baseline_market_share = market[:, dec23]
    growth_rows = []
    for change_name, (end, start) in change_specs.items():
        outcome = market[:, end] - market[:, start]
        for group in ["ALL", *PROFILE_ORDER]:
            take = ag if group == "ALL" else profiles == group
            rho, p_value = spearmanr(baseline_log_total[take], outcome[take])
            growth_rows.append({"change": change_name, "group": group, "N": int(take.sum()), "spearman_rho": rho, "p_raw": p_value})
    growth = pd.DataFrame(growth_rows)
    growth["p_holm"] = holm_adjust(growth.p_raw)
    growth.to_csv(output / "marketplace_growth_initial_total.csv", index=False)
    valid_h26 = ag & external["region"].notna().to_numpy()
    regression_frame = pd.DataFrame({
        "outcome": primary_market[valid_h26], "log_total": baseline_log_total[valid_h26], "baseline_marketplace_share": baseline_market_share[valid_h26],
        "profile": profiles[valid_h26], "region": external["region"].to_numpy()[valid_h26],
    })
    reduced_h26 = design_dummies(regression_frame, ["baseline_marketplace_share"], ["profile", "region"])
    full_h26 = np.column_stack([reduced_h26, regression_frame.log_total.to_numpy(float)])
    beta, se, p_hc3 = hc3_ols(regression_frame.outcome.to_numpy(float), full_h26)
    h26_partial, h26_perm_p = freedman_lane_partial_r2(
        regression_frame.outcome.to_numpy(float), reduced_h26, regression_frame[["log_total"]].to_numpy(float),
        regression_frame.profile.to_numpy(), reps, seed + 20,
    )
    adjusted_h26 = pd.DataFrame([{
        "N": len(regression_frame), "log_total_coefficient": beta[-1], "HC3_se": se[-1], "HC3_p": p_hc3[-1],
        "partial_R2_log_total": h26_partial, "within_profile_permutation_p": h26_perm_p,
        "controls": "baseline_marketplace_share+profile+region",
    }])
    adjusted_h26.to_csv(output / "marketplace_growth_adjusted.csv", index=False)

    # H27: wage/population matched examples and aggregate comparison.
    complete = ag & external["wage"].notna().to_numpy() & external["population"].notna().to_numpy()
    matched = pd.DataFrame({
        "municipality": np.asarray(names)[complete], "profile": profiles[complete],
        "region": external.loc[complete, "region"].to_numpy(), "wage": external.loc[complete, "wage"].to_numpy(float),
        "population": external.loc[complete, "population"].to_numpy(float), "panel_index": np.flatnonzero(complete),
    }).reset_index(drop=True)
    covariates = robust_z_matrix(np.column_stack([np.log(matched.wage), np.log(matched.population)]))
    different_region = matched.region.to_numpy()[:, None] != matched.region.to_numpy()[None, :]
    different_profile = matched.profile.to_numpy()[:, None] != matched.profile.to_numpy()[None, :]
    caliper = float(cfg["h27_matched_economic_twins"]["caliper_standardized_euclidean"])
    cross_pairs = greedy_unique_pairs(covariates, different_region & different_profile, caliper)
    same_pairs = greedy_unique_pairs(covariates, different_region & ~different_profile, caliper)

    def pair_frame(pairs: list[tuple[int, int, float, bool]], pair_type: str) -> pd.DataFrame:
        rows = []
        for left, right, distance, mutual in pairs:
            a, b = matched.iloc[left], matched.iloc[right]
            ia, ib = int(a.panel_index), int(b.panel_index)
            rows.append({
                "pair_type": pair_type, "municipality_a": a.municipality, "municipality_b": b.municipality,
                "profile_a": a.profile, "profile_b": b.profile, "region_a": a.region, "region_b": b.region,
                "wage_a": a.wage, "wage_b": b.wage, "population_a": a.population, "population_b": b.population,
                "wage_relative_difference": abs(a.wage - b.wage) / ((a.wage + b.wage) / 2),
                "population_relative_difference": abs(a.population - b.population) / ((a.population + b.population) / 2),
                "match_distance": distance, "mutual_nearest": mutual,
                "aitchison_dec2024": float(aitchison_rows(compositions[ia:ia+1, dec24, :], compositions[ib:ib+1, dec24, :])[0]),
                "food_share_a": food[ia, dec24], "food_share_b": food[ib, dec24],
                "marketplace_share_a": market[ia, dec24], "marketplace_share_b": market[ib, dec24],
            })
        return pd.DataFrame(rows)

    cross_frame, same_frame = pair_frame(cross_pairs, "different_profile"), pair_frame(same_pairs, "same_profile")
    all_pairs = pd.concat([cross_frame, same_frame], ignore_index=True)
    all_pairs.to_csv(output / "matched_pair_all.csv", index=False)
    cross_values, same_values = cross_frame.aitchison_dec2024.to_numpy(), same_frame.aitchison_dec2024.to_numpy()
    observed_pair_difference = float(np.median(cross_values) - np.median(same_values))
    bootstrap_difference = np.empty(boots)
    for start in range(0, boots, 250):
        width = min(250, boots - start)
        cross_draw = rng.choice(cross_values, size=(width, len(cross_values)), replace=True)
        same_draw = rng.choice(same_values, size=(width, len(same_values)), replace=True)
        bootstrap_difference[start:start+width] = np.median(cross_draw, axis=1) - np.median(same_draw, axis=1)
    pair_summary = pd.DataFrame([{
        "cross_profile_pairs": len(cross_frame), "same_profile_control_pairs": len(same_frame),
        "cross_profile_median_aitchison": np.median(cross_values), "same_profile_median_aitchison": np.median(same_values),
        "median_difference": observed_pair_difference, "bootstrap_ci_low": np.quantile(bootstrap_difference, .025),
        "bootstrap_ci_high": np.quantile(bootstrap_difference, .975),
        "bootstrap_one_sided_p": (np.count_nonzero(bootstrap_difference <= 0) + 1) / (boots + 1),
    }])
    pair_summary.to_csv(output / "matched_pair_summary.csv", index=False)
    example_rows, seen_profile_pairs = [], set()
    sorted_cross = cross_frame.assign(profile_pair=cross_frame.apply(lambda row: "-".join(sorted([row.profile_a, row.profile_b])), axis=1)).sort_values(["aitchison_dec2024", "match_distance"], ascending=[False, True])
    for _, row in sorted_cross.iterrows():
        if row.profile_pair not in seen_profile_pairs:
            example_rows.append(row)
            seen_profile_pairs.add(row.profile_pair)
        if len(example_rows) == int(cfg["h27_matched_economic_twins"]["examples"]["maximum"]): break
    if len(example_rows) < int(cfg["h27_matched_economic_twins"]["examples"]["maximum"]):
        used = {(row.municipality_a, row.municipality_b) for row in example_rows}
        for _, row in sorted_cross.iterrows():
            if (row.municipality_a, row.municipality_b) not in used:
                example_rows.append(row)
                used.add((row.municipality_a, row.municipality_b))
            if len(example_rows) == int(cfg["h27_matched_economic_twins"]["examples"]["maximum"]): break
    matched_examples = pd.DataFrame(example_rows).drop(columns=["profile_pair"], errors="ignore")
    matched_examples.to_csv(output / "matched_pair_examples.csv", index=False)

    # H28: seven-profile dispersion through time.
    profile_market = np.vstack([market[profiles == profile].mean(axis=0) for profile in PROFILE_ORDER])
    profile_log_total = np.vstack([np.log(totals[profiles == profile]).mean(axis=0) for profile in PROFILE_ORDER])
    market_dispersion = np.std(profile_market, axis=0, ddof=1)
    total_dispersion = np.std(profile_log_total, axis=0, ddof=1)
    dispersion = pd.DataFrame({"month": months, "marketplace_share_sd": market_dispersion, "mean_log_total_sd": total_dispersion})
    dispersion["marketplace_index_100"] = 100 * dispersion.marketplace_share_sd / dispersion.marketplace_share_sd.iloc[0]
    dispersion["total_index_100"] = 100 * dispersion.mean_log_total_sd / dispersion.mean_log_total_sd.iloc[0]
    dispersion.to_csv(output / "profile_dispersion_monthly.csv", index=False)
    market_slope = float(theilslopes(market_dispersion, np.arange(len(months)))[0])
    total_slope = float(theilslopes(total_dispersion, np.arange(len(months)))[0])
    market_boot = bootstrap_profile_dispersion(market[ag], profiles[ag], boots, rng)
    total_boot = bootstrap_profile_dispersion(np.log(totals[ag]), profiles[ag], boots, rng)
    market_slopes = theil_sen_batch(market_boot)
    total_slopes = theil_sen_batch(total_boot)
    dispersion_trend = pd.DataFrame([
        {"metric": "marketplace_share_sd", "theil_sen_slope": market_slope, "bootstrap_ci_low": np.quantile(market_slopes, .025), "bootstrap_ci_high": np.quantile(market_slopes, .975), "OLS_slope": linregress(np.arange(len(months)), market_dispersion).slope, "start": market_dispersion[0], "end": market_dispersion[-1]},
        {"metric": "mean_log_total_sd", "theil_sen_slope": total_slope, "bootstrap_ci_low": np.quantile(total_slopes, .025), "bootstrap_ci_high": np.quantile(total_slopes, .975), "OLS_slope": linregress(np.arange(len(months)), total_dispersion).slope, "start": total_dispersion[0], "end": total_dispersion[-1]},
    ])
    dispersion_trend.to_csv(output / "profile_dispersion_trends.csv", index=False)
    yoy_rows = []
    for metric, values in (("marketplace_share_sd", market_dispersion), ("mean_log_total_sd", total_dispersion)):
        for month_number in range(12):
            yoy_rows.append({"metric": metric, "month_of_year": month_number + 1, "year_2023": values[month_number], "year_2024": values[month_number + 12], "yoy_change": values[month_number + 12] - values[month_number]})
    pd.DataFrame(yoy_rows).to_csv(output / "profile_dispersion_yoy.csv", index=False)

    # H29: top-three graph neighbors and geographic distance.
    with (output / "baseline_gate" / "baseline_graphs.pkl").open("rb") as handle:
        graph_bundle = pickle.load(handle)
    graph: nx.Graph = graph_bundle["static"]
    if graph_bundle["names"] != names:
        raise RuntimeError("baseline-gate graph order differs from Round23 panel")
    point_data = pd.DataFrame(json.loads(Path(cfg["inputs"]["representative_points"]).read_text(encoding="utf-8"))).set_index("reference_mo")
    point_data = point_data.reindex(names)
    neighbor_rows = []
    nodes_below_three = 0
    for node in range(len(names)):
        neighbors = sorted(graph[node].items(), key=lambda item: (float(item[1].get("distance", np.inf)), item[0]))[:3]
        if len(neighbors) < 3: nodes_below_three += 1
        for rank, (other, attributes) in enumerate(neighbors, start=1):
            if point_data.iloc[node][["longitude", "latitude"]].isna().any() or point_data.iloc[other][["longitude", "latitude"]].isna().any():
                continue
            geo = float(haversine_km(point_data.iloc[node].longitude, point_data.iloc[node].latitude, point_data.iloc[other].longitude, point_data.iloc[other].latitude))
            neighbor_rows.append({
                "municipality": names[node], "neighbor": names[other], "profile": profiles[node], "neighbor_profile": profiles[other],
                "region": external.iloc[node].region, "neighbor_region": external.iloc[other].region,
                "rank": rank, "feature_distance": float(attributes.get("distance", np.nan)), "edge_weight": float(attributes.get("weight", np.nan)),
                "geographic_km": geo, "above_500km": geo > 500, "above_1000km": geo > 1000,
                "longitude": point_data.iloc[node].longitude, "latitude": point_data.iloc[node].latitude,
                "neighbor_longitude": point_data.iloc[other].longitude, "neighbor_latitude": point_data.iloc[other].latitude,
            })
    neighbors = pd.DataFrame(neighbor_rows)
    neighbors.to_csv(output / "network_neighbor_geography_directed.csv", index=False)
    neighbors["pair_key"] = neighbors.apply(lambda row: "||".join(sorted([row.municipality, row.neighbor])), axis=1)
    unique_neighbors = neighbors.sort_values(["feature_distance", "pair_key"]).drop_duplicates("pair_key").copy()
    unique_neighbors.to_csv(output / "network_neighbor_geography_unique.csv", index=False)
    neighbor_summary = pd.DataFrame([
        {"selection": "directed_top3", "pairs": len(neighbors), "median_km": neighbors.geographic_km.median(), "share_above_500km": neighbors.above_500km.mean(), "share_above_1000km": neighbors.above_1000km.mean(), "nodes_with_fewer_than_3_graph_neighbors": nodes_below_three},
        {"selection": "unique_pairs", "pairs": len(unique_neighbors), "median_km": unique_neighbors.geographic_km.median(), "share_above_500km": unique_neighbors.above_500km.mean(), "share_above_1000km": unique_neighbors.above_1000km.mean(), "nodes_with_fewer_than_3_graph_neighbors": nodes_below_three},
    ])
    neighbor_summary.to_csv(output / "network_neighbor_geography_summary.csv", index=False)
    eligible_examples = unique_neighbors.loc[unique_neighbors.above_1000km & unique_neighbors.region.ne(unique_neighbors.neighbor_region)].sort_values(["feature_distance", "geographic_km"], ascending=[True, False])
    twin_examples, twin_profiles = [], set()
    for _, row in eligible_examples.iterrows():
        profile_pair = "-".join(sorted([str(row.profile), str(row.neighbor_profile)]))
        if profile_pair not in twin_profiles:
            twin_examples.append(row)
            twin_profiles.add(profile_pair)
        if len(twin_examples) == int(cfg["h29_geographically_distant_network_twins"]["examples"]["maximum"]): break
    if len(twin_examples) < int(cfg["h29_geographically_distant_network_twins"]["examples"]["maximum"]):
        used = {row.pair_key for row in twin_examples}
        for _, row in eligible_examples.iterrows():
            if row.pair_key not in used:
                twin_examples.append(row); used.add(row.pair_key)
            if len(twin_examples) == int(cfg["h29_geographically_distant_network_twins"]["examples"]["maximum"]): break
    distant_examples = pd.DataFrame(twin_examples)
    distant_examples.to_csv(output / "network_twin_examples.csv", index=False)

    # H30: endpoint Food-share changes by frozen profile.
    food_rows = []
    for change_name, (end, start) in change_specs.items():
        delta = food[:, end] - food[:, start]
        for profile in PROFILE_ORDER:
            values = delta[profiles == profile]
            statistic, p_value = wilcoxon(values, alternative="two-sided", zero_method="wilcox")
            draw = np.empty(boots)
            for begin in range(0, boots, 250):
                width = min(250, boots - begin)
                draw[begin:begin+width] = rng.choice(values, size=(width, len(values)), replace=True).mean(axis=1)
            food_rows.append({
                "change": change_name, "profile": profile, "N": len(values), "mean_change": values.mean(), "median_change": np.median(values),
                "mean_ci_low": np.quantile(draw, .025), "mean_ci_high": np.quantile(draw, .975), "wilcoxon_W": statistic, "p_raw": p_value,
            })
    food_changes = pd.DataFrame(food_rows)
    food_changes["p_holm"] = holm_adjust(food_changes.p_raw)
    food_changes.to_csv(output / "food_share_profile_changes.csv", index=False)

    # Fixed support rules.
    primary_vol = volatility_summary.loc[volatility_summary.atlas_state.isin(primary_states)].pivot(index="atlas_state", columns="metric", values="median")
    ordered_both = all(primary_vol.loc["stable_core", metric] < primary_vol.loc["transition", metric] < primary_vol.loc["unresolved", metric] for metric in ("total_volatility", "composition_volatility"))
    required_pairs = pairwise.loc[pairwise.state_a.eq("stable_core") & pairwise.state_b.isin(["transition", "unresolved"])]
    h24_supported = bool(ordered_both and (required_pairs.p_holm < .05).all())
    primary_sub = substitution.loc[substitution.change.eq("primary_dec24_minus_dec23")].set_index("group")
    h25_supported = bool(primary_sub.loc["FG", "spearman_rho"] < 0 and primary_sub.loc["FG", "p_holm"] < .05 and observed_contrast < 0 and contrast_p < .05 and primary_sub.loc["F", "spearman_rho"] < 0 and primary_sub.loc["G", "spearman_rho"] < 0)
    primary_growth = growth.loc[growth.change.eq("primary_dec24_minus_dec23") & growth.group.eq("ALL")].iloc[0]
    h26_supported = bool(primary_growth.spearman_rho < 0 and primary_growth.p_holm < .05 and beta[-1] < 0 and h26_perm_p < .05)
    h27_supported = bool(pair_summary.iloc[0].bootstrap_ci_low > 0)
    h28_supported = bool(dispersion_trend.iloc[0].bootstrap_ci_high < 0 and dispersion_trend.iloc[1].bootstrap_ci_high >= 0)
    primary_food_table = food_changes.loc[food_changes.change.eq("primary_dec24_minus_dec23")].set_index("profile")
    h30_supported = bool(all(primary_food_table.loc[p, "mean_change"] > 0 and primary_food_table.loc[p, "p_holm"] < .05 for p in ["F", "G"]) and all(primary_food_table.loc[p, "mean_change"] <= 0 for p in ["B", "D", "E"]))
    statuses = {
        "H24_uncertainty_equals_economic_volatility": "SUPPORTED_BY_FIXED_RULE" if h24_supported else "NOT_SUPPORTED_BY_FIXED_RULE",
        "H25_marketplaces_replace_food_in_FG": "SUPPORTED_AS_ASSOCIATION_ONLY" if h25_supported else "NOT_SUPPORTED_BY_FIXED_RULE",
        "H26_marketplaces_grow_where_initial_total_is_lower": "SUPPORTED_AS_ASSOCIATION_ONLY" if h26_supported else "NOT_SUPPORTED_BY_FIXED_RULE",
        "H27_same_income_population_different_profiles_different_baskets": "SUPPORTED_DESCRIPTIVELY" if h27_supported else "NOT_SUPPORTED_BY_FIXED_RULE",
        "H28_digital_convergence_without_level_convergence": "SUPPORTED_DESCRIPTIVELY" if h28_supported else "NOT_SUPPORTED_BY_FIXED_RULE",
        "H29_distant_network_twins": "DESCRIPTIVE_RESULT_NO_INFERENTIAL_RULE",
        "H30_food_share_inflation_pressure": "SUPPORTED_AS_SHARE_PATTERN_NOT_INFLATION" if h30_supported else "NOT_SUPPORTED_BY_FIXED_RULE",
    }

    # Figures.
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for axis, metric, title in zip(axes, ["total_volatility", "composition_volatility"], ["Volatility of Δ log Total", "Volatility of Δ CLR composition"]):
        arrays = [municipality.loc[municipality.atlas_state.eq(state), metric].to_numpy() for state in STATE_ORDER]
        axis.boxplot(arrays, tick_labels=[state.replace("_", "\n") for state in STATE_ORDER], showfliers=False)
        axis.set_title(title); axis.grid(axis="y", alpha=.2)
    fig.suptitle("Atlas state and observed month-to-month volatility")
    save_figure(fig, output / "figure_h24_uncertainty_volatility")

    fig, axes = plt.subplots(2, 2, figsize=(10, 8), sharex=True, sharey=True)
    for axis, profile in zip(axes.flat, ["B", "D", "F", "G"]):
        take = profiles == profile
        axis.scatter(100 * primary_market[take], 100 * primary_food[take], s=10, alpha=.45, color=COLORS[profile])
        axis.axhline(0, color="#999", lw=.7); axis.axvline(0, color="#999", lw=.7)
        axis.set_title(f"{profile}: ρ={spearmanr(primary_market[take], primary_food[take])[0]:.2f}")
    fig.supxlabel("Δ Marketplace share, Dec 2023 → Dec 2024, pp")
    fig.supylabel("Δ Food share, pp")
    fig.suptitle("Marketplace and Food share co-movement")
    save_figure(fig, output / "figure_h25_marketplace_food")

    fig, axis = plt.subplots(figsize=(9, 5.5))
    for profile in PROFILE_ORDER:
        take = profiles == profile
        axis.scatter(baseline_log_total[take], 100 * primary_market[take], s=10, alpha=.45, label=profile, color=COLORS[profile])
    axis.axhline(0, color="#999", lw=.7); axis.set_xlabel("log Total, Dec 2023"); axis.set_ylabel("Δ Marketplace share, pp")
    axis.set_title("Initial Total and Marketplace-share growth, Dec-to-Dec"); axis.legend(ncol=7, frameon=False)
    save_figure(fig, output / "figure_h26_marketplace_growth_total")

    fig, axis = plt.subplots(figsize=(9, 5))
    axis.plot(pd.to_datetime(months), dispersion.marketplace_index_100, marker="o", ms=3, label="Marketplace-share dispersion")
    axis.plot(pd.to_datetime(months), dispersion.total_index_100, marker="o", ms=3, label="mean log Total dispersion")
    axis.axhline(100, color="#999", lw=.7); axis.set_ylabel("Index, Jan 2023 = 100")
    axis.set_title("Between-profile dispersion: structure versus level"); axis.legend(frameon=False); axis.grid(alpha=.2)
    save_figure(fig, output / "figure_h28_two_convergence_trends")

    fig, axis = plt.subplots(figsize=(10, 5.5))
    axis.scatter(point_data.longitude, point_data.latitude, s=3, color="#b9c0c7", alpha=.5)
    for _, row in distant_examples.iterrows():
        if abs(row.longitude - row.neighbor_longitude) < 100:
            axis.plot([row.longitude, row.neighbor_longitude], [row.latitude, row.neighbor_latitude], color="#d1495b", alpha=.65, lw=1)
    axis.set_xlabel("Longitude"); axis.set_ylabel("Latitude"); axis.set_title("Selected distant neighbors in the December demand graph")
    save_figure(fig, output / "figure_h29_distant_twins")

    primary_food_plot = primary_food_table.loc[PROFILE_ORDER]
    fig, axis = plt.subplots(figsize=(9, 5))
    y = 100 * primary_food_plot.mean_change.to_numpy()
    low = 100 * (primary_food_plot.mean_change - primary_food_plot.mean_ci_low).to_numpy()
    high = 100 * (primary_food_plot.mean_ci_high - primary_food_plot.mean_change).to_numpy()
    axis.bar(PROFILE_ORDER, y, color=[COLORS[p] for p in PROFILE_ORDER])
    axis.errorbar(np.arange(7), y, yerr=np.vstack([low, high]), fmt="none", color="#222", capsize=3)
    axis.axhline(0, color="#333", lw=.8); axis.set_ylabel("Mean Δ Food share, pp")
    axis.set_title("Food share change, Dec 2023 → Dec 2024")
    save_figure(fig, output / "figure_h30_food_share")

    summary = {
        "statuses": statuses,
        "H24": {"ordered_both": ordered_both, "adjusted": adjusted_h24.to_dict("records")},
        "H25": {"primary": primary_sub.reset_index().to_dict("records"), "rho_FG_minus_BD": observed_contrast, "contrast_p": contrast_p},
        "H26": {"primary_spearman": primary_growth.to_dict(), "adjusted": adjusted_h26.iloc[0].to_dict()},
        "H27": pair_summary.iloc[0].to_dict(),
        "H28": dispersion_trend.to_dict("records"),
        "H29": neighbor_summary.to_dict("records"),
        "H30": primary_food_table.reset_index().to_dict("records"),
        "baseline_changed": False, "reference_specification_changed": False, "A_G_status_changed": False,
    }
    write_json(output / cfg["outputs"]["summary"], summary)

    report = build_report(cfg, statuses, volatility_summary, adjusted_h24, pairwise, substitution, substitution_contrast, growth, adjusted_h26, pair_summary, matched_examples, dispersion_trend, neighbor_summary, distant_examples, food_changes)
    (output / cfg["outputs"]["report"]).write_text(report, encoding="utf-8")
    audit = build_audit(cfg, statuses, len(names), len(matched), nodes_below_three)
    (output / cfg["outputs"]["audit"]).write_text(audit, encoding="utf-8")

    after = snapshot(frozen_paths)
    changed = [path for path in before if before[path] != after.get(path)]
    freeze["after"], freeze["changed_paths"] = after, changed
    freeze["final_hash_gate"] = "PASS" if not changed else "FAIL"
    write_json(output / "BASELINE_FREEZE.json", freeze)
    if changed:
        raise RuntimeError(f"frozen Round23 input changed: {changed}")

    manifest = {
        "experiment": cfg["experiment"]["id"], "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_output("rev-parse", "HEAD"), "dirty_worktree": bool(git_output("status", "--short")),
        "config": str(cfg_path).replace("\\", "/"), "config_sha256": sha256(cfg_path),
        "implementation": {"scripts/run_round23_economic_mechanisms.py": sha256(Path(__file__)), "src/sbernet/economic_mechanisms.py": sha256(Path("src/sbernet/economic_mechanisms.py"))},
        "python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__, "sklearn": sklearn.__version__, "networkx": nx.__version__,
        "permutation_reps": reps, "bootstrap_reps": boots, "seed": seed,
        "baseline_reproduction": "PASS", "final_hash_gate": freeze["final_hash_gate"], "runtime_seconds": time.perf_counter() - started,
    }
    write_json(output / cfg["outputs"]["manifest"], manifest)

    evidence_dir = Path("outputs/evidence_v2_10_0")
    evidence_dir.mkdir(exist_ok=True)
    prior_matrix = pd.read_csv(cfg["inputs"]["prior_evidence_matrix"])
    h30_map = primary_food_table.mean_change.to_dict()
    h25_profile = primary_sub.spearman_rho.to_dict()
    prior_matrix["round23_food_share_change_dec_yoy"] = prior_matrix.profile.map(h30_map)
    prior_matrix["round23_marketplace_food_spearman_dec_yoy"] = prior_matrix.profile.map(h25_profile)
    prior_matrix["round23_mechanism_status"] = "additive exploratory; legacy status unchanged"
    matrix_path = evidence_dir / "MASTER_PROFILE_EVIDENCE_MATRIX_v2.10.0.csv"
    prior_matrix.to_csv(matrix_path, index=False)
    evidence_text = build_evidence_update(statuses, summary)
    (evidence_dir / "ROUND23_EVIDENCE_UPDATE.md").write_text(evidence_text, encoding="utf-8")
    write_json(evidence_dir / "run_manifest.json", {"evidence_version": "2.10.0", "round": 23, "source_summary": str(output / cfg["outputs"]["summary"]), "matrix_sha256": sha256(matrix_path), "scientific_status_changes": False})

    checksum_paths = sorted(path for path in output.rglob("*") if path.is_file() and path.name != cfg["outputs"]["checksums"])
    (output / cfg["outputs"]["checksums"]).write_text("".join(f"{sha256(path)}  {path.relative_to(output).as_posix()}\n" for path in checksum_paths), encoding="utf-8")


def build_report(cfg, statuses, volatility, adjusted_h24, pairwise, substitution, substitution_contrast, growth, adjusted_h26, pair_summary, examples, dispersion, neighbor_summary, twins, food_changes) -> str:
    primary_sub = substitution.loc[substitution.change.eq("primary_dec24_minus_dec23")]
    primary_growth = growth.loc[growth.change.eq("primary_dec24_minus_dec23")]
    primary_food = food_changes.loc[food_changes.change.eq("primary_dec24_minus_dec23")]
    return f"""# Round 23 — Economic-mechanism hypothesis checks

## Scope

Seven user-proposed mechanisms were tested under the frozen YAML before results were inspected. This is an additive exploratory round. It does not retune L1, relabel A–G, or establish causality.

## Status summary

{markdown_table(pd.DataFrame([{"hypothesis": key, "status": value} for key, value in statuses.items()]), ["hypothesis", "status"])}

## H24 — Atlas uncertainty and economic volatility

{markdown_table(volatility, ["metric", "atlas_state", "N", "mean", "median", "q25", "q75"], 6)}

Adjusted association after mean log Total, reference profile and region controls:

{markdown_table(adjusted_h24, ["metric", "N", "partial_R2_atlas_state", "permutation_p", "controls"], 6)}

Pairwise tests are Holm-adjusted in `uncertainty_volatility_pairwise.csv`. Atlas classes are methodological diagnostics; association with observed volatility does not prove that uncertainty is economic rather than algorithmic.

## H25 — Marketplace/Food substitution

{markdown_table(primary_sub, ["group", "N", "spearman_rho", "p_holm", "mean_delta_marketplace_share", "mean_delta_food_share", "mean_delta_log_marketplace_food_ratio"], 6)}

FG-minus-BD correlation contrast: {float(substitution_contrast.iloc[0].rho_FG_minus_rho_BD):.4f}; one-sided permutation p={float(substitution_contrast.iloc[0].one_sided_permutation_p):.4f}. A negative closed-composition correlation cannot identify grocery purchases through marketplaces; transaction merchant taxonomy would be required.

## H26 — Marketplace growth and initial Total

{markdown_table(primary_growth, ["group", "N", "spearman_rho", "p_holm"], 6)}

{markdown_table(adjusted_h26, ["N", "log_total_coefficient", "HC3_se", "HC3_p", "partial_R2_log_total", "within_profile_permutation_p", "controls"], 6)}

The association cannot by itself establish absent local retail; baseline share, region and profile are controlled only observationally.

## H27 — Wage/population matched municipalities

{markdown_table(pair_summary, list(pair_summary.columns), 6)}

Selected examples use a declared rule, not manual curation:

{markdown_table(examples.head(10), ["municipality_a", "profile_a", "municipality_b", "profile_b", "wage_relative_difference", "population_relative_difference", "aitchison_dec2024"], 4)}

These pairs illustrate conditional differences; they do not isolate income causally and wages are not household income.

## H28 — Digital convergence without level convergence

{markdown_table(dispersion, ["metric", "theil_sen_slope", "bootstrap_ci_low", "bootstrap_ci_high", "start", "end"], 6)}

`Total` is nominal and its denominator is unresolved. The calculation concerns dispersion in mean log Total, not welfare.

## H29 — Geographically distant network neighbors

{markdown_table(neighbor_summary, list(neighbor_summary.columns), 4)}

{markdown_table(twins.head(10), ["municipality", "profile", "neighbor", "neighbor_profile", "feature_distance", "geographic_km"], 3)}

Representative-point distance is descriptive and does not mean the territories are economically identical.

## H30 — Food-share change by profile

{markdown_table(primary_food, ["profile", "N", "mean_change", "median_change", "mean_ci_low", "mean_ci_high", "p_holm"], 6)}

This tests basket-share movement, not inflation. No price index, real expenditure, quantity, or household-income measure enters the analysis.

## Reproducibility

The fresh baseline gate reproduced full supra, temporal December and static December labels at ARI=NMI=1. Config, municipality-level results, exact pairs, figures, manifest, final hash gate and checksums are saved with this report.
"""


def build_audit(cfg, statuses, panel_n, external_n, nodes_below_three) -> str:
    return f"""# Round23 audit

1. Fresh baseline replay before downstream work: **PASS**.
2. Strict panel: **{panel_n} municipalities × 24 months**.
3. Config frozen before viewing results: **YES**.
4. L1 representation changed: **NO**.
5. Graph, k, omega, resolution or seed changed: **NO**.
6. A–G labels or scientific statuses changed: **NO**.
7. Atlas assignments or thresholds changed: **NO**.
8. External complete wage/population candidates: **{external_n}**.
9. Graph nodes with fewer than three available graph neighbors: **{nodes_below_three}**.
10. Multiplicity: **Holm within each saved hypothesis family**.
11. Permutations: **{cfg['inference']['permutation_reps']}**, seed **{cfg['inference']['seed']}**.
12. Bootstrap repetitions: **{cfg['inference']['bootstrap_reps']}**.
13. Negative results retained: **YES**.
14. Causal marketplace substitution/local-retail claims allowed: **NO**.
15. Inflation claim allowed: **NO; only Food-share movement is observed**.
16. Welfare claim allowed: **NO; Total is nominal and its denominator remains unresolved**.
17. Atlas classes interpreted as probabilities: **NO**.
18. Commit: **NOT DONE**.
19. Push: **NOT DONE**.

Statuses: `{json.dumps(statuses, ensure_ascii=False)}`.
"""


def build_evidence_update(statuses: dict, summary: dict) -> str:
    return f"""# Evidence v2.10.0 — Round23 economic-mechanism checks

Round23 adds seven fixed exploratory diagnostics over frozen L1/A–G/Atlas inputs. It does not alter the reference specification or any legacy profile status.

The exact claim-level statuses are:

{markdown_table(pd.DataFrame([{"hypothesis": key, "status": value} for key, value in statuses.items()]), ["hypothesis", "status"])}

All marketplace, matching and volatility results remain observational. Closed-composition correlations cannot identify purchases of groceries through marketplaces. Nominal Total is not welfare, and Food-share changes are not inflation without prices/quantities. Distant graph neighbors are analogues in the fixed demand-feature graph, not universal economic twins.

Machine-readable statistics are in `outputs/round23_economic_mechanisms/round23_summary.json`; raw tables and figures are preserved beside it. Baseline and final frozen-input gates passed. A–G statuses remain unchanged.
"""


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/round23_economic_mechanisms.yaml")
    args = parser.parse_args()
    main(args.config)
