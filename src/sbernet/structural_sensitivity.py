"""Formal structural-sensitivity and adjusted-validation helpers for Round21."""
from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact, mannwhitneyu, norm
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

from .dual_lens import median_distance_scale


def contingency(reference: np.ndarray, candidate: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    reference, candidate = np.asarray(reference), np.asarray(candidate)
    if reference.ndim != 1 or reference.shape != candidate.shape:
        raise ValueError("partitions must be equal-length vectors")
    r, ri = np.unique(reference, return_inverse=True)
    c, ci = np.unique(candidate, return_inverse=True)
    table = np.zeros((len(r), len(c)), dtype=np.int64)
    np.add.at(table, (ri, ci), 1)
    return r, c, table


def crosswalk_table(reference: np.ndarray, candidate: np.ndarray) -> pd.DataFrame:
    """Return one row per reference group with transparent destination statistics."""
    r, c, table = contingency(reference, candidate)
    rows = []
    for label, counts in zip(r, table):
        order = np.argsort(-counts, kind="stable")
        positive = order[counts[order] > 0]
        total = int(counts.sum())
        probabilities = counts[counts > 0] / total
        rows.append({
            "reference_cluster": int(label), "size": total,
            "dominant_candidate_cluster": int(c[positive[0]]),
            "dominant_count": int(counts[positive[0]]),
            "retention": float(counts[positive[0]] / total),
            "second_candidate_cluster": int(c[positive[1]]) if len(positive) > 1 else None,
            "second_share": float(counts[positive[1]] / total) if len(positive) > 1 else 0.0,
            "destination_entropy_bits": float(-(probabilities * np.log2(probabilities)).sum()),
            "destination_count": int(len(positive)),
        })
    return pd.DataFrame(rows)


def nestedness_metrics(reference: np.ndarray, candidate: np.ndarray, thresholds=(0.90, 0.95, 0.99)) -> dict:
    crosswalk = crosswalk_table(reference, candidate)
    retention = crosswalk.retention.to_numpy()
    weights = crosswalk["size"].to_numpy()
    result = {
        "N": int(weights.sum()), "reference_K": len(weights),
        "candidate_K": int(np.unique(candidate).size),
        "micro_purity": float(np.average(retention, weights=weights)),
        "macro_purity": float(retention.mean()),
        "weighted_macro_purity": float(np.average(retention, weights=weights)),
        "minimum_retention": float(retention.min()),
    }
    result.update({f"fine_cluster_share_retention_ge_{value:.2f}": float(np.mean(retention >= value)) for value in thresholds})
    return result


def pairwise_agreement(reference: np.ndarray, candidate: np.ndarray) -> dict:
    """Pair retention/precision from contingency counts, without O(N^2) loops."""
    _, _, table = contingency(reference, candidate)
    choose2 = lambda x: x * (x - 1) // 2
    intersection = int(choose2(table).sum())
    fine_pairs = int(choose2(table.sum(axis=1)).sum())
    coarse_pairs = int(choose2(table.sum(axis=0)).sum())
    return {
        "same_pair_intersection": intersection, "fine_same_pairs": fine_pairs,
        "coarse_same_pairs": coarse_pairs,
        "fine_pair_retention": float(intersection / fine_pairs) if fine_pairs else None,
        "coarse_pair_precision": float(intersection / coarse_pairs) if coarse_pairs else None,
    }


def information_decomposition(reference: np.ndarray, candidate: np.ndarray) -> dict:
    """Conditional entropies and variation of information in bits."""
    _, _, table = contingency(reference, candidate)
    joint = table / table.sum()
    pr, pc = joint.sum(axis=1), joint.sum(axis=0)
    entropy = lambda p: float(-(p[p > 0] * np.log2(p[p > 0])).sum())
    h_ref, h_candidate, h_joint = entropy(pr), entropy(pc), entropy(joint.ravel())
    h_candidate_given_ref = h_joint - h_ref
    h_ref_given_candidate = h_joint - h_candidate
    vi = h_candidate_given_ref + h_ref_given_candidate
    return {
        "units": "bits", "H_reference": h_ref, "H_candidate": h_candidate,
        "H_candidate_given_reference": h_candidate_given_ref,
        "H_reference_given_candidate": h_ref_given_candidate, "VI": vi,
        "VI_normalized_by_log2_N": float(vi / np.log2(table.sum())) if table.sum() > 1 else 0.0,
    }


def structural_metrics(reference: np.ndarray, candidate: np.ndarray) -> dict:
    return {
        "ARI": float(adjusted_rand_score(reference, candidate)),
        "NMI": float(normalized_mutual_info_score(reference, candidate)),
        **nestedness_metrics(reference, candidate),
        **pairwise_agreement(reference, candidate),
        **information_decomposition(reference, candidate),
    }


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if total <= 0:
        return np.nan, np.nan
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = z * np.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return float(center - half), float(center + half)


def atlas_state_table(frame: pd.DataFrame, reference_col: str, candidate_col: str, state_col: str, changed_col: str) -> pd.DataFrame:
    rows = []
    for state, group in frame.groupby(state_col, sort=True):
        n, changed = len(group), int(group[changed_col].sum())
        lower, upper = wilson_interval(changed, n)
        nested = nestedness_metrics(group[reference_col].to_numpy(), group[candidate_col].to_numpy())
        pair = pairwise_agreement(group[reference_col].to_numpy(), group[candidate_col].to_numpy())
        rows.append({"stability_class": state, "N": n, "changed_n": changed,
                     "changed_share": changed / n, "changed_wilson95_low": lower,
                     "changed_wilson95_high": upper,
                     "ARI_within_state": float(adjusted_rand_score(group[reference_col], group[candidate_col])),
                     "dominant_destination_purity": nested["micro_purity"], **pair})
    return pd.DataFrame(rows)


def risk_ratio(frame: pd.DataFrame, state_col: str, changed_col: str, exposed: str, baseline: str) -> dict:
    a = int(frame.loc[frame[state_col].eq(exposed), changed_col].sum())
    n1 = int(frame[state_col].eq(exposed).sum())
    c = int(frame.loc[frame[state_col].eq(baseline), changed_col].sum())
    n0 = int(frame[state_col].eq(baseline).sum())
    if min(a, c, n1, n0) <= 0:
        return {"risk_ratio": None, "ci95_low": None, "ci95_high": None, "fisher_p": None}
    rr = (a / n1) / (c / n0)
    se = np.sqrt(1 / a - 1 / n1 + 1 / c - 1 / n0)
    odds_p = fisher_exact([[a, n1 - a], [c, n0 - c]], alternative="two-sided").pvalue
    return {"exposed": exposed, "baseline": baseline, "risk_ratio": float(rr),
            "ci95_low": float(np.exp(np.log(rr) - 1.959963984540054 * se)),
            "ci95_high": float(np.exp(np.log(rr) + 1.959963984540054 * se)),
            "fisher_p": float(odds_p), "exposed_changed": a, "exposed_N": n1,
            "baseline_changed": c, "baseline_N": n0}


def model_matrices(frame: pd.DataFrame, population: str, region: str, profile: str):
    data = frame.copy()
    data["log_population"] = np.log(data[population].to_numpy(dtype=float))
    region_dummies = pd.get_dummies(data[region].astype(str), prefix="region", drop_first=True, dtype=float)
    profile_dummies = pd.get_dummies(data[profile].astype(str), prefix="profile", drop_first=True, dtype=float)
    reduced_names = ["intercept", "log_population", *region_dummies.columns.tolist()]
    reduced = np.column_stack([np.ones(len(data)), data.log_population, region_dummies.to_numpy()])
    full = np.column_stack([reduced, profile_dummies.to_numpy()])
    return data, reduced, full, reduced_names + profile_dummies.columns.tolist(), profile_dummies.columns.tolist()


def _fit(x: np.ndarray, y: np.ndarray):
    beta = np.linalg.lstsq(x, y, rcond=None)[0]
    residual = y - x @ beta
    return beta, residual, int(np.linalg.matrix_rank(x))


def _incremental_stat(reduced: np.ndarray, full: np.ndarray, y: np.ndarray):
    _, er, rr = _fit(reduced, y); _, ef, rf = _fit(full, y)
    ssr, ssf = float(np.sum(er * er)), float(np.sum(ef * ef))
    q, df = rf - rr, len(y) - rf
    statistic = ((ssr - ssf) / q) / (ssf / df)
    return statistic, ssr, ssf, q, df, er, ef


def adjusted_scalar_test(frame: pd.DataFrame, outcome: str, population: str, region: str, profile: str,
                         reps: int, seed: int) -> tuple[dict, pd.DataFrame, dict]:
    data = frame[[outcome, population, region, profile]].dropna().copy()
    data = data.loc[(data[outcome] > 0) & (data[population] > 0)].reset_index(drop=True)
    data, reduced, full, names, profile_names = model_matrices(data, population, region, profile)
    y = np.log(data[outcome].to_numpy(dtype=float))
    observed, ssr, ssf, q, df, er, ef = _incremental_stat(reduced, full, y)
    beta, _, _ = _fit(full, y)
    inv = np.linalg.pinv(full.T @ full)
    leverage = np.sum((full @ inv) * full, axis=1)
    score = full * (ef / (1 - leverage))[:, None]
    covariance = inv @ (score.T @ score) @ inv
    se = np.sqrt(np.diag(covariance)); z = beta / se
    coefficients = pd.DataFrame({"outcome": outcome, "term": names, "coefficient": beta,
                                 "HC3_SE": se, "z": z, "HC3_p": 2 * norm.sf(np.abs(z))})
    profile_idx = [names.index(name) for name in profile_names]
    b = beta[profile_idx]; cov = covariance[np.ix_(profile_idx, profile_idx)]
    wald = float(b @ np.linalg.pinv(cov) @ b)
    q_reduced, _ = np.linalg.qr(reduced, mode="reduced")
    fitted = y - er; groups = list(data.groupby(region, sort=True).indices.values())
    rng = np.random.default_rng(seed); null = np.empty(reps)
    for i in range(reps):
        perm = er.copy()
        for indices in groups: perm[indices] = rng.permutation(perm[indices])
        null[i] = _incremental_stat(reduced, full, fitted + perm)[0]
    exceed = int(np.count_nonzero(null >= observed))
    result = {"outcome": outcome, "formula_reduced": f"log({outcome}) ~ log({population}) + region_FE",
              "formula_full": f"log({outcome}) ~ log({population}) + region_FE + profile_A_to_G",
              "reference_profile_dummy": sorted(data[profile].unique())[0], "coding": "treatment_drop_first",
              "N": len(data), "missing_or_nonpositive_excluded": len(frame) - len(data),
              "regions": int(data[region].nunique()), "profile_df": q, "residual_df": df,
              "SSE_reduced": ssr, "SSE_full": ssf, "partial_R2": (ssr - ssf) / ssr,
              "incremental_F": observed, "HC3_joint_Wald_chi2": wald,
              "HC3_joint_p": float(__import__('scipy').stats.chi2.sf(wald, q)),
              "permutations": reps, "permutation_exceedances": exceed,
              "Freedman_Lane_p": (1 + exceed) / (1 + reps), "seed": seed}
    null_summary = {"outcome": outcome, "minimum": float(null.min()), "q05": float(np.quantile(null, .05)),
                    "median": float(np.median(null)), "q95": float(np.quantile(null, .95)),
                    "maximum": float(null.max()), "mean": float(null.mean()), "SD": float(null.std(ddof=1))}
    return result, coefficients, null_summary


def sector_clr(frame: pd.DataFrame, sectors: list[str]) -> tuple[pd.DataFrame, np.ndarray]:
    data = frame.dropna(subset=sectors, how="all").copy()
    values = data[sectors].fillna(0.0).to_numpy(dtype=float)
    keep = values.sum(axis=1) > 0; data, values = data.loc[keep].reset_index(drop=True), values[keep]
    values /= values.sum(axis=1, keepdims=True)
    positive_min = np.where(values > 0, values, np.inf).min(axis=1)
    values = np.where(values > 0, values, positive_min[:, None] * .5)
    values /= values.sum(axis=1, keepdims=True)
    logged = np.log(values); return data, logged - logged.mean(axis=1, keepdims=True)


def adjusted_multivariate_test(frame: pd.DataFrame, y: np.ndarray, population: str, region: str, profile: str,
                               reps: int, seed: int) -> tuple[dict, dict]:
    data, reduced, full, _, profile_names = model_matrices(frame, population, region, profile)
    observed, ssr, ssf, q, df, er, _ = _incremental_stat(reduced, full, y)
    fitted = y - er; groups = list(data.groupby(region, sort=True).indices.values())
    rng = np.random.default_rng(seed); null = np.empty(reps)
    for i in range(reps):
        perm = er.copy()
        for indices in groups: perm[indices] = rng.permutation(perm[indices])
        null[i] = _incremental_stat(reduced, full, fitted + perm)[0]
    exceed = int(np.count_nonzero(null >= observed))
    result = {"model": "sector_CLR multivariate linear model", "N": len(data), "dimensions": y.shape[1],
              "regions": int(data[region].nunique()), "reference_profile_dummy": sorted(data[profile].unique())[0],
              "profile_terms": ";".join(profile_names), "SSE_trace_reduced": ssr, "SSE_trace_full": ssf,
              "incremental_explained_SS": ssr - ssf, "partial_R2": (ssr - ssf) / ssr,
              "pseudo_F": observed, "profile_df": q, "residual_df": df, "permutations": reps,
              "permutation_exceedances": exceed, "permutation_p": (1 + exceed) / (1 + reps), "seed": seed}
    summary = {"minimum": float(null.min()), "q05": float(np.quantile(null, .05)),
               "median": float(np.median(null)), "q95": float(np.quantile(null, .95)),
               "maximum": float(null.max()), "mean": float(null.mean()), "SD": float(null.std(ddof=1))}
    return result, summary


def cliffs_delta(a: np.ndarray, b: np.ndarray) -> float:
    statistic = mannwhitneyu(a, b, alternative="two-sided", method="auto").statistic
    return float(2 * statistic / (len(a) * len(b)) - 1)


def bootstrap_cliffs_delta(a: np.ndarray, b: np.ndarray, reps: int, seed: int) -> tuple[float, float]:
    rng = np.random.default_rng(seed); values = np.empty(reps)
    for i in range(reps):
        values[i] = cliffs_delta(rng.choice(a, len(a), replace=True), rng.choice(b, len(b), replace=True))
    return float(np.quantile(values, .025)), float(np.quantile(values, .975))


def bh(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float); order = np.argsort(values); ranked = values[order]
    adjusted = np.minimum.accumulate((ranked * len(values) / np.arange(1, len(values) + 1))[::-1])[::-1]
    result = np.empty_like(adjusted); result[order] = np.minimum(adjusted, 1); return result


def scalar_merge_tests(frame: pd.DataFrame, groups: dict[str, list[str]], outcomes: list[str], profile: str,
                       reps: int, seed: int) -> pd.DataFrame:
    rows = []
    for family, labels in groups.items():
        start = len(rows)
        for left, right in combinations(labels, 2):
            for outcome in outcomes:
                a = np.log(frame.loc[frame[profile].eq(left) & frame[outcome].gt(0), outcome].dropna().to_numpy())
                b = np.log(frame.loc[frame[profile].eq(right) & frame[outcome].gt(0), outcome].dropna().to_numpy())
                u, p = mannwhitneyu(a, b, alternative="two-sided", method="auto")
                delta = cliffs_delta(a, b); low, high = bootstrap_cliffs_delta(a, b, reps, seed)
                pooled_mad = np.median(np.abs(np.r_[a, b] - np.median(np.r_[a, b]))) * 1.4826
                rows.append({"analysis_type": "pairwise", "analysis_family": family, "profile_a": left, "profile_b": right,
                             "variable": f"log_{outcome}", "n_a": len(a), "n_b": len(b),
                             "median_a": float(np.median(a)), "median_b": float(np.median(b)),
                             "robust_median_difference_over_pooled_MAD": float((np.median(a)-np.median(b))/pooled_mad),
                             "cliffs_delta": delta, "cliffs_delta_ci95_low": low,
                             "cliffs_delta_ci95_high": high, "Mann_Whitney_U": float(u), "p": float(p)})
        family_rows = rows[start:]
        adjusted = bh(np.array([row["p"] for row in family_rows]))
        for row, value in zip(family_rows, adjusted): row["p_BH_within_family"] = float(value)
    return pd.DataFrame(rows)


def scalar_merge_omnibus(frame: pd.DataFrame, groups: dict[str, list[str]], outcomes: list[str], profile: str) -> pd.DataFrame:
    """Kruskal omnibus diagnostics for each predeclared merge family."""
    from scipy.stats import kruskal
    rows = []
    for family, labels in groups.items():
        for outcome in outcomes:
            samples = [np.log(frame.loc[frame[profile].eq(label) & frame[outcome].gt(0), outcome].dropna().to_numpy()) for label in labels]
            statistic, p = kruskal(*samples); n, k = sum(map(len, samples)), len(samples)
            rows.append({"analysis_type":"omnibus","analysis_family":family,"profile_a":"/".join(labels),"profile_b":"",
                         "variable":f"log_{outcome}","n_a":n,"n_b":0,"K_groups":k,"Kruskal_H":float(statistic),
                         "Kruskal_epsilon_squared":max(0.0,float((statistic-k+1)/(n-k))),"p":float(p),
                         "p_BH_within_family":float(p)})
    return pd.DataFrame(rows)


def multivariate_permutation(y: np.ndarray, labels: np.ndarray, reps: int, seed: int) -> dict:
    labels = np.asarray(labels); values = np.unique(labels)
    if len(values) < 2: raise ValueError("multivariate test requires at least two labels")
    grand = y.mean(axis=0); total = float(np.sum((y - grand) ** 2))
    def statistic(z):
        between = sum(np.sum(z == value) * float(np.sum((y[z == value].mean(axis=0)-grand)**2)) for value in values)
        within = total - between
        return (between / (len(values)-1)) / (within / (len(y)-len(values))), between / total
    observed, effect = statistic(labels); rng = np.random.default_rng(seed)
    null = np.array([statistic(rng.permutation(labels))[0] for _ in range(reps)])
    exceed = int(np.count_nonzero(null >= observed))
    return {"pseudo_F": observed, "R2": effect, "permutations": reps, "exceedances": exceed,
            "p": (1 + exceed) / (1 + reps)}


pairwise_multivariate_permutation = multivariate_permutation


def scale_semantic_blocks(blocks: dict[str, np.ndarray], weights: dict[str, float]):
    """Median-distance-normalize semantic blocks and apply fixed squared-distance weights."""
    if set(blocks) != set(weights) or not np.isclose(sum(weights.values()), 1):
        raise ValueError("block names must match and weights must sum to one")
    coordinates, scales = {}, {}
    for name, block in blocks.items():
        normalized, scale = median_distance_scale(block)
        coordinates[name] = np.sqrt(float(weights[name])) * normalized
        scales[name] = scale
    return coordinates, scales
