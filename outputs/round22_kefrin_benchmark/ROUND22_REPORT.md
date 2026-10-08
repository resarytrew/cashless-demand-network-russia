# Round 22 — Attributed-network method benchmark

## 1. Motivation

KEFRiN is used as a held-out attributed-network clustering formulation. It is not
a new baseline, a winner-selection exercise or independent-data validation.

## 2. Frozen reference

The exact 1,904-node December L1 matrix and saved mutual-k20 adaptive-RBF graph
were used. The baseline reproduction and final hash gates passed.

## 3. Why KEFRiN

KEFRiNc jointly minimizes cosine distances in the attribute and adjacency-row
spaces, unlike the reference attributes → graph → community-detection sequence.

## 4. Provenance and implementation

The clean-room implementation follows DOI 10.3390/e24050626. Author upstream
commit `f9f96b1a778cb8d2e5ba85baae452dc813c4f110` has no verifiable license file, so no
upstream code was used.

## 5. Inputs and comparability

K=9, seed 0, Z-standardized L1 attributes, modularity-residual weighted adjacency,
rho=xi=1. Seeds 0–9 are separate runs; no run was selected by agreement.

## 6. Important dependence: graph is derived from attributes

The reference graph is derived from the same behavioral feature geometry. The two
KEFRiN blocks are not statistically independent information sources.

## 7. Primary December experiment

The canonical run converged in 20 iterations with objective
1887.666454 and exact K=9.

## 8. KEFRiN seed stability

Pairwise ARI mean=0.5213, median=0.5048,
min=0.3996, max=0.7143.

## 9. KEFRiN vs static reference

ARI=0.3080, NMI=0.4797, VI=3.1374 bits,
Hungarian accuracy=0.4842, micro purity=0.5263,
pair retention=0.3688, pair precision=0.4312.

## 10. KEFRiN vs temporal December

ARI=0.2568, NMI=0.4798, VI=2.7454 bits.

## 11. A–G crosswalk

| profile | N | kefrin_primary_destination | kefrin_retention | kefrin_stable_core_retention | kefrin_transition_retention |
| --- | --- | --- | --- | --- | --- |
| A | 141 | 2 | 0.5532 | 0.5714 | 0.0000 |
| B | 98 | 8 | 1.0000 | NA | NA |
| C | 29 | 0 | 0.5517 | NA | 0.9167 |
| D | 153 | 6 | 0.8693 | NA | 0.6667 |
| E | 186 | 8 | 0.5484 | 0.8400 | 0.8889 |
| F | 327 | 4 | 0.2905 | NA | 0.2905 |
| G | 965 | 1 | 0.2995 | 0.3729 | 0.0556 |

## 12. Agreement by Atlas state

| stability_class | N | disagreement_n | disagreement_share | ARI_within_state | NMI_within_state |
| --- | --- | --- | --- | --- | --- |
| expansive_core | 374 | 167 | 0.4465 | 0.6957 | 0.6751 |
| stable_core | 824 | 492 | 0.5971 | 0.0922 | 0.2907 |
| transition | 388 | 263 | 0.6778 | 0.0166 | 0.1905 |
| unresolved | 318 | 268 | 0.8428 | 0.3065 | 0.4996 |

## 13. ICVI v2 benchmark

| Method | K | SW | CH | S_Dbw | AVI | AVU | ANUI | MQ | Q |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| KEFRiN | 9 | 0.1318 | 725.3640 | 1.2784 | 0.7749 | 0.5416 | 0.5458 | 6.9738 | 0.6674 |

These are descriptive fixed-partition metrics, not a ranking or selection rule.

## 14. Agreement across method families

KEFRiN is closest by ARI to Ward (ARI=0.3217). Full matrices are saved.

## 15. External socioeconomic validation

| analysis | outcome | N | statistic | effect_size | effect_name | p |
| --- | --- | --- | --- | --- | --- | --- |
| raw_kruskal | population | 1903 | 969.2213 | 0.5075 | epsilon_squared | 0.0000 |
| raw_kruskal | wage | 1890 | 1154.9743 | 0.6098 | epsilon_squared | 0.0000 |
| raw_kruskal | employment_total | 1890 | 1036.9201 | 0.5470 | epsilon_squared | 0.0000 |
| raw_sector_PERMANOVA | sector_CLR | 1888 | 45.6069 | 0.1626 | R2 | 0.0005 |
| adjusted_scalar | wage | 1890 | 35.5809 | 0.1360 | partial_R2 | 0.0005 |
| adjusted_scalar | employment_total | 1890 | 18.2575 | 0.0747 | partial_R2 | 0.0005 |
| adjusted_sector | sector_CLR | 1888 | 8.7004 | 0.0371 | partial_R2 | 0.0005 |

External data were used only after the primary partition was frozen.

## 16. Optional parameter sensitivity

Not run (disabled in YAML).

## 17. Optional monthly experiment

Not run (disabled in YAML).

## 18. Negative results

All method disagreement and seed variation are retained; no seed or parameter was
chosen to improve agreement.

## 19. What changed scientifically

Evidence v2.9.0 adds one held-out algorithm-family sensitivity measurement.

## 20. What did not change

L1, graph construction, k=20, omega=2, resolution=.5, A–G IDs/statuses, Atlas
assignments, ICVI definitions, original L2 and all Round21 artifacts are unchanged.

## 21. Limitations

Graph/attribute dependence, fixed K, optimization variability and observational
external associations limit interpretation. Exact agreement is not correctness.

## 22. Reproducibility

Config, per-seed labels/objectives, runtime, package versions, hashes and final
baseline gate are saved in this directory.
