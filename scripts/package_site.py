"""Publish one identical static Atlas build to every supported URL prefix."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "site"
DIST = ROOT / "dist"
DESTINATIONS = (DIST, DIST / "atlas", DIST / "site")
CURRENT_CARD_SCHEMA = 4


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if not SOURCE.is_dir():
        raise SystemExit(f"Site source is missing: {SOURCE}")

    source_files = tuple(path for path in SOURCE.rglob("*") if path.is_file())
    if not source_files:
        raise SystemExit(f"Site source is empty: {SOURCE}")

    for destination in DESTINATIONS:
        for source in source_files:
            target = destination / source.relative_to(SOURCE)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    expected_js = sha256(SOURCE / "assets" / "landing.js")
    expected_cards = sha256(SOURCE / "data" / "profile_cards.json")
    for destination in DESTINATIONS:
        if sha256(destination / "assets" / "landing.js") != expected_js:
            raise SystemExit(f"JavaScript publish mismatch: {destination}")
        if sha256(destination / "data" / "profile_cards.json") != expected_cards:
            raise SystemExit(f"Profile-card publish mismatch: {destination}")
        payload = json.loads(
            (destination / "data" / "profile_cards.json").read_text(encoding="utf-8")
        )
        if payload.get("schema") != CURRENT_CARD_SCHEMA:
            raise SystemExit(
                f"Unexpected profile-card schema in {destination}: {payload.get('schema')}"
            )

    print(
        f"Published {len(source_files)} files to "
        + ", ".join(str(path.relative_to(ROOT)) for path in DESTINATIONS)
    )


if __name__ == "__main__":
    main()
