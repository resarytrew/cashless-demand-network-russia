"""Configuration-driven, immutable-input Atlas build with verified resume."""
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import subprocess

import numpy as np
import pandas as pd
import yaml

from . import soft_consensus as core


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def write_json(path, value):
    path = Path(path)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
                    encoding="utf-8")
    temp.replace(path)


def local_path(repo, relative):
    path = (repo / relative).resolve()
    if not path.is_relative_to(repo.resolve()):
        raise ValueError(f"Input path escapes repository: {relative}")
    return path


def validate_inputs(repo, cfg):
    """Authenticate label bytes and their reference axes before any output is created."""
    registry_path = local_path(repo, cfg["input_registry"])
    if core.sha256(registry_path) != cfg["input_registry_sha256"]:
        raise ValueError("Input registry checksum mismatch")
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    paths = [cfg[k] for k in ("reference_labels", "profile_config", "stability_table")]
    if tuple(cfg["families"]) != core.FAMILY_ORDER:
        raise ValueError("Atlas requires the four recorded families in canonical order")
    # New weight experiments need a separate protocol; this release preserves v2.2 semantics.
    if cfg["family_weights"] != {key: .25 for key in core.FAMILY_ORDER}:
        raise ValueError("This engineering release supports the recorded equal-family design only")
    if cfg["vote_threshold"] not in (3, 4) or cfg["minimum_anchors"] < 2:
        raise ValueError("Invalid anchor/vote settings")
    if not 0 < cfg["anchor_fraction"] <= 1:
        raise ValueError("anchor_fraction must be in (0, 1]")
    if cfg["tie_policy"] != "stable_profile_order" or cfg["zero_affinity_policy"] != "unresolved":
        raise ValueError("Unsupported tie/zero-affinity policy")
    if cfg["micro_policy"] != "descriptive_affinity_only":
        raise ValueError("Unsupported micro-community policy")
    if any(not 0 <= v <= 1 for v in cfg["stability_thresholds"].values()):
        raise ValueError("Stability thresholds must be in [0,1]")
    for family, members in cfg["families"].items():
        if not members or len(members) != len(set(members)):
            raise ValueError(f"Empty or duplicate runs: {family}")
        paths.extend(members)
    if set(paths) != set(registry["inputs"]):
        raise ValueError("Configured input set differs from frozen input registry")
    for relative in paths:
        path = local_path(repo, relative)
        if not path.is_file() or core.sha256(path) != registry["inputs"][relative]["sha256"]:
            raise ValueError(f"Input checksum mismatch: {relative}")
    reference = pd.read_csv(repo / cfg["reference_labels"], index_col=0)
    if reference.index.has_duplicates or reference.columns.has_duplicates:
        raise ValueError("Duplicate reference axes")
    names, months = reference.index.astype(str).tolist(), reference.columns.astype(str).tolist()
    if digest(names) != registry["panel_ids_sha256"] or digest(months) != registry["months_sha256"]:
        raise ValueError("Reference municipality order/calendar mismatch")
    month = cfg["reference_month"]
    if month not in months:
        raise ValueError(f"Reference month absent: {month}")
    month_index = months.index(month)
    family_paths, family_labels = {}, {}
    for family, members in cfg["families"].items():
        family_paths[family], family_labels[family] = [], []
        for relative in members:
            path = repo / relative
            if path.suffix == ".npy":
                # Exact bytes are bound to the historically gated axes by the input registry.
                labels = np.load(path, allow_pickle=False)
                if labels.shape not in ((len(months) * len(names),), (len(months), len(names))):
                    raise ValueError(f"Label dimensions mismatch: {relative}")
                labels = labels.reshape(len(months), len(names))[month_index]
            else:
                frame = pd.read_csv(path, index_col=0)
                if frame.index.has_duplicates or set(frame.index) != set(names) or month not in frame:
                    raise ValueError(f"Municipality/calendar mismatch: {relative}")
                labels = frame.loc[names, month].to_numpy()
            if not np.isfinite(labels).all() or not np.equal(labels, np.floor(labels)).all():
                raise ValueError(f"Non-integral/non-finite labels: {relative}")
            family_paths[family].append(path)
            family_labels[family].append(labels.astype(np.int64))
    return (names, months, reference[month].to_numpy(dtype=np.int64),
            family_paths, family_labels), registry


