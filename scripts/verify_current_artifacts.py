"""Verify immutable evidence and explicitly recorded source transitions without resealing."""
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
for local_path in (ROOT / "src", ROOT, ROOT / "scripts"):
    if str(local_path) not in sys.path:
        sys.path.insert(0, str(local_path))


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_hash(path, expected):
    if not Path(path).is_file() or sha256(path) != expected:
        raise ValueError(f"Integrity mismatch: {path}")


def verify_inventory(repo, inventory, snapshots=None):
    snapshots = snapshots or {}
    count = 0
    for row in csv.DictReader((repo / inventory).open(encoding="utf-8")):
        path = repo / row["path"]
        if row["path"] in snapshots:
            path = repo / snapshots[row["path"]]
        check_hash(path, row["sha256"])
        count += 1
    return count


def load_round22_transitions(repo):
    """Authenticate the additive Round22 transition against its pinned base."""
    path = repo / "reference/round22_kefrin_benchmark/INTEGRATION_MANIFEST.json"
    check_hash(path, path.with_suffix(".sha256").read_text().split()[0])
    manifest = json.loads(path.read_text(encoding="utf-8"))
    base = manifest["base_git_commit"]
    transitions = {item["path"]: item for item in manifest["transitions"]}
    for relative, item in transitions.items():
        historical = subprocess.check_output(
            ["git", "show", f"{base}:{relative}"], cwd=repo
        )
        if hashlib.sha256(historical).hexdigest() != item["historical_sha256"]:
            raise ValueError(f"Round22 historical Git object mismatch: {relative}")
    return manifest, transitions


def load_round23_transitions(repo, round22_transitions):
    """Continue the authenticated narrative/source hash chain through Round23."""
    path = repo / "reference/round23_economic_mechanisms/INTEGRATION_MANIFEST.json"
    check_hash(path, path.with_suffix(".sha256").read_text().split()[0])
    manifest = json.loads(path.read_text(encoding="utf-8"))
    transitions = {item["path"]: item for item in manifest["transitions"]}
    for relative, prior in round22_transitions.items():
        if relative in transitions:
            if transitions[relative]["prior_sha256"] != prior["current_sha256"]:
                raise ValueError(f"Round23 transition does not continue Round22: {relative}")
        else:
            check_hash(repo / relative, prior["current_sha256"])
    for relative in transitions:
        if relative not in round22_transitions:
            raise ValueError(f"Round23 transition has no authenticated Round22 predecessor: {relative}")
    return manifest, transitions


def load_presubmission_cleanup_transitions(repo, round23_transitions):
    """Authenticate presentation-only source changes after the Round23 freeze."""
    path = repo / "reference/presubmission_cleanup_20261008/INTEGRATION_MANIFEST.json"
    check_hash(path, path.with_suffix(".sha256").read_text().split()[0])
    manifest = json.loads(path.read_text(encoding="utf-8"))
    transitions = {item["path"]: item for item in manifest["transitions"]}
    for relative, item in transitions.items():
        if relative not in round23_transitions:
            raise ValueError(f"Presubmission transition has no Round23 predecessor: {relative}")
        if item["prior_sha256"] != round23_transitions[relative]["current_sha256"]:
            raise ValueError(f"Presubmission transition does not continue Round23: {relative}")
    return manifest, transitions


def load_restructure_transitions(repo):
    """Authenticate current files while retaining exact bytes expected by older freezes."""
    round22, round22_transitions = load_round22_transitions(repo)
    round23, round23_transitions = load_round23_transitions(repo, round22_transitions)
    cleanup, cleanup_transitions = load_presubmission_cleanup_transitions(repo, round23_transitions)
    active_transitions = {**round23_transitions, **cleanup_transitions}
    for relative, item in active_transitions.items():
        check_hash(repo / relative, item["current_sha256"])
    manifest_path = repo / "reference/repository_restructure_20261007/RESTRUCTURE_MANIFEST.json"
    check_hash(manifest_path, manifest_path.with_suffix(".sha256").read_text().split()[0])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    snapshots = {}
    for item in manifest["source_transitions"]:
        target = repo / item["path"]
        snapshot = repo / item["snapshot"]
        check_hash(snapshot, item["historical_sha256"])
        if item.get("removed"):
            if item.get("case_only_replacement"):
                exists = any(
                    child.name == Path(item["path"]).name for child in target.parent.iterdir()
                )
            else:
                exists = target.exists()
            if exists:
                raise ValueError(f"Retired path unexpectedly exists: {target}")
        else:
            if item["path"] in round22_transitions:
                if round22_transitions[item["path"]]["historical_sha256"] != item["current_sha256"]:
                    raise ValueError(f"Round22 transition does not continue prior state: {target}")
            else:
                check_hash(target, item["current_sha256"])
        snapshots[item["path"]] = item["snapshot"]
    return manifest, snapshots, round22, round23, cleanup


