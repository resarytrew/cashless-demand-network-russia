# Community-to-profile mapping

## Two distinct reference partitions

The project uses two distinct December-2024 label objects. Their community IDs
are arbitrary outputs of separate Louvain calls and cannot be compared by ID.

1. **Static graph benchmark.** `outputs/baseline/static_dec2024_labels.csv`
   clusters the single December mutual-kNN graph. It has K=9 communities. This
   is the partition used for the static ICVI and edge-rule benchmark.
2. **Temporal reference profile layer.** `outputs/baseline/supra_labels.csv`
   is one joint 24-month omega=2 supra-graph partition. Its December slice has
   K=10 raw communities. The A–G profile layer is defined only on this temporal
   December slice.

Therefore, K=9 in the static benchmark does **not** mean seven profiles plus
two merged groups, and A–G are not a merge or renaming of the static K=9
partition.

## Deterministic temporal mapping

`configs/competition_artifacts.yaml` fixes the mapping before the post-hoc
interpretation artifacts: A=1, B=3, C=7, D=8, E=9, F=10, G=11. These seven
raw temporal communities contain 1,899 of 1,904 municipalities. Raw IDs 0, 4
and 5 have sizes 2, 2 and 1 and are classified as `micro`; they have no A–G
economic-profile label. The mapping is direct one-to-one for its seven selected
major communities, not a merge.

The `micro` designation is an interpretation/presentation scope rule for tiny
technical communities. It does not erase those labels from raw files and does
not claim that they form an eighth profile. The mapping is applied to the
December slice of the single joint temporal partition; it is not a separate
month-by-month relabelling scheme.

Neither external wages, population, investment nor any other socioeconomic
variable was used to construct this mapping. They remain post-hoc validation
variables. The machine-readable counts are in
`outputs/final_competition_upgrade/profile_mapping/raw_to_profile_mapping.csv`.