def completion(directory):
    path = directory / "COMPLETED.json"
    if not path.is_file():
        raise ValueError(f"Incomplete Atlas output: {directory}")
    saved = json.loads(path.read_text(encoding="utf-8"))
    actual = {p.relative_to(directory).as_posix() for p in directory.rglob("*") if p.is_file()
              and p != path}
    if actual != set(saved["files_sha256"]):
        raise ValueError("Atlas output file set changed")
    for relative, checksum in saved["files_sha256"].items():
        if core.sha256(local_path(directory, relative)) != checksum:
            raise ValueError(f"Atlas output checksum mismatch: {relative}")
    return saved


def runtime():
    return {"python": platform.python_version(), "platform": platform.platform(),
            "packages": {name: importlib.metadata.version(name)
                         for name in ("numpy", "pandas", "PyYAML")}}


def run(config_path=Path("configs/stability_atlas_v2_2_1.yaml"), repo=Path("."),
        output_dir=None, force=False):
    repo = repo.resolve()
    config_path = local_path(repo, config_path)
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    inputs, registry = validate_inputs(repo, cfg)
    output = Path(output_dir).resolve() if output_dir else local_path(repo, cfg["output_dir"])
    implementation = Path(__file__).resolve().parent
    source_files = list(implementation.glob("*consensus*.py"))
    source_files += list(implementation.glob("atlas_report.*"))
    source_files.append(Path(__file__).resolve())
    sources = {"src/sbernet/robustness/" + p.name: core.sha256(p) for p in sorted(source_files)}
    context = {"resolved_config": cfg, "config_file_sha256": core.sha256(config_path),
               "input_registry_sha256": core.sha256(repo / cfg["input_registry"]),
               "source_sha256": sources, "runtime": runtime()}
    fingerprint = digest(context)
    if output.exists():
        manifest_path = output / "run_manifest.json"
        if not manifest_path.is_file():
            raise FileExistsError(f"Output is not a managed Atlas directory: {output}")
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        if previous.get("managed_by") != "sbernet.atlas_runner":
            raise FileExistsError(f"Refusing to replace non-managed/historical output: {output}")
        if not force:
            completion(output)
            if previous.get("resume_fingerprint") != fingerprint:
                raise ValueError("Atlas resume mismatch; use a new output directory")
            return {"status": "verified_existing", "output_dir": str(output), "runs_recomputed": 0}
        # Only a positively identified managed output can be archived; never repo/ancestors.
        if output == repo or repo.is_relative_to(output) or output.is_symlink():
            raise ValueError("Unsafe Atlas archive target")
        archive = output.with_name(output.name + "_archived_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f"))
        shutil.move(str(output), str(archive))
    output.mkdir(parents=True, exist_ok=False)
    try:
        git_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
        git_dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=repo, text=True).strip())
    except (OSError, subprocess.CalledProcessError):
        git_commit, git_dirty = None, None
    manifest = {"managed_by": "sbernet.atlas_runner", "resume_fingerprint": fingerprint,
                "git_commit": git_commit, "git_dirty": git_dirty,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(), **context,
                "panel_ids_sha256": registry["panel_ids_sha256"],
                "months_sha256": registry["months_sha256"], "clustering_runs": 0,
                "seed": None, "seed_note": "Deterministic aggregation of explicitly listed saved runs"}
    write_json(output / "run_manifest.json", manifest)
    from .soft_consensus_v2_2 import build_tables
    derived = build_tables(repo, output, anchor_fraction=cfg["anchor_fraction"],
                           validated_inputs=inputs, settings=cfg)
    manifest.update(derived)
    manifest["reference_month"] = cfg["reference_month"]
    manifest["terminology"]["D_G_transition_direction"] = (
        f"For reference F, D/G-leaning requires at least {cfg['vote_threshold']} of 4 family votes; otherwise mixed"
    )
    from .atlas_report import build_report
    build_report(output, repo / cfg["reference_labels"], cfg)
    manifest["outputs"].extend(["index.html", "DATA_DICTIONARY.md"])
    write_json(output / "run_manifest.json", manifest)
    # Recheck inputs after reading: never seal a result if its provenance changed mid-build.
    validate_inputs(repo, cfg)
    write_json(output / "COMPLETED.json", {"files_sha256": {
        p.relative_to(output).as_posix(): core.sha256(p) for p in sorted(output.rglob("*"))
        if p.is_file() and p.name != "COMPLETED.json"}})
    completion(output)
    return {"status": "built", "output_dir": str(output), "clustering_runs": 0,
            "municipalities": len(inputs[0])}


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/stability_atlas_v2_2_1.yaml"))
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.config, args.repo, args.output_dir, args.force), indent=2))


if __name__ == "__main__":
    main()
