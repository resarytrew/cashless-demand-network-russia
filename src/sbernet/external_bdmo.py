"""Deterministic ingestion and conservative matching for publisher BDMO extracts."""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd


def normalize_municipality_name(value: str) -> str:
    """Normalise only typography; do not remove administrative words or fuzzy-match."""
    value = unicodedata.normalize("NFKC", str(value)).casefold().replace("ё", "е")
    return re.sub(r"\s+", " ", re.sub(r"[^\w]+", " ", value, flags=re.UNICODE)).strip()


def primary_csv_member(path: Path) -> str:
    from zipfile import ZipFile
    with ZipFile(path) as archive:
        members = [item for item in archive.namelist() if item.endswith(".csv") and "/" not in item]
    if len(members) != 1:
        raise ValueError(f"Expected exactly one primary CSV in {path}, got {members}")
    return members[0]


def read_indicator_2024(spec: dict, year: int, chunksize: int = 250_000) -> tuple[pd.DataFrame, dict]:
    """Select a declared BDMO indicator/dimension without imputing or aggregating."""
    from zipfile import ZipFile
    path = Path(spec["raw_file"])
    member = primary_csv_member(path)
    selected: list[pd.DataFrame] = []
    source_rows = year_rows = dimension_rows = upper_rows = 0
    with ZipFile(path) as archive:
        with archive.open(member) as raw:
            for chunk in pd.read_csv(raw, sep=";", chunksize=chunksize, low_memory=False, dtype={"oktmo": "string", "oktmo_stable": "string"}):
                source_rows += len(chunk)
                chunk = chunk.loc[chunk["year"].eq(year)].copy()
                year_rows += len(chunk)
                column = spec.get("dimension_column")
                if column:
                    if "dimension_value" in spec:
                        chunk = chunk.loc[chunk[column].eq(spec["dimension_value"])]
                    else:
                        chunk = chunk.loc[chunk[column].fillna("").str.startswith(spec["dimension_prefix"])]
                if "period_value" in spec:
                    chunk = chunk.loc[chunk["indicator_period"].eq(spec["period_value"])]
                dimension_rows += len(chunk)
                chunk = chunk.loc[chunk["mun_level"].fillna("").str.contains("верхнего уровня", regex=False)]
                upper_rows += len(chunk)
                selected.append(chunk)
    frame = pd.concat(selected, ignore_index=True) if selected else pd.DataFrame()
    return frame, {"source_rows": source_rows, "year_rows": year_rows,
                   "dimension_rows": dimension_rows, "upper_level_rows": upper_rows,
                   "primary_csv_member": member}


