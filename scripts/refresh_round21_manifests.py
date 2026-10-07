"""Refresh Round21 hashes after deterministic acceptance-audit finalization."""
from __future__ import annotations

import json
from pathlib import Path

from sbernet.robustness.reproduction_gate import sha256


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def main() -> None:
    out = Path("outputs/round21_structural_sensitivity")
    manifest_path = out / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sources = [
        Path("scripts/run_round21_structural_sensitivity.py"),
        Path("src/sbernet/structural_sensitivity.py"),
        Path("scripts/finalize_round21_tables.py"),
        Path("scripts/refresh_round21_manifests.py"),
    ]
    manifest["source_sha256"] = {str(path): sha256(path) for path in sources}
    manifest["artifact_sha256"] = {
        str(path.relative_to(out)).replace("\\", "/"): sha256(path)
        for path in sorted(out.rglob("*"))
        if path.is_file() and path.name not in {"run_manifest.json", "checksums.sha256", "COMPLETED.json"}
    }
    write_json(manifest_path, manifest)

    checksum_files = [
        path for path in sorted(out.rglob("*"))
        if path.is_file() and path.name not in {"checksums.sha256", "COMPLETED.json"}
    ]
    checksums = out / "checksums.sha256"
    checksums.write_text(
        "\n".join(
            f"{sha256(path)}  {str(path.relative_to(out)).replace(chr(92), '/')}"
            for path in checksum_files
        ) + "\n",
        encoding="utf-8",
    )
    write_json(out / "COMPLETED.json", {
        "status": "COMPLETED", "baseline_unchanged": True,
        "checksums_sha256": sha256(checksums),
    })

    evidence_manifest_path = Path("outputs/evidence_v2_8_0/run_manifest.json")
    evidence = json.loads(evidence_manifest_path.read_text(encoding="utf-8"))
    evidence["round21_manifest_sha256"] = sha256(manifest_path)
    evidence["round21_checksums_sha256"] = sha256(checksums)
    write_json(evidence_manifest_path, evidence)


if __name__ == "__main__":
    main()
