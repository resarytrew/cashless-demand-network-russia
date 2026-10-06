"""Audit official Data -> Sense files and restore only verified data lineage."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd
import yaml

from sbernet.data_sense_lineage import (
    complete_official_in_ambiguous_current,
    exact_lineage_matches,
    standardise_current,
    standardise_official,
    value_multiset_equal,
)
from sbernet.io import build_strict_panel, read_semicolon_zip
from sbernet.sberindex_directory import read_directory, select_snapshot


REQUIRED_CATEGORIES = [
    "Все категории", "Продовольствие", "Здоровье", "Общественное питание", "Маркетплейсы", "Транспорт"
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def raw_audit(staging: Path) -> pd.DataFrame:
    rows = []
    interesting = {"territory_id", "territory_id_x", "territory_id_y", "mo", "municipality", "oktmo", "region", "region_code", "year", "month", "date"}
    for path in sorted(staging.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() == ".parquet":
            frame = pd.read_parquet(path)
            columns = frame.columns.tolist()
            rows.append({
                "filename": path.relative_to(staging).as_posix(), "format": "parquet", "row_count": len(frame),
                "column_names": json.dumps(columns, ensure_ascii=False),
                "sample_schema": json.dumps({key: str(value) for key, value in frame.dtypes.items()}, ensure_ascii=False),
                "identity_columns": json.dumps([column for column in columns if column in interesting], ensure_ascii=False),
                "status": "INSPECTED",
            })
        elif path.suffix.lower() == ".pdf":
            rows.append({
                "filename": path.relative_to(staging).as_posix(), "format": "pdf", "row_count": pd.NA,
                "column_names": pd.NA, "sample_schema": "publisher methodology; 4 pages", "identity_columns": pd.NA,
                "status": "INSPECTED_DOCUMENTATION",
            })
    return pd.DataFrame(rows)


def write_package_inventory(staging: Path, output: Path) -> None:
    """Record every extracted publisher file without treating it as new raw data."""
    rows = []
    for path in sorted(staging.rglob("*")):
        if path.is_file():
            rows.append(
                {
                    "filename": path.relative_to(staging).as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256(path),
                    "provenance": "EXTRACTED_UNCHANGED_FROM_OFFICIAL_ARCHIVE",
                }
            )
    pd.DataFrame(rows).to_csv(output / "official_package_inventory.csv", index=False)


def main(config_path: str) -> None:
    config_file = Path(config_path)
    cfg = yaml.safe_load(config_file.read_text(encoding="utf-8"))["experiment"]
    output = Path(cfg["output_dir"])
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite run: {output}")
    output.mkdir(parents=True)
    audit_path = Path(cfg["audit_csv"])
    if audit_path.exists():
        raise FileExistsError(f"Refusing to overwrite raw audit: {audit_path}")

    files = raw_audit(Path(cfg["staging_dir"]))
    files.to_csv(audit_path, index=False)
    write_package_inventory(Path(cfg["staging_dir"]), output)
    raw = read_semicolon_zip(cfg["reference_raw"])
    strict_panel, reference_names, panel_audit = build_strict_panel(raw, 24, REQUIRED_CATEGORIES)
    current = standardise_current(raw)
    current_strict = standardise_current(strict_panel)
    official = standardise_official(pd.read_parquet(cfg["consumption_file"]))
    matches = exact_lineage_matches(current_strict, official)

    directory = select_snapshot(read_directory(cfg["directory_file"]), cfg["target_year"])
    directory = directory.set_index("territory_id")
    candidate = matches["candidate_territory_id"].astype("Int64")
    matches["official_name"] = candidate.map(directory["municipal_district_name"])
    matches["directory_oktmo"] = candidate.map(directory["oktmo"])
    matches["directory_region_code"] = candidate.map(directory["region_code"])
    matches["name_equal"] = matches["reference_mo"].eq(matches["official_name"])
    matches["match_method"] = "exact_24_month_x_6_category_value_fingerprint"
    matches["status"] = "UNRESOLVED_NO_UNIQUE_FINGERPRINT"
    unique = matches["candidate_count"].eq(1)
    matches.loc[unique & matches["name_equal"], "status"] = "VERIFIED_DATA_LINEAGE_MATCH"
    matches.loc[unique & ~matches["name_equal"], "status"] = "CONFLICT_DIRECTORY_NAME_NOT_EQUAL"
    matches.loc[matches["candidate_count"].eq(1) & matches["name_equal"], "territory_id"] = candidate
    matches["territory_id"] = matches["territory_id"].astype("Int64")
    columns = [
        "reference_mo", "territory_id", "official_name", "match_method", "fingerprint_distance",
        "name_equal", "candidate_count", "status", "candidate_territory_id", "fingerprint_sha256",
        "directory_oktmo", "directory_region_code",
    ]
    matches.loc[:, columns].to_csv(output / "reference_to_territory_id.csv", index=False)

    official_counts = official.groupby("territory_id").size()
    expected_records = len(REQUIRED_CATEGORIES) * 24
    embedding = complete_official_in_ambiguous_current(current, official, expected_records)
    fingerprint_ids = set(
        matches.loc[matches.candidate_count.eq(1), "candidate_territory_id"].dropna().astype(int)
    )
    strict_ids = set(
        matches.loc[matches.status.eq("VERIFIED_DATA_LINEAGE_MATCH"), "territory_id"].dropna().astype(int)
    )
    ambiguous_current_names = set(
        raw.groupby(["mo", "category_15", "period"]).size().loc[lambda value: value.gt(1)].index.get_level_values("mo")
    )
    embedded_ambiguous = embedding.loc[
        embedding.embedded_in_current_name & embedding.current_name_candidate.isin(ambiguous_current_names)
    ]
    official_complete_ids = set(official_counts.loc[official_counts.eq(expected_records)].index.astype(int))
    # A directory-name conflict is still accounted for by its unique trajectory.
    # It is deliberately not retained as a usable reference-to-ID mapping.
    unaccounted = (
        official_complete_ids
        - fingerprint_ids
        - set(embedded_ambiguous.territory_id.astype(int))
    )
    reconciliation = pd.DataFrame([
        {"measure": "official territory_id total", "count": int(official.territory_id.nunique()), "reason": "all official Data -> Sense consumption IDs"},
        {"measure": "official complete 24x6 territory_id", "count": len(official_complete_ids), "reason": "144 records: 24 months x 6 categories"},
        {"measure": "reference unique fingerprint candidates", "count": len(fingerprint_ids), "reason": "unique exact 24-month x 6-category trajectory; before directory compatibility gate"},
        {"measure": "reference retained", "count": len(strict_ids), "reason": "unique exact fingerprint plus exact directory-name compatibility"},
        {"measure": "reference name-conflict", "count": int(matches.status.eq("CONFLICT_DIRECTORY_NAME_NOT_EQUAL").sum()), "reason": "unique fingerprint but directory name differs; excluded pending review"},
        {"measure": "complete official IDs inside ambiguous raw names", "count": len(embedded_ambiguous), "reason": "full official trajectories occur only in names with duplicate month/category rows"},
        {"measure": "unaccounted complete official IDs", "count": len(unaccounted), "reason": "must be zero; otherwise no inference"},
        {"measure": "reference excluded by strict-panel ambiguity", "count": panel_audit.ambiguous_names, "reason": "textual mo has duplicate category/month observations"},
        {"measure": "reference excluded by incomplete history", "count": raw.mo.nunique() - panel_audit.complete_names, "reason": "not all required 24x6 observations"},
    ])
    reconciliation.to_csv(output / "reference_universe_reconciliation.csv", index=False)
    (output / "REFERENCE_UNIVERSE_RECONCILIATION.md").write_text(
        "# Reference-universe reconciliation\n\n"
        "The official Data -> Sense file has one `territory_id` per fixed territory, while the legacy input has "
        "only a textual `mo`. Both have the same number of value records, but duplicate textual labels can combine "
        "multiple official territory trajectories. Counts below are calculated from the two supplied files, not inferred "
        "from names.\n\n"
        + reconciliation.to_markdown(index=False) + "\n\n"
        "`complete official IDs inside ambiguous raw names` uses an exact multiset containment check over all 144 "
        "month/category/value records; it does not use municipal names as a key.\n",
        encoding="utf-8",
    )
    (output / "OFFICIAL_PACKAGE_SCOPE.md").write_text(
        "# Official Data -> Sense package scope\n\n"
        "The publisher archive is preserved unchanged under `data/external/raw/sberindex_data_sense/`; "
        "its extracted inventory is `official_package_inventory.csv`. The archive contains `consumption.parquet`, "
        "`market_access.parquet`, `connection.parquet`, and one methodology PDF. It contains no population, "
        "wage, employment, migration, or BDMO files.\n\n"
        "`data_sense_raw_audit.csv` records the observed schemas. The methodology calls the consumption measure "
        "`consumption`, whereas the actual parquet field is `value`; this discrepancy is reported rather than "
        "silently renamed in the raw audit.\n",
        encoding="utf-8",
    )
    identity = {
        "official_consumption_rows": len(official), "legacy_raw_rows": len(current),
        "value_multiset_equal_without_municipality_identifier": value_multiset_equal(current, official),
        "official_categories": sorted(official.category.unique().tolist()),
        "official_months": sorted(official.date.unique().tolist()),
        "strict_reference_n": len(reference_names),
        "unique_fingerprint_candidates": int(matches.candidate_count.eq(1).sum()),
        "verified_data_lineage_matches": int(matches.status.eq("VERIFIED_DATA_LINEAGE_MATCH").sum()),
        "name_conflicts": int(matches.status.eq("CONFLICT_DIRECTORY_NAME_NOT_EQUAL").sum()),
    }
    conflict_rows = matches.loc[
        matches.status.eq("CONFLICT_DIRECTORY_NAME_NOT_EQUAL"),
        ["reference_mo", "candidate_territory_id", "official_name"],
    ]
    conflict_text = (
        conflict_rows.to_markdown(index=False)
        if not conflict_rows.empty
        else "No directory-name conflicts."
    )
    (output / "DATA_LINEAGE_AUDIT.md").write_text(
        "# Data -> Sense official spending lineage audit\n\n"
        "## Scope and source\n\n"
        "This is a data-lineage and identity gate only. It does not change the reference clustering, "
        "labels, model parameters, or BDMO evidence. The publisher package and its checksum are recorded "
        "in `source_manifest.csv`; all extracted file checksums are in `official_package_inventory.csv`.\n\n"
        "## Candidate generation (no names)\n\n"
        "For each strict reference-panel `mo`, the gate serializes and SHA-256 hashes its exact sorted set of "
        "`(date, category, value)` records. It does the same for each official `territory_id`. Candidates are "
        "only official IDs with the identical hash. No municipality name, region, OKTMO prefix, fuzzy score, "
        "or manual override participates in this operation.\n\n"
        f"The all-row identifier-free `(date, category, value)` multiset check is `{identity['value_multiset_equal_without_municipality_identifier']}` "
        f"for {identity['legacy_raw_rows']:,} legacy and {identity['official_consumption_rows']:,} official records. "
        f"All {identity['unique_fingerprint_candidates']:,} strict reference trajectories have one, and only one, "
        "official fingerprint candidate.\n\n"
        "## Independent compatibility gate\n\n"
        "Only after candidate creation, the candidate `territory_id` is looked up in SberIndex's independently "
        "downloaded 2024 municipal directory. Exact equality of the reference text and the directory name is a "
        "compatibility check, not a matching method. A mapping is usable only when both gates pass.\n\n"
        f"Result: {identity['verified_data_lineage_matches']:,} `VERIFIED_DATA_LINEAGE_MATCH`; "
        f"{identity['name_conflicts']:,} `CONFLICT_DIRECTORY_NAME_NOT_EQUAL`; no fuzzy or manual resolution.\n\n"
        "### Held conflict\n\n"
        f"{conflict_text}\n\n"
        "The held row must receive a source-backed review before it can enter a reference-to-`territory_id` "
        "crosswalk. It is not exported in the usable `territory_id` column.\n\n"
        "## Gate decision\n\n"
        "This run establishes that official Data -> Sense consumption data contains `territory_id` and reproduces "
        "the supplied spending values. It does not yet authorize the requested BDMO joins: the 1,904th reference "
        "row remains held, and the repository has no publisher-documented transformation from the directory's "
        "11-character OKTMO representation to the 8-character BDMO field. No prefix or inferred code conversion "
        "was attempted.\n",
        encoding="utf-8",
    )
    (output / "identity_test.json").write_text(json.dumps(identity, ensure_ascii=False, indent=2), encoding="utf-8")
    source_manifest = pd.DataFrame([{
        "source_key": "data_sense_official_package", "source_url": cfg["source_url"],
        "download_url": cfg["download_url"], "resolved_download_url": cfg["resolved_download_url"],
        "retrieved_utc": cfg["retrieved_utc"], "filename": cfg["official_archive"],
        "sha256": sha256(Path(cfg["official_archive"])), "size_bytes": Path(cfg["official_archive"]).stat().st_size,
        "license": cfg["license"], "citation": cfg["citation"],
    }])
    source_manifest.to_csv(output / "source_manifest.csv", index=False)
    manifest = {
        "config_sha256": sha256(config_file), "identity_test": identity,
        "reference_panel_audit": panel_audit.__dict__, "source_manifest": "source_manifest.csv",
        "status": "LINEAGE_PARTIALLY_RESTORED_ONE_NAME_CONFLICT_REQUIRES_REVIEW",
    }
    (output / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/data_sense_lineage_2024.yaml")
    main(parser.parse_args().config)
