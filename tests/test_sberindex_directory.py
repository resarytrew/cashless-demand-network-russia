import pandas as pd

from sbernet.sberindex_directory import reference_identity_audit, select_snapshot, territory_to_oktmo


def test_year_to_is_exclusive_and_keeps_single_version():
    frame = pd.DataFrame(
        {
            "territory_id": [1, 1, 2],
            "oktmo": ["01-001-000-000", "01-501-000-000", "02-001-000-000"],
            "municipal_district_name": ["old", "new", "other"],
            "region_code": [1, 1, 2],
            "year_from": [2018, 2024, 2018],
            "year_to": [2024, 9999, 9999],
        }
    )
    selected = select_snapshot(frame, 2024)
    assert selected.loc[selected.territory_id.eq(1), "oktmo"].item() == "01-501-000-000"
    out = territory_to_oktmo(selected, "source")
    assert out.oktmo.dtype.name == "object"


def test_reference_without_official_identifier_is_not_name_matched():
    reference = pd.DataFrame({"2024-12-01": [7]}, index=["Тестовый район"])
    mapping, audit = reference_identity_audit(reference)
    assert mapping.territory_id.isna().all()
    assert mapping.status.item() == "MISSING_UPSTREAM_TERRITORY_ID"
    assert audit["mapped_to_territory_id"] == 0
