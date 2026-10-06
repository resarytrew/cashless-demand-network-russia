"""Deterministic handling of the versioned SberIndex municipality directory.

This module deliberately does not infer a municipality identity from a name.  It
only selects an explicitly versioned directory snapshot and records whether a
reference row has an upstream ``territory_id`` to use as a join key.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


DIRECTORY_COLUMNS = {
    "territory_id",
    "oktmo",
    "municipal_district_name",
    "region_code",
    "year_from",
    "year_to",
}


def read_directory(path: str | Path) -> pd.DataFrame:
    """Read the supplied directory while retaining hyphenated OKTMO as text."""
    frame = pd.read_excel(path, dtype={"oktmo": "string", "territory_id": "Int64"})
    missing = DIRECTORY_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"SberIndex directory misses required columns: {sorted(missing)}")
    frame["oktmo"] = frame["oktmo"].astype("string")
    return frame


def select_snapshot(frame: pd.DataFrame, year: int) -> pd.DataFrame:
    """Select the [year_from, year_to) snapshot and reject unresolved versions.

    In the publisher's 2024 directory, treating ``year_to`` as inclusive would
    create 86 duplicate territory IDs.  The exclusive upper bound produces one
    version per territory, and is therefore the operational documented-data
    semantics recorded by this pipeline.
    """
    snapshot = frame.loc[frame["year_from"].le(year) & frame["year_to"].gt(year)].copy()
    duplicate_territory = snapshot.loc[snapshot["territory_id"].duplicated(False), "territory_id"]
    if not duplicate_territory.empty:
        raise ValueError(
            "Multiple directory versions match snapshot year for territory IDs: "
            + ", ".join(map(str, sorted(duplicate_territory.dropna().unique())))
        )
    return snapshot.sort_values(["territory_id", "oktmo"], kind="stable").reset_index(drop=True)


def territory_to_oktmo(snapshot: pd.DataFrame, source: str) -> pd.DataFrame:
    """Create the official 2024 territory-to-OKTMO table without code coercion."""
    out = snapshot.rename(columns={"municipal_district_name": "official_name"}).loc[
        :, ["territory_id", "official_name", "region_code", "oktmo", "year_from", "year_to"]
    ].copy()
    out["version_status"] = "selected_snapshot_2024_exclusive_year_to"
    out["source"] = source
    return out


def reference_identity_audit(reference: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Record reference identities; refuse to fabricate a missing territory key."""
    identity_columns = [
        column
        for column in ("territory_id", "municipality_id", "mo_id", "raw_id")
        if column in reference.columns
    ]
    rows = []
    for number, name in enumerate(reference.index.astype(str)):
        territory_id = None
        source_column = None
        for column in identity_columns:
            value = reference.iloc[number][column]
            if pd.notna(value) and str(value).strip():
                territory_id = str(value)
                source_column = column
                break
        rows.append(
            {
                "reference_municipality_id": number,
                "reference_name": name,
                "territory_id": territory_id,
                "source_file": "outputs/baseline/supra_labels.csv",
                "source_column": source_column,
                "mapping_method": (
                    "upstream_reference_territory_id" if territory_id is not None
                    else "none_no_upstream_official_identifier"
                ),
                "status": "MAPPED" if territory_id is not None else "MISSING_UPSTREAM_TERRITORY_ID",
            }
        )
    mapping = pd.DataFrame(rows)
    audit = {
        "reference_total": len(mapping),
        "reference_identifier_columns": identity_columns,
        "mapped_to_territory_id": int(mapping["territory_id"].notna().sum()),
        "missing_territory_id": int(mapping["territory_id"].isna().sum()),
    }
    return mapping, audit
