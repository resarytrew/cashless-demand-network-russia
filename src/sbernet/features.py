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
    representation: str = "reference_6part_clr",
) -> tuple[np.ndarray, pd.DataFrame]:
    """Build one monthly feature matrix for a declared representation.

    ``reference_6part_clr`` deliberately retains the pre-Round18 operations in
    their original order so that the frozen reference remains byte-identical.
    ``observed_5part_clr`` never constructs ``Other``.  ``observed_5levels``
    robust-scales each published category log-level before block scaling.
    """
    pivot = (
        month_df.pivot(index="mo", columns="category_15", values="value")
        .loc[municipality_order]
        .copy()
    )

    if representation == "reference_6part_clr":
        # Keep this branch operationally identical to the historical reference.
        pivot[other_category] = (
            pivot[total_category] - pivot[selected_categories].sum(axis=1)
        )
        parts = selected_categories + [other_category]
        if (pivot[parts] <= 0).any().any():
            raise ValueError("All composition parts must be positive.")
        composition = pivot[parts].div(pivot[total_category], axis=0).to_numpy()
        x_structure = clr(composition)
    elif representation == "observed_5part_clr":
        if (pivot[selected_categories] <= 0).any().any():
            raise ValueError("All observed composition parts must be positive.")
        # CLR is invariant to closure; using observed parts does not assert that
        # they add to Total or exhaust all spending.
        x_structure = clr(pivot[selected_categories].to_numpy(dtype=float))
    elif representation == "observed_5levels":
        if (pivot[selected_categories] <= 0).any().any():
            raise ValueError("All observed category values must be positive.")
        logs = np.log(pivot[selected_categories].to_numpy(dtype=float))
        x_structure = np.column_stack([robust_z(logs[:, j]) for j in range(logs.shape[1])])
    else:
        raise ValueError(f"Unknown representation: {representation}")

    if (pivot[total_category] <= 0).any():
        raise ValueError("Total must be strictly positive.")
    log_total = np.log(pivot[total_category].to_numpy(dtype=float))
    x_level = robust_z(log_total)[:, None]

    structure_scale = _median_pairwise_distance(x_structure)
    level_scale = _median_pairwise_distance(x_level)

    x = np.concatenate(
        [
            np.sqrt(structure_weight) * x_structure / structure_scale,
            np.sqrt(level_weight) * x_level / level_scale,
        ],
        axis=1,
    )
    return x, pivot
