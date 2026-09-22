# Data dictionary

`external_validation_58.csv` contains the 58-municipality external validation sample.

- `profile`: reference A–G profile from the project.
- `consensus`: Stability Atlas v2.2.1 consensus class. It is a descriptive affinity class, not a posterior probability.
- `stability_class`: current Atlas v2.2.1 class (`stable_core`, `expansive_core`, `transition`, `unresolved`).
- `population_2024`: permanent population on 1 January 2024.
- `urban_population_2024`: urban population on 1 January 2024.
- `urban_share_2024`: urban_population_2024 / population_2024.
- `salary_2024`, `salary_2025`: average monthly nominal accrued wage of employees of large and medium enterprises and non-profit organizations, where supplied by the regional Rosstat source.
- `investment_per_capita_2024`: investment in fixed capital excluding budget funds per capita. Available for the Yakutia subset only; missing elsewhere by design.
- `workers_2024`: average number of employees in surveyed organizations; used only for Republic Altai descriptive context.
- `oktmo_2024`: period-aware 2024 OKTMO identifier from the project crosswalk.

Missing values are deliberate. No cross-region imputation is performed.


Round17 canonical additions: panel_index is inherited from current Atlas (not present historically); reference_profile is the recovered profile verified against current Atlas; consensus_class and stability_class are current Atlas classes verified against recovery. Atlas affinity, entropy, margin, destination precision/Jaccard and leave-one-family-out fields are copied from the pinned Atlas; shares are descriptive, not probabilities. historical_* fields retain the original recovered labels. match_status is exact name/profile/consensus/stability agreement. notes explicitly records the index limitation. Empty numeric fields are missing, never zero-imputed. source_provenance.csv uses 1-based data-record positions in the canonical table, not raw-document row numbers. Reported source hashes are unverified when raw files are unavailable. source_manifest.csv separates hash_type and reported_hash: the recovered Atlas hash was a Git blob SHA1 mislabeled under sha256, not a SHA256 file checksum. All other raw-source hashes are reported SHA256. Internal matrix row order is verified against Atlas panel_index. No source cell/page locations were supplied.