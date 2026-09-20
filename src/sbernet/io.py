from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import zipfile

import pandas as pd


@dataclass(frozen=True)
class PanelAudit:
    unique_names: int
    ambiguous_names: int
    complete_names: int
    strict_panel_names: int


def read_semicolon_zip(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    with zipfile.ZipFile(path) as zf:
        members = [x for x in zf.namelist() if not x.endswith("/")]
        if len(members) != 1:
            raise ValueError(f"Expected one file inside {path}, found {len(members)}")
        with zf.open(members[0]) as fh:
            return pd.read_csv(fh, sep=";")


def build_strict_panel(
    raw: pd.DataFrame,
    expected_months: int,
    required_categories: list[str],
) -> tuple[pd.DataFrame, list[str], PanelAudit]:
    df = raw.copy()
    df["period"] = pd.to_datetime(df["period"])

    unique_names = df["mo"].nunique()

    multiplicity = df.groupby(["mo", "category_15", "period"]).size()
    ambiguous = set(
        multiplicity[multiplicity > 1].reset_index()["mo"].astype(str)
    )

    counts = (
        df[df["category_15"].isin(required_categories)]
        .groupby(["mo", "category_15"])["period"]
        .nunique()
        .unstack(fill_value=0)
    )

    complete = [
        str(name)
        for name, row in counts.iterrows()
        if all(row.get(cat, 0) == expected_months for cat in required_categories)
    ]

    strict = sorted(set(complete) - ambiguous)
    panel = df[df["mo"].astype(str).isin(strict)].copy()

    audit = PanelAudit(
        unique_names=unique_names,
        ambiguous_names=len(ambiguous),
        complete_names=len(complete),
        strict_panel_names=len(strict),
    )
    return panel, strict, audit
