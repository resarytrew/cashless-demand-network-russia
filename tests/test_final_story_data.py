import json
import math
from pathlib import Path


def test_final_story_assets_reconcile_and_contain_no_nan():
    root = Path("outputs/final_competition_upgrade/story_data")
    assert len(json.loads((root / "municipalities.json").read_text(encoding="utf-8"))) == 1903
    profiles = json.loads((root / "profiles.json").read_text(encoding="utf-8"))
    assert {item["technical_label"] for item in profiles} == set("ABCDEFG")
    assert len({item["status"] for item in profiles if item["technical_label"] == "C"}) == 1
    assert next(item for item in profiles if item["technical_label"] == "C")["status"] != "ROBUST_TYPE"
    for file in root.glob("*.json"):
        def walk(item):
            if isinstance(item, dict): return all(walk(value) for value in item.values())
            if isinstance(item, list): return all(walk(value) for value in item)
            return not isinstance(item, float) or math.isfinite(item)
        assert walk(json.loads(file.read_text(encoding="utf-8"))), file
