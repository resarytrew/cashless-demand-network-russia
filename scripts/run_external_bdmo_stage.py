"""Download-independent processing of locally preserved BDMO publisher archives."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from sbernet.external_bdmo import collapse_nonconflicting, conservative_crosswalk, read_indicator_2024


def digest(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(config_path: str) -> None:
    cfg = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    output = Path(cfg["experiment"]["output_dir"])
    completed = output / "COMPLETED.json"
    if completed.exists():
        raise FileExistsError(f"Completed output exists: {output}")
    output.mkdir(parents=True, exist_ok=True)
    processed = Path("data/external/processed"); matching = Path("data/external/matching")
    processed.mkdir(parents=True, exist_ok=True); matching.mkdir(parents=True, exist_ok=True)
    manual = matching / "manual_overrides.csv"
    if not manual.exists():
        pd.DataFrame(columns=["reference_name", "external_oktmo", "reviewer", "rationale", "source_url"]).to_csv(manual, index=False)
    overrides = pd.read_csv(manual, dtype=str)
    selected, conflicts, stats = [], [], {}
    for name, spec in cfg["sources"].items():
        frame, read_stats = read_indicator_2024(spec, cfg["experiment"]["target_year"])
        flat, problem = collapse_nonconflicting(frame, spec["variable"])
        selected.append(flat); conflicts.append(problem); stats[name] = {**read_stats, "accepted_rows": len(flat), "conflicts": len(problem)}
    entities = selected[0][["oktmo_stable", "oktmo", "region_id", "region_name", "municipality"]].copy()
    for frame in selected:
        entities = entities.merge(frame.drop(columns=["oktmo_stable", "region_id", "region_name", "municipality", "indicator_unit"], errors="ignore"), on="oktmo", how="outer", validate="one_to_one")
    entities.to_csv(processed / "bdmo_2024_indicator_panel_by_oktmo.csv", index=False)
    pd.concat(conflicts, ignore_index=True).to_csv(processed / "bdmo_2024_indicator_conflicts.csv", index=False)
    reference = pd.read_csv(cfg["experiment"]["reference_labels"], index_col=0)
    crosswalk, unmatched, audit = conservative_crosswalk(reference.index.tolist(), entities, overrides)
    crosswalk.to_csv(matching / "municipality_crosswalk.csv", index=False)
    unmatched.to_csv(matching / "unmatched.csv", index=False)
    (matching / "matching_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    quality = []
    for name, spec in cfg["sources"].items():
        value = spec["variable"]
        available = int(entities[value].notna().sum()) if value in entities else 0
        quality.append({"variable": value, "source": "BDMO/Rosstat processed by Если быть точным", "year": 2024,
                        "source_coverage_n": available, "reference_coverage_n": 0, "coverage_n": 0, "coverage_pct": 0.0,
                        "missing_n": len(reference), "median": None, "p01": None, "p99": None,
                        "unit": spec["unit"], "quality_status": "BLOCKED_FOR_REFERENCE_VALIDATION",
                        "reason": audit["blocking_reason"]})
    pd.DataFrame(quality).to_csv(output / "data_quality.csv", index=False)
    provenance = []
    catalog = Path(cfg["experiment"]["catalog_raw_file"])
    provenance.append({"source_key": "publisher_catalog", "source_url": cfg["experiment"]["catalog_url"],
                       "retrieved_utc": datetime.now(timezone.utc).isoformat(), "raw_file": str(catalog),
                       "sha256": digest(catalog), "bytes": catalog.stat().st_size, "indicator_code": None,
                       "variable": "publisher_indicator_catalog", "unit": None})
    for name, spec in cfg["sources"].items():
        path = Path(spec["raw_file"])
        provenance.append({"source_key": name, "source_url": spec["url"], "retrieved_utc": datetime.now(timezone.utc).isoformat(),
                           "raw_file": str(path), "sha256": digest(path), "bytes": path.stat().st_size,
                           "indicator_code": spec["indicator_code"], "variable": spec["variable"], "unit": spec["unit"]})
    pd.DataFrame(provenance).to_csv(output / "source_manifest.csv", index=False)
    Path("docs/EXTERNAL_DATA_PROVENANCE.md").write_text(
        "# External data provenance\n\n"
        "Source: the public BDMO-derived publication [Муниципальная статистика России с 2005 года](https://tochno.st/datasets/bdmo), published by «Если быть точным» from Rosstat БД ПМО. The locally preserved archive inventory, URLs, retrieval timestamps and SHA-256 values are `outputs/final_competition_upgrade/external_validation/source_manifest.csv`. Citation: " + cfg["experiment"]["publisher_citation"] + ".\n\n"
        "The publisher page did not state a machine-readable reuse license at retrieval; `" + cfg["experiment"]["source_license_status"] + "`. Original ZIPs remain in `data/external/raw/`; processed 2024 tables preserve BDMO's stable OKTMO fields and never alter the SberIndex clustering.\n\n"
        "Matching is intentionally blocked until a nationwide reference municipality-to-region/OKTMO crosswalk is supplied or independently built with a reviewed source. Name-only matches are not accepted.\n", encoding="utf-8")
    manifest = {"config_sha256": digest(config_path), "raw_sources": provenance, "read_stats": stats, "matching_audit": audit,
                "status": "BLOCKED_PENDING_REFERENCE_OKTMO_OR_REGION_CROSSWALK"}
    (output / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    completed.write_text(json.dumps({"status": manifest["status"], "files": ["data_quality.csv", "source_manifest.csv", "run_manifest.json"]}, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--config", default="configs/external_bdmo_2024.yaml")
    main(parser.parse_args().config)
