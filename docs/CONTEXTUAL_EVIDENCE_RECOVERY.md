# Contextual evidence recovery — Round16

Available inputs were searched in the GitHub checkout and the four local
`sberindex-attributed-network-*.zip` archives in Downloads. The user-supplied DOCX and
review text are preserved in `reference/round16`. They contain historical summaries,
not the missing municipality-level control inputs. No undiscovered file is claimed to
be legally restricted: its availability and redistribution permission are simply unestablished.
No third-party bytes were substituted for the historical snapshots.

| Expected input | Source identifier | Required schema / role | Recovery limit |
|---|---|---|---|
| `data/processed/municipality_crosswalk_final_1904.csv` | Historical Rosstat OKTMO snapshots, https://rosstat.gov.ru/opendata/ | `sber_name`, `subject_name_2024`, `resolution_tier`; historical OKTMO and flags needed for spatial joins | Snapshot dates/manual resolutions unavailable; SHA256 unknown. Restore author's exact crosswalk, including 13 manual and 4 provisional decisions; generic name matching is not an equivalent reconstruction. |
| `data/processed/municipality_spatial_join_1904.csv` | SberIndex https://sberindex.ru/ru/research/dataset-borders-and-changes-of-municipalities | At minimum `sber_name`, `centroid_lon`, `centroid_lat`, `sber_type_2023_24`; area/geometry source for density | Exact polygon release/hash and join decisions unavailable; do not assume a current release reproduces historical geometry. |
| `data/processed/supra_labels_admin_residual_base.csv` | Historical project pipeline | Municipality key (`Unnamed: 0` renamed to `sber_name` by old code), month columns including `2024-12-01` | Generator/config and exact semantics unavailable; do not rename baseline labels to satisfy the filename. SHA256 unknown. |
| `outputs/reference/economic_space_points.csv` | Historical project feature export | `mo`, `period`, `cluster`, `level_z`, `food`, `health`, `catering`, `marketplace`, `transport`, `other` | Feature ingredients can be derived from baseline, but original export/order/labels provenance is not established. |
| Municipal population covariates | Rosstat municipal population, https://www.rosstat.gov.ru/folder/11110/document/13282 ; Jan01 2024 and Jan01 2025 per project context | Municipality/OKTMO, date, population, area, density, match/suppression flags (required conceptual schema; original field names unavailable) | Exact workbooks/hash, join and residualization scripts absent. Historical residual-control numerical reproduction is blocked. |
| Historical B within-stratum result | Prior research session, exact source unavailable | n, feature, effect, uncertainty/p, multiplicity family/correction | No historical result CSV recovered. Round16 supplies a descriptive reconstruction with p/correction unavailable, not invented inference. |

The schema above distinguishes code-required column names from conceptual recovery
requirements. It does not claim a complete reconstruction recipe where historical decisions
are missing. A valid recovery must restore the snapshots, scripts/config and manual joins,
check unique 1904-key alignment and missing/provisional flags, and then compare output
hashes or numerical results against the original artifacts. No exact SHA256 is fabricated.

Current claim scopes are machine-readable in
`outputs/round16_evidence/CONTEXTUAL_EVIDENCE_REPRODUCIBILITY_MATRIX.csv`.
Until recovery, spatial/population/density/residual claims remain historical-only. Group-level
attenuation in the DOCX cannot be assigned to an individual case study.
