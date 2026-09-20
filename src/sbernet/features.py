from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist


def clr(composition: np.ndarray) -> np.ndarray:
    if np.any(composition <= 0):
        raise ValueError("CLR requires strictly positive composition parts.")
    logx = np.log(composition)
    return logx - logx.mean(axis=1, keepdims=True)


def robust_z(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    median = np.median(values)
    mad = np.median(np.abs(values - median))
    scale = 1.4826 * mad
    if scale == 0:
        raise ValueError("MAD is zero; robust z-score is undefined.")
    return (values - median) / scale


def _median_pairwise_distance(x: np.ndarray) -> float:
    d = pdist(x)
    if len(d) == 0:
        raise ValueError("Need at least two rows.")
    value = float(np.median(d))
    if value <= 0:
        raise ValueError("Median pairwise distance must be positive.")
    return value


def monthly_feature_matrix(
    month_df: pd.DataFrame,
    municipality_order: list[str],
    total_category: str,
    selected_categories: list[str],
    other_category: str,
    structure_weight: float,
    level_weight: float,
) -> tuple[np.ndarray, pd.DataFrame]:
    pivot = (
        month_df.pivot(index="mo", columns="category_15", values="value")
        .loc[municipality_order]
        .copy()
    )

    pivot[other_category] = (
        pivot[total_category] - pivot[selected_categories].sum(axis=1)
    )

    parts = selected_categories + [other_category]
    if (pivot[parts] <= 0).any().any():
        raise ValueError("All composition parts must be positive.")

    composition = pivot[parts].div(pivot[total_category], axis=0).to_numpy()
    x_clr = clr(composition)

    log_total = np.log(pivot[total_category].to_numpy(dtype=float))
    x_level = robust_z(log_total)[:, None]

    structure_scale = _median_pairwise_distance(x_clr)
    level_scale = _median_pairwise_distance(x_level)

    x = np.concatenate(
        [
            np.sqrt(structure_weight) * x_clr / structure_scale,
            np.sqrt(level_weight) * x_level / level_scale,
        ],
        axis=1,
    )
    return x, pivot
