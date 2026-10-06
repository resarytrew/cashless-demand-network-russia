"""Copy saved external evidence into a public display contract; no fitted models."""
from pathlib import Path
import csv
import hashlib
import json

import yaml

ROOT = Path(__file__).resolve().parents[1]


def build():
    config_path = ROOT / "configs/landing_evidence.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    paths = {key: ROOT / value for key, value in config["inputs"].items()}
    regional = json.loads(paths["regional"].read_text(encoding="utf-8"))
    prediction = json.loads(paths["prediction"].read_text(encoding="utf-8"))
    with paths["profiles"].open(encoding="utf-8-sig", newline="") as stream:
        profiles = list(csv.DictReader(stream))
    artifact = {
        "schema": config["schema_version"],
        "profile_statistics": profiles,
        "regional": {key: regional[key] for key in ("grouped_cv", "region_only")},
        "prediction": prediction,
        "provenance": {
            "scope": "Saved external interpretation; no clustering or status changes",
            "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
            "inputs": {key: {"path": config["inputs"][key],
                             "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                       for key, path in paths.items()},
        },
    }
    return artifact, ROOT / config["output"]


if __name__ == "__main__":
    artifact, output = build()
    output.write_text(json.dumps(artifact, ensure_ascii=False, separators=(",", ":"),
                                 allow_nan=False) + "\n", encoding="utf-8")
    print(f"Copied saved evidence to {output}")