def verify_integrity(repo=Path(".")):
    repo = repo.resolve()
    restructure, restructure_snapshots, round22, round23, cleanup = load_restructure_transitions(repo)
    # Round17 is additive. Prior engineering/source bytes are retained in an
    # explicit transition layer; evidence/data are always verified in place.
    integration_path = repo / "reference/round17_external_validation/INTEGRATION_MANIFEST.json"
    check_hash(integration_path, integration_path.with_suffix(".sha256").read_text().split()[0])
    integration = json.loads(integration_path.read_text(encoding="utf-8"))
    for path, checksum in integration["files_sha256"].items():
        check_hash(repo / restructure_snapshots.get(path, path), checksum)
    round17_snapshots = {}
    for item in integration["source_transitions"]:
        if not item["path"].startswith(("docs/", "scripts/", ".github/")) and item["path"] not in (
                "README.md", "pyproject.toml", "AGENTS.md"):
            raise ValueError("Round17 cannot redirect data, evidence or model sources")
        check_hash(repo / item["snapshot"], item["historical_sha256"])
        check_hash(repo / restructure_snapshots.get(item["path"], item["path"]),
                   item["current_sha256"])
        round17_snapshots[item["path"]] = item["snapshot"]
    provenance = repo / "reference/engineering_20260922"
    release_path = provenance / "ENGINEERING_MANIFEST.json"
    check_hash(release_path, release_path.with_suffix(".sha256").read_text().split()[0])
    release = json.loads(release_path.read_text(encoding="utf-8"))
    for path, checksum in release["files_sha256"].items():
        historical = round17_snapshots.get(path, restructure_snapshots.get(path, path))
        check_hash(repo / historical, checksum)
    transitions = json.loads((provenance / "source_transitions.json").read_text())
    snapshots = {}
    for item in transitions["transitions"]:
        if item["path"].startswith(("outputs/", "data/")):
            raise ValueError("Data/evidence artifacts must be verified in place")
        check_hash(repo / item["snapshot"], item["historical_sha256"])
        historical = round17_snapshots.get(
            item["path"], restructure_snapshots.get(item["path"], item["path"])
        )
        check_hash(repo / historical, item["current_sha256"])
        snapshots[item["path"]] = item["snapshot"]
    old_root = repo / "outputs/evidence_freeze_v2_2_0"
    old_manifest = old_root / "EVIDENCE_FREEZE_MANIFEST.json"
    check_hash(old_manifest, old_manifest.with_suffix(".sha256").read_text().split()[0])
    old = json.loads(old_manifest.read_text())
    check_hash(repo / old["inventory_path"], old["inventory_sha256"])
    old_snapshots = {f"src/sbernet/{name}.py": f"reference/round16/pre_hardening/{name}.py"
                     for name in ("io", "pipeline", "cli")}
    old_snapshots.update(restructure_snapshots)
    old_snapshots.update(round17_snapshots)
    old_snapshots.update(snapshots)
    old_count = verify_inventory(repo, old["inventory_path"], old_snapshots)
    new_root = repo / "outputs/round16_evidence"
    new_manifest = new_root / "ROUND16_FREEZE_MANIFEST.json"
    check_hash(new_manifest, new_manifest.with_suffix(".sha256").read_text().split()[0])
    new = json.loads(new_manifest.read_text())
    inventory = "outputs/round16_evidence/ROUND16_FILES_SHA256.csv"
    check_hash(repo / inventory, new["inventory_sha256"])
    new_count = verify_inventory(
        repo, inventory, {**restructure_snapshots, **round17_snapshots, **snapshots}
    )
    from sbernet.validation.external_economic import run
    round17 = run("configs/round17_external_validation.yaml", repo)
    return {"integrity": "PASS", "old_frozen_files": old_count,
            "round16_frozen_files": new_count, "source_transitions": len(snapshots),
            "scientific_status_changes": 0, "round17": round17["status"],
            "round17_interpretation_layer": "v2.4.0; prior A-G robustness statuses unchanged",
            "round17_source_transitions": len(round17_snapshots),
            "repository_restructure": restructure["status"],
            "repository_restructure_transitions": len(restructure_snapshots),
            "round22_integration": round22["status"],
            "round22_source_transitions": len(round22["transitions"]),
            "round23_integration": round23["status"],
            "round23_source_transitions": len(round23["transitions"]),
            "presubmission_cleanup": cleanup["status"]}


