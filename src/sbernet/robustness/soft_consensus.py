"""Family-balanced municipality-level soft consensus for Stability Atlas v2.1.

This module deliberately treats A--G as reference anchors rather than an objective
seven-class taxonomy. Pairwise co-assignment is label-invariant, so community IDs
may permute across runs without alignment.

The final consensus matrix gives equal weight to four experiment families:
perturbation, feature-weight (alpha), resolution (gamma), and algorithm (Leiden).
Within a family, runs receive equal weight.

Soft membership is a normalized affinity to the reference A--G groups:
for municipality i and profile c, affinity(i, c) is the mean consensus
co-assignment between i and reference members of c. When i itself belongs to c,
the diagonal self-pair is excluded. The seven affinities are normalized to sum
to one. These are consensus membership weights, not Bayesian probabilities.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import yaml


FAMILY_ORDER = ("perturbation", "alpha", "gamma", "algorithm")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def coassignment_matrix(label_runs: Iterable[np.ndarray]) -> np.ndarray:
    """Average label-invariant co-assignment matrix across runs."""
    runs = [np.asarray(labels) for labels in label_runs]
    if not runs:
        raise ValueError("At least one label run is required")
    n = runs[0].size
    if any(labels.ndim != 1 or labels.size != n for labels in runs):
        raise ValueError("All label runs must be one-dimensional and equally sized")
    out = np.zeros((n, n), dtype=np.float32)
    for labels in runs:
        out += (labels[:, None] == labels[None, :]).astype(np.float32)
    out /= np.float32(len(runs))
    np.fill_diagonal(out, 1.0)
    return out


def balanced_consensus(family_matrices: dict[str, np.ndarray]) -> np.ndarray:
    """Give each experiment family exactly the same weight."""
    missing = [name for name in FAMILY_ORDER if name not in family_matrices]
    if missing:
        raise ValueError(f"Missing consensus families: {missing}")
    shapes = {family_matrices[name].shape for name in FAMILY_ORDER}
    if len(shapes) != 1:
        raise ValueError("Family consensus matrices have inconsistent shapes")
    out = np.zeros(next(iter(shapes)), dtype=np.float32)
    for name in FAMILY_ORDER:
        out += family_matrices[name].astype(np.float32, copy=False)
    out /= np.float32(len(FAMILY_ORDER))
    np.fill_diagonal(out, 1.0)
    return out


def profile_affinities(
    consensus: np.ndarray,
    reference_labels: np.ndarray,
    profiles: dict[str, int],
) -> tuple[list[str], np.ndarray, np.ndarray]:
    """Return raw mean co-assignment affinities and row-normalized weights."""
    reference_labels = np.asarray(reference_labels)
    n = reference_labels.size
    if consensus.shape != (n, n):
        raise ValueError("Consensus matrix and reference labels disagree in size")

    names = list(profiles)
    raw = np.zeros((n, len(names)), dtype=np.float64)
    diag = np.diag(consensus)

    for col, profile in enumerate(names):
        label = profiles[profile]
        members = np.flatnonzero(reference_labels == label)
        if members.size == 0:
            raise ValueError(f"Reference profile {profile} (label={label}) is empty")
        numer = consensus[:, members].sum(axis=1, dtype=np.float64)
        denom = np.full(n, float(members.size), dtype=np.float64)
        own = reference_labels == label
        numer[own] -= diag[own]
        denom[own] -= 1.0
        if np.any(denom <= 0):
            raise ValueError(f"Reference profile {profile} is too small for leave-self-out affinity")
        raw[:, col] = numer / denom

    total = raw.sum(axis=1, keepdims=True)
    weights = np.divide(raw, total, out=np.zeros_like(raw), where=total > 0)
    return names, raw, weights


def normalized_entropy(weights: np.ndarray) -> np.ndarray:
    """Entropy in [0, 1] for row-normalized membership weights."""
    weights = np.asarray(weights, dtype=np.float64)
    if weights.ndim != 2 or weights.shape[1] < 2:
        raise ValueError("Expected an n x K weight matrix with K >= 2")
    if not np.isfinite(weights).all() or np.any(weights < 0):
        raise ValueError("Affinities must be finite and nonnegative")
    positive = np.where(weights > 0, weights, 1.0)
    entropy = -np.sum(np.where(weights > 0, weights * np.log(positive), 0.0), axis=1)
    result = entropy / np.log(weights.shape[1])
    result[weights.sum(axis=1) == 0] = np.nan
    return result


def rank_memberships(profile_names: list[str], weights: np.ndarray) -> dict[str, np.ndarray]:
    weights = np.asarray(weights, dtype=float)
    if weights.ndim != 2 or weights.shape[1] != len(profile_names):
        raise ValueError("Affinity shape differs from profiles")
    if not np.isfinite(weights).all() or np.any(weights < 0):
        raise ValueError("Affinities must be finite and nonnegative")
    order = np.argsort(-weights, axis=1, kind="stable")
    top = order[:, 0]
    second = order[:, 1]
    labels = np.asarray(profile_names, dtype=object)
    return {
        "top_profile": np.where(weights.sum(axis=1) > 0, labels[top], "unresolved"),
        "second_profile": np.where(weights.sum(axis=1) > 0, labels[second], "unresolved"),
        "top_weight": weights[np.arange(len(weights)), top],
        "second_weight": weights[np.arange(len(weights)), second],
        "margin": weights[np.arange(len(weights)), top]
        - weights[np.arange(len(weights)), second],
    }


def family_vote_subtype(
    family_raw: dict[str, np.ndarray],
    profile_names: list[str],
    left: str,
    right: str,
) -> tuple[np.ndarray, np.ndarray]:
    """Count family-level wins for a pair of reference profiles."""
    li = profile_names.index(left)
    ri = profile_names.index(right)
    left_wins = np.zeros(next(iter(family_raw.values())).shape[0], dtype=np.int8)
    right_wins = np.zeros_like(left_wins)
    for name in FAMILY_ORDER:
        values = family_raw[name]
        left_wins += (values[:, li] > values[:, ri]).astype(np.int8)
        right_wins += (values[:, ri] > values[:, li]).astype(np.int8)
    return left_wins, right_wins


def classify_f_transition(left_wins: np.ndarray, right_wins: np.ndarray) -> np.ndarray:
    """F→D/G requires agreement of at least 3 of 4 experiment families."""
    out = np.full(left_wins.shape, "F-middle", dtype=object)
    out[left_wins >= 3] = "F→D"
    out[right_wins >= 3] = "F→G"
    return out


def load_reference(path: Path) -> tuple[list[str], list[str], np.ndarray]:
    frame = pd.read_csv(path, index_col=0)
    if frame.empty:
        raise ValueError(f"Empty reference file: {path}")
    names = frame.index.astype(str).tolist()
    months = frame.columns.astype(str).tolist()
    return names, months, frame.iloc[:, -1].to_numpy(dtype=np.int64)


def load_csv_dec_labels(path: Path, names: list[str]) -> np.ndarray:
    frame = pd.read_csv(path, index_col=0)
    if frame.index.has_duplicates:
        raise ValueError(f"Duplicate municipality names in {path}")
    missing = [name for name in names if name not in frame.index]
    if missing:
        raise ValueError(f"{path} is missing {len(missing)} reference municipalities")
    return frame.loc[names].iloc[:, -1].to_numpy(dtype=np.int64)


def load_npy_dec_labels(path: Path, n_months: int, n_municipalities: int) -> np.ndarray:
    values = np.load(path, allow_pickle=False)
    if values.ndim == 1:
        expected = n_months * n_municipalities
        if values.size != expected:
            raise ValueError(f"{path}: expected {expected} labels, found {values.size}")
        values = values.reshape(n_months, n_municipalities)
    elif values.shape != (n_months, n_municipalities):
        raise ValueError(
            f"{path}: expected {(n_months, n_municipalities)}, found {values.shape}"
        )
    return np.asarray(values[-1], dtype=np.int64)


def load_profile_map(path: Path) -> dict[str, int]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    profiles = config.get("experiment", {}).get("profiles")
    if not profiles:
        raise ValueError(f"No experiment.profiles mapping in {path}")
    return {str(name): int(label) for name, label in profiles.items()}


def load_stability_table(path: Path, names: list[str]) -> pd.DataFrame | None:
    if not path.exists():
        return None
    frame = pd.read_csv(path)
    # Round16 persisted the same quantities under mean_* names. Normalize the
    # historical evidence schema instead of rewriting frozen evidence.
    aliases = {
        "profile": "reference_profile",
        "mean_peer_coassignment": "peer_coassignment",
        "mean_destination_precision": "destination_precision",
        "mean_destination_Jaccard": "destination_jaccard",
    }
    frame = frame.rename(columns={old: new for old, new in aliases.items() if old in frame.columns})
    required = {
        "municipality",
        "reference_profile",
        "peer_coassignment",
        "destination_precision",
        "destination_jaccard",
    }
    if not required.issubset(frame.columns):
        missing_columns = sorted(required - set(frame.columns))
        raise ValueError(f"{path} lacks required stability columns: {missing_columns}")
    frame = frame.set_index("municipality")
    missing = [name for name in names if name not in frame.index]
    if missing:
        raise ValueError(f"{path} is missing {len(missing)} municipalities")
    return frame.loc[names].reset_index()


def stability_class(peer: float, precision: float, jaccard: float, profile: str, thresholds=None) -> str:
    thresholds = thresholds or {"core_peer": 0.85, "core_precision": 0.75, "core_jaccard": 0.65, "transition_peer": 0.75, "transition_jaccard": 0.50}
    if profile == "micro":
        return "unresolved"
    if peer >= thresholds["core_peer"] and precision >= thresholds["core_precision"] and jaccard >= thresholds["core_jaccard"]:
        return "stable_core"
    if peer >= thresholds["core_peer"] and (precision < thresholds["core_precision"] or jaccard < thresholds["core_jaccard"]):
        return "expansive_core"
    if peer < thresholds["transition_peer"] and jaccard < thresholds["transition_jaccard"]:
        return "transition"
    return "unresolved"


def _collect_inputs(repo: Path, expected_perturbation_runs: int) -> dict[str, list[Path]]:
    perturbation = sorted((repo / "outputs/perturbation_v2/seeds").glob("*/supra_labels.npy"))
    if len(perturbation) != expected_perturbation_runs:
        raise ValueError(
            f"Expected {expected_perturbation_runs} perturbation runs, found {len(perturbation)}"
        )

    families = {
        "perturbation": perturbation,
        "alpha": [
            repo / "outputs/alpha_50_50/supra_labels.csv",
            repo / "outputs/alpha_90_10/supra_labels.csv",
        ],
        "gamma": [
            repo / "outputs/round16_resolution/runs/resolution_0.25/supra_labels.npy",
            repo / "outputs/round16_resolution/runs/resolution_0.75/supra_labels.npy",
            repo / "outputs/round16_resolution/runs/resolution_1.0/supra_labels.npy",
        ],
        "algorithm": [repo / "outputs/leiden_robustness/supra_labels.csv"],
    }
    for family, paths in families.items():
        absent = [str(path) for path in paths if not path.exists()]
        if absent:
            raise FileNotFoundError(f"Missing {family} inputs: {absent}")
    return families


def _reference_profile_names(reference_dec: np.ndarray, profiles: dict[str, int]) -> np.ndarray:
    inverse = {label: profile for profile, label in profiles.items()}
    return np.asarray([inverse.get(int(label), "micro") for label in reference_dec], dtype=object)


def _summary_table(frame: pd.DataFrame, profile_names: list[str]) -> pd.DataFrame:
    rows = []
    for profile in profile_names:
        group = frame[frame["reference_profile"] == profile]
        own = group[f"weight_{profile}"]
        secondary = group["second_profile"].value_counts()
        rows.append(
            {
                "reference_profile": profile,
                "n": len(group),
                "mean_self_weight": float(own.mean()),
                "median_self_weight": float(own.median()),
                "median_entropy": float(group["entropy"].median()),
                "median_margin": float(group["margin"].median()),
                "share_consensus_matches_reference": float(
                    np.mean(group["consensus_profile"] == profile)
                ),
                "most_common_secondary": secondary.index[0] if len(secondary) else "",
                "most_common_secondary_share": (
                    float(secondary.iloc[0] / len(group)) if len(group) else np.nan
                ),
            }
        )
    return pd.DataFrame(rows)


def run(
    repo: Path,
    output_dir: Path,
    expected_perturbation_runs: int = 50,
    save_family_matrices: bool = True,
) -> dict[str, object]:
    repo = repo.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    reference_path = repo / "outputs/baseline/supra_labels.csv"
    profile_config = repo / "configs/perturbation_v2.yaml"
    stability_path = (
        repo / "outputs/round16_competition/municipality_perturbation_stability.csv"
    )
    names, months, reference_dec = load_reference(reference_path)
    profiles = load_profile_map(profile_config)
    reference_profile = _reference_profile_names(reference_dec, profiles)
    family_paths = _collect_inputs(repo, expected_perturbation_runs)

    family_labels: dict[str, list[np.ndarray]] = {}
    for family, paths in family_paths.items():
        loaded = []
        for path in paths:
            if path.suffix == ".npy":
                loaded.append(load_npy_dec_labels(path, len(months), len(names)))
            else:
                loaded.append(load_csv_dec_labels(path, names))
        family_labels[family] = loaded

    family_matrices = {
        family: coassignment_matrix(label_runs)
        for family, label_runs in family_labels.items()
    }
    consensus = balanced_consensus(family_matrices)
    np.save(output_dir / "consensus_matrix_dec2024.npy", consensus)
    if save_family_matrices:
        np.savez_compressed(
            output_dir / "family_consensus_matrices.npz",
            **{name: family_matrices[name] for name in FAMILY_ORDER},
        )

    profile_names, raw, weights = profile_affinities(consensus, reference_dec, profiles)
    ranks = rank_memberships(profile_names, weights)
    entropy = normalized_entropy(weights)

    family_raw = {}
    for family in FAMILY_ORDER:
        family_profile_names, raw_family, _ = profile_affinities(
            family_matrices[family], reference_dec, profiles
        )
        if family_profile_names != profile_names:
            raise AssertionError("Profile order drifted across families")
        family_raw[family] = raw_family

    d_wins, g_wins = family_vote_subtype(family_raw, profile_names, "D", "G")
    b_wins, e_wins = family_vote_subtype(family_raw, profile_names, "B", "E")
    f_subtype_all = classify_f_transition(d_wins, g_wins)

    frame = pd.DataFrame(
        {
            "panel_index": np.arange(len(names), dtype=int),
            "municipality": names,
            "reference_profile": reference_profile,
            "consensus_profile": ranks["top_profile"],
            "second_profile": ranks["second_profile"],
            "top_weight": ranks["top_weight"],
            "second_weight": ranks["second_weight"],
            "margin": ranks["margin"],
            "entropy": entropy,
            "reference_match": ranks["top_profile"] == reference_profile,
        }
    )
    for col, profile in enumerate(profile_names):
        frame[f"affinity_{profile}"] = raw[:, col]
        frame[f"weight_{profile}"] = weights[:, col]

    d_idx, g_idx = profile_names.index("D"), profile_names.index("G")
    b_idx, e_idx = profile_names.index("B"), profile_names.index("E")
    dg_denom = weights[:, d_idx] + weights[:, g_idx]
    be_denom = weights[:, b_idx] + weights[:, e_idx]
    frame["D_G_balance"] = np.divide(
        weights[:, d_idx] - weights[:, g_idx],
        dg_denom,
        out=np.zeros(len(frame), dtype=float),
        where=dg_denom > 0,
    )
    frame["B_E_balance"] = np.divide(
        weights[:, b_idx] - weights[:, e_idx],
        be_denom,
        out=np.zeros(len(frame), dtype=float),
        where=be_denom > 0,
    )
    frame["family_wins_D_over_G"] = d_wins
    frame["family_wins_G_over_D"] = g_wins
    frame["family_wins_B_over_E"] = b_wins
    frame["family_wins_E_over_B"] = e_wins
    frame["F_transition_subtype"] = np.where(
        reference_profile == "F", f_subtype_all, ""
    )

    stability = load_stability_table(stability_path, names)
    if stability is not None:
        frame["perturbation_peer_coassignment"] = stability["peer_coassignment"].to_numpy()
        frame["destination_precision"] = stability["destination_precision"].to_numpy()
        frame["destination_jaccard"] = stability["destination_jaccard"].to_numpy()
        frame["stability_class"] = [
            stability_class(peer, precision, jaccard, profile)
            for peer, precision, jaccard, profile in zip(
                frame["perturbation_peer_coassignment"],
                frame["destination_precision"],
                frame["destination_jaccard"],
                frame["reference_profile"],
            )
        ]

    frame.to_csv(output_dir / "municipality_soft_membership.csv", index=False)

    family_affinity = pd.DataFrame(
        {
            "panel_index": np.arange(len(names), dtype=int),
            "municipality": names,
            "reference_profile": reference_profile,
        }
    )
    for family in FAMILY_ORDER:
        for col, profile in enumerate(profile_names):
            family_affinity[f"{family}_{profile}"] = family_raw[family][:, col]
    family_affinity.to_csv(output_dir / "family_profile_affinity.csv", index=False)

    cluster_cols = [
        "panel_index",
        "municipality",
        "reference_profile",
        "consensus_profile",
        "second_profile",
        "top_weight",
        "second_weight",
        "margin",
        "entropy",
        "reference_match",
    ]
    frame[cluster_cols].to_csv(output_dir / "consensus_clusters.csv", index=False)

    f_columns = [
        "panel_index",
        "municipality",
        "reference_profile",
        "consensus_profile",
        "second_profile",
        "weight_D",
        "weight_F",
        "weight_G",
        "D_G_balance",
        "family_wins_D_over_G",
        "family_wins_G_over_D",
        "F_transition_subtype",
        "entropy",
        "margin",
    ]
    frame.loc[frame["reference_profile"] == "F", f_columns].to_csv(
        output_dir / "F_transition_subtypes.csv", index=False
    )

    be_columns = [
        "panel_index",
        "municipality",
        "reference_profile",
        "consensus_profile",
        "second_profile",
        "weight_B",
        "weight_E",
        "B_E_balance",
        "family_wins_B_over_E",
        "family_wins_E_over_B",
        "entropy",
        "margin",
    ]
    frame.loc[frame["reference_profile"].isin(["B", "E"]), be_columns].to_csv(
        output_dir / "BE_gradient.csv", index=False
    )

    summary = _summary_table(frame, profile_names)
    summary.to_csv(output_dir / "soft_consensus_summary.csv", index=False)

    input_rows = []
    for family in FAMILY_ORDER:
        for path in family_paths[family]:
            input_rows.append(
                {
                    "family": family,
                    "path": str(path.relative_to(repo)),
                    "sha256": sha256(path),
                }
            )
    input_rows.extend(
        [
            {
                "family": "reference",
                "path": str(reference_path.relative_to(repo)),
                "sha256": sha256(reference_path),
            },
            {
                "family": "configuration",
                "path": str(profile_config.relative_to(repo)),
                "sha256": sha256(profile_config),
            },
        ]
    )
    if stability_path.exists():
        input_rows.append(
            {
                "family": "municipality_stability",
                "path": str(stability_path.relative_to(repo)),
                "sha256": sha256(stability_path),
            }
        )
    pd.DataFrame(input_rows).to_csv(output_dir / "input_checksums.csv", index=False)

    f_counts = (
        frame.loc[frame["reference_profile"] == "F", "F_transition_subtype"]
        .value_counts()
        .to_dict()
    )
    manifest = {
        "method": "family_balanced_pairwise_coassignment_reference_affinity_v1",
        "reference_month": months[-1],
        "n_municipalities": len(names),
        "profiles": profiles,
        "family_order": list(FAMILY_ORDER),
        "family_weights": {name: 1 / len(FAMILY_ORDER) for name in FAMILY_ORDER},
        "runs_per_family": {
            family: len(family_labels[family]) for family in FAMILY_ORDER
        },
        "soft_membership_semantics": (
            "Normalized mean co-assignment affinity to reference A-G groups; "
            "not a Bayesian probability."
        ),
        "self_pair_excluded_from_own_reference_profile": True,
        "f_subtype_rule": (
            "F→D if D beats G in at least 3/4 families; F→G if G beats D "
            "in at least 3/4; otherwise F-middle."
        ),
        "f_subtype_counts": {str(k): int(v) for k, v in f_counts.items()},
        "outputs": [
            "consensus_matrix_dec2024.npy",
            "family_consensus_matrices.npz" if save_family_matrices else None,
            "municipality_soft_membership.csv",
            "family_profile_affinity.csv",
            "consensus_clusters.csv",
            "F_transition_subtypes.csv",
            "BE_gradient.csv",
            "soft_consensus_summary.csv",
            "input_checksums.csv",
        ],
    }
    manifest["outputs"] = [item for item in manifest["outputs"] if item]
    (output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/stability_atlas_v2_1"),
    )
    parser.add_argument("--expected-perturbation-runs", type=int, default=50)
    parser.add_argument("--no-family-matrices", action="store_true")
    args = parser.parse_args()
    manifest = run(
        repo=args.repo,
        output_dir=args.output_dir,
        expected_perturbation_runs=args.expected_perturbation_runs,
        save_family_matrices=not args.no_family_matrices,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
