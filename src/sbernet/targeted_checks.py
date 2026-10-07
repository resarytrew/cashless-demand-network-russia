"""Statistical helpers for the fixed Round20 targeted checks."""
from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import pdist
from scipy.stats import chi2, f as f_distribution, kruskal, mannwhitneyu


def _design(frame: pd.DataFrame, region: str, profile: str) -> tuple[np.ndarray, np.ndarray, list[str]]:
    region_dummy = pd.get_dummies(frame[region].astype(str), prefix="region", drop_first=True, dtype=float)
    profile_dummy = pd.get_dummies(frame[profile].astype(str), prefix="profile", drop_first=True, dtype=float)
    reduced = np.column_stack([
        np.ones(len(frame), dtype=float), frame["log_population"].to_numpy(dtype=float),
        region_dummy.to_numpy(dtype=float),
    ])
    return reduced, profile_dummy.to_numpy(dtype=float), profile_dummy.columns.tolist()


def _ols(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray, int]:
    beta = np.linalg.lstsq(x, y, rcond=None)[0]
    residual = y - x @ beta
    return beta, residual, int(np.linalg.matrix_rank(x))


def _f_statistic(reduced_residual: np.ndarray, residualized_profile: np.ndarray, rank_reduced: int) -> tuple[float, float, int, int]:
    n = len(reduced_residual)
    q = int(np.linalg.matrix_rank(residualized_profile))
    if q < 1:
        raise ValueError("profile design has no residual rank after controls")
    coefficient = np.linalg.lstsq(residualized_profile, reduced_residual, rcond=None)[0]
    full_residual = reduced_residual - residualized_profile @ coefficient
    rss_reduced = float(reduced_residual @ reduced_residual)
    rss_full = float(full_residual @ full_residual)
    df_denominator = n - rank_reduced - q
    statistic = ((rss_reduced - rss_full) / q) / (rss_full / df_denominator)
    return float(statistic), float(rss_full), q, df_denominator


