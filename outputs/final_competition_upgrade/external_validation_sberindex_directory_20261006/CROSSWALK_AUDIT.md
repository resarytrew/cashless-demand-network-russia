# External BDMO crosswalk — SberIndex-directory gate

## Result

| Outcome | Count |
| --- | ---: |
| Reference municipalities | 1,904 |
| Mapped from original `territory_id` | 0 |
| Mapped to OKTMO | 0 |
| Validated in Rosstat registry | 0 |
| Matched BDMO population / wage / employment / investment | 0 / 0 / 0 / 0 |
| Unresolved | 1,904 |

## Gate decision

The official SberIndex directory was downloaded and its 2024 snapshot is valid and one-to-one by `territory_id`. The original behavioural source (`spending.csv.zip`) has only `mo` as the municipality field and has no `territory_id`, `municipality_id`, `mo_id`, `raw_id`, region or OKTMO. No raw-to-reference identifier mapping is stored in this checkout. In accordance with the protocol, this run does not attempt an exact name-only join and does not use fuzzy matching.

Rosstat's prescribed registry endpoint was not downloaded because this host cannot establish a trusted TLS connection to it. `oktmo_registry_validation.csv` deliberately records this as unavailable rather than marking codes absent. It is a validation-layer limitation, not evidence against an OKTMO.

No external-profile statistics, transition tests, pairwise tests or prediction were run because the identifier gate remains closed.
