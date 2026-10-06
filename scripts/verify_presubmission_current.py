"""Current competition verifier; does not rewrite the historic publication freeze."""
from __future__ import annotations
import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT=Path(__file__).resolve().parents[1]
FINAL=ROOT/"outputs/final_competition_upgrade"


def run(command: list[str]) -> None:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(ROOT / "src"), str(ROOT), str(ROOT / "scripts")]
    )
    subprocess.run(command, cwd=ROOT, check=True, env=environment)


def walk_no_nan(value) -> bool:
    if isinstance(value,dict): return all(walk_no_nan(x) for x in value.values())
    if isinstance(value,list): return all(walk_no_nan(x) for x in value)
    return not isinstance(value,float) or math.isfinite(value)


def check_required() -> None:
    required=[
        FINAL/"synthetic_temporal_v3/run_manifest.json", FINAL/"geographic_confounding/run_manifest.json",
        FINAL/"profile_naming/profile_evidence_table.csv", FINAL/"story_data_v3/summary.json",
        FINAL/"external_validation_national_20261006_r6/run_manifest.json",
    ]
    missing=[str(x.relative_to(ROOT)) for x in required if not x.exists()]
    if missing: raise FileNotFoundError(f"Missing presubmission outputs: {missing}")
    for manifest in required[:2]:
        status=json.loads(manifest.read_text(encoding="utf-8")).get("status")
        if status not in {"COMPLETED","COMPLETED_NATIONAL_EXTERNAL_INTERPRETATION"}: raise ValueError(f"Unexpected manifest status: {manifest}: {status}")
    external_completion = json.loads((FINAL / "external_validation_national_20261006_r6/COMPLETED.json").read_text(encoding="utf-8"))
    if external_completion.get("status") != "COMPLETED_NATIONAL_EXTERNAL_INTERPRETATION":
        raise ValueError("National external-validation completion marker is invalid")
    story=FINAL/"story_data_v3"; files=sorted(story.glob("*.json"))
    expected={"summary.json","profiles.json","municipalities.json","external_validation.json","external_prediction.json","regional_generalization.json","temporal_benchmark.json","transition_flows.json","temporal_trajectories.json","robustness.json","icvi.json"}
    if {x.name for x in files} != expected: raise ValueError("Story JSON contract is incomplete or has unexpected files")
    for file in files:
        if not walk_no_nan(json.loads(file.read_text(encoding="utf-8"))): raise ValueError(f"Non-finite JSON value: {file}")
    if len(json.loads((story/"municipalities.json").read_text(encoding="utf-8"))) != 1903: raise ValueError("Municipality story count does not reconcile")
    # A direct architectural guard: clustering pipeline must not import or reference post-hoc BDMO data.
    pipeline=(ROOT/"src/sbernet/pipeline.py").read_text(encoding="utf-8").lower()
    if "external_bdmo" in pipeline or "bdmo" in pipeline: raise ValueError("External-feature leakage into clustering pipeline")


def main(skip_tests: bool) -> None:
    if not skip_tests:
        run([sys.executable,"-m","pytest","-q"])
        # The historic repository predates its current Ruff style baseline.
        # Enforce fatal/static correctness checks on the current upgrade surface
        # without claiming that untouched historical style debt is clean.
        run([sys.executable, "-m", "ruff", "check", "--select", "F",
             "src/sbernet/synthetic_temporal.py", "src/sbernet/regional_validation.py",
             "src/sbernet/graph.py",
             "src/sbernet/edge_sensitivity.py", "src/sbernet/representations.py",
             "scripts/run_synthetic_temporal_benchmark.py", "scripts/run_geographic_confounding.py",
             "scripts/build_profile_naming.py", "scripts/build_final_story_data.py",
             "scripts/run_presubmission_experiments.py", "scripts/verify_presubmission_current.py",
             "tests/test_graph.py", "tests/test_synthetic_temporal.py", "tests/test_regional_validation.py",
             "tests/test_final_story_data.py"])
        with tempfile.TemporaryDirectory(prefix="presubmission-baseline-") as temporary:
            run([sys.executable,"-m","sbernet.robustness.reproduction_gate","--config","configs/baseline.yaml","--output",str(Path(temporary)/"baseline")])
    check_required()
    print(json.dumps({"status":"PASS","scope":"current presubmission; historic freeze remains separately authenticated"}))


if __name__ == "__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--skip-tests",action="store_true"); main(parser.parse_args().skip_tests)
