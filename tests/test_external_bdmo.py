import pandas as pd

from sbernet.external_bdmo import conservative_crosswalk, municipality_oktmo11_to_8, normalize_municipality_name


def test_normalizer_only_changes_typography():
    assert normalize_municipality_name("  Ёлкинский—район ") == "елкинский район"


def test_no_region_or_oktmo_means_no_name_only_match():
    entities = pd.DataFrame({"oktmo_stable": ["01000000"], "municipality": ["Ёлкинский район"]})
    crosswalk, unmatched, audit = conservative_crosswalk(["Елкинский район"], entities, pd.DataFrame())
    assert crosswalk.external_id.isna().all()
    assert len(unmatched) == 1
    assert audit["matched_by_normalized_identity"] == 0


def test_oktmo_transformation_needs_zero_suffix_and_unique_candidate():
    lineage = pd.DataFrame({"reference_mo": ["a", "b", "held"], "territory_id": [1, 2, pd.NA], "status": ["VERIFIED_DATA_LINEAGE_MATCH", "VERIFIED_DATA_LINEAGE_MATCH", "CONFLICT_DIRECTORY_NAME_NOT_EQUAL"]})
    directory = pd.DataFrame({"territory_id": [1, 2], "municipal_district_name": ["a", "b"], "region_code": ["01", "01"], "oktmo": ["01-234-567-000", "01-234-568-123"]})
    result = municipality_oktmo11_to_8(lineage, directory, {"01234567", "01234568"})
    assert result.loc[0, "candidate_oktmo8"] == "01234567"
    assert bool(result.loc[0, "transform_allowed"])
    assert not bool(result.loc[1, "transform_allowed"])
    assert result.loc[1, "reason"] == "NOT_MUNICIPALITY_LEVEL_REVIEW_REQUIRED"
    assert result.loc[2, "reason"] == "EXCLUDED_UNRESOLVED_LINEAGE"


def test_oktmo_many_to_one_is_never_silent():
    lineage = pd.DataFrame({"reference_mo": ["a", "b"], "territory_id": [1, 2], "status": ["VERIFIED_DATA_LINEAGE_MATCH"] * 2})
    directory = pd.DataFrame({"territory_id": [1, 2], "municipal_district_name": ["a", "b"], "region_code": ["01", "01"], "oktmo": ["01-234-567-000", "01-234-567-000"]})
    result = municipality_oktmo11_to_8(lineage, directory, {"01234567"})
    assert not result.transform_allowed.any()
    assert set(result.reason) == {"MANY_TO_ONE_TRANSFORMATION_CONFLICT"}
