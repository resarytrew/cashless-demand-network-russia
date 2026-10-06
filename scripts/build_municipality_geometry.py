"""Build a web-safe municipal geometry artifact from the official SberIndex archive.

The join is deliberately territory_id-only.  Reference names are included only as
output labels after the verified Data -> Sense lineage gate has supplied the ID.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path

import geopandas as gpd
import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main(config_path: Path) -> None:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))["experiment"]
    output = ROOT / config["output_dir"]
    output.mkdir(parents=True, exist_ok=False)
    year = int(config["target_year"])
    gpkg = ROOT / config["extracted_gpkg"]
    archive = ROOT / config["source_archive"]
    lineage = pd.read_csv(ROOT / config["lineage_csv"], dtype={"territory_id": "Int64"})
    verified = lineage.loc[lineage.status.eq(config["selected_lineage_status"])].copy()
    if len(verified) != 1903 or verified.territory_id.isna().any() or verified.territory_id.duplicated().any():
        raise ValueError("Verified lineage must contain 1,903 unique, non-null territory_id values")

    source = gpd.read_file(gpkg, layer=config["layer"])
    source["territory_id"] = pd.to_numeric(source["territory_id"], errors="raise").astype("int64")
    active = source.loc[source.year_from.le(year) & source.year_to.gt(year)].copy()
    if active.territory_id.duplicated().any():
        duplicated = active.loc[active.territory_id.duplicated(False), "territory_id"].sort_values().unique().tolist()
        raise ValueError(f"Active {year} snapshot has duplicate territory_id values: {duplicated[:10]}")

    joined = verified.loc[:, ["reference_mo", "territory_id"]].merge(
        active.loc[:, ["territory_id", "year_from", "year_to", "geometry"]],
        on="territory_id", how="left", validate="one_to_one", indicator=True,
    )
    joined["geometry_match_status"] = joined.pop("_merge").map({"both": "MATCHED", "left_only": "MISSING_GEOMETRY"})
    missing = joined.loc[joined.geometry_match_status.ne("MATCHED")].copy()
    ambiguities = pd.DataFrame(columns=["territory_id", "reason"])

    profiles = pd.read_csv(ROOT / config["profile_csv"], dtype={"territory_id": "Int64"})
    profile_lookup = profiles.loc[:, ["territory_id", "profile"]].drop_duplicates("territory_id")
    matched = joined.loc[joined.geometry_match_status.eq("MATCHED")].merge(profile_lookup, on="territory_id", how="left", validate="one_to_one")
    gdf = gpd.GeoDataFrame(matched, geometry="geometry", crs=source.crs).to_crs(config["working_crs"])
    representative = gdf.geometry.representative_point()
    gdf["geometry"] = gdf.geometry.simplify(float(config["simplification_tolerance_m"]), preserve_topology=True)
    web = gdf.to_crs(config["geometry_crs"])
    points = gpd.GeoSeries(representative, crs=config["working_crs"]).to_crs(config["geometry_crs"])

    web.loc[:, ["territory_id", "reference_mo", "profile", "year_from", "year_to", "geometry"]].to_file(
        output / "municipality_geometry.geojson", driver="GeoJSON", index=False
    )
    pd.DataFrame({
        "territory_id": web.territory_id.astype(int),
        "reference_mo": web.reference_mo,
        "profile": web.profile,
        "longitude": points.x,
        "latitude": points.y,
    }).to_json(output / "municipality_representative_points.json", orient="records", force_ascii=False)
    joined.drop(columns="geometry").to_csv(output / "geometry_match_audit.csv", index=False)
    missing.drop(columns="geometry").to_csv(output / "missing_geometry_matches.csv", index=False)
    ambiguities.to_csv(output / "ambiguous_geometry_matches.csv", index=False)

    manifest = {
        "status": "COMPLETED",
        "target_year": year,
        "version_semantics": "year_from <= target_year < year_to",
        "join_key": "territory_id",
        "name_matching_used": False,
        "verified_lineage_n": int(len(verified)),
        "geometry_matched_n": int(len(web)),
        "geometry_coverage_pct": float(len(web) / len(verified) * 100),
        "missing_geometry_n": int(len(missing)),
        "ambiguous_geometry_n": int(len(ambiguities)),
        "source": {
            "url": config["source_url"],
            "archive": str(archive.relative_to(ROOT)),
            "archive_sha256": sha256(archive),
            "gpkg": str(gpkg.relative_to(ROOT)),
            "gpkg_sha256": sha256(gpkg),
            "layer": config["layer"],
            "license": config["license"],
        },
        "transformation": {
            "script": "scripts/build_municipality_geometry.py",
            "working_crs": config["working_crs"],
            "output_crs": config["geometry_crs"],
            "simplification": "GeoSeries.simplify(preserve_topology=True)",
            "simplification_tolerance_m": config["simplification_tolerance_m"],
            "point": "geometry.representative_point() before simplification",
        },
        "environment": {"python": platform.python_version(), "geopandas": gpd.__version__},
    }
    (output / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "GEOMETRY_AUDIT.md").write_text(
        "# Municipal geometry artifact audit\n\n"
        f"- Official source: `{config['source_url']}`\n"
        f"- License: {config['license']}\n"
        f"- Source archive SHA-256: `{manifest['source']['archive_sha256']}`\n"
        f"- Extracted GPKG SHA-256: `{manifest['source']['gpkg_sha256']}`\n"
        f"- Layer: `{config['layer']}`; CRS: `{source.crs}`\n"
        f"- 2024 version selection: `year_from <= 2024 < year_to`\n"
        f"- Join: only verified `territory_id`; no name matching\n"
        f"- Coverage: {len(web)}/{len(verified)} ({len(web) / len(verified) * 100:.2f}%)\n"
        f"- Missing geometry: {len(missing)}; ambiguous geometry: {len(ambiguities)}\n"
        f"- Web geometry: EPSG:4326, topology-preserving simplification at {config['simplification_tolerance_m']} m in {config['working_crs']}\n"
        "- Representative points were calculated from original polygons before simplification.\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/municipality_geometry_2024.yaml")
    args = parser.parse_args()
    main(ROOT / args.config)
