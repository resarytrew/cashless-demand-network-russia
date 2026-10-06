# Final competition upgrade — pre-stage audit

## Frozen work not repeated

The baseline, Round18 representation sensitivity, ICVI, edge and omega
sensitivity, sealed Stability Atlas, and Round17 external validation are inputs
to this stage. No external variable will enter the SberIndex feature space or
alter a reference partition.

## Partition objects: K=9 versus A–G

These are different objects and must not be conflated.

- `outputs/baseline/static_dec2024_labels.csv` is a standalone December graph
  partition with **K=9** raw Louvain communities (sizes: 17, 342, 208, 147,
  316, 60, 299, 219, 296).
- `outputs/baseline/supra_labels.csv` is the omega=2 joint 24-month supra
  partition. Its December slice has **K=10** raw IDs: 0, 1, 3, 4, 5, 7, 8, 9,
  10, 11.
- The deterministic profile map in `configs/competition_artifacts.yaml` maps
  seven temporal raw IDs to A–G: A=1, B=3, C=7, D=8, E=9, F=10, G=11. IDs
  0, 4 and 5 contain five municipalities and are explicitly `micro`, not an
  eighth/ninth/tenth economic profile.

No external socioeconomic data participated in this mapping. The planned
machine-readable mapping and public documentation will state the different
static and temporal partitions explicitly.

## External-data branch

The independent source is the publisher's public BDMO-derived dataset at
`https://tochno.st/datasets/bdmo`, not any competing repository. The publisher
catalog was retrieved before transformations. The full section archives for 31
and 32 are 7.07 GB and 7.61 GB respectively; this stage uses the publisher's
own indicator-level archives for a predeclared population, wage, employment and
investment set. Full-section URLs, sizes and the indicator catalog are retained
in the source provenance.

The primary matching objective is deterministic identity through external
OKTMO/region/name fields. This reference repository has municipality names but
no supplied nationwide reference OKTMO or region crosswalk, so it cannot claim
an OKTMO or region-qualified name match until an independently sourced or
manually reviewed reference crosswalk is present. There will be no fuzzy match.
