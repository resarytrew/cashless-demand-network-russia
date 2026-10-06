import pandas as pd

from sbernet.data_sense_lineage import exact_lineage_matches, standardise_current, value_multiset_equal


def test_exact_fingerprint_recovers_identifier_without_using_name():
    current = pd.DataFrame({
        "mo": ["legacy A", "legacy A", "legacy B", "legacy B"],
        "period": ["2024-01-01", "2024-02-01", "2024-01-01", "2024-02-01"],
        "category_15": ["Все категории"] * 4,
        "value": [10, 11, 20, 21],
    })
    official = pd.DataFrame({
        "territory_id": [7, 7, 9, 9], "date": ["2024-01", "2024-02"] * 2,
        "category": ["Все категории"] * 4, "value": [10, 11, 20, 21],
    })
    found = exact_lineage_matches(standardise_current(current), official)
    assert found.set_index("reference_mo").loc["legacy A", "candidate_territory_id"] == 7
    assert found.candidate_count.eq(1).all()
    assert value_multiset_equal(standardise_current(current), official)


def test_doubled_fingerprint_is_a_conflict_not_a_match():
    current = pd.DataFrame({
        "mo": ["legacy"] * 2, "period": ["2024-01-01", "2024-02-01"],
        "category_15": ["Все категории"] * 2, "value": [10, 11],
    })
    official = pd.DataFrame({
        "territory_id": [7, 7, 9, 9], "date": ["2024-01", "2024-02"] * 2,
        "category": ["Все категории"] * 4, "value": [10, 11, 10, 11],
    })
    found = exact_lineage_matches(standardise_current(current), official)
    assert found.candidate_count.item() == 2
    assert pd.isna(found.candidate_territory_id.item())
