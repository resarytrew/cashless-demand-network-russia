"""Explicit non-reference feature representations for fixed sensitivity runs."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .config import load_config
from .features import _median_pairwise_distance, clr, robust_z
from .io import build_strict_panel, read_semicolon_zip
from .pipeline import _prepare


def _alternative_monthly_matrix(month_df: pd.DataFrame, names: list[str], cfg: dict, representation: str) -> np.ndarray:
    pivot = month_df.pivot(index="mo", columns="category_15", values="value").loc[names].copy()
    selected = cfg["panel"]["selected_categories"]
    total_category = cfg["panel"]["total_category"]
    if (pivot[selected] <= 0).any().any() or (pivot[total_category] <= 0).any():
        raise ValueError("Alternative representations require positive observed categories and Total")
    if representation == "observed_5part_clr":
        structure = clr(pivot[selected].to_numpy(dtype=float))
    elif representation == "observed_5levels":
        logs = np.log(pivot[selected].to_numpy(dtype=float))
        structure = np.column_stack([robust_z(logs[:, column]) for column in range(logs.shape[1])])
    else:
        raise ValueError(f"Unknown alternative representation: {representation}")
    level = robust_z(np.log(pivot[total_category].to_numpy(dtype=float)))[:, None]
    return np.concatenate([
        np.sqrt(cfg["features"]["structure_weight"]) * structure / _median_pairwise_distance(structure),
        np.sqrt(cfg["features"]["level_weight"]) * level / _median_pairwise_distance(level),
    ], axis=1)


def prepare_representation(cfg_path: str | Path):
    """Prepare fixed reference or explicit alternative matrices without altering the reference pipeline."""
    cfg = load_config(cfg_path)
    representation = cfg["features"].get("representation", "reference_6part_clr")
    if representation == "reference_6part_clr":
        return _prepare(cfg_path)
    raw = read_semicolon_zip(cfg["paths"]["spending_zip"])
    required = [cfg["panel"]["total_category"], *cfg["panel"]["selected_categories"]]
    panel, names, audit = build_strict_panel(raw, cfg["panel"]["expected_months"], required, cfg["panel"].get("expected_periods"))
    panel["period"] = pd.to_datetime(panel["period"])
    months = sorted(panel["period"].unique())
    matrices = {str(pd.Timestamp(month).date()): _alternative_monthly_matrix(panel[panel["period"].eq(month)], names, cfg, representation) for month in months}
    return cfg, names, audit, months, matrices
