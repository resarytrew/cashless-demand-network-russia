"""Publish saved Round23 neighbors for cartographic presentation; no refitting."""
import csv
import hashlib
import json
import platform
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def build():
    config_path = ROOT / "configs/landing_network.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    source = ROOT / config["input"]
    research = ROOT / config["municipalities"]
    municipalities = json.loads(research.read_text(encoding="utf-8"))["municipalities"]
    by_name = {m["name"]: m["id"] for m in municipalities}
    edges = []
    with source.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if int(row["rank"]) not in config["presentation"]["ranks"]:
                continue
            edges.append({"source": by_name[row["municipality"]],
                          "target": by_name[row["neighbor"]],
                          "rank": int(row["rank"]),
                          "km": float(row["geographic_km"]),
                          "weight": float(row["edge_weight"]),
                          "from": [float(row["longitude"]), float(row["latitude"])],
                          "to": [float(row["neighbor_longitude"]), float(row["neighbor_latitude"])]})
    return {"schema": config["schema_version"], "edges": edges,
            "presentation": config["presentation"],
            "provenance": {"scope": "Saved directed top-three graph neighbors, Round23; not the complete network",
                           "input": config["input"],
                           "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                           "municipalities_sha256": hashlib.sha256(research.read_bytes()).hexdigest(),
                           "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
                           "python": platform.python_version(), "pyyaml": yaml.__version__,
                           "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                           "seed": None}}, ROOT / config["output"]


if __name__ == "__main__":
    artifact, output = build()
    output.write_text(json.dumps(artifact, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")
    print(f"Published {len(artifact['edges'])} saved neighbor relations")
