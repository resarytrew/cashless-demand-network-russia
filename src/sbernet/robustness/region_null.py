from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist, squareform

ARCHETYPE_MAP = {1: "A", 3: "B", 7: "C", 8: "D", 9: "E", 10: "F", 11: "G"}
PARTS = ["food", "health", "catering", "marketplace", "transport", "other"]


def admin_form(name: str) -> str:
    x = name.lower()
    if "внутригородская территория города федерального значения" in x:
        return "federal_intracity"
    if "муниципальный район" in x:
        return "municipal_raion"
    if "муниципальный округ" in x:
        return "municipal_okrug"
    if "городской округ" in x:
        return "urban_okrug"
    return "other"


def baseline_feature_matrix(dec: pd.DataFrame, structure_weight: float = 0.7) -> np.ndarray:
    level_weight = 1.0 - structure_weight
    composition = dec[PARTS].to_numpy(dtype=float)
    if np.any(composition <= 0):
        raise ValueError("CLR requires strictly positive composition parts")
    logx = np.log(composition)
    clr = logx - logx.mean(axis=1, keepdims=True)
    level = dec["level_z"].to_numpy(dtype=float)[:, None]

    structure_scale = float(np.median(pdist(clr)))
    level_scale = float(np.median(pdist(level)))
    return np.concatenate(
        [
            np.sqrt(structure_weight) * clr / structure_scale,
            np.sqrt(level_weight) * level / level_scale,
        ],
        axis=1,
    )


def mean_within_distance(distance_matrix: np.ndarray, indices: np.ndarray) -> float:
    sub = distance_matrix[np.ix_(indices, indices)]
    return float(sub[np.triu_indices(len(indices), 1)].mean())


def expected_mean_distance_stratified(
    distance_matrix: np.ndarray,
    strata: np.ndarray,
    sample_indices: np.ndarray,
) -> float:
    """Exact null expectation preserving the sample count in every stratum.

    This computes the expected mean pairwise distance under uniform sampling
    without replacement independently inside each stratum. It is exact for the
    null mean; it does not provide an exact variance.
    """
    strata = np.asarray(strata)
    sample_indices = np.asarray(sample_indices, dtype=int)
    sample_counts = Counter(strata[sample_indices])

    candidates: dict[str, list[int]] = defaultdict(list)
    for idx, stratum in enumerate(strata):
        candidates[stratum].append(idx)

    labels = list(sample_counts)
    weighted_sum = 0.0
    total_pairs = 0

    for pos, left in enumerate(labels):
        n_left = sample_counts[left]
        i_left = np.asarray(candidates[left], dtype=int)

        if n_left >= 2:
            within = distance_matrix[np.ix_(i_left, i_left)]
            mu = float(within[np.triu_indices(len(i_left), 1)].mean())
            pairs = n_left * (n_left - 1) // 2
            weighted_sum += pairs * mu
            total_pairs += pairs

        for right in labels[pos + 1 :]:
            n_right = sample_counts[right]
            i_right = np.asarray(candidates[right], dtype=int)
            mu = float(distance_matrix[np.ix_(i_left, i_right)].mean())
            pairs = n_left * n_right
            weighted_sum += pairs * mu
            total_pairs += pairs

    return weighted_sum / total_pairs


def monte_carlo_stratified(
    x: np.ndarray,
    strata: np.ndarray,
    sample_indices: np.ndarray,
    observed: float,
    draws: int,
    seed: int,
) -> dict[str, float]:
    strata = np.asarray(strata)
    counts = Counter(strata[sample_indices])
    candidates = {s: np.flatnonzero(strata == s) for s in counts}
    items = sorted(counts.items(), key=lambda item: item[0])
    rng = np.random.default_rng(seed)
    values = np.empty(draws, dtype=float)

    for draw in range(draws):
        pieces = []
        for stratum, n in items:
            pool = candidates[stratum]
            chosen = pool if n == len(pool) else rng.choice(pool, size=n, replace=False)
            pieces.append(chosen)
        sampled = np.concatenate(pieces)
        values[draw] = float(pdist(x[sampled]).mean())

    return {
        "mc_draws": draws,
        "mc_null_mean": float(values.mean()),
        "mc_null_sd": float(values.std(ddof=1)),
        "mc_q025": float(np.quantile(values, 0.025)),
        "mc_median": float(np.quantile(values, 0.5)),
        "mc_q975": float(np.quantile(values, 0.975)),
        "empirical_lower_tail_p": float((1 + np.sum(values <= observed)) / (draws + 1)),
    }


def run_region_admin_null(
    economic_space_points: str | Path,
    crosswalk: str | Path,
    output_csv: str | Path,
    period: str = "2024-12-01",
    structure_weight: float = 0.7,
    draws: int = 3000,
    seed: int = 20260918,
) -> pd.DataFrame:
    econ = pd.read_csv(economic_space_points)
    cross = pd.read_csv(crosswalk, dtype=str)

    dec = econ[econ["period"].eq(period)].copy()
    if len(dec) != 1904 or dec["mo"].nunique() != 1904:
        raise ValueError("Expected the strict 1904-municipality Dec-2024 panel")

    dec = dec.merge(
        cross[["sber_name", "subject_name_2024", "resolution_tier"]],
        left_on="mo",
        right_on="sber_name",
        how="left",
        validate="one_to_one",
    )
    if dec["subject_name_2024"].isna().any():
        raise ValueError("Crosswalk is missing subject_name_2024 values")

    dec["admin_form"] = dec["mo"].map(admin_form)
    x = baseline_feature_matrix(dec, structure_weight=structure_weight)
    distances = squareform(pdist(x))

    admin = dec["admin_form"].astype(str).to_numpy()
    region = dec["subject_name_2024"].astype(str).to_numpy()
    joint = (dec["subject_name_2024"].astype(str) + "||" + dec["admin_form"].astype(str)).to_numpy()

    rows = []
    for cluster, archetype in ARCHETYPE_MAP.items():
        idx = np.flatnonzero(dec["cluster"].to_numpy() == cluster)
        observed = mean_within_distance(distances, idx)
        admin_null = expected_mean_distance_stratified(distances, admin, idx)
        region_null = expected_mean_distance_stratified(distances, region, idx)
        joint_null = expected_mean_distance_stratified(distances, joint, idx)
        mc = monte_carlo_stratified(
            x=x,
            strata=joint,
            sample_indices=idx,
            observed=observed,
            draws=draws,
            seed=seed + cluster,
        )

        region_counts = dec.iloc[idx]["subject_name_2024"].value_counts()
        rows.append(
            {
                "archetype": archetype,
                "n": len(idx),
                "observed_mean_within_distance": observed,
                "admin_null_mean": admin_null,
                "ratio_vs_admin_null": observed / admin_null,
                "region_null_mean": region_null,
                "ratio_vs_region_null": observed / region_null,
                "region_admin_null_mean": joint_null,
                "ratio_vs_region_admin_null": observed / joint_null,
                "n_subjects": int(region_counts.size),
                "largest_subject": str(region_counts.index[0]),
                "largest_subject_share": float(region_counts.iloc[0] / len(idx)),
                "top3_subject_share": float(region_counts.iloc[:3].sum() / len(idx)),
                **mc,
            }
        )

    result = pd.DataFrame(rows)
    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_csv, index=False)
    return result
