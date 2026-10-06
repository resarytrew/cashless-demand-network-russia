# SberIndex municipality directory — schema audit

Rows: 3,101; 2024 exclusive snapshot rows: 2,594.

## Required fields

| Required concept | Actual column | Status |
| --- | --- | --- |
| stable territory identifier | `territory_id` | present |
| official OKTMO | `oktmo` | present as text |
| official municipality name | `municipal_district_name` | present |
| region | `region_code`, `region_name` | present |
| start year | `year_from` | present |
| end year | `year_to` | present |
| transformation identifiers | `change_id_from`, `change_id_to` | present |

## Snapshot semantics

The selected snapshot uses `year_from <= 2024 AND year_to > 2024`. The inclusive alternative produces 86 duplicate territory IDs, whereas the exclusive selection has zero. `year_to` is therefore treated as an exclusive endpoint in this run. No row with multiple active versions is selected silently.

## Code handling

`oktmo` remains text in the source form (including hyphens and leading zeroes). This stage does not reduce an 11-digit directory code to BDMO's 8-digit field and does not perform a prefix join; that conversion requires a separately documented matching rule after the reference territory ID is available.
