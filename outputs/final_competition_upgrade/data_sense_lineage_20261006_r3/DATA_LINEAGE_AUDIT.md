# Data -> Sense official spending lineage audit

## Scope and source

This is a data-lineage and identity gate only. It does not change the reference clustering, labels, model parameters, or BDMO evidence. The publisher package and its checksum are recorded in `source_manifest.csv`; all extracted file checksums are in `official_package_inventory.csv`.

## Candidate generation (no names)

For each strict reference-panel `mo`, the gate serializes and SHA-256 hashes its exact sorted set of `(date, category, value)` records. It does the same for each official `territory_id`. Candidates are only official IDs with the identical hash. No municipality name, region, OKTMO prefix, fuzzy score, or manual override participates in this operation.

The all-row identifier-free `(date, category, value)` multiset check is `True` for 303,126 legacy and 303,126 official records. All 1,904 strict reference trajectories have one, and only one, official fingerprint candidate.

## Independent compatibility gate

Only after candidate creation, the candidate `territory_id` is looked up in SberIndex's independently downloaded 2024 municipal directory. Exact equality of the reference text and the directory name is a compatibility check, not a matching method. A mapping is usable only when both gates pass.

Result: 1,903 `VERIFIED_DATA_LINEAGE_MATCH`; 1 `CONFLICT_DIRECTORY_NAME_NOT_EQUAL`; no fuzzy or manual resolution.

### Held conflict

| reference_mo                                                                                 |   candidate_territory_id | official_name                                                                    |
|:---------------------------------------------------------------------------------------------|-------------------------:|:---------------------------------------------------------------------------------|
| внутригородская территория города федерального значения  Александровский муниципальный округ |                     2454 | внутригородская территория города федерального значения муниципальный округ № 75 |

The held row must receive a source-backed review before it can enter a reference-to-`territory_id` crosswalk. It is not exported in the usable `territory_id` column.

## Gate decision

This run establishes that official Data -> Sense consumption data contains `territory_id` and reproduces the supplied spending values. It does not yet authorize the requested BDMO joins: the 1,904th reference row remains held, and the repository has no publisher-documented transformation from the directory's 11-character OKTMO representation to the 8-character BDMO field. No prefix or inferred code conversion was attempted.
