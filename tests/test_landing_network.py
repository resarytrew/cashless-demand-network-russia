import csv
import hashlib
import json
import re

from scripts.build_landing_network import ROOT, build


def test_network_export_replays_saved_neighbors_deterministically():
    artifact, output = build()
    second, _ = build()
    assert artifact == second
    saved = json.loads(output.read_text(encoding="utf-8"))
    # Environment provenance describes the original export, not today's checkout.
    for document in (saved, artifact):
        assert re.fullmatch(r"[0-9a-f]{40}", document["provenance"]["git_commit"])
        for field in ("git_commit", "python", "pyyaml"):
            assert document["provenance"].pop(field)
    assert artifact == saved
    source = ROOT / artifact["provenance"]["input"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == artifact["provenance"]["input_sha256"]
    with source.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == len(artifact["edges"])
    ids = {m["id"] for m in json.loads((ROOT / "site/data/research.json").read_text(encoding="utf-8"))["municipalities"]}
    for raw, edge in zip(rows, artifact["edges"]):
        assert edge["source"] in ids and edge["target"] in ids
        assert edge["rank"] in (1, 2, 3)
        assert edge["km"] == float(raw["geographic_km"])
        assert edge["weight"] == float(raw["edge_weight"])
        assert len(edge["from"]) == len(edge["to"]) == 2
