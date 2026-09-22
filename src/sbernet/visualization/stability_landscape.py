"""Fixed-anchor display. No model fitting, embedding or changes to Atlas values."""
import math

import numpy as np


PROFILES = list("ABCDEFG")
FIELDS = ["panel_index", "municipality", "reference_profile", "consensus_class", "second_class",
          *[f"affinity_share_{p}" for p in PROFILES], "top_affinity_share", "second_affinity_share",
          "affinity_margin", "affinity_entropy", "stability_class", "perturbation_peer_coassignment",
          "destination_precision", "destination_jaccard", "D_G_transition_direction", "B_E_transition_direction"]


def project(frame, config):
    """Return a new table; never normalize, jitter or mutate the scientific inputs."""
    if len(frame) != 1904 or not frame.panel_index.is_unique or not frame.municipality.is_unique:
        raise ValueError("Expected 1904 unique municipalities")
    shares = frame[[f"affinity_share_{p}" for p in PROFILES]].to_numpy()
    if not np.isfinite(shares).all() or (shares < 0).any() or not np.allclose(shares.sum(1), 1, atol=1e-12, rtol=0):
        raise ValueError("Invalid affinity shares; no silent renormalization")
    for field in ["affinity_margin", "affinity_entropy", "top_affinity_share", "perturbation_peer_coassignment",
                  "destination_precision", "destination_jaccard"]:
        if not np.isfinite(frame[field]).all() or not frame[field].between(0, 1).all():
            raise ValueError(f"Invalid field {field}")
    out = frame[FIELDS].copy()
    coordinates = shares @ np.array([config["anchors"][p] for p in PROFILES])
    out["x"], out["y"] = coordinates.T
    out["uncertainty"] = (out.affinity_entropy + 1 - out.affinity_margin) / 2
    out["DFG_share"] = sum(out[f"affinity_share_{p}"] for p in "DFG")
    out["BE_share"] = sum(out[f"affinity_share_{p}"] for p in "BE")
    # Only the explicitly labelled hard-class illustration uses decorative offsets.
    for profile, group in out.groupby("reference_profile", sort=True):
        centre = config["anchors"].get(profile, config["hard_layout"]["micro"])
        for ordinal, idx in enumerate(group.sort_values("panel_index").index):
            angle = ordinal * config["hard_layout"]["angle_step"]
            r = config["hard_layout"]["radius"] * math.sqrt((ordinal + .5) / len(group))
            out.loc[idx, "hard_x"] = centre[0] + r * math.cos(angle)
            out.loc[idx, "hard_y"] = centre[1] + r * math.sin(angle)
    return out


def field_grid(points, config):
    """Local display average of (entropy+1-margin)/2, masked outside support.

    This raster is a visual aid, not a density estimate or probability model.
    Bandwidth is fixed in display units, never chosen from the observed narrative.
    """
    settings = config["field"]
    cells = []
    xy = points[["x", "y"]].to_numpy()
    for x in range(70, 741, settings["step"]):
        for y in range(60, 601, settings["step"]):
            d2 = ((xy - [x, y]) ** 2).sum(1)
            weights = np.exp(-d2 / (2 * settings["bandwidth"] ** 2))
            weights[d2 > settings["cutoff"] ** 2] = 0
            if weights.sum() < settings["minimum_support"]:
                continue
            cells.append([x, y, float(weights @ points.uncertainty / weights.sum())])
    return cells
