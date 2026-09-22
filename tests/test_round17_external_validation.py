"""Numerical, data-lineage, immutability and negative-gate tests for Round17."""
import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from sbernet.validation.external_economic import (
    calculate, compare_expected, join_atlas, run, sha256, validate_package,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path("configs/round17_external_validation.yaml")


@pytest.fixture(scope="module")
def sample():
    cfg = yaml.safe_load((ROOT / CONFIG).read_text(encoding="utf-8"))
    data, expected, gates = validate_package(ROOT, cfg)
    atlas = pd.read_csv(ROOT / cfg["atlas"])
    canonical, audit = join_atlas(data, atlas)
    return cfg, data, atlas, canonical, audit, expected, gates


def test_recovered_inventory_and_sample(sample):
    cfg, data, _, _, _, _, gates = sample
    assert gates["checksums_verified"] == 14
    assert len(data) == data.municipality.nunique() == 58
    assert data.profile.value_counts().to_dict() == {"A": 43, "C": 4, "D": 2, "F": 2, "G": 7}
    assert data.region.nunique() == 4
    assert data.region.value_counts().to_dict() == cfg["region_counts"]


def test_exact_join_and_missing_historical_index(sample):
    _, _, _, canonical, audit, _, _ = sample
    assert len(audit) == 58 and audit.match_status.eq("MATCH").all()
    assert audit.historical_panel_index.isna().all()
    assert audit.panel_index_check.str.startswith("NOT_IN_RECOVERY").all()
    assert canonical.panel_index.is_unique
    assert canonical.reference_profile.equals(canonical.historical_profile)


@pytest.mark.parametrize("field,value", [("profile", "B"), ("consensus", "B"),
                                         ("stability_class", "changed"), ("municipality", "unknown")])
def test_mismatched_atlas_is_rejected(sample, field, value):
    _, data, atlas, *_ = sample
    changed = data.copy()
    changed.loc[0, field] = value
    with pytest.raises(ValueError, match="Atlas join mismatch"):
        join_atlas(changed, atlas)


def test_duplicate_keys_and_supplied_wrong_index_rejected(sample):
    _, data, atlas, *_ = sample
    with pytest.raises(pd.errors.MergeError):
        join_atlas(pd.concat([data, data.iloc[[0]]]), atlas)
    wrong = data.copy()
    wrong["panel_index"] = -1
    with pytest.raises(ValueError, match="Atlas join mismatch"):
        join_atlas(wrong, atlas)


def test_all_ten_statistics_and_regressions(sample):
    cfg, _, _, canonical, _, expected, _ = sample
    results = calculate(canonical, cfg)
    assert len(results) == 10
    compare_expected(results, expected, cfg["tolerance"])
    table = results.set_index("test_id")
    assert table.loc["ALT_DFG_WAGE_GRADIENT", "n"] == 6
    assert table.loc["ALT_DFG_ADJUSTED", "p_value"] == pytest.approx(.08886930080635241)
    assert table.loc["KHAB_A_G_WAGE", "p_value"] == pytest.approx(.27985347985347986)
    assert table.loc["A_YAK_WAGE_POP", "statistic"] < 0
    assert table.loc["CHU_A_WAGE_2024", "statistic"] == pytest.approx(185074.3)
    assert table.loc["CHU_A_WAGE_2025", "statistic"] == pytest.approx(213819.7)
    gradient = canonical.loc[canonical.region.eq(cfg["gradient_region"]) &
                             canonical.reference_profile.isin(cfg["rank"])]
    assert gradient.reference_profile.value_counts().to_dict() == {"G": 3, "D": 2, "F": 1}
    assert gradient.groupby("reference_profile").salary_2024.median().to_dict() == pytest.approx(
        expected["dfg_median_salary_2024"])


def test_missing_investments_preserved_and_inputs_not_imputed(sample):
    cfg, data, _, canonical, *_ = sample
    assert canonical.investment_per_capita_2024.isna().sum() == 30
    assert canonical.loc[canonical.region.ne(cfg["investment_region"]), "investment_per_capita_2024"].isna().all()
    assert not canonical.investment_per_capita_2024.eq(0).any()
    assert canonical.salary_2025.isna().sum() == 11
    assert canonical.set_index("municipality").investment_per_capita_2024.sort_index().equals(
        data.set_index("municipality").investment_per_capita_2024.sort_index())


@pytest.fixture(scope="module")
def replay_pair(tmp_path_factory):
    root = tmp_path_factory.mktemp("round17")
    a, b = root / "a", root / "b"
    assert run(CONFIG, ROOT, a)["status"] == "built"
    assert run(CONFIG, ROOT, b)["status"] == "built"
    return a, b


def test_deterministic_csv_report_and_verified_resume(replay_pair):
    a, b = replay_pair
    for path in a.iterdir():
        if path.name not in {"run_manifest.json", "COMPLETED.json"}:
            assert path.read_bytes() == (b / path.name).read_bytes(), path.name
    before = {p.name: (p.stat().st_mtime_ns, p.read_bytes()) for p in a.iterdir()}
    assert run(CONFIG, ROOT, a)["status"] == "verified_existing"
    assert before == {p.name: (p.stat().st_mtime_ns, p.read_bytes()) for p in a.iterdir()}


def test_schema_claim_scopes_and_provenance(replay_pair):
    a, _ = replay_pair
    claims = pd.read_csv(a / "CLAIM_EVIDENCE_MATRIX_v2.4.0.csv").set_index("claim_id")
    assert set(["claim", "evidence_source", "sample", "method", "statistic", "effect_size",
                "p_value", "limitations", "status", "reproducible"]) <= set(claims.columns)
    assert claims.loc["R17_BE_EXTERNAL", "status"] == "EXTERNALLY_UNVALIDATED"
    assert claims.loc["R17_A_MINING", "status"] == "NOT_ESTABLISHED"
    assert claims.loc["R17_C", "status"] == "UNRESOLVED"
    assert claims.loc["R17_SEVEN", "status"] == "REJECTED"
    provenance = pd.read_csv(a / "source_provenance.csv")
    canonical = pd.read_csv(a / "external_validation_58.csv")
    for indicator, rows in provenance.groupby("indicator"):
        assert len(rows) == canonical[indicator].notna().sum()
        assert rows.source_sha256.str.len().eq(64).all()
        assert canonical.iloc[rows.extract_record.to_numpy() - 1].municipality.tolist() == rows.municipality.tolist()
    assert provenance.source_location.eq("NOT_SUPPLIED_IN_RECOVERY").all()
    source = pd.read_csv(a / "source_manifest.csv").set_index("source_id")
    assert source.loc["atlas_v2_2_1", "hash_type"] == "git_blob_sha1"
    old = pd.read_csv(ROOT / "outputs/round16_evidence/MASTER_PROFILE_EVIDENCE_MATRIX_v2.3.0.csv", dtype=str, keep_default_na=False)
    new = pd.read_csv(a / "MASTER_PROFILE_EVIDENCE_MATRIX_v2.4.0.csv", dtype=str, keep_default_na=False)
    pd.testing.assert_frame_equal(old, new[old.columns])
    manifest = json.loads((a / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["normalized_dataset_sha256"] == sha256(a / "external_validation_58.csv")
    assert manifest["seed"] is None


def test_completed_output_tamper_rejected(replay_pair):
    _, b = replay_pair
    with (b / "statistical_tests.csv").open("a") as stream:
        stream.write("tampered\n")
    with pytest.raises(ValueError, match="Hash mismatch"):
        run(CONFIG, ROOT, b)


def test_partial_run_not_overwritten(tmp_path):
    (tmp_path / "partial.txt").write_text("preserve me")
    with pytest.raises(ValueError, match="Incomplete output"):
        run(CONFIG, ROOT, tmp_path)
    assert (tmp_path / "partial.txt").read_text() == "preserve me"
    assert not (tmp_path / "COMPLETED.json").exists()


def test_failure_writes_audit_and_no_completion(tmp_path, monkeypatch):
    import sbernet.validation.external_economic as module
    def fail(*args):
        raise ValueError("synthetic required gate failure")
    monkeypatch.setattr(module, "validate_package", fail)
    with pytest.raises(ValueError, match="synthetic required gate"):
        run(CONFIG, ROOT, tmp_path)
    assert not (tmp_path / "COMPLETED.json").exists()
    assert json.loads((tmp_path / "FAILURE_AUDIT.json").read_text())["status"] == "INTEGRATION_STOPPED"


def test_changed_expected_statistic_is_rejected(sample):
    cfg, _, _, canonical, _, expected, _ = sample
    results = calculate(canonical, cfg)
    results.loc[0, "statistic"] = 0
    with pytest.raises(ValueError, match="HISTORICAL_RESULT_NOT_REPRODUCED"):
        compare_expected(results, expected, cfg["tolerance"])