def benjamini_hochberg(values: np.ndarray) -> np.ndarray:
    """Return monotone Benjamini–Hochberg adjusted p-values."""
    values = np.asarray(values, dtype=float)
    order = np.argsort(values)
    ranked = values[order]
    adjusted = ranked * len(values) / np.arange(1, len(values) + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    result = np.empty_like(adjusted)
    result[order] = np.minimum(adjusted, 1.0)
    return result


def residual_profile_test(
    frame: pd.DataFrame,
    *,
    outcome: str,
    population: str,
    region: str,
    profile: str,
    permutation_reps: int,
    seed: int,
) -> tuple[pd.DataFrame, dict, pd.DataFrame, pd.DataFrame]:
    """Residualize log outcome on log population and region, then test profiles.

    The global model comparison reports classical partial F, HC3 joint Wald, a
    Freedman–Lane within-region permutation p-value, and Kruskal–Wallis on the
    reduced-model residuals. Pairwise residual contrasts are Mann–Whitney tests
    with Benjamini–Hochberg correction.
    """
    columns = [outcome, population, region, profile]
    data = frame[columns].dropna().copy()
    data = data.loc[(data[outcome] > 0) & (data[population] > 0)].copy()
    data["log_outcome"] = np.log(data[outcome].to_numpy(dtype=float))
    data["log_population"] = np.log(data[population].to_numpy(dtype=float))
    y = data.log_outcome.to_numpy(dtype=float)
    reduced, profile_design, profile_names = _design(data, region, profile)
    beta_reduced, residual, rank_reduced = _ols(reduced, y)
    q_matrix, _ = np.linalg.qr(reduced, mode="reduced")
    residualized_profile = profile_design - q_matrix @ (q_matrix.T @ profile_design)
    f_stat, rss_full, q, df_denominator = _f_statistic(
        residual, residualized_profile, rank_reduced
    )
    rss_reduced = float(residual @ residual)

    full = np.column_stack([reduced, profile_design])
    beta_full, full_residual, rank_full = _ols(full, y)
    xtx_inverse = np.linalg.pinv(full.T @ full)
    leverage = np.sum((full @ xtx_inverse) * full, axis=1)
    if np.any(leverage >= 1):
        raise ValueError("HC3 undefined because leverage reached one")
    hc3_score = full * (full_residual / (1.0 - leverage))[:, None]
    covariance = xtx_inverse @ (hc3_score.T @ hc3_score) @ xtx_inverse
    profile_slice = slice(reduced.shape[1], full.shape[1])
    profile_beta = beta_full[profile_slice]
    profile_covariance = covariance[profile_slice, profile_slice]
    wald = float(profile_beta @ np.linalg.pinv(profile_covariance) @ profile_beta)
    wald_df = int(np.linalg.matrix_rank(profile_covariance))

    rng = np.random.default_rng(seed)
    region_indices = [indices for _, indices in data.groupby(region, sort=True).indices.items()]
    null_f = np.empty(permutation_reps, dtype=float)
    for rep in range(permutation_reps):
        permuted = residual.copy()
        for indices in region_indices:
            permuted[indices] = rng.permutation(permuted[indices])
        permuted = permuted - q_matrix @ (q_matrix.T @ permuted)
        null_f[rep] = _f_statistic(permuted, residualized_profile, rank_reduced)[0]
    permutation_p = float((1 + np.count_nonzero(null_f >= f_stat)) / (permutation_reps + 1))

    data["residual"] = residual
    groups = [group.residual.to_numpy() for _, group in data.groupby(profile, sort=True)]
    h_stat, h_p = kruskal(*groups)
    k = len(groups)
    epsilon_squared = max(0.0, float((h_stat - k + 1) / (len(data) - k)))
    diagnostics = {
        "outcome": outcome,
        "n": len(data),
        "regions": int(data[region].nunique()),
        "profiles": int(data[profile].nunique()),
        "beta_log_population": float(beta_reduced[1]),
        "reduced_R2": float(1.0 - rss_reduced / np.sum((y - y.mean()) ** 2)),
        "partial_F": f_stat,
        "partial_F_df_num": q,
        "partial_F_df_den": df_denominator,
        "partial_F_p": float(f_distribution.sf(f_stat, q, df_denominator)),
        "partial_R2_profile": float((rss_reduced - rss_full) / rss_reduced),
        "HC3_Wald_chi2": wald,
        "HC3_Wald_df": wald_df,
        "HC3_Wald_p": float(chi2.sf(wald, wald_df)),
        "Freedman_Lane_within_region_reps": permutation_reps,
        "Freedman_Lane_within_region_p": permutation_p,
        "Kruskal_H_residual": float(h_stat),
        "Kruskal_p_residual": float(h_p),
        "Kruskal_epsilon_squared": epsilon_squared,
        "rank_reduced": rank_reduced,
        "rank_full": rank_full,
    }
    summary = data.groupby(profile).residual.agg(["count", "mean", "median", "std"]).reset_index()
    summary.insert(0, "outcome", outcome)
    pair_rows = []
    for left, right in combinations(sorted(data[profile].unique()), 2):
        a = data.loc[data[profile].eq(left), "residual"].to_numpy()
        b = data.loc[data[profile].eq(right), "residual"].to_numpy()
        statistic, p_value = mannwhitneyu(a, b, alternative="two-sided", method="auto")
        pair_rows.append({
            "outcome": outcome, "profile_a": left, "profile_b": right,
            "n_a": len(a), "n_b": len(b), "median_difference_a_minus_b": float(np.median(a) - np.median(b)),
            "U": float(statistic), "p_value": float(p_value),
        })
    pairs = pd.DataFrame(pair_rows)
    pairs["p_BH"] = benjamini_hochberg(pairs.p_value.to_numpy())
    residual_output = data[[outcome, population, region, profile, "log_outcome", "log_population", "residual"]]
    return residual_output, diagnostics, summary, pairs


def optimal_label_alignment(reference: np.ndarray, candidate: np.ndarray) -> tuple[np.ndarray, dict[int, int], float]:
    """One-to-one maximum-overlap alignment for a transparent change-share diagnostic."""
    reference = np.asarray(reference)
    candidate = np.asarray(candidate)
    if reference.shape != candidate.shape or reference.ndim != 1:
        raise ValueError("reference and candidate labels must be equal-length vectors")
    ref_values = np.unique(reference)
    candidate_values = np.unique(candidate)
    contingency = np.zeros((len(ref_values), len(candidate_values)), dtype=int)
    for i, left in enumerate(ref_values):
        for j, right in enumerate(candidate_values):
            contingency[i, j] = int(np.sum((reference == left) & (candidate == right)))
    row, column = linear_sum_assignment(-contingency)
    mapping = {int(candidate_values[j]): int(ref_values[i]) for i, j in zip(row, column)}
    unmatched_start = int(ref_values.max()) + 1
    for value in candidate_values:
        if int(value) not in mapping:
            mapping[int(value)] = unmatched_start
            unmatched_start += 1
    aligned = np.array([mapping[int(value)] for value in candidate], dtype=int)
    match_share = float(np.mean(aligned == reference))
    return aligned, mapping, match_share


def distance_contribution_table(
    blocks: dict[str, np.ndarray],
    *,
    scope: str,
    pairs: np.ndarray | None = None,
    quantiles: tuple[float, ...] = (0.05, 0.25, 0.50, 0.75, 0.95),
) -> pd.DataFrame:
    """Decompose exact squared Euclidean distance into named coordinate blocks."""
    if not blocks:
        raise ValueError("at least one block is required")
    n = len(next(iter(blocks.values())))
    if any(np.asarray(block).ndim != 2 or len(block) != n for block in blocks.values()):
        raise ValueError("all blocks must be 2D and share the same row count")
    contributions = {}
    for name, block in blocks.items():
        block = np.asarray(block, dtype=float)
        if not np.isfinite(block).all():
            raise ValueError("distance blocks must be finite")
        if pairs is None:
            contributions[name] = pdist(block, metric="sqeuclidean")
        else:
            pairs = np.asarray(pairs, dtype=int)
            contributions[name] = np.sum((block[pairs[:, 0]] - block[pairs[:, 1]]) ** 2, axis=1)
    total = np.sum(np.vstack(list(contributions.values())), axis=0)
    valid = total > 0
    if not np.any(valid):
        raise ValueError("all evaluated distances are zero")
    rows = []
    for name, squared in contributions.items():
        share = squared[valid] / total[valid]
        row = {
            "scope": scope, "block": name, "pairs_n": int(valid.sum()),
            "mean_squared_distance": float(np.mean(squared[valid])),
            "mean_share": float(np.mean(share)), "median_share": float(np.median(share)),
        }
        row.update({f"share_q{int(q * 100):02d}": float(np.quantile(share, q)) for q in quantiles})
        rows.append(row)
    result = pd.DataFrame(rows)
    if not np.isclose(result.mean_share.sum(), 1.0):
        raise RuntimeError("mean distance shares do not sum to one")
    return result
