# BDMO crosswalk audit

## Result

| Outcome | Count |
| --- | ---: |
| Reference municipalities | 1,904 |
| Matched by OKTMO | 0 |
| Matched by BDMO transformation | 0 |
| Matched by normalized name + region | 0 |
| Manual matches | 0 |
| Unmatched | 1,904 |
| Reference names with more than one BDMO normalized-name candidate | 8 |
| Many-to-one accepted conflicts | 0 |

## Why the gate is blocked

The supplied SberIndex file has a municipality-name field only: it contains no
nationwide OKTMO, OKATO, region or official reference municipality ID. BDMO
has all of these external-side attributes, including transformation metadata,
but they cannot create a validated reference-side identifier. Even a globally
unique name is not accepted as a region-qualified identity match; a similar
name can represent a renamed or differently scoped municipality.

`municipality_crosswalk.csv` and `unmatched.csv` preserve every reference row.
`manual_overrides.csv` is intentionally empty and must contain a reviewed
reference name, current external OKTMO, reviewer, rationale and source URL
before a manual match can be accepted. No fuzzy matching was run.
