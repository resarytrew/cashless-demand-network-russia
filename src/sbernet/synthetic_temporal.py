"""Controlled dynamic attributed-network benchmark for temporal coupling.

This module deliberately has no connection to the observed SberIndex panel.  It
implements the same feature-block and graph architecture on a small simulated
panel whose latent states and change points are known.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import linear_sum_assignment
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

from .clustering import louvain_labels
from .graph import mutual_knn_graph
from .temporal import build_supra_graph


@dataclass(frozen=True)
class SyntheticPanel:
    features: np.ndarray  # (months, nodes, 6): 5 CLR-like composition dims + level
    truth: np.ndarray  # (months, nodes), latent state labels
    change_month: np.ndarray  # (nodes,), -1 when no true state change
    scenario: str


def _scale_block(values: np.ndarray) -> np.ndarray:
    """Median-pairwise normalization equivalent in purpose to the reference block scaling."""
    distance = np.linalg.norm(values[:, None, :] - values[None, :, :], axis=2)
    median = np.median(distance[np.triu_indices(len(values), 1)])
    return values / max(float(median), 1e-9)


def generate_panel(
    scenario: str,
    seed: int,
    *,
    n_nodes: int = 120,
    months: int = 12,
    communities: int = 4,
    noise: float = 0.28,
    separation: float = 2.6,
    switching_fraction: float = 0.20,
) -> SyntheticPanel:
    """Generate deterministic composition-plus-level observations and latent truth.

    Labels remain fixed for boundary and temporary-shock cases; gradual drift has
    a predeclared midpoint change point, not a point selected from observations.
    """
    if scenario not in {"stable", "abrupt", "gradual", "boundary", "shock", "mixed"}:
        raise ValueError(f"Unknown scenario: {scenario}")
    if n_nodes % communities:
        raise ValueError("n_nodes must divide communities for balanced latent groups")
    rng = np.random.default_rng(seed)
    base = np.repeat(np.arange(communities), n_nodes // communities)
    # Community directions create comparable five CLR coordinates and one level block.
    centroid = rng.normal(size=(communities, 6))
    centroid = centroid / np.linalg.norm(centroid, axis=1, keepdims=True) * separation
    truth = np.tile(base, (months, 1))
    change = np.full(n_nodes, -1, dtype=int)
    transition = max(2, months // 2)
    candidates = rng.permutation(n_nodes)[:max(1, round(n_nodes * switching_fraction))]

    if scenario in {"abrupt", "gradual", "mixed"}:
        chosen = candidates if scenario != "mixed" else candidates[:max(1, len(candidates) // 2)]
        target = (base[chosen] + 1) % communities
        truth[transition:, chosen] = target
        change[chosen] = transition
    # Non-switch cases intentionally retain -1 change month.

    output = np.empty((months, n_nodes, 6), dtype=float)
    boundary_nodes = candidates if scenario in {"boundary", "mixed"} else np.empty(0, dtype=int)
    shock_nodes = candidates if scenario in {"shock", "mixed"} else np.empty(0, dtype=int)
    for month in range(months):
        latent = centroid[truth[month]].copy()
        if scenario in {"gradual", "mixed"}:
            selected = np.flatnonzero(change >= 0)
            if len(selected):
                before, after = transition - 2, transition + 2
                share = np.clip((month - before) / max(after - before, 1), 0, 1)
                origin = base[selected]
                destination = (origin + 1) % communities
                latent[selected] = (1 - share) * centroid[origin] + share * centroid[destination]
        if len(boundary_nodes):
            origin = base[boundary_nodes]
            latent[boundary_nodes] = .5 * (centroid[origin] + centroid[(origin + 1) % communities])
        if len(shock_nodes) and transition <= month < min(months, transition + 2):
            latent[shock_nodes] += rng.normal(0, separation * .9, size=(len(shock_nodes), 6))
        observed = latent + rng.normal(0, noise, size=(n_nodes, 6))
        # First five dimensions act as a centred composition block.  The last
        # dimension is the level block, with independently stable scaling.
        observed[:, :5] -= observed[:, :5].mean(axis=1, keepdims=True)
        output[month, :, :5] = _scale_block(observed[:, :5]) * np.sqrt(.70)
        output[month, :, 5:] = _scale_block(observed[:, 5:]) * np.sqrt(.30)
    return SyntheticPanel(output, truth, change, scenario)


def align_to_truth(labels: np.ndarray, truth: np.ndarray) -> np.ndarray:
    """Map arbitrary clustering labels to contemporaneous latent states."""
    out = np.empty_like(labels)
    for month in range(labels.shape[0]):
        found, expected = np.unique(labels[month]), np.unique(truth[month])
        table = np.array([[np.sum((labels[month] == a) & (truth[month] == b)) for b in expected] for a in found])
        rows, cols = linear_sum_assignment(-table)
        mapping = {found[row]: expected[col] for row, col in zip(rows, cols, strict=True)}
        # Extra detected communities are assigned to their modal true state.
        for label in found:
            if label not in mapping:
                choices = truth[month][labels[month] == label]
                mapping[label] = np.bincount(choices).argmax()
        out[month] = np.array([mapping[x] for x in labels[month]])
    return out


def infer_labels(panel: SyntheticPanel, omega: float, k: int, resolution: float, seed: int) -> np.ndarray:
    graphs = [mutual_knn_graph(panel.features[month], k=k, isolate_fallback=False) for month in range(panel.features.shape[0])]
    if omega == 0:
        return np.stack([louvain_labels(graph, resolution, seed) for graph in graphs])
    supra = build_supra_graph(graphs, panel.features.shape[1], omega)
    return louvain_labels(supra, resolution, seed).reshape(panel.features.shape[0], panel.features.shape[1])


def score(panel: SyntheticPanel, inferred: np.ndarray) -> dict[str, float]:
    """Score partitions and month-level event calls against declared latent truth."""
    aligned = align_to_truth(inferred, panel.truth)
    truth_events = np.zeros((panel.truth.shape[0] - 1, panel.truth.shape[1]), dtype=bool)
    pred_events = np.zeros_like(truth_events)
    truth_events[:] = panel.truth[1:] != panel.truth[:-1]
    pred_events[:] = aligned[1:] != aligned[:-1]
    tp = int((truth_events & pred_events).sum())
    fp = int((~truth_events & pred_events).sum())
    fn = int((truth_events & ~pred_events).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    delays, signed = [], []
    for node, expected in enumerate(panel.change_month):
        if expected < 0:
            continue
        reported = np.flatnonzero(pred_events[:, node]) + 1
        if len(reported):
            delta = int(reported[np.argmin(np.abs(reported - expected))] - expected)
            delays.append(abs(delta))
            signed.append(delta)
    return {
        "ari": adjusted_rand_score(panel.truth.ravel(), inferred.ravel()),
        "nmi": normalized_mutual_info_score(panel.truth.ravel(), inferred.ravel()),
        "node_state_accuracy": float((aligned == panel.truth).mean()),
        "switch_precision": precision, "switch_recall": recall, "switch_f1": f1,
        "false_switches": fp, "missed_switches": fn,
        "false_switch_rate": fp / max((~truth_events).sum(), 1),
        "false_persistence": fn / max(truth_events.sum(), 1),
        "false_instability": fp / max((~truth_events).sum(), 1),
        "absolute_change_point_delay": float(np.mean(delays)) if delays else np.nan,
        "signed_change_point_delay": float(np.mean(signed)) if signed else np.nan,
    }
