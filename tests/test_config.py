from pathlib import Path

from sbernet.config import load_config


def test_config_inheritance(tmp_path: Path):
    (tmp_path / "base.yaml").write_text("network:\n  k: 20\ntemporal:\n  omega: 2\n")
    (tmp_path / "child.yaml").write_text("extends: base.yaml\nnetwork:\n  k: 30\n")
    cfg = load_config(tmp_path / "child.yaml")
    assert cfg["network"]["k"] == 30
    assert cfg["temporal"]["omega"] == 2
