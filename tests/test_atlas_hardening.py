import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from sbernet.robustness.atlas_runner import completion, digest, run, validate_inputs
from sbernet.robustness.soft_consensus import normalized_entropy, rank_memberships
from scripts.verify_current_artifacts import verify_inventory


def test_zero_affinity_is_unresolved_and_entropy_is_undefined():
    values = np.array([[0., 0.], [.5, .5], [.1, .9]])
    assert rank_memberships(["A", "B"], values)["top_profile"].tolist() == ["unresolved", "A", "B"]
    assert np.isnan(normalized_entropy(values)[0])
    assert normalized_entropy(values)[1] == 1
    with pytest.raises(ValueError, match="finite"):
        rank_memberships(["A", "B"], np.array([[np.nan, 0.]]))


@pytest.fixture
def atlas_repo(tmp_path):
    cfg = yaml.safe_load(Path("configs/stability_atlas_v2_2_1.yaml").read_text())
    names = [f"municipality-{i}" for i in range(14)]
    months = ["2024-11-01", "2024-12-01"]
    labels = np.repeat(np.arange(1, 8), 2)
    ref = pd.DataFrame({m: labels for m in months}, index=names)
    ref.to_csv(tmp_path / "reference.csv")
    (tmp_path / "profiles.yaml").write_text(yaml.safe_dump({"experiment": {
        "profiles": dict(zip("ABCDEFG", range(1, 8)))}}))
    pd.DataFrame({"municipality": names, "reference_profile": np.repeat(list("ABCDEFG"), 2),
                  "peer_coassignment": 1., "destination_precision": 1.,
                  "destination_jaccard": 1.}).to_csv(tmp_path / "stability.csv", index=False)
    cfg.update(reference_labels="reference.csv", profile_config="profiles.yaml",
               stability_table="stability.csv", input_registry="inputs.json", output_dir="out")
    cfg["families"] = {name: [name + ".npy"] for name in cfg["families"]}
    for name in cfg["families"]:
        np.save(tmp_path / (name + ".npy"), np.tile(labels, (2, 1)))
    paths = ["reference.csv", "profiles.yaml", "stability.csv"] + [x[0] for x in cfg["families"].values()]
    registry = {"panel_ids_sha256": digest(names), "months_sha256": digest(months),
                "inputs": {p: {"sha256": hashlib.sha256((tmp_path / p).read_bytes()).hexdigest()}
                           for p in paths}}
    registry_path = tmp_path / "inputs.json"
    registry_path.write_text(json.dumps(registry))
    cfg["input_registry_sha256"] = hashlib.sha256(registry_path.read_bytes()).hexdigest()
    (tmp_path / "config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
    # Source files are recorded by the runner; mirror the actual reviewed implementation.
    source = tmp_path / "src/sbernet/robustness"
    source.mkdir(parents=True)
    for pattern in ("*consensus*.py", "atlas_report.*"):
        for path in Path("src/sbernet/robustness").glob(pattern):
            (source / path.name).write_bytes(path.read_bytes())
    return tmp_path, cfg


def test_recorded_build_resumes_without_touching_files(atlas_repo):
    repo, cfg = atlas_repo
    assert run(Path("config.yaml"), repo)["status"] == "built"
    output = repo / "out"
    before = {p.name: (p.stat().st_mtime_ns, p.read_bytes()) for p in output.iterdir()}
    assert run(Path("config.yaml"), repo)["status"] == "verified_existing"
    assert before == {p.name: (p.stat().st_mtime_ns, p.read_bytes()) for p in output.iterdir()}
    assert "__ATLAS_DATA__" not in (output / "index.html").read_text(encoding="utf-8")
    frame = pd.read_csv(output / "municipality_affinity_atlas.csv")
    assert len(frame) == 14 and frame.consensus_matches_reference.all()
    # Replacing bytes under the same filename cannot be accepted on resume.
    with (output / "municipality_affinity_atlas.csv").open("a") as f:
        f.write("corruption")
    with pytest.raises(ValueError, match="checksum"):
        run(Path("config.yaml"), repo)


@pytest.mark.parametrize("corruption", ["missing_run", "reordered_npy", "reordered_reference"])
def test_changed_inputs_rejected_before_output_creation(atlas_repo, corruption):
    repo, cfg = atlas_repo
    if corruption == "missing_run":
        (repo / "gamma.npy").unlink()
    elif corruption == "reordered_npy":
        values = np.load(repo / "gamma.npy")
        np.save(repo / "gamma.npy", values[:, ::-1])
    else:
        frame = pd.read_csv(repo / "reference.csv", index_col=0)
        frame.iloc[::-1].to_csv(repo / "reference.csv")
    with pytest.raises(ValueError, match="checksum"):
        run(Path("config.yaml"), repo)
    assert not (repo / "out").exists()


def test_calendar_and_registry_order_are_checked(atlas_repo):
    repo, cfg = atlas_repo
    cfg["reference_month"] = "2025-01-01"
    with pytest.raises(ValueError, match="month"):
        validate_inputs(repo, cfg)
    cfg["reference_month"] = "2024-12-01"
    path = repo / "inputs.json"
    registry = json.loads(path.read_text())
    registry["panel_ids_sha256"] = "0" * 64
    path.write_text(json.dumps(registry))
    cfg["input_registry_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="order/calendar"):
        validate_inputs(repo, cfg)


def test_incomplete_or_unmanaged_output_is_never_silently_replaced(atlas_repo):
    repo, cfg = atlas_repo
    out = repo / "out"
    out.mkdir()
    (out / "important.txt").write_text("preserve")
    for force in (False, True):
        with pytest.raises(FileExistsError, match="not a managed"):
            run(Path("config.yaml"), repo, force=force)
    assert (out / "important.txt").read_text() == "preserve"
    with pytest.raises(ValueError, match="Incomplete"):
        completion(out)


def test_force_archives_only_managed_output(atlas_repo):
    repo, cfg = atlas_repo
    run(Path("config.yaml"), repo)
    saved = (repo / "out/COMPLETED.json").read_bytes()
    run(Path("config.yaml"), repo, force=True)
    archived = list(repo.glob("out_archived_*"))
    assert len(archived) == 1
    assert (archived[0] / "COMPLETED.json").read_bytes() == saved


def test_resume_rejects_changed_config_without_mutation(atlas_repo):
    repo, cfg = atlas_repo
    run(Path("config.yaml"), repo)
    checkpoint = (repo / "out/COMPLETED.json").read_bytes()
    cfg["anchor_fraction"] = .5
    (repo / "config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
    with pytest.raises(ValueError, match="resume mismatch"):
        run(Path("config.yaml"), repo)
    assert (repo / "out/COMPLETED.json").read_bytes() == checkpoint


def test_historical_import_correction_only_changes_import_path():
    old = Path("reference/engineering_20260922/snapshots/scripts/build_competition_artifacts.py").read_text(encoding="utf-8")
    current = Path("scripts/build_competition_artifacts.py").read_text(encoding="utf-8")
    assert old.replace("from round16_common import require_fresh, seal",
                       "from scripts.round16_common import require_fresh, seal") == current
    from scripts.build_competition_artifacts import require_fresh, seal
    from scripts import round16_common
    assert require_fresh is round16_common.require_fresh and seal is round16_common.seal


def test_inventory_rejects_corruption_even_with_historical_snapshot(tmp_path):
    path = tmp_path / "historical.py"
    path.write_bytes(b"original")
    inventory = tmp_path / "inventory.csv"
    inventory.write_text("path,sha256\ncurrent.py," + hashlib.sha256(b"original").hexdigest())
    assert verify_inventory(tmp_path, Path("inventory.csv"), {"current.py": "historical.py"}) == 1
    path.write_bytes(b"edited")
    with pytest.raises(ValueError, match="Integrity mismatch"):
        verify_inventory(tmp_path, Path("inventory.csv"), {"current.py": "historical.py"})
