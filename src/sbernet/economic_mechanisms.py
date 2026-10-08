"""Deterministic helpers for the additive Round 23 mechanism diagnostics."""
from __future__ import annotations

from collections.abc import Iterable

import numpy as np
from scipy.spatial.distance import cdist


def holm_adjust(p_values: Iterable[float]) -> np.ndarray:
    """Return Holm step-down adjusted p-values in the original order."""
    values = np.asarray(list(p_values), dtype=float)
    if values.ndim != 1 or np.any(~np.isfinite(values)):
        raise ValueError("p-values must be a finite one-dimensional sequence")
    if np.any((values < 0) | (values > 1)):
        raise ValueError("p-values must lie in [0, 1]")
    order = np.argsort(values, kind="stable")
    ranked = values[order]
    adjusted_ranked = np.maximum.accumulate((len(values) - np.arange(len(values))) * ranked)
    adjusted = np.empty_like(values)
    adjusted[order] = np.minimum(adjusted_ranked, 1.0)
    return adjusted


def clr(composition: np.ndarray) -> np.ndarray:
    values = np.asarray(composition, dtype=float)
    if values.ndim < 2 or np.any(~np.isfinite(values)) or np.any(values <= 0):
        raise ValueError("CLR requires a finite positive array with a parts axis")
    logged = np.log(values)
    return logged - logged.mean(axis=-1, keepdims=True)


def composition_change_volatility(composition: np.ndarray) -> np.ndarray:
    """Multivariate SD of month-to-month CLR changes for each municipality.

    Input shape is (municipality, month, part). The result is the square root of
    the mean squared deviation of CLR first differences from each municipality's
    mean CLR first-difference vector.
    """
    transformed = clr(composition)
    delta = np.diff(transformed, axis=1)
    centered = delta - delta.mean(axis=1, keepdims=True)
    return np.sqrt(np.mean(centered * centered, axis=(1, 2)))


def aitchison_rows(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    left_clr = clr(np.asarray(left, dtype=float))
    right_clr = clr(np.asarray(right, dtype=float))
    if left_clr.shape != right_clr.shape:
        raise ValueError("left and right compositions must have identical shapes")
    return np.linalg.norm(left_clr - right_clr, axis=-1)


def robust_z_matrix(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    median = np.median(values, axis=0)
    mad = np.median(np.abs(values - median), axis=0)
    scale = 1.4826 * mad
    if np.any(scale <= 0):
        raise ValueError("all columns need positive MAD")
    return (values - median) / scale


def greedy_unique_pairs(
    standardized_covariates: np.ndarray,
    eligible: np.ndarray,
    caliper: float,
) -> list[tuple[int, int, float, bool]]:
    """Mutual nearest pairs first, then greedy unique pairs below a caliper."""
    x = np.asarray(standardized_covariates, dtype=float)
    mask = np.asarray(eligible, dtype=bool)
    if mask.shape != (len(x), len(x)):
        raise ValueError("eligible must be an NxN matrix")
    distances = cdist(x, x)
    distances[~mask] = np.inf
    np.fill_diagonal(distances, np.inf)
    nearest = np.argmin(distances, axis=1)
    nearest_distance = distances[np.arange(len(x)), nearest]
    mutual: set[tuple[int, int]] = set()
    for i, j in enumerate(nearest):
        if np.isfinite(nearest_distance[i]) and nearest[j] == i:
            mutual.add((min(i, int(j)), max(i, int(j))))
    candidates: list[tuple[int, int, float, bool]] = []
    rows, cols = np.where(np.triu(mask & (distances <= caliper), k=1))
    for i, j in zip(rows.tolist(), cols.tolist()):
        candidates.append((i, j, float(distances[i, j]), (i, j) in mutual))
    candidates.sort(key=lambda item: (not item[3], item[2], item[0], item[1]))
    used: set[int] = set()
    selected: list[tuple[int, int, float, bool]] = []
    for item in candidates:
        i, j = item[:2]
        if i not in used and j not in used:
            selected.append(item)
            used.update((i, j))
    return selected


def haversine_km(
    lon1: np.ndarray | float,
    lat1: np.ndarray | float,
    lon2: np.ndarray | float,
    lat2: np.ndarray | float,
) -> np.ndarray:
    lon1, lat1, lon2, lat2 = map(np.asarray, (lon1, lat1, lon2, lat2))
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = phi2 - phi1
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2) ** 2
    return 6371.0088 * 2 * np.arctan2(np.sqrt(a), np.sqrt(np.maximum(0.0, 1 - a)))


def partial_r2(y: np.ndarray, reduced: np.ndarray, added: np.ndarray) -> float:
    y = np.asarray(y, dtype=float)
    reduced = np.asarray(reduced, dtype=float)
    added = np.asarray(added, dtype=float)
    reduced_residual = y - reduced @ np.linalg.lstsq(reduced, y, rcond=None)[0]
    full = np.column_stack([reduced, added])
    full_residual = y - full @ np.linalg.lstsq(full, y, rcond=None)[0]
    rss_reduced = float(reduced_residual @ reduced_residual)
    rss_full = float(full_residual @ full_residual)
    if rss_reduced <= 0:
        raise ValueError("reduced residual sum of squares must be positive")
    return max(0.0, min(1.0, 1.0 - rss_full / rss_reduced))
