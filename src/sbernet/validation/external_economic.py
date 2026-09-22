"""Round17: offline, fail-closed replay of a recovered analytical extract.

No clustering, parameter selection, network access, or raw-source reconstruction.
The configuration fixes sample restrictions, transformations and inference methods.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm
import yaml


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                    allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check(path, expected):
    require(Path(path).is_file() and sha256(path) == expected, f"Hash mismatch: {path}")


def csv(path, frame):
    frame.to_csv(path, index=False, encoding="utf-8", lineterminator="\n",
                 float_format="%.17g", na_rep="")


def validate_package(repo, cfg):
    root = repo / cfg["recovered_dir"]
    for relative, expected in cfg["input_sha256"].items():
        check(repo / relative, expected)
    listed = {}
    for line in (root / "SHA256SUMS.txt").read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        name = name.strip()
        require(Path(name).name == name and name not in listed, "Unsafe/duplicate checksum entry")
        check(root / name, digest)
        listed[name] = digest
    require(set(listed) | {"SHA256SUMS.txt"} == {p.name for p in root.iterdir()},
            "Recovered package inventory differs")
    manifest = json.loads((root / "MANIFEST.json").read_text(encoding="utf-8"))
    expected = json.loads((root / "expected_results.json").read_text(encoding="utf-8"))
    require(manifest["external_n"] == cfg["expected_n"], "Manifest sample size")
    for field in ("profile_counts", "region_counts"):
        require(manifest[field] == expected[field] == cfg[field], f"Manifest {field}")
    require(manifest["atlas_version"] == expected["atlas"]["version"] == cfg["atlas_version"],
            "Atlas version")
    require(manifest["atlas_commit"] == expected["atlas"]["repo_commit"] == cfg["atlas_commit"],
            "Atlas provenance commit")
    atlas_bytes = (repo / cfg["atlas"]).read_bytes()
    blob = hashlib.sha1(b"blob " + str(len(atlas_bytes)).encode() + b"\0" + atlas_bytes).hexdigest()
    require(blob == manifest["atlas_blob_sha"] == expected["atlas"]["blob_sha"], "Atlas Git blob")
    data = pd.read_csv(root / "external_validation_58.csv", dtype={"oktmo_2024": "string"})
    require(len(data) == cfg["expected_n"] and data.municipality.is_unique
            and not data.municipality.isna().any(), "Sample size/duplicate municipality")
    require(not data.duplicated(["region", "oktmo_2024"]).any()
            and not data.oktmo_2024.isna().any(), "Duplicate/missing regional OKTMO key")
    require(data.profile.value_counts().to_dict() == cfg["profile_counts"], "Profile counts")
    require(data.region.value_counts().to_dict() == cfg["region_counts"], "Region counts")
    for column, count in cfg["nonmissing_counts"].items():
        require(int(data[column].notna().sum()) == count, f"Coverage: {column}")
    for column in cfg["positive_columns"]:
        values = data[column].dropna().to_numpy()
        require(np.isfinite(values).all() and (values > 0).all(), f"Invalid positive data: {column}")
    require(data.urban_share_2024.between(0, 1).all(), "Urban share bounds")
    require(np.allclose(data.urban_population_2024 / data.population_2024,
                        data.urban_share_2024, rtol=0, atol=cfg["tolerance"]), "Urban share formula")
    require(data.loc[data.region != cfg["investment_region"], "investment_per_capita_2024"].isna().all(),
            "Unexpected investments outside Yakutia")
    require(data.atlas_commit.eq(cfg["atlas_commit"]).all()
            and data.atlas_blob_sha.eq(blob).all(), "Row Atlas provenance")
    return data, expected, {"checksums_verified": len(listed), "atlas_git_blob_sha1": blob}


def join_atlas(data, atlas):
    require(atlas.municipality.is_unique and atlas.panel_index.is_unique, "Atlas keys not unique")
    historical = data.rename(columns={"profile": "historical_profile", "consensus": "historical_consensus",
                                      "stability_class": "historical_stability",
                                      "panel_index": "historical_panel_index"})
    merged = historical.merge(atlas, on="municipality", how="left", validate="one_to_one", indicator=True)
    audit = merged[["municipality", "historical_profile", "reference_profile", "historical_consensus",
                    "consensus_class", "historical_stability", "stability_class", "panel_index"]].copy()
    audit = audit.rename(columns={"reference_profile": "current_reference_profile",
                                 "consensus_class": "current_consensus", "stability_class": "current_stability"})
    matches = (merged._merge.eq("both") & merged.historical_profile.eq(merged.reference_profile)
               & merged.historical_consensus.eq(merged.consensus_class)
               & merged.historical_stability.eq(merged.stability_class))
    if "historical_panel_index" in merged:
        audit["historical_panel_index"] = merged.historical_panel_index
        matches &= merged.historical_panel_index.eq(merged.panel_index)
        audit["panel_index_check"] = "COMPARED"
    else:
        audit["historical_panel_index"] = pd.NA
        audit["panel_index_check"] = "NOT_IN_RECOVERY; ASSIGNED_FROM_CURRENT_ATLAS"
    audit["match_status"] = np.where(matches, "MATCH", "MISMATCH")
    require(matches.all(), "Atlas join mismatch: " + ", ".join(audit.loc[~matches, "municipality"]))
    merged = merged.drop(columns="_merge").sort_values("panel_index").reset_index(drop=True)
    merged["match_status"] = "MATCH"
    merged["notes"] = "panel_index inherited from current Atlas; original source rows unavailable"
    return merged, audit.sort_values("municipality").reset_index(drop=True)


def calculate(data, cfg):
    result = []
    for spec in cfg["tests"]:
        sample = data.loc[data.region.eq(spec["region"]) & data.reference_profile.isin(spec["profiles"])].copy()
        require(len(sample) == spec["n"], f"Sample size: {spec['id']}")
        if "rank" in spec:
            sample["profile_rank"] = sample.reference_profile.map(spec["rank"])
        used = spec["variables"]
        require(not sample[used].isna().any().any(), f"Missing test inputs: {spec['id']}")
        method = spec["method"]
        p = None
        if method == "spearman":
            value, p = stats.spearmanr(sample[used[0]], sample[used[1]],
                                       alternative=spec["alternative"], nan_policy="raise")
        elif method == "ols":
            x = np.column_stack([np.log(sample[v]) if v in spec["log"] else sample[v]
                                 for v in used[1:]])
            y = np.log(sample[used[0]]) if used[0] in spec["log"] else sample[used[0]]
            fit = sm.OLS(y.to_numpy(), sm.add_constant(x, has_constant="add"), missing="raise").fit(
                cov_type=spec["covariance"], use_t=spec["use_t"])
            value, p = fit.params[spec["coefficient_index"]], fit.pvalues[spec["coefficient_index"]]
        elif method == "cliff_mannwhitney":
            a, b = (sample.loc[sample.reference_profile.eq(p), used[0]].to_numpy() for p in spec["groups"])
            require([len(a), len(b)] == spec["group_n"], "Group counts")
            value = (np.sum(a[:, None] > b) - np.sum(a[:, None] < b)) / (len(a) * len(b))
            p = stats.mannwhitneyu(a, b, alternative=spec["alternative"], method=spec["mw_method"],
                                    use_continuity=spec["use_continuity"]).pvalue
        elif method == "median":
            value = sample[used[0]].median()
        else:
            raise ValueError(f"Unknown method: {method}")
        require(np.isfinite(value) and (p is None or np.isfinite(p)), "Nonfinite statistic")
        result.append({"test_id": spec["id"], "n": len(sample), "statistic": float(value),
                       "p_value": None if p is None else float(p),
                       "effect_direction": "descriptive" if method == "median" else ("positive" if value > 0 else "negative"),
                       "method": method, "variables": ";".join(used),
                       "transformation": spec["transformation"], "inference": spec["inference"],
                       "interpretation": spec["interpretation"], "evidence_status": spec["status"]})
    return pd.DataFrame(result)


def compare_expected(results, expected, tolerance):
    require(set(results.test_id) == set(expected["tests"]), "Test inventory mismatch")
    for row in results.itertuples():
        for field, actual in (("value", row.statistic), ("p_value", row.p_value)):
            target = expected["tests"][row.test_id][field]
            if target is None:
                require(pd.isna(actual), f"Expected missing: {row.test_id}/{field}")
            else:
                require(np.isfinite(actual) and abs(actual - target) <= tolerance * max(1, abs(target)),
                        f"HISTORICAL_RESULT_NOT_REPRODUCED: {row.test_id}/{field}")


def provenance(data, sources):
    rows = []
    by_file = sources.set_index("file_name")
    for i, row in data.iterrows():
        for indicator in ("salary_2024", "salary_2025", "investment_per_capita_2024", "workers_2024",
                          "population_2024", "urban_population_2024", "urban_share_2024", "oktmo_2024"):
            if pd.isna(row[indicator]):
                continue
            field = "crosswalk_source_file" if indicator == "oktmo_2024" else (
                "population_source_file" if indicator in ("population_2024", "urban_population_2024", "urban_share_2024")
                else "economic_source_file")
            name = row[field]
            require(name in by_file.index, f"Missing source: {name}")
            source = by_file.loc[name]
            rows.append({"extract_record": i + 1, "municipality": row.municipality, "region": row.region,
                         "panel_index": row.panel_index, "indicator": indicator, "year": indicator.rsplit("_", 1)[1],
                         "source_id": source.source_id, "source_file": name, "source_sha256": source["sha256"],
                         "source_url": source.source_url, "source_location": "NOT_SUPPLIED_IN_RECOVERY",
                         "transformation": "urban_population_2024 / population_2024" if indicator == "urban_share_2024"
                         else "inherited normalized value; raw extraction not independently replayable",
                         "verification_scope": "normalized extract replay; raw file hash is reported provenance"})
    return pd.DataFrame(rows)


def internal_diagnostics(repo, cfg, atlas):
    require(np.array_equal(atlas.panel_index.to_numpy(), np.arange(len(atlas))),
            "Atlas matrix/index order differs")
    b = np.flatnonzero(atlas.reference_profile.eq("B"))
    e = np.flatnonzero(atlas.reference_profile.eq("E"))
    matrix = np.load(repo / cfg["consensus_matrix"], mmap_mode="r")
    with np.load(repo / cfg["family_matrices"]) as families:
        algorithm = float(families["algorithm"][np.ix_(b, e)].mean())
    f = atlas.loc[atlas.reference_profile.eq("F")]
    return {"scope": "existing internal evidence; no new external B/E observations",
            "BE_balanced_cross_coassignment": float(matrix[np.ix_(b, e)].mean()),
            "BE_algorithm_cross_coassignment": algorithm, "F_n": len(f),
            "F_consensus_counts": f.consensus_class.value_counts().sort_index().to_dict(),
            "F_stability_counts": f.stability_class.value_counts().sort_index().to_dict(),
            "F_median_entropy": float(f.affinity_entropy.median()),
            "F_median_margin": float(f.affinity_margin.median()),
            "F_median_peer_coassignment": float(f.perturbation_peer_coassignment.median()),
            "F_median_destination_precision": float(f.destination_precision.median()),
            "F_median_destination_jaccard": float(f.destination_jaccard.median()),
            "F_lofo_all_class_match_share": float(f.lofo_all_class_match.mean())}


def report(results, internal, cfg):
    lines = ["# Round17 — Independent economic validation", "", "Status: REPRODUCED.", "",
             "58 municipalities; four regions; A=43, C=4, D=2, F=2, G=7; B/E absent. "
             "58/58 exact name joins match reference profile, consensus and stability in Atlas v2.2.1. "
             "Historical panel_index was not supplied; canonical indices come from the current Atlas.", "",
             "External data were not used to construct or tune the original network. "
             "This is interpretation evidence, not a new clustering. The sample is selected, "
             "not nationally representative; nominal employee wages are not household income or real purchasing power.", "",
             "## Reproduced statistics", "", "| Test | n | Statistic | p-value |", "|---|---:|---:|---:|"]
    for row in results.itertuples():
        p = "NA (descriptive)" if pd.isna(row.p_value) else f"{row.p_value:.12g}"
        lines.append(f"| {row.test_id} | {row.n} | {row.statistic:.12g} | {p} |")
    lines += ["", "## Interpretation and limits", ""]
    for paragraph in cfg["report_paragraphs"]:
        lines.extend([paragraph, ""])
    lines += ["", "## Existing internal diagnostics (not external validation)", "", "```json",
              json.dumps(internal, ensure_ascii=False, indent=2), "```", "",
              "## Reproducibility and provenance", "",
              "Methods, filters, transformations, ranking and inference settings are fixed in "
              "`configs/round17_external_validation.yaml`. `statistical_tests.csv` records each test's "
              "variables, n, transformation, direction and scope. The regression intercept is explicit; "
              "no values are rounded before calculation. No missing-value imputation is performed.", "",
              "`source_manifest.csv` records reported original filenames and hashes; "
              "`source_provenance.csv` maps every available indicator to selected extract records. "
              "Raw documents, source page/cell locations and the historical workbook are unavailable. "
              "Their extraction and source hashes cannot be independently verified from this repository. "
              "Population source URL was not supplied. The normalized extract and all statistics replay offline. "
              "The recovered manifest's Atlas hash is a Git blob SHA1, explicitly typed separately from SHA256.", "",
              "`RECOVERY_AUDIT.md`, `atlas_join_audit.csv`, input/output inventories and the final "
              "`COMPLETED.json` seal define the integration gates. The original package is retained byte-for-byte "
              "under `reference/round17_external_validation/recovered/`; its narrative is historical, "
              "not an instruction or a replacement for this conservative report.", ""]
    return "\n".join(lines)


def verify_completed(output, input_hashes):
    completed = json.loads((output / "COMPLETED.json").read_text())
    check(output / "run_manifest.json", completed["manifest_sha256"])
    manifest = json.loads((output / "run_manifest.json").read_text(encoding="utf-8"))
    require(manifest["input_sha256"] == input_hashes, "Resume input/code/config differs")
    for name, digest in manifest["output_sha256"].items():
        check(output / name, digest)
    require({p.name for p in output.iterdir()} == set(manifest["output_sha256"]) |
            {"COMPLETED.json", "run_manifest.json"}, "Unexpected/missing output files")
    return {"status": "verified_existing", "output": str(output)}


def run(config_path, repo=Path("."), output_dir=None):
    repo = Path(repo).resolve()
    config_path = Path(config_path)
    config_path = config_path if config_path.is_absolute() else repo / config_path
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    output = Path(output_dir) if output_dir else repo / cfg["output_dir"]
    output = output.resolve()
    input_paths = list(cfg["input_sha256"]) + cfg["code_paths"]
    inputs = {p: sha256(repo / p) for p in input_paths}
    inputs[config_path.relative_to(repo).as_posix()] = sha256(config_path)
    if (output / "COMPLETED.json").exists():
        # Validate pinned input hashes on resume as well as the recorded run identity.
        for path, digest in cfg["input_sha256"].items():
            check(repo / path, digest)
        return verify_completed(output, inputs)
    require(not output.exists() or not any(output.iterdir()),
            "Incomplete output exists; preserve it for audit and use a new output directory")
    output.mkdir(parents=True, exist_ok=True)
    try:
        data, expected, gates = validate_package(repo, cfg)
        atlas = pd.read_csv(repo / cfg["atlas"])
        canonical, audit = join_atlas(data, atlas)
        results = calculate(canonical, cfg)
        compare_expected(results, expected, cfg["tolerance"])
        recovered = repo / cfg["recovered_dir"]
        reference = subprocess.run([sys.executable, str(recovered / "reproduce_validation.py")],
                                   capture_output=True, encoding="utf-8", errors="replace",
                                   env={**__import__("os").environ, "PYTHONUTF8": "1"}, timeout=120)
        (output / "reference_replay.txt").write_text(reference.stdout + reference.stderr, encoding="utf-8")
        require(reference.returncode == 0, "Reference replay failed; see reference_replay.txt")
        sources = pd.read_csv(recovered / "source_manifest.csv")
        sources["hash_type"] = np.where(sources.source_id.eq("atlas_v2_2_1"), "git_blob_sha1", "sha256")
        sources = sources.rename(columns={"sha256": "reported_hash"})
        sources["verification_scope"] = np.where(sources.source_id.eq("atlas_v2_2_1"),
                                                "current bytes verified", "reported; raw source unavailable")
        csv(output / "source_manifest.csv", sources)
        csv(output / "source_provenance.csv", provenance(canonical, pd.read_csv(recovered / "source_manifest.csv")))
        csv(output / "external_validation_58.csv", canonical)
        csv(output / "atlas_join_audit.csv", audit)
        csv(output / "statistical_tests.csv", results)
        csv(output / "a_validation_cases.csv", canonical.loc[canonical.reference_profile.eq("A")])
        alt = canonical.loc[canonical.region.eq(cfg["gradient_region"]) & canonical.reference_profile.isin(cfg["rank"])]
        gradient = alt.groupby("reference_profile").salary_2024.agg(["size", "median"]).reset_index()
        for row in gradient.itertuples():
            require(abs(row.median - expected["dfg_median_salary_2024"][row.reference_profile]) <=
                    cfg["tolerance"] * max(1, abs(row.median)), "Gradient median mismatch")
        csv(output / "dfg_gradient_altai.csv", gradient)
        claims = pd.DataFrame(cfg["claims"])
        csv(output / "hypothesis_status.csv", claims)
        csv(output / "CLAIM_EVIDENCE_MATRIX_v2.4.0.csv", claims)
        # Preserve all Round16 fields as text; add new scope columns only.
        master = pd.read_csv(repo / cfg["previous_matrix"], dtype=str, keep_default_na=False)
        master["round17_evidence_version"] = cfg["evidence_version"]
        master["round17_external_n"] = master.archetype.map(cfg["profile_counts"]).fillna(0).astype(int)
        master["round17_scope"] = master.archetype.map(cfg["profile_scope"])
        csv(output / "MASTER_PROFILE_EVIDENCE_MATRIX_v2.4.0.csv", master)
        internal = internal_diagnostics(repo, cfg, atlas)
        dump(output / "internal_diagnostics.json", internal)
        (output / "INDEPENDENT_ECONOMIC_VALIDATION.md").write_text(report(results, internal, cfg), encoding="utf-8")
        (output / "README.md").write_text(cfg["readme"], encoding="utf-8")
        (output / "DATA_DICTIONARY.md").write_text(
            (recovered / "DATA_DICTIONARY.md").read_text(encoding="utf-8") + "\n\n" + cfg["dictionary_addendum"], encoding="utf-8")
        (output / "RECOVERY_AUDIT.md").write_text(cfg["audit"] + "\n\nGates: " +
                                               json.dumps(gates, indent=2) + "\n", encoding="utf-8")
        (output / "expected_results.json").write_bytes((recovered / "expected_results.json").read_bytes())
        dump(output / "gate_results.json", {**gates, "status": "PASS", "unique_municipalities": len(canonical),
                                           "exact_atlas_joins": len(audit), "statistics_reproduced": len(results),
                                           "reference_replay_exit_code": reference.returncode})
        csv(output / "input_checksums.csv", pd.DataFrame([{"path": p, "sha256": h} for p, h in sorted(inputs.items())]))
        outputs = {p.name: sha256(p) for p in sorted(output.iterdir())}
        csv(output / "output_checksums.csv", pd.DataFrame([{"path": p, "sha256": h} for p, h in outputs.items()]))
        outputs["output_checksums.csv"] = sha256(output / "output_checksums.csv")
        manifest = {"timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(),
                    "git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=repo)),
                    "python": platform.python_version(), "packages": {p: importlib.metadata.version(p) for p in cfg["packages"]},
                    "input_sha256": inputs, "output_sha256": outputs, "evidence_round": 17,
                    "methodology_version": cfg["methodology_version"], "evidence_version": cfg["evidence_version"],
                    "seed": None, "seed_scope": "deterministic statistics; no random experiment",
                    "source_archive_sha256": cfg["source_archive_sha256"],
                    "atlas_sha256": sha256(repo / cfg["atlas"]),
                    "normalized_dataset_sha256": sha256(output / "external_validation_58.csv")}
        dump(output / "run_manifest.json", manifest)
        dump(output / "COMPLETED.tmp", {"status": "COMPLETE", "evidence_round": 17,
                                         "manifest_sha256": sha256(output / "run_manifest.json")})
        (output / "COMPLETED.tmp").replace(output / "COMPLETED.json")
        return {"status": "built", "output": str(output), "gates": gates}
    except Exception as exc:
        dump(output / "FAILURE_AUDIT.json", {"status": "INTEGRATION_STOPPED", "error": str(exc),
                                             "baseline_modified": False, "completion_written": False})
        raise
