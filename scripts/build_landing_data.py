"""Package saved evidence for the static landing. No clustering or model fitting."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import subprocess
import importlib.metadata

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def build(config_path=ROOT / "configs/landing.yaml"):
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    inputs, spec = config["inputs"], config["presentation"]
    story = ROOT / inputs["story"]
    atlas = pd.read_csv(ROOT / inputs["atlas"])
    labels = pd.read_csv(ROOT / inputs["labels"], index_col=0)
    lineage = pd.read_csv(ROOT / inputs["lineage"])
    external = read_json(story / "municipalities.json")
    assert len(atlas) == spec["expected_municipalities"]
    assert labels.shape == (spec["expected_municipalities"], spec["expected_months"])
    assert labels.index.is_unique and atlas.municipality.is_unique
    assert set(labels.index) == set(atlas.municipality)
    assert len(external) == spec["expected_external_records"]
    by_territory = {int(r["territory_id"]): r for r in external}
    territory = {r.reference_mo: int(r.territory_id) for r in lineage.itertuples()
                 if pd.notna(r.territory_id)}
    profiles = read_json(story / "profiles.json")
    mapping = {v: k for k, v in spec["profile_communities"].items()}
    rows = []
    for r in atlas.itertuples(index=False):
        e = by_territory.get(territory.get(r.municipality), {})
        series = [int(v) for v in labels.loc[r.municipality]]
        assert mapping.get(series[-1], "micro") == r.reference_profile
        rows.append({
            "id": r.panel_index, "name": r.municipality,
            "profile": r.reference_profile, "consensus": r.consensus_class,
            "stability": r.stability_class,
            "affinity": [getattr(r, "affinity_share_" + p) for p in spec["profile_communities"]],
            "margin": r.affinity_margin, "trajectory": series,
            "switches": sum(a != b for a, b in zip(series, series[1:])),
            "region": e.get("region"), "wage": e.get("wage"),
            "population": e.get("population"), "employment": e.get("employment"),
        })
    # Use exact saved month-end labels, not majority labels or profile-name remapping.
    months = spec["halfyear_month_indices"]
    flows = []
    for step, (left, right) in enumerate(zip(months, months[1:])):
        counts = labels.groupby([labels.columns[left], labels.columns[right]]).size()
        flows.extend({"step": step, "source": int(a), "target": int(b), "n": int(n)}
                     for (a, b), n in counts.items())
    assert sum(r["population"] is not None for r in rows) == spec["expected_external_records"]
    retention = pd.read_csv(ROOT / inputs["retention"])
    assert retention.seed.nunique() == 50
    payload = {
        "schema": config["schema_version"], "summary": read_json(story / "summary.json"),
        "profiles": profiles, "colors": spec["colors"], "profileCommunities": spec["profile_communities"],
        "months": list(labels.columns), "flowMonths": [labels.columns[i] for i in months],
        "municipalities": rows, "flows": flows,
        "reference": yaml.safe_load((ROOT / inputs["reference"]).read_text(encoding="utf-8")),
        "retention": retention.groupby("archetype")[["retention", "precision"]].mean().to_dict(orient="index"),
    }
    return payload, config


def main():
    config_path = ROOT / "configs/landing.yaml"
    payload, config = build(config_path)
    output = ROOT / config["output"]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    # A lazily loaded map derivative. Simplification affects drawing only.
    import geopandas as gpd
    from shapely.geometry.polygon import orient
    from shapely.geometry import MultiPolygon, mapping

    geometry = gpd.read_file(ROOT / config["inputs"]["geometry"])
    assert geometry.reference_mo.is_unique
    assert len(geometry) == config["presentation"]["expected_external_records"]
    simplified = geometry.to_crs(6933).geometry.simplify(
        config["presentation"]["map_simplification_m"], preserve_topology=True
    ).to_crs(4326)
    ids = {r["name"]: r["id"] for r in payload["municipalities"]}
    digits = config["presentation"]["map_coordinate_decimals"]

    def rounded(value):
        if isinstance(value, (list, tuple)):
            return [rounded(v) for v in value]
        return round(value, digits)

    features = []
    for r, shape in zip(geometry.itertuples(), simplified):
        shape = (MultiPolygon([orient(p, sign=-1) for p in shape.geoms])
                 if shape.geom_type == "MultiPolygon" else orient(shape, sign=-1))
        geo = mapping(shape)
        features.append({"type": "Feature", "properties": {"id": ids[r.reference_mo]},
                         "geometry": {"type": geo["type"], "coordinates": rounded(geo["coordinates"])}})
    map_path = output.with_name("municipalities.geojson")
    map_path.write_text(json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")), encoding="utf-8")
    paths = [config_path, Path(__file__), *(ROOT / v for k, v in config["inputs"].items() if k != "story")]
    paths += list((ROOT / config["inputs"]["story"]).glob("*.json"))
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    manifest = {
        "scope": "Presentation derivative; saved evidence only; no scientific status change",
        "python": platform.python_version(), "seed": config["presentation"]["seed"],
        "packages": {p: importlib.metadata.version(p) for p in ["pandas", "PyYAML", "geopandas", "shapely", "pyproj"]},
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "config_sha256": sha(config_path), "output_sha256": sha(output),
        "map_sha256": sha(map_path),
        "inputs": {p.relative_to(ROOT).as_posix(): sha(p) for p in paths},
    }
    manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    output.with_name("manifest.json").write_bytes(manifest_text.encode("utf-8"))
    print(f"Built {output.relative_to(ROOT)} ({output.stat().st_size:,} bytes; {len(payload['municipalities'])} municipalities)")


if __name__ == "__main__":
    main()
