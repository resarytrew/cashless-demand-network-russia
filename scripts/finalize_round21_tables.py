"""Deterministically finalize small Round21 tables after acceptance-audit additions.

This does not rerun clustering and only rewrites additive Round21 artifacts.
"""
from __future__ import annotations

from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from sbernet.structural_sensitivity import (
    bh,
    multivariate_permutation,
    scalar_merge_omnibus,
    scalar_merge_tests,
    sector_clr,
)
from run_round21_structural_sensitivity import l2_crosswalk


def main() -> None:
    cfg = yaml.safe_load(Path("configs/round21_structural_sensitivity.yaml").read_text(encoding="utf-8"))
    out = Path(cfg["experiment"]["output_dir"])
    ext_cfg = cfg["external"]
    external = pd.read_csv(ext_cfg["joined"])
    major = external.loc[external.profile.isin(list("ABCDEFG"))].copy()

    scalar = scalar_merge_tests(
        major, ext_cfg["merge_groups"], ["population", "wage", "employment_total"], "profile",
        ext_cfg["bootstrap"]["reps"], ext_cfg["bootstrap"]["seed"],
    )
    scalar = pd.concat([
        scalar,
        scalar_merge_omnibus(
            major, ext_cfg["merge_groups"], ["population", "wage", "employment_total"], "profile"
        ),
    ], ignore_index=True, sort=False)
    scalar.to_csv(out / "external_merge_validation.csv", index=False)

    sector_base = major.loc[major.population.gt(0) & major.region.notna() & major.profile.notna()].copy()
    sector_frame, sector_y = sector_clr(sector_base, ext_cfg["sectors"])
    sector_rows: list[dict] = []
    reps = ext_cfg["permutation_tests"]["n_permutations"]
    seed = ext_cfg["permutation_tests"]["seed"]
    for family, labels in ext_cfg["merge_groups"].items():
        first = len(sector_rows)
        for left, right in combinations(labels, 2):
            mask = sector_frame.profile.isin([left, right]).to_numpy()
            result = multivariate_permutation(
                sector_y[mask], sector_frame.loc[mask, "profile"].to_numpy(), reps, seed
            )
            sector_rows.append({
                "analysis_type": "pairwise", "analysis_family": family,
                "profile_a": left, "profile_b": right, "N": int(mask.sum()),
                "dimensions": sector_y.shape[1], **result,
            })
        adjusted = bh(np.array([row["p"] for row in sector_rows[first:]]))
        for row, value in zip(sector_rows[first:], adjusted):
            row["p_BH_within_family"] = float(value)
        mask = sector_frame.profile.isin(labels).to_numpy()
        result = multivariate_permutation(
            sector_y[mask], sector_frame.loc[mask, "profile"].to_numpy(), reps, seed
        )
        sector_rows.append({
            "analysis_type": "omnibus", "analysis_family": family,
            "profile_a": "/".join(labels), "profile_b": "", "N": int(mask.sum()),
            "dimensions": sector_y.shape[1], **result, "p_BH_within_family": result["p"],
        })
    pd.DataFrame(sector_rows).to_csv(out / "external_merge_sector_validation.csv", index=False)

    migration = pd.read_csv(cfg["l2"]["original_migration"])
    original = l2_crosswalk(migration, "L2_community", cfg["l2"]["major_min_share"])
    original.to_csv(out / "l2_crosswalk_l1.csv", index=False)
    balanced = []
    for specification in cfg["l2"]["balanced_sensitivities"]:
        labels = pd.read_csv(out / "checkpoints" / f"l2_{specification}_labels.csv", index_col=0)
        labels = labels.loc[migration.municipality, labels.columns[-1]].to_numpy()
        frame = migration[["municipality", "L1_profile"]].copy()
        frame[specification] = labels
        crosswalk = l2_crosswalk(frame, specification, cfg["l2"]["major_min_share"])
        crosswalk.insert(0, "specification", specification)
        balanced.append(crosswalk)
    pd.concat(balanced, ignore_index=True).to_csv(out / "l2_balanced_crosswalk.csv", index=False)

    for table_path in out.glob("*.csv"):
        table = pd.read_csv(table_path)
        if table.isna().any().any():
            table.fillna("NOT_APPLICABLE").to_csv(table_path, index=False)

    assert int(original.N.sum()) == len(migration)
    assert scalar.query("analysis_type == 'omnibus' and analysis_family == 'DFG'").shape[0] == 3
    assert any(row["analysis_type"] == "omnibus" and row["analysis_family"] == "DFG" for row in sector_rows)


if __name__ == "__main__":
    main()
