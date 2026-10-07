"""Feature and comparison helpers for the additive L1/L2 experiment."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist


def median_distance_scale(values: np.ndarray) -> tuple[np.ndarray, float]:
    """Scale one feature block by its positive median pairwise distance."""
    values = np.asarray(values, dtype=float)
    if values.ndim != 2 or len(values) < 2 or not np.isfinite(values).all():
        raise ValueError("feature block must be a finite 2D array with at least two rows")
    scale = float(np.median(pdist(values)))
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError("median pairwise distance must be positive and finite")
    return values / scale, scale


def robust_standardize_columns(values: np.ndarray) -> np.ndarray:
    """Columnwise median/MAD standardisation with no silent constant columns."""
    values = np.asarray(values, dtype=float)
    if values.ndim != 2 or not np.isfinite(values).all():
        raise ValueError("values must be a finite 2D array")
    median = np.median(values, axis=0)
    mad = np.median(np.abs(values - median), axis=0)
    scale = 1.4826 * mad
    if np.any(scale <= 0) or not np.isfinite(scale).all():
        raise ValueError("every socioeconomic feature must have positive finite MAD")
    return (values - median) / scale


def employment_clr(frame: pd.DataFrame, columns: list[str]) -> tuple[np.ndarray, pd.DataFrame]:
    """Build employment-share CLR with documented rowwise zero replacement."""
    values = frame[columns].fillna(0.0).to_numpy(dtype=float)
    if not np.isfinite(values).all() or np.any(values < 0):
        raise ValueError("employment values must be finite and non-negative")
    positive_count = (values > 0).sum(axis=1)
    if np.any(positive_count == 0):
        raise ValueError("each row needs at least one positive employment sector")
    positive_min = np.where(values > 0, values, np.inf).min(axis=1)
    replaced = np.where(values > 0, values, positive_min[:, None] * 0.5)
    shares = replaced / replaced.sum(axis=1, keepdims=True)
    logged = np.log(shares)
    clr = logged - logged.mean(axis=1, keepdims=True)
    share_frame = pd.DataFrame(shares, columns=columns, index=frame.index)
    return clr, share_frame


def combine_lenses(
    l1: np.ndarray,
    socioeconomic: np.ndarray,
    employment: np.ndarray,
    weights: dict[str, float],
) -> tuple[np.ndarray, dict[str, float]]:
    """Combine three separately distance-normalised blocks using fixed weights."""
    expected = {"l1", "socioeconomic", "employment"}
    if set(weights) != expected or any(float(value) <= 0 for value in weights.values()):
        raise ValueError(f"weights must be positive and exactly {sorted(expected)}")
    total = float(sum(weights.values()))
    if not np.isclose(total, 1.0):
        raise ValueError("block weights must sum to one")
    if not (len(l1) == len(socioeconomic) == len(employment)):
        raise ValueError("all feature blocks must have the same number of rows")
    scaled: list[np.ndarray] = []
    scales: dict[str, float] = {}
    for name, block in (
        ("l1", l1), ("socioeconomic", socioeconomic), ("employment", employment)
    ):
        normalized, scale = median_distance_scale(block)
        scaled.append(np.sqrt(float(weights[name])) * normalized)
        scales[name] = scale
    return np.concatenate(scaled, axis=1), scales


def canonicalize_partition(labels: np.ndarray) -> tuple[np.ndarray, dict[int, int]]:
    """Rename communities by descending size, then original ID, without changing membership."""
    labels = np.asarray(labels)
    if labels.ndim != 1:
        raise ValueError("labels must be one-dimensional")
    values, counts = np.unique(labels, return_counts=True)
    order = sorted(zip(values.tolist(), counts.tolist()), key=lambda item: (-item[1], item[0]))
    mapping = {int(old): new for new, (old, _) in enumerate(order, start=1)}
    return np.array([mapping[int(value)] for value in labels], dtype=int), mapping


def cross_lens_migration(
    names: list[str],
    l1_labels: np.ndarray,
    l2_labels: np.ndarray,
    l1_public: np.ndarray,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return contingency and municipality-level cross-lens reassignment diagnostics."""
    if not (len(names) == len(l1_labels) == len(l2_labels) == len(l1_public)):
        raise ValueError("cross-lens inputs must have identical lengths")
    frame = pd.DataFrame(
        {"municipality": names, "L1_community": l1_labels, "L1_profile": l1_public,
         "L2_community": l2_labels}
    )
    contingency = pd.crosstab(frame["L1_profile"], frame["L2_community"], dropna=False)
    contingency.index.name = "L1_profile"
    dominant = (
        frame.groupby("L2_community")["L1_profile"]
        .agg(lambda series: series.value_counts().sort_index().idxmax())
        .rename("dominant_L1_profile_in_L2")
    )
    frame = frame.join(dominant, on="L2_community")
    frame["cross_lens_reassigned"] = frame.L1_profile.ne(frame.dominant_L1_profile_in_L2)
    return contingency.reset_index(), frame
