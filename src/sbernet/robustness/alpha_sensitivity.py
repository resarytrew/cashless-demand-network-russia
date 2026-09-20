"""Utilities for alpha (feature-block weight) sensitivity analysis.

The production sensitivity grid is defined in configs/baseline.yaml and uses
50/50, 70/30 and 90/10 structure/level weights. This module intentionally
does not select an optimum alpha; it supports partition-comparison reporting.
"""
from __future__ import annotations

import numpy as np
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

def partition_similarity(a: np.ndarray, b: np.ndarray) -> dict[str, float]:
    return {
        "ari": float(adjusted_rand_score(a, b)),
        "nmi": float(normalized_mutual_info_score(a, b)),
    }

def dominant_retention(reference: np.ndarray, alternative: np.ndarray, reference_label: int) -> dict[str, float | int]:
    mask = reference == reference_label
    n = int(mask.sum())
    if n == 0:
        raise ValueError("reference_label is absent")
    values, counts = np.unique(alternative[mask], return_counts=True)
    j = int(np.argmax(counts))
    destination = int(values[j])
    intersection = int(counts[j])
    alt_n = int(np.sum(alternative == destination))
    return {
        "reference_n": n,
        "destination": destination,
        "intersection": intersection,
        "retention": intersection / n,
        "precision": intersection / alt_n,
        "jaccard": intersection / (n + alt_n - intersection),
    }