def collapse_nonconflicting(frame: pd.DataFrame, variable: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Retain one value per current OKTMO; preserve stable OKTMO for transformations."""
    columns = ["oktmo_stable", "oktmo", "region_id", "region_name", "municipality", "indicator_value", "indicator_unit"]
    frame = frame[columns].copy()
    frame["oktmo"] = frame["oktmo"].astype("string")
    frame["indicator_value"] = pd.to_numeric(frame["indicator_value"], errors="coerce")
    grouped = frame.groupby("oktmo", dropna=False, sort=True)
    conflicts = []
    accepted = []
    for code, group in grouped:
        values = group["indicator_value"].dropna().unique()
        names = group[["region_name", "municipality"]].drop_duplicates()
        if len(values) == 1 and len(names) == 1 and pd.notna(code):
            row = group.iloc[0][["oktmo_stable", "oktmo", "region_id", "region_name", "municipality", "indicator_unit"]].to_dict()
            row[variable] = float(values[0]); accepted.append(row)
        else:
            conflicts.append({"variable": variable, "oktmo": code, "n_rows": len(group),
                              "n_distinct_values": len(values), "n_distinct_names": len(names),
                              "reason": "duplicate_or_conflicting_2024_current_oktmo"})
    return pd.DataFrame(accepted), pd.DataFrame(conflicts)


def conservative_crosswalk(reference_names: list[str], entities: pd.DataFrame, overrides: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Build an auditable crosswalk; missing reference region/OKTMO blocks name matches."""
    entity = entities.copy()
    entity["normalized_external_name"] = entity["municipality"].map(normalize_municipality_name)
    candidates = entity.groupby("normalized_external_name").size().to_dict()
    override_by_reference = overrides.set_index("reference_name") if not overrides.empty else pd.DataFrame()
    rows = []
    for index, name in enumerate(reference_names):
        norm = normalize_municipality_name(name)
        override = override_by_reference.loc[name] if not overrides.empty and name in override_by_reference.index else None
        if override is not None:
            hit = entity.loc[entity["oktmo"].eq(str(override["external_oktmo"]))]
            if len(hit) == 1:
                external = hit.iloc[0]; method, confidence, manual = "manual_override", "reviewed", True
            else:
                external = None; method, confidence, manual = "unmatched_invalid_manual_override", "none", True
        else:
            external = None; method, confidence, manual = "unmatched_reference_region_or_oktmo_unavailable", "none", False
        rows.append({"reference_municipality_id": index, "reference_name": name, "region": None,
                     "external_id": None if external is None else external["oktmo"],
                     "external_name": None if external is None else external["municipality"],
                     "match_method": method, "match_confidence": confidence, "manual_override": manual,
                     "normalized_name_candidate_count": int(candidates.get(norm, 0))})
    crosswalk = pd.DataFrame(rows)
    unmatched = crosswalk.loc[crosswalk.external_id.isna()].copy()
    audit = {"reference_n": len(crosswalk), "matched_by_oktmo": 0, "matched_by_transformation": 0,
             "matched_by_normalized_identity": 0,
             "matched_manual": int((crosswalk.manual_override & crosswalk.external_id.notna()).sum()),
             "unmatched": int(len(unmatched)),
             "one_to_many_name_candidates": int((crosswalk.normalized_name_candidate_count > 1).sum()),
             "many_to_one_conflicts": 0,
             "blocking_reason": "reference panel supplies neither nationwide region nor OKTMO; global name-only matching is prohibited"}
    return crosswalk, unmatched, audit


def municipality_oktmo11_to_8(
    lineage: pd.DataFrame, directory: pd.DataFrame, bdmo_oktmo8: set[str]
) -> pd.DataFrame:
    """Apply the explicit, gated municipality-level OKTMO transformation.

    ``lineage`` must contain only the original reference rows.  The function
    neither tries to repair a lineage conflict nor uses a municipal name as a
    join key.  The BDMO-code set is an independent existence gate for the
    proposed eight-digit code.
    """
    required = {"reference_mo", "territory_id", "status"}
    if missing := required - set(lineage.columns):
        raise ValueError(f"Lineage file misses columns: {sorted(missing)}")
    directory = directory.set_index("territory_id", verify_integrity=True)
    rows: list[dict] = []
    for item in lineage.itertuples(index=False):
        tid = getattr(item, "territory_id")
        status = getattr(item, "status")
        record = {
            "territory_id": tid,
            "official_name": pd.NA,
            "region": pd.NA,
            "oktmo11": pd.NA,
            "last3": pd.NA,
            "last6": pd.NA,
            "candidate_oktmo8": pd.NA,
            "municipality_type": pd.NA,
            "transform_allowed": False,
            "reason": "EXCLUDED_UNRESOLVED_LINEAGE",
        }
        if status != "VERIFIED_DATA_LINEAGE_MATCH" or pd.isna(tid):
            rows.append(record)
            continue
        source = directory.loc[int(tid)]
        raw = str(source["oktmo"])
        digits = raw.replace("-", "")
        record.update({
            "official_name": source["municipal_district_name"],
            "region": str(source["region_code"]),
            "oktmo11": digits,
            "last3": digits[-3:] if len(digits) >= 3 else pd.NA,
            "last6": digits[-6:] if len(digits) >= 6 else pd.NA,
            "candidate_oktmo8": digits[:8] if len(digits) == 11 and digits.isdigit() else pd.NA,
            "municipality_type": "SBERINDEX_DIRECTORY_MUNICIPALITY",
        })
        if len(digits) != 11 or not digits.isdigit():
            record["reason"] = "INVALID_11_DIGIT_OKTMO"
        elif digits[-3:] != "000":
            record["reason"] = "NOT_MUNICIPALITY_LEVEL_REVIEW_REQUIRED"
        elif digits[:8] not in bdmo_oktmo8:
            record["reason"] = "CANDIDATE_OKTMO8_NOT_IN_BDMO_MUNICIPALITY_CODES"
        else:
            record["transform_allowed"] = True
            record["reason"] = "VALIDATED_11_TO_8_MUNICIPALITY_TRANSFORMATION"
        rows.append(record)
    audit = pd.DataFrame(rows)
    allowed = audit.loc[audit["transform_allowed"]]
    duplicate = allowed["candidate_oktmo8"].duplicated(keep=False)
    if duplicate.any():
        duplicate_codes = set(allowed.loc[duplicate, "candidate_oktmo8"])
        audit.loc[audit["candidate_oktmo8"].isin(duplicate_codes), "transform_allowed"] = False
        audit.loc[audit["candidate_oktmo8"].isin(duplicate_codes), "reason"] = "MANY_TO_ONE_TRANSFORMATION_CONFLICT"
    return audit
