"""Stability Atlas v2.2: leave-one-family-out and anchor sensitivity.

v2.2 preserves the v2.1 family-balanced co-assignment construction while adding:
1. explicit terminology: affinity shares, not probabilities/weights;
2. separation of hard consensus class from D--G transition direction;
3. leave-one-family-out (LOFO) robustness over the four experiment families;
4. a consensus-core-anchor sensitivity analysis.

Consensus-core anchors are a sensitivity device, not an independent validation set.
Within each reference A--G profile, the top 25% of municipalities by their full
consensus affinity to their own reference profile are selected as anchors. This
tests whether conclusions are driven by diffuse profile boundaries.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from . import soft_consensus as v21


FAMILY_ORDER = v21.FAMILY_ORDER


def balanced_consensus_subset(
    family_matrices: dict[str, np.ndarray],
    included_families: tuple[str, ...] | list[str],
) -> np.ndarray:
    """Equal-weight consensus over an explicit non-empty subset of families."""
    included = tuple(included_families)
    if not included:
        raise ValueError("At least one family must be included")
    missing = [name for name in included if name not in family_matrices]
    if missing:
        raise ValueError(f"Missing consensus families: {missing}")
    shapes = {family_matrices[name].shape for name in included}
    if len(shapes) != 1:
        raise ValueError("Family consensus matrices have inconsistent shapes")
    out = np.zeros(next(iter(shapes)), dtype=np.float32)
    for name in included:
        out += family_matrices[name].astype(np.float32, copy=False)
    out /= np.float32(len(included))
    np.fill_diagonal(out, 1.0)
    return out


def affinities_to_members(
    consensus: np.ndarray,
    profile_names: list[str],
    member_indices: dict[str, np.ndarray],
) -> tuple[np.ndarray, np.ndarray]:
    """Mean co-assignment to arbitrary anchor sets, plus row-normalized shares."""
    n = consensus.shape[0]
    if consensus.shape != (n, n):
        raise ValueError("Consensus must be square")
    raw = np.zeros((n, len(profile_names)), dtype=np.float64)
    diag = np.diag(consensus)
    all_indices = np.arange(n)

    for col, profile in enumerate(profile_names):
        members = np.asarray(member_indices[profile], dtype=int)
        if members.ndim != 1 or members.size < 2:
            raise ValueError(f"Profile {profile} needs at least two anchor members")
        if np.any((members < 0) | (members >= n)):
            raise ValueError(f"Profile {profile} has out-of-range anchor indices")
        numer = consensus[:, members].sum(axis=1, dtype=np.float64)
        denom = np.full(n, float(members.size), dtype=np.float64)
        is_member = np.isin(all_indices, members)
        numer[is_member] -= diag[is_member]
        denom[is_member] -= 1.0
        raw[:, col] = numer / denom

    total = raw.sum(axis=1, keepdims=True)
    shares = np.divide(raw, total, out=np.zeros_like(raw), where=total > 0)
    return raw, shares


def select_consensus_core_anchors(
    reference_profiles: np.ndarray,
    profile_names: list[str],
    raw_full_affinity: np.ndarray,
    fraction: float = 0.25,
    minimum_anchors: int = 2,
) -> dict[str, np.ndarray]:
    """Select exactly the top fraction of each reference profile as core anchors.

    The score is the municipality's full-consensus raw affinity to its own
    reference profile. panel_index provides deterministic tie-breaking.
    """
    if not (0 < fraction <= 1):
        raise ValueError("anchor fraction must be in (0, 1]")
    anchors: dict[str, np.ndarray] = {}
    for col, profile in enumerate(profile_names):
        members = np.flatnonzero(reference_profiles == profile)
        if members.size < 2:
            raise ValueError(f"Reference profile {profile} has fewer than two members")
        k = min(members.size, max(minimum_anchors, int(math.ceil(members.size * fraction))))
        scores = raw_full_affinity[members, col]
        order = np.lexsort((members, -scores))
        anchors[profile] = np.sort(members[order[:k]])
    return anchors


def transition_direction(
    left_wins: np.ndarray,
    right_wins: np.ndarray,
    left_label: str,
    right_label: str,
    threshold: int = 3,
) -> np.ndarray:
    """Direction from family votes, kept separate from the hard consensus class."""
    out = np.full(left_wins.shape, "mixed", dtype=object)
    out[left_wins >= threshold] = f"{left_label}-leaning"
    out[right_wins >= threshold] = f"{right_label}-leaning"
    return out


def balance(shares: np.ndarray, profile_names: list[str], left: str, right: str) -> np.ndarray:
    li, ri = profile_names.index(left), profile_names.index(right)
    denom = shares[:, li] + shares[:, ri]
    return np.divide(
        shares[:, li] - shares[:, ri],
        denom,
        out=np.zeros(shares.shape[0], dtype=float),
        where=denom > 0,
    )


def _load_families(
    repo: Path,
    expected_perturbation_runs: int,
    names: list[str],
    months: list[str],
) -> tuple[dict[str, list[Path]], dict[str, list[np.ndarray]], dict[str, np.ndarray]]:
    paths = v21._collect_inputs(repo, expected_perturbation_runs)
    labels: dict[str, list[np.ndarray]] = {}
    for family, family_paths in paths.items():
        loaded = []
        for path in family_paths:
            if path.suffix == ".npy":
                loaded.append(v21.load_npy_dec_labels(path, len(months), len(names)))
            else:
                loaded.append(v21.load_csv_dec_labels(path, names))
        labels[family] = loaded
    matrices = {
        family: v21.coassignment_matrix(label_runs)
        for family, label_runs in labels.items()
    }
    return paths, labels, matrices


def _membership_frame(
    names: list[str],
    reference_profile: np.ndarray,
    profile_names: list[str],
    raw: np.ndarray,
    shares: np.ndarray,
) -> pd.DataFrame:
    ranks = v21.rank_memberships(profile_names, shares)
    frame = pd.DataFrame(
        {
            "panel_index": np.arange(len(names), dtype=int),
            "municipality": names,
            "reference_profile": reference_profile,
            "consensus_class": ranks["top_profile"],
            "second_class": ranks["second_profile"],
            "top_affinity_share": ranks["top_weight"],
            "second_affinity_share": ranks["second_weight"],
            "affinity_margin": ranks["margin"],
            "affinity_entropy": v21.normalized_entropy(shares),
            "consensus_matches_reference": ranks["top_profile"] == reference_profile,
        }
    )
    for col, profile in enumerate(profile_names):
        frame[f"raw_affinity_{profile}"] = raw[:, col]
        frame[f"affinity_share_{profile}"] = shares[:, col]
    return frame


def _lofo(
    family_matrices: dict[str, np.ndarray],
    names: list[str],
    reference_dec: np.ndarray,
    reference_profile: np.ndarray,
    profiles: dict[str, int],
    profile_names: list[str],
    full_frame: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    long_frames = []
    summary_rows = []
    municipality = pd.DataFrame(
        {
            "panel_index": np.arange(len(names), dtype=int),
            "municipality": names,
            "reference_profile": reference_profile,
            "full_consensus_class": full_frame["consensus_class"].to_numpy(),
        }
    )
    class_match_cols = []
    direction_match_cols = []
    full_dg_sign = np.sign(full_frame["D_G_balance"].to_numpy())

    for omitted in FAMILY_ORDER:
        included = tuple(name for name in FAMILY_ORDER if name != omitted)
        matrix = balanced_consensus_subset(family_matrices, included)
        _, raw, shares = v21.profile_affinities(matrix, reference_dec, profiles)
        part = _membership_frame(names, reference_profile, profile_names, raw, shares)
        part.insert(0, "omitted_family", omitted)
        part["matches_full_consensus"] = (
            part["consensus_class"].to_numpy() == full_frame["consensus_class"].to_numpy()
        )
        part["D_G_balance"] = balance(shares, profile_names, "D", "G")
        part["B_E_balance"] = balance(shares, profile_names, "B", "E")
        part["D_G_side"] = np.where(
            part["D_G_balance"] > 0,
            "D-side",
            np.where(part["D_G_balance"] < 0, "G-side", "balanced"),
        )
        long_frames.append(part)

        class_col = f"without_{omitted}_class_matches_full"
        direction_col = f"without_{omitted}_DG_side_matches_full"
        municipality[class_col] = part["matches_full_consensus"].to_numpy()
        municipality[direction_col] = (
            np.sign(part["D_G_balance"].to_numpy()) == full_dg_sign
        )
        class_match_cols.append(class_col)
        direction_match_cols.append(direction_col)

        scopes = [("ALL", np.ones(len(part), dtype=bool))]
        scopes.extend(
            (profile, reference_profile == profile) for profile in profile_names
        )
        for scope, mask in scopes:
            sub = part.loc[mask]
            summary_rows.append(
                {
                    "omitted_family": omitted,
                    "reference_profile": scope,
                    "n": len(sub),
                    "share_matches_full_consensus": float(sub["matches_full_consensus"].mean()),
                    "share_matches_reference": float(
                        sub["consensus_matches_reference"].mean()
                    ),
                    "median_affinity_entropy": float(sub["affinity_entropy"].median()),
                    "median_affinity_margin": float(sub["affinity_margin"].median()),
                    "share_D_side": float((sub["D_G_balance"] > 0).mean()),
                    "share_G_side": float((sub["D_G_balance"] < 0).mean()),
                }
            )

    long = pd.concat(long_frames, ignore_index=True)
    municipality["lofo_class_match_count"] = municipality[class_match_cols].sum(axis=1)
    municipality["lofo_all_class_match"] = municipality["lofo_class_match_count"] == 4
    municipality["lofo_DG_side_match_count"] = municipality[direction_match_cols].sum(axis=1)
    municipality["lofo_all_DG_side_match"] = municipality["lofo_DG_side_match_count"] == 4

    # Range of entropy/margin across the four omissions.
    entropy_wide = long.pivot(index="panel_index", columns="omitted_family", values="affinity_entropy")
    margin_wide = long.pivot(index="panel_index", columns="omitted_family", values="affinity_margin")
    municipality["lofo_entropy_range"] = (
        entropy_wide.max(axis=1) - entropy_wide.min(axis=1)
    ).to_numpy()
    municipality["lofo_min_margin"] = margin_wide.min(axis=1).to_numpy()

    return long, pd.DataFrame(summary_rows), municipality


def _anchor_analysis(
    consensus: np.ndarray,
    names: list[str],
    reference_profile: np.ndarray,
    profile_names: list[str],
    raw_full: np.ndarray,
    full_shares: np.ndarray,
    full_frame: pd.DataFrame,
    fraction: float,
    minimum_anchors: int = 2,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, np.ndarray]]:
    anchors = select_consensus_core_anchors(
        reference_profile, profile_names, raw_full, fraction=fraction, minimum_anchors=minimum_anchors
    )
    anchor_raw, anchor_shares = affinities_to_members(consensus, profile_names, anchors)
    anchor_frame = _membership_frame(
        names, reference_profile, profile_names, anchor_raw, anchor_shares
    )
    anchor_frame = anchor_frame.rename(
        columns={
            "consensus_class": "anchor_consensus_class",
            "second_class": "anchor_second_class",
            "top_affinity_share": "anchor_top_affinity_share",
            "second_affinity_share": "anchor_second_affinity_share",
            "affinity_margin": "anchor_affinity_margin",
            "affinity_entropy": "anchor_affinity_entropy",
            "consensus_matches_reference": "anchor_consensus_matches_reference",
            **{
                f"raw_affinity_{p}": f"anchor_raw_affinity_{p}"
                for p in profile_names
            },
            **{
                f"affinity_share_{p}": f"anchor_affinity_share_{p}"
                for p in profile_names
            },
        }
    )
    comparison = full_frame[
        ["panel_index", "municipality", "reference_profile", "consensus_class"]
    ].copy()
    comparison = comparison.merge(
        anchor_frame.drop(columns=["reference_profile"]),
        on=["panel_index", "municipality"],
        how="left",
        validate="one_to_one",
    )
    comparison["anchor_class_matches_full"] = (
        comparison["anchor_consensus_class"] == comparison["consensus_class"]
    )
    l1 = np.abs(anchor_shares - full_shares).sum(axis=1)
    comparison["anchor_vs_all_L1_affinity_share"] = l1

    summary_rows = []
    for profile in profile_names:
        mask = reference_profile == profile
        summary_rows.append(
            {
                "reference_profile": profile,
                "n_reference": int(mask.sum()),
                "n_anchors": int(len(anchors[profile])),
                "anchor_fraction_realized": float(len(anchors[profile]) / mask.sum()),
                "share_anchor_class_matches_full": float(
                    comparison.loc[mask, "anchor_class_matches_full"].mean()
                ),
                "share_anchor_class_matches_reference": float(
                    comparison.loc[mask, "anchor_consensus_matches_reference"].mean()
                ),
                "median_anchor_vs_all_L1": float(
                    comparison.loc[mask, "anchor_vs_all_L1_affinity_share"].median()
                ),
                "median_anchor_entropy": float(
                    comparison.loc[mask, "anchor_affinity_entropy"].median()
                ),
            }
        )

    return comparison, pd.DataFrame(summary_rows), anchors


def build_tables(
    repo: Path,
    output_dir: Path,
    expected_perturbation_runs: int = 50,
    anchor_fraction: float = 0.25,
    validated_inputs=None,
    settings=None,
) -> dict[str, object]:
    if validated_inputs is None or settings is None:
        raise ValueError("Use atlas_runner.run with a verified YAML configuration")
    (names, months, reference_dec, family_paths, family_labels) = validated_inputs
    reference_path = repo / settings["reference_labels"]
    profile_config = repo / settings["profile_config"]
    stability_path = repo / settings["stability_table"]
    profiles = v21.load_profile_map(profile_config)
    profile_names = list(profiles)
    reference_profile = v21._reference_profile_names(reference_dec, profiles)
    family_matrices = {family: v21.coassignment_matrix(labels)
                       for family, labels in family_labels.items()}
    consensus = v21.balanced_consensus(family_matrices)
    np.save(output_dir / "consensus_matrix_dec2024.npy", consensus)
    np.savez_compressed(
        output_dir / "family_consensus_matrices.npz",
        **{name: family_matrices[name] for name in FAMILY_ORDER},
    )

    _, raw_full, shares_full = v21.profile_affinities(
        consensus, reference_dec, profiles
    )
    frame = _membership_frame(
        names, reference_profile, profile_names, raw_full, shares_full
    )
    frame["D_G_balance"] = balance(shares_full, profile_names, "D", "G")
    frame["B_E_balance"] = balance(shares_full, profile_names, "B", "E")

    family_raw = {}
    for family in FAMILY_ORDER:
        _, raw_family, _ = v21.profile_affinities(
            family_matrices[family], reference_dec, profiles
        )
        family_raw[family] = raw_family
    d_wins, g_wins = v21.family_vote_subtype(
        family_raw, profile_names, "D", "G"
    )
    b_wins, e_wins = v21.family_vote_subtype(
        family_raw, profile_names, "B", "E"
    )
    frame["family_votes_D_over_G"] = d_wins
    frame["family_votes_G_over_D"] = g_wins
    frame["family_votes_B_over_E"] = b_wins
    frame["family_votes_E_over_B"] = e_wins
    dg_direction = transition_direction(d_wins, g_wins, "D", "G", settings["vote_threshold"])
    be_direction = transition_direction(b_wins, e_wins, "B", "E", settings["vote_threshold"])
    frame["D_G_transition_direction"] = np.where(
        reference_profile == "F", dg_direction, ""
    )
    frame["B_E_transition_direction"] = np.where(
        np.isin(reference_profile, ["B", "E"]), be_direction, ""
    )

    stability = v21.load_stability_table(stability_path, names)
    if stability is not None:
        frame["perturbation_peer_coassignment"] = stability["peer_coassignment"].to_numpy()
        frame["destination_precision"] = stability["destination_precision"].to_numpy()
        frame["destination_jaccard"] = stability["destination_jaccard"].to_numpy()
        frame["stability_class"] = [
            v21.stability_class(peer, precision, jaccard, profile, settings["stability_thresholds"])
            for peer, precision, jaccard, profile in zip(
                frame["perturbation_peer_coassignment"],
                frame["destination_precision"],
                frame["destination_jaccard"],
                frame["reference_profile"],
            )
        ]

    lofo_long, lofo_summary, lofo_municipality = _lofo(
        family_matrices,
        names,
        reference_dec,
        reference_profile,
        profiles,
        profile_names,
        frame,
    )
    frame = frame.merge(
        lofo_municipality.drop(columns=["reference_profile", "full_consensus_class"]),
        on=["panel_index", "municipality"],
        how="left",
        validate="one_to_one",
    )

    anchor_comparison, anchor_summary, anchors = _anchor_analysis(
        consensus,
        names,
        reference_profile,
        profile_names,
        raw_full,
        shares_full,
        frame,
        anchor_fraction,
        settings["minimum_anchors"],
    )
    anchor_small = anchor_comparison[
        [
            "panel_index",
            "anchor_consensus_class",
            "anchor_second_class",
            "anchor_top_affinity_share",
            "anchor_affinity_margin",
            "anchor_affinity_entropy",
            "anchor_class_matches_full",
            "anchor_vs_all_L1_affinity_share",
        ]
    ]
    frame = frame.merge(anchor_small, on="panel_index", how="left", validate="one_to_one")

    # Main outputs.
    frame.to_csv(output_dir / "municipality_affinity_atlas.csv", index=False)
    lofo_long.to_csv(output_dir / "leave_one_family_out.csv", index=False)
    lofo_summary.to_csv(output_dir / "leave_one_family_out_summary.csv", index=False)
    lofo_municipality.to_csv(output_dir / "leave_one_family_out_municipality.csv", index=False)
    anchor_comparison.to_csv(output_dir / "anchor_affinity_comparison.csv", index=False)
    anchor_summary.to_csv(output_dir / "anchor_affinity_summary.csv", index=False)

    anchor_rows = []
    for profile, indices in anchors.items():
        for index in indices:
            anchor_rows.append(
                {
                    "profile": profile,
                    "panel_index": int(index),
                    "municipality": names[int(index)],
                    "raw_self_affinity_full": float(
                        raw_full[int(index), profile_names.index(profile)]
                    ),
                }
            )
    pd.DataFrame(anchor_rows).to_csv(
        output_dir / "consensus_core_anchors.csv", index=False
    )

    # Family-level affinity table retained for audit.
    family_affinity = pd.DataFrame(
        {
            "panel_index": np.arange(len(names), dtype=int),
            "municipality": names,
            "reference_profile": reference_profile,
        }
    )
    for family in FAMILY_ORDER:
        _, family_shares = affinities_to_members(
            family_matrices[family],
            profile_names,
            {
                p: np.flatnonzero(reference_profile == p)
                for p in profile_names
            },
        )
        for col, profile in enumerate(profile_names):
            family_affinity[f"{family}_affinity_share_{profile}"] = family_shares[:, col]
    family_affinity.to_csv(output_dir / "family_affinity_shares.csv", index=False)

    hard_transition = frame[frame["reference_profile"] == "F"][
        [
            "panel_index",
            "municipality",
            "consensus_class",
            "second_class",
            "affinity_share_D",
            "affinity_share_F",
            "affinity_share_G",
            "D_G_balance",
            "D_G_transition_direction",
            "family_votes_D_over_G",
            "family_votes_G_over_D",
            "lofo_class_match_count",
            "lofo_DG_side_match_count",
            "anchor_consensus_class",
            "affinity_entropy",
            "affinity_margin",
        ]
    ]
    hard_transition.to_csv(output_dir / "F_DG_transition_atlas.csv", index=False)

    be = frame[frame["reference_profile"].isin(["B", "E"])][
        [
            "panel_index",
            "municipality",
            "reference_profile",
            "consensus_class",
            "second_class",
            "affinity_share_B",
            "affinity_share_E",
            "B_E_balance",
            "B_E_transition_direction",
            "family_votes_B_over_E",
            "family_votes_E_over_B",
            "lofo_class_match_count",
            "anchor_consensus_class",
            "affinity_entropy",
            "affinity_margin",
        ]
    ]
    be.to_csv(output_dir / "BE_metropolitan_gradient.csv", index=False)

    # Compact profile summary.
    summary_rows = []
    for profile in profile_names:
        group = frame[frame["reference_profile"] == profile]
        secondary = group["second_class"].value_counts()
        summary_rows.append(
            {
                "reference_profile": profile,
                "n": len(group),
                "mean_self_affinity_share": float(group[f"affinity_share_{profile}"].mean()),
                "median_self_affinity_share": float(group[f"affinity_share_{profile}"].median()),
                "median_affinity_entropy": float(group["affinity_entropy"].median()),
                "median_affinity_margin": float(group["affinity_margin"].median()),
                "share_consensus_matches_reference": float(
                    group["consensus_matches_reference"].mean()
                ),
                "share_all_four_LOFO_match_full": float(
                    group["lofo_all_class_match"].mean()
                ),
                "share_anchor_class_matches_full": float(
                    group["anchor_class_matches_full"].mean()
                ),
                "most_common_second_class": (
                    secondary.index[0] if len(secondary) else ""
                ),
                "most_common_second_class_share": (
                    float(secondary.iloc[0] / len(group)) if len(group) else np.nan
                ),
            }
        )
    pd.DataFrame(summary_rows).to_csv(
        output_dir / "profile_robustness_summary.csv", index=False
    )

    input_rows = []
    for family in FAMILY_ORDER:
        for path in family_paths[family]:
            input_rows.append(
                {
                    "family": family,
                    "path": str(path.relative_to(repo)),
                    "sha256": v21.sha256(path),
                }
            )
    for family, path in [
        ("reference", reference_path),
        ("configuration", profile_config),
        ("municipality_stability", stability_path),
    ]:
        if path.exists():
            input_rows.append(
                {
                    "family": family,
                    "path": str(path.relative_to(repo)),
                    "sha256": v21.sha256(path),
                }
            )
    pd.DataFrame(input_rows).to_csv(output_dir / "input_checksums.csv", index=False)

    f = frame[frame["reference_profile"] == "F"]
    manifest = {
        "atlas_version": settings["atlas_version"],
        "method": "family_balanced_pairwise_coassignment_affinity_with_lofo_and_anchor_sensitivity",
        "reference_month": months[-1],
        "n_municipalities": len(names),
        "profiles": profiles,
        "family_order": list(FAMILY_ORDER),
        "family_weights_full": {
            family: 1 / len(FAMILY_ORDER) for family in FAMILY_ORDER
        },
        "runs_per_family": {
            family: len(family_labels[family]) for family in FAMILY_ORDER
        },
        "terminology": {
            "affinity_share": (
                "row-normalized mean co-assignment affinity to reference groups; "
                "not a Bayesian probability"
            ),
            "consensus_class": "profile with the largest affinity share",
            "D_G_transition_direction": (
                "for reference-F only: D-leaning/G-leaning if at least 3 of 4 "
                "families prefer D/G; otherwise mixed"
            ),
        },
        "lofo": {
            "runs": 4,
            "families_per_run": 3,
            "equal_weight_within_each_run": True,
        },
        "anchor_sensitivity": {
            "definition": (
                "top fraction within each reference profile by full-consensus "
                "raw self-affinity"
            ),
            "fraction": anchor_fraction,
            "independent_validation": False,
            "purpose": "boundary-dilution sensitivity",
            "counts": {p: int(len(indices)) for p, indices in anchors.items()},
        },
        "F_reference_n": int(len(f)),
        "F_consensus_class_counts": {
            str(k): int(v) for k, v in f["consensus_class"].value_counts().to_dict().items()
        },
        "F_transition_direction_counts": {
            str(k): int(v)
            for k, v in f["D_G_transition_direction"].value_counts().to_dict().items()
        },
        "outputs": [
            "consensus_matrix_dec2024.npy",
            "family_consensus_matrices.npz",
            "municipality_affinity_atlas.csv",
            "leave_one_family_out.csv",
            "leave_one_family_out_summary.csv",
            "leave_one_family_out_municipality.csv",
            "anchor_affinity_comparison.csv",
            "anchor_affinity_summary.csv",
            "consensus_core_anchors.csv",
            "family_affinity_shares.csv",
            "F_DG_transition_atlas.csv",
            "BE_metropolitan_gradient.csv",
            "profile_robustness_summary.csv",
            "input_checksums.csv",
        ],
    }
    return manifest


def main() -> None:
    from .atlas_runner import main as hardened_main
    hardened_main()


if __name__ == "__main__":
    main()
