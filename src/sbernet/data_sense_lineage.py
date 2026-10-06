"""Exact data-lineage matching from official Data -> Sense consumption data.

No municipality names participate in candidate generation.  A candidate is
created exclusively by an exact 24-month x category value fingerprint.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib

import pandas as pd


FINGERPRINT_COLUMNS = ["date", "category", "value"]


def standardise_current(frame: pd.DataFrame) -> pd.DataFrame:
    """Translate the supplied legacy raw schema without joining on names."""
    out = frame.loc[:, ["mo", "period", "category_15", "value"]].copy()
    out["date"] = pd.to_datetime(out.pop("period")).dt.strftime("%Y-%m")
    out = out.rename(columns={"category_15": "category"})
    out["value"] = pd.to_numeric(out["value"], errors="raise").astype("int64")
    return out.loc[:, ["mo", *FINGERPRINT_COLUMNS]]


def standardise_official(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate and standardise official Data -> Sense consumption records."""
    required = {"territory_id", *FINGERPRINT_COLUMNS}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Official consumption is missing required fields: {sorted(missing)}")
    out = frame.loc[:, ["territory_id", *FINGERPRINT_COLUMNS]].copy()
    out["territory_id"] = out["territory_id"].astype("int64")
    out["date"] = out["date"].astype(str)
    out["value"] = pd.to_numeric(out["value"], errors="raise").astype("int64")
    return out


def fingerprint(frame: pd.DataFrame) -> str:
    """Hash every observed month/category/value record in canonical order."""
    ordered = frame.loc[:, FINGERPRINT_COLUMNS].sort_values(
        ["date", "category", "value"], kind="stable"
    )
    serial = ordered.to_csv(index=False, header=False, lineterminator="\n")
    return hashlib.sha256(serial.encode("utf-8")).hexdigest()


def fingerprints(frame: pd.DataFrame, key: str) -> dict[object, str]:
    return {value: fingerprint(group) for value, group in frame.groupby(key, sort=False)}


def exact_lineage_matches(current_strict: pd.DataFrame, official: pd.DataFrame) -> pd.DataFrame:
    """Return candidates from exact fingerprints, never from a textual name."""
    current_fp = fingerprints(current_strict, "mo")
    official_fp = fingerprints(official, "territory_id")
    inverse: dict[str, list[int]] = defaultdict(list)
    for territory_id, digest in official_fp.items():
        inverse[digest].append(int(territory_id))
    rows = []
    for reference_mo, digest in current_fp.items():
        candidates = sorted(inverse.get(digest, []))
        rows.append(
            {
                "reference_mo": reference_mo,
                "fingerprint_sha256": digest,
                "candidate_territory_id": candidates[0] if len(candidates) == 1 else pd.NA,
                "candidate_count": len(candidates),
                "fingerprint_distance": 0 if len(candidates) == 1 else pd.NA,
            }
        )
    return pd.DataFrame(rows).sort_values("reference_mo", kind="stable").reset_index(drop=True)


def value_multiset_equal(current: pd.DataFrame, official: pd.DataFrame) -> bool:
    """Test source equivalence while intentionally omitting municipality identifiers."""
    def records(frame: pd.DataFrame) -> Counter[tuple[str, str, int]]:
        return Counter(
            zip(
                frame["date"].astype(str),
                frame["category"].astype(str),
                frame["value"].astype(int),
                strict=True,
            )
        )

    return records(current) == records(official)


def complete_official_in_ambiguous_current(
    current: pd.DataFrame, official: pd.DataFrame, expected_records: int
) -> pd.DataFrame:
    """Identify complete official trajectories embedded in ambiguous legacy names.

    This is a reconciliation calculation, not a match used to restore the
    reference panel.  It proves why the strict name-keyed panel excludes them.
    """
    raw_counters = {
        name: Counter(zip(group.date, group.category, group.value, strict=True))
        for name, group in current.groupby("mo", sort=False)
    }
    inverted: dict[tuple[str, str, int], set[str]] = defaultdict(set)
    for name, counter in raw_counters.items():
        for record in counter:
            inverted[record].add(name)

    rows = []
    for territory_id, group in official.groupby("territory_id", sort=False):
        if len(group) != expected_records:
            continue
        counter = Counter(zip(group.date, group.category, group.value, strict=True))
        possible: set[str] | None = None
        for record in counter:
            names = inverted[record]
            possible = names if possible is None else possible & names
            if not possible:
                break
        confirmed = [
            name for name in sorted(possible or []) if raw_counters[name] >= counter
        ]
        rows.append(
            {
                "territory_id": int(territory_id),
                "current_name_candidate_count": len(confirmed),
                "current_name_candidate": confirmed[0] if len(confirmed) == 1 else pd.NA,
                "embedded_in_current_name": len(confirmed) == 1,
            }
        )
    return pd.DataFrame(rows)
