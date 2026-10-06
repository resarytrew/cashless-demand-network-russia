"""Presentation contract: exact saved labels, complete counts, no invented external data."""
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_landing_data import build  # noqa: E402


def test_landing_derivative_is_deterministic_and_current():
    first, _ = build()
    second, _ = build()
    assert first == second
    assert first == json.loads((ROOT / "site/data/research.json").read_text(encoding="utf-8"))
    assert len(first["municipalities"]) == 1904
    assert sum(p["n"] for p in first["profiles"]) == 1899
    assert sum(r["profile"] == "micro" for r in first["municipalities"]) == 5
    assert sum(r["population"] is not None for r in first["municipalities"]) == 1903
    assert sum(r["wage"] is not None for r in first["municipalities"]) == 1890
    assert sum(r["switches"] <= 2 for r in first["municipalities"]) == 1624


def test_flows_conserve_every_municipality_and_saved_membership():
    data, _ = build()
    labels = pd.read_csv(ROOT / "outputs/baseline/supra_labels.csv", index_col=0)
    for r in data["municipalities"]:
        assert r["trajectory"] == labels.loc[r["name"]].astype(int).tolist()
    for step in range(3):
        flows = [f for f in data["flows"] if f["step"] == step]
        assert sum(f["n"] for f in flows) == 1904
        source_counts = labels[data["flowMonths"][step]].value_counts().to_dict()
        for c, n in source_counts.items():
            assert sum(f["n"] for f in flows if f["source"] == c) == n


def test_map_ids_match_verified_external_coverage():
    data, _ = build()
    geometry = json.loads((ROOT / "site/data/municipalities.geojson").read_text())
    ids = [f["properties"]["id"] for f in geometry["features"]]
    assert len(ids) == len(set(ids)) == 1903
    assert set(ids) == {r["id"] for r in data["municipalities"] if r["population"] is not None}


def test_public_external_evidence_copies_saved_statistics_without_refitting():
    from scripts.build_landing_evidence import build as build_evidence
    import hashlib

    first, output = build_evidence()
    second, _ = build_evidence()
    assert first == second == json.loads(output.read_text(encoding="utf-8"))
    for source in first["provenance"]["inputs"].values():
        assert hashlib.sha256((ROOT / source["path"]).read_bytes()).hexdigest() == source["sha256"]
    landing = json.loads((ROOT / "site/data/research.json").read_text(encoding="utf-8"))
    for profile in landing["profiles"]:
        for variable, field in [("wage", "wage_median"), ("population", "population_median"),
                                ("employment_total", "employment_median")]:
            row = next(r for r in first["profile_statistics"]
                       if r["variable"] == variable and r["profile"] == profile["technical_label"])
            assert float(row["median"]) == profile[field]
            assert float(row["q25"]) <= float(row["median"]) <= float(row["q75"])
    assert first["regional"]["grouped_cv"] == json.loads(
        (ROOT / "outputs/final_competition_upgrade/story_data_v3/regional_generalization.json")
        .read_text(encoding="utf-8"))["grouped_cv"]
