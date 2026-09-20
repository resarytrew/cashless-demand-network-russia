from __future__ import annotations

from pathlib import Path
from typing import Iterable

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist, squareform


def grouped_distance_sums(distance_matrix: np.ndarray, group_ids: np.ndarray, n_groups: int) -> np.ndarray:
    """Return ordered pair-distance sums between groups.

    Element [h, g] is sum(D[i, j]) for i in group h and j in group g.
    Diagonal entries therefore contain each unordered pair twice.
    """
    n = distance_matrix.shape[0]
    tmp = np.empty((n, n_groups), dtype=float)
    members = [np.flatnonzero(group_ids == g) for g in range(n_groups)]
    for g, idx in enumerate(members):
        tmp[:, g] = distance_matrix[:, idx].sum(axis=1)
    out = np.empty((n_groups, n_groups), dtype=float)
    for h, idx in enumerate(members):
        out[h, :] = tmp[idx, :].sum(axis=0)
    return out


def exact_matched_total_distance(
    group_distance_sums: np.ndarray,
    universe_counts: np.ndarray,
    sample_counts: np.ndarray,
) -> float:
    """Exact expected total unordered pair distance under SRSWOR within strata."""
    n = np.asarray(universe_counts, dtype=float)
    m = np.asarray(sample_counts, dtype=float)
    p = np.divide(m, n, out=np.zeros_like(m), where=n > 0)
    q = np.zeros_like(p)
    ok = n > 1
    q[ok] = m[ok] * (m[ok] - 1) / (n[ok] * (n[ok] - 1))

    weighted = np.outer(p, p) * group_distance_sums
    np.fill_diagonal(weighted, q * np.diag(group_distance_sums))
    return float(0.5 * weighted.sum())


def exact_matched_mean_distance(
    distance_matrix: np.ndarray,
    strata: np.ndarray,
    sample_mask: np.ndarray,
) -> float:
    strata_codes, _ = pd.factorize(strata, sort=True)
    k = int(strata_codes.max()) + 1
    sums = grouped_distance_sums(distance_matrix, strata_codes, k)
    universe_counts = np.bincount(strata_codes, minlength=k)
    sample_counts = np.bincount(strata_codes[sample_mask], minlength=k)
    total = exact_matched_total_distance(sums, universe_counts, sample_counts)
    n = int(sample_mask.sum())
    return total / (n * (n - 1) / 2)


def equal_area_block_ids(
    longitude: Iterable[float],
    latitude: Iterable[float],
    block_size_km: float,
    shift_x_fraction: float = 0.0,
    shift_y_fraction: float = 0.0,
    target_crs: str = "EPSG:6933",
) -> np.ndarray:
    points = gpd.GeoDataFrame(
        geometry=gpd.points_from_xy(list(longitude), list(latitude)),
        crs="EPSG:4326",
    ).to_crs(target_crs)
    size = block_size_km * 1000.0
    x = np.floor((points.geometry.x.to_numpy() - shift_x_fraction * size) / size).astype(int)
    y = np.floor((points.geometry.y.to_numpy() - shift_y_fraction * size) / size).astype(int)
    return np.asarray([f"{a}:{b}" for a, b in zip(x, y)], dtype=object)


def spatial_block_ratios(
    x: np.ndarray,
    longitude: np.ndarray,
    latitude: np.ndarray,
    admin_form: np.ndarray,
    archetype: np.ndarray,
    block_sizes_km: Iterable[int] = (300, 500, 750, 1000),
    shifts: Iterable[tuple[float, float]] = ((0, 0), (0.5, 0), (0, 0.5), (0.5, 0.5)),
) -> pd.DataFrame:
    """Compute exact spatial-block × admin matched-null ratios."""
    d = squareform(pdist(x))
    rows: list[dict] = []
    labels = [v for v in sorted(pd.unique(archetype)) if pd.notna(v)]

    for size in block_sizes_km:
        for sx, sy in shifts:
            blocks = equal_area_block_ids(longitude, latitude, size, sx, sy)
            strata = np.asarray([f"{b}|{a}" for b, a in zip(blocks, admin_form)], dtype=object)
            for label in labels:
                mask = archetype == label
                idx = np.flatnonzero(mask)
                observed = float(d[np.ix_(idx, idx)][np.triu_indices(len(idx), 1)].mean())
                expected = exact_matched_mean_distance(d, strata, mask)
                rows.append(
                    {
                        "block_size_km": size,
                        "shift_x_fraction": sx,
                        "shift_y_fraction": sy,
                        "archetype": label,
                        "n": len(idx),
                        "observed_mean_distance": observed,
                        "spatial_block_admin_null_mean": expected,
                        "ratio_spatial_block_admin": observed / expected,
                    }
                )
    return pd.DataFrame(rows)
