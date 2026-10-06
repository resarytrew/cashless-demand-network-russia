"""Audit the official SberIndex directory before any BDMO match is attempted."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

import pandas as pd
import yaml

from sbernet.sberindex_directory import (
    DIRECTORY_COLUMNS,
    read_directory,
    reference_identity_audit,
    select_snapshot,
    territory_to_oktmo,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def raw_spending_columns(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        members = [member for member in archive.namelist() if not member.endswith("/")]
        if len(members) != 1:
            raise ValueError(f"Expected one raw spending member, got {members}")
        with archive.open(members[0]) as handle:
            return pd.read_csv(handle, sep=";", nrows=0).columns.tolist()


def write_schema_audit(path: Path, directory: pd.DataFrame, snapshot: pd.DataFrame) -> None:
    inclusive = directory.loc[directory["year_from"].le(2024) & directory["year_to"].ge(2024)]
    path.write_text(
        "# SberIndex municipality directory — schema audit\n\n"
        f"Rows: {len(directory):,}; 2024 exclusive snapshot rows: {len(snapshot):,}.\n\n"
        "## Required fields\n\n"
        "| Required concept | Actual column | Status |\n| --- | --- | --- |\n"
        "| stable territory identifier | `territory_id` | present |\n"
        "| official OKTMO | `oktmo` | present as text |\n"
        "| official municipality name | `municipal_district_name` | present |\n"
        "| region | `region_code`, `region_name` | present |\n"
        "| start year | `year_from` | present |\n"
        "| end year | `year_to` | present |\n"
        "| transformation identifiers | `change_id_from`, `change_id_to` | present |\n\n"
        "## Snapshot semantics\n\n"
        "The selected snapshot uses `year_from <= 2024 AND year_to > 2024`. "
        f"The inclusive alternative produces {int(inclusive.territory_id.duplicated().sum()):,} duplicate "
        "territory IDs, whereas the exclusive selection has zero. `year_to` is therefore treated as an "
        "exclusive endpoint in this run. No row with multiple active versions is selected silently.\n\n"
        "## Code handling\n\n"
        "`oktmo` remains text in the source form (including hyphens and leading zeroes). This stage does "
        "not reduce an 11-digit directory code to BDMO's 8-digit field and does not perform a prefix join; "
        "that conversion requires a separately documented matching rule after the reference territory ID is available.\n",
        encoding="utf-8",
    )


def main(config_path: str) -> None:
    config_file = Path(config_path)
    cfg = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    exp = cfg["experiment"]
    output = Path(exp["output_dir"])
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite completed/new run directory: {output}")
    output.mkdir(parents=True)

    directory_path = Path(exp["directory_workbook"])
    directory = read_directory(directory_path)
    snapshot = select_snapshot(directory, exp["target_year"])
    write_schema_audit(output / "SBERINDEX_DIRECTORY_SCHEMA.md", directory, snapshot)
    territory = territory_to_oktmo(snapshot, exp["landing_url"])
    territory.to_csv(output / "sberindex_territory_to_oktmo.csv", index=False)

    reference = pd.read_csv(exp["reference_labels"], index_col=0)
    raw_columns = raw_spending_columns(Path(exp["reference_raw"]))
    reference_map, identity_audit = reference_identity_audit(reference)
    reference_map["raw_source_columns"] = ",".join(raw_columns)
    reference_map.to_csv(output / "reference_to_territory_id.csv", index=False)

    # This branch must not use names before recovering an upstream territory ID.
    crosswalk = reference_map.loc[:, ["reference_municipality_id", "reference_name", "territory_id"]].copy()
    crosswalk["sberindex_name"] = pd.NA
    crosswalk["region_code"] = pd.NA
    crosswalk["oktmo"] = pd.NA
    crosswalk["bdmo_name"] = pd.NA
    crosswalk["match_method"] = "none_no_upstream_territory_id"
    crosswalk["match_status"] = "UNRESOLVED_NO_UPSTREAM_TERRITORY_ID"
    crosswalk.to_csv(output / "municipality_crosswalk.csv", index=False)

    registry = territory.loc[:, ["oktmo", "official_name", "region_code"]].rename(
        columns={"official_name": "sberindex_name"}
    )
    registry["rosstat_name"] = pd.NA
    registry["exists"] = pd.NA
    registry["name_status"] = "UNAVAILABLE_OFFICIAL_REGISTRY_NOT_RETRIEVED"
    registry["region_status"] = "UNAVAILABLE_OFFICIAL_REGISTRY_NOT_RETRIEVED"
    registry.to_csv(output / "oktmo_registry_validation.csv", index=False)

    source_entries = [
        {
            "source_key": "sberindex_municipality_directory_rar",
            "source_url": exp["download_url"],
            "resolved_source_url": exp["resolved_download_url"],
            "retrieved_utc": exp["retrieved_utc"],
            "filename": str(Path(exp["directory_archive"])),
            "sha256": sha256(Path(exp["directory_archive"])),
            "size_bytes": Path(exp["directory_archive"]).stat().st_size,
            "license": exp["license"],
            "citation": exp["citation"],
        },
        {
            "source_key": "sberindex_directory_workbook_extracted",
            "source_url": exp["download_url"],
            "resolved_source_url": exp["resolved_download_url"],
            "retrieved_utc": None,
            "filename": str(directory_path),
            "sha256": sha256(directory_path),
            "size_bytes": directory_path.stat().st_size,
            "license": exp["license"],
            "citation": "derived only by extracting the preserved RAR; not independently downloaded",
        },
    ]
    pd.DataFrame(source_entries).to_csv(output / "source_manifest.csv", index=False)

    audit = {
        "reference_total": len(reference),
        **identity_audit,
        "mapped_to_oktmo": 0,
        "validated_in_rosstat_registry": 0,
        "matched_population": 0,
        "matched_wage": 0,
        "matched_employment": 0,
        "matched_investment": 0,
        "missing_oktmo": int(len(reference)),
        "oktmo_not_in_registry": 0,
        "version_conflict": 0,
        "other_conflict": 0,
        "directory_snapshot_rows": len(snapshot),
        "directory_snapshot_duplicate_oktmo": int(snapshot["oktmo"].duplicated().sum()),
        "registry_validation_status": "UNAVAILABLE_OFFICIAL_REGISTRY_TLS_CERTIFICATE_NOT_TRUSTED_BY_HOST",
        "status": "BLOCKED_NO_UPSTREAM_TERRITORY_ID_IN_SBERINDEX_RAW_PANEL",
    }
    (output / "matching_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "CROSSWALK_AUDIT.md").write_text(
        "# External BDMO crosswalk — SberIndex-directory gate\n\n"
        "## Result\n\n"
        "| Outcome | Count |\n| --- | ---: |\n"
        f"| Reference municipalities | {len(reference):,} |\n"
        f"| Mapped from original `territory_id` | {identity_audit['mapped_to_territory_id']:,} |\n"
        "| Mapped to OKTMO | 0 |\n| Validated in Rosstat registry | 0 |\n"
        "| Matched BDMO population / wage / employment / investment | 0 / 0 / 0 / 0 |\n"
        f"| Unresolved | {identity_audit['missing_territory_id']:,} |\n\n"
        "## Gate decision\n\n"
        "The official SberIndex directory was downloaded and its 2024 snapshot is valid and one-to-one by "
        "`territory_id`. The original behavioural source (`spending.csv.zip`) has only `mo` as the "
        "municipality field and has no `territory_id`, `municipality_id`, `mo_id`, `raw_id`, region or "
        "OKTMO. No raw-to-reference identifier mapping is stored in this checkout. In accordance with the "
        "protocol, this run does not attempt an exact name-only join and does not use fuzzy matching.\n\n"
        "Rosstat's prescribed registry endpoint was not downloaded because this host cannot establish a trusted "
        "TLS connection to it. `oktmo_registry_validation.csv` deliberately records this as unavailable rather "
        "than marking codes absent. It is a validation-layer limitation, not evidence against an OKTMO.\n\n"
        "No external-profile statistics, transition tests, pairwise tests or prediction were run because the "
        "identifier gate remains closed.\n",
        encoding="utf-8",
    )
    manifest = {
        "config_sha256": sha256(config_file),
        "source_manifest": "source_manifest.csv",
        "required_directory_columns": sorted(DIRECTORY_COLUMNS),
        "raw_spending_columns": raw_columns,
        "audit": audit,
    }
    (output / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "COMPLETED.json").write_text(
        json.dumps({"status": audit["status"], "output": str(output)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/external_bdmo_sberindex_directory_2024.yaml")
    main(parser.parse_args().config)
