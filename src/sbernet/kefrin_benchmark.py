"""Round22 comparison helpers, kept separate from the reference clustering code."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

from .structural_sensitivity import contingency, structural_metrics, wilson_interval


def hungarian_alignment(reference: np.ndarray, candidate: np.ndarray) -> dict[int, int]:
    reference_values, candidate_values, table = contingency(reference, candidate)
    rows, columns = linear_sum_assignment(-table)
    return {int(candidate_values[column]): int(reference_values[row]) for row, column in zip(rows, columns)}


def aligned_labels(candidate: np.ndarray, mapping: dict[int, int]) -> np.ndarray:
    candidate = np.asarray(candidate)
    missing = set(map(int, np.unique(candidate))) - set(mapping)
    if missing:
        raise ValueError(f"unmapped candidate labels: {sorted(missing)}")
    return np.asarray([mapping[int(value)] for value in candidate], dtype=np.int64)


def comparison_metrics(reference: np.ndarray, candidate: np.ndarray) -> dict[str, float | int | str]:
    mapping = hungarian_alignment(reference, candidate)
    aligned = aligned_labels(candidate, mapping)
    base = structural_metrics(reference, candidate)
    base["hungarian_aligned_accuracy"] = float(np.mean(reference == aligned))
    base["mapping"] = ";".join(f"{key}->{value}" for key, value in sorted(mapping.items()))
    return base


def crosswalk(reference: np.ndarray, candidate: np.ndarray) -> pd.DataFrame:
    reference_values, candidate_values, table = contingency(reference, candidate)
    rows = []
    for i, reference_label in enumerate(reference_values):
        total = int(table[i].sum())
        for j, candidate_label in enumerate(candidate_values):
            count = int(table[i, j])
            if count:
                rows.append({
                    "reference_cluster": reference_label,
                    "kefrin_cluster": candidate_label,
                    "count": count,
                    "share_of_reference": count / total,
                })
    return pd.DataFrame(rows)


def atlas_agreement(
    reference: np.ndarray,
    candidate: np.ndarray,
    states: np.ndarray,
) -> tuple[pd.DataFrame, dict[str, float | int | None]]:
    global_mapping = hungarian_alignment(reference, candidate)
    globally_aligned = aligned_labels(candidate, global_mapping)
    rows = []
    for state in sorted(np.unique(states)):
        take = states == state
        n = int(take.sum())
        mapped = globally_aligned[take]
        changed = int(np.count_nonzero(mapped != reference[take]))
        low, high = wilson_interval(changed, n)
        rows.append({
            "stability_class": state,
            "N": n,
            "disagreement_n": changed,
            "disagreement_share": changed / n,
            "wilson95_low": low,
            "wilson95_high": high,
            "ARI_within_state": adjusted_rand_score(reference[take], candidate[take]),
            "NMI_within_state": normalized_mutual_info_score(reference[take], candidate[take]),
            "mapped_agreement": 1 - changed / n,
            "global_mapping": ";".join(f"{k}->{v}" for k, v in sorted(global_mapping.items())),
        })
    frame = pd.DataFrame(rows)
    by_state = frame.set_index("stability_class")
    stable = by_state.loc["stable_core"]
    transition = by_state.loc["transition"]
    risk_stable = stable.disagreement_n / stable.N
    risk_transition = transition.disagreement_n / transition.N
    contrast = {
        "stable_disagreement_n": int(stable.disagreement_n),
        "stable_N": int(stable.N),
        "transition_disagreement_n": int(transition.disagreement_n),
        "transition_N": int(transition.N),
        "difference_transition_minus_stable": float(risk_transition - risk_stable),
        "risk_ratio_transition_vs_stable": float(risk_transition / risk_stable) if risk_stable else None,
    }
    return frame, contrast
