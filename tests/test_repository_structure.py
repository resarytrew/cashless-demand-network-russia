from pathlib import Path

import pytest

from scripts.verify_repository_structure import RETIRED, check_paths, verify


ROOT = Path(__file__).resolve().parents[1]


def test_current_repository_structure_passes():
    result = verify(ROOT)
    assert result["status"] == "PASS"
    assert result["evidence_version"] == "2.8.0"
    assert result["latest_research_round"] == 21


def test_retired_path_is_rejected(tmp_path):
    retired = tmp_path / RETIRED[0]
    retired.parent.mkdir(parents=True)
    retired.write_text("stale", encoding="utf-8")
    with pytest.raises(ValueError, match="Retired paths remain"):
        check_paths(tmp_path, (), (RETIRED[0],))
