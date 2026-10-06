"""Prepare lightweight temporal trajectory and half-year flow data for Atlas consumers."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def main() -> None:
    output = Path("outputs/presubmission_upgrade/visualization")
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    labels = pd.read_csv("outputs/baseline/supra_labels.csv", index_col=0)
    atlas = pd.read_csv("outputs/stability_atlas_v2_2_1/municipality_affinity_atlas.csv").set_index("municipality")
    trajectories = labels.copy()
    trajectories.insert(0, "stability_class", atlas.reindex(trajectories.index)["stability_class"])
    trajectories.insert(0, "reference_profile", atlas.reindex(trajectories.index)["reference_profile"])
    trajectories.insert(0, "municipality", trajectories.index)
    trajectories.to_csv(output / "municipality_profile_trajectories.csv", index=False)
    periods = {"2023_H1": labels.columns[:6], "2023_H2": labels.columns[6:12], "2024_H1": labels.columns[12:18], "2024_H2": labels.columns[18:24]}
    representative = pd.DataFrame({name: labels.loc[:, months].mode(axis=1).iloc[:, 0] for name, months in periods.items()})
    flows = []
    for left, right in zip(representative.columns[:-1], representative.columns[1:]):
        frame = representative.groupby([left, right]).size().rename("n").reset_index()
        frame.insert(0, "period_from", left); frame.insert(1, "period_to", right)
        frame.columns = ["period_from", "period_to", "source_community", "target_community", "n"]
        flows.append(frame)
    pd.concat(flows, ignore_index=True).to_csv(output / "halfyear_transition_flows.csv", index=False)
    (output / "README.md").write_text(
        "# Temporal Atlas companion data\n\n`municipality_profile_trajectories.csv` provides the 24 saved supra-community labels for each municipality together with its frozen Atlas class. `halfyear_transition_flows.csv` aggregates modal half-year community flows for an alluvial/Sankey view. Community IDs remain arbitrary supra-partition labels, not economic states or causal transitions. These data do not alter the sealed Atlas viewer.\n", encoding="utf-8")


if __name__ == "__main__":
    main()