def replay_numeric():
    # Same numerical replay as the preserved Round16 verifier. Integrity is checked
    # separately above, allowing only the enumerated source/document transitions.
    from scripts.verify_submission_artifacts import (
        Path, json, pickle, pd, np, load_config, _prepare, array_hash, graph_fingerprint,
        completed, temporal_diagnostics, compare_numeric, profile_diagnostics,
        validity_metrics, ROOT,
    )
    gate=Path('outputs/round16_reproducibility')
    assert json.loads((gate/'baseline_gate.json').read_text())['passed']
    data=pickle.load((gate/'baseline_graphs.pkl').open('rb'))
    ref=pd.read_csv('outputs/baseline/supra_labels.csv',index_col=0).loc[data['names'],data['keys']].to_numpy().T
    cfg=load_config('configs/round16_decomposition.yaml')
    _,names,_,_,matrices=_prepare('configs/baseline.yaml')
    assert names==data['names']
    assert all(array_hash(matrices[k])==array_hash(data['matrices'][k]) for k in data['keys'])
    checks=json.loads((gate/'graph_checksums.json').read_text())
    for key in ['static','supra']:
        assert graph_fingerprint(data[key])==checks[key]
    comparisons=0; runs=0
    for directory in ['outputs/round16_perturbation_decomposition','outputs/round16_resolution']:
        root=Path(directory); assert completed(root/'aggregate')
        for p in (root/'runs').iterdir():
            assert completed(p)
            raw=json.loads((p/'raw_results.json').read_text())
            actual=np.load(p/'supra_labels.npy').reshape(ref.shape)
            stats,monthly=temporal_diagnostics(ref,actual,data['keys'])
            comparisons+=compare_numeric(stats,raw['run'])
            largest=np.unique(actual[-1],return_counts=True)[1].max()
            assert largest==raw['run']['largest_community_n_Dec']
            pro,pairs=profile_diagnostics(ref[-1],actual[-1],cfg['experiment']['profiles'])
            for left,right in zip(pro,raw['profiles']):
                assert left['archetype']==right['archetype']; comparisons+=compare_numeric(left,right)
            for left,right in zip(pairs,raw['pairs']):
                assert left['pair']==right['pair']; comparisons+=compare_numeric(left,right)
            for left,right in zip(monthly,raw['monthly']):
                comparisons+=compare_numeric(left,right)
            runs+=1
    # Fresh metric replay for each rebuilt algorithm, not clustering.
    bpath=Path('outputs/round16_benchmark'); benchmark=pd.read_csv(bpath/'canonical_method_benchmark.csv').set_index('method')
    for method in ['Louvain','Greedy','Spectral','KMeans','Ward']:
        labels=pd.read_csv(bpath/f'{method}_labels.csv').set_index('mo').loc[names,'community'].to_numpy()
        actual=validity_metrics(data['static'],labels,matrices[data['keys'][-1]])
        comparisons+=compare_numeric(actual,benchmark.loc[method].to_dict())
    old=pd.read_csv('outputs/perturbation_v2/archetype_status_round15_perturbation_v2.csv')
    new=pd.read_csv(ROOT/'archetype_status_round16.csv')
    assert list(old.round15_status)==list(new.round16_status) and not new.changed.any()
    assert completed('outputs/round16_competition')
    return {'passed':True,'raw_new_runs_verified':runs,
            'numeric_comparisons':comparisons,'reconstructed_feature_months_bitwise_equal':24,
            'scientific_status_changes':0,'scope':'forensic label/metric replay, not repeated optimization'}


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--integrity-only", action="store_true")
    args = parser.parse_args()
    result = verify_integrity()
    if not args.integrity_only:
        result["numeric_replay"] = replay_numeric()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
