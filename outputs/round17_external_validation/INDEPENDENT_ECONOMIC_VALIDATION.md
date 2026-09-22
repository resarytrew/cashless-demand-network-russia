# Round17 — Independent economic validation

Status: REPRODUCED.

58 municipalities; four regions; A=43, C=4, D=2, F=2, G=7; B/E absent. 58/58 exact name joins match reference profile, consensus and stability in Atlas v2.2.1. Historical panel_index was not supplied; canonical indices come from the current Atlas.

External data were not used to construct or tune the original network. This is interpretation evidence, not a new clustering. The sample is selected, not nationally representative; nominal employee wages are not household income or real purchasing power.

## Reproduced statistics

| Test | n | Statistic | p-value |
|---|---:|---:|---:|
| A_YAK_WAGE_INVEST | 27 | 0.790598290598 | 9.25131931828e-07 |
| A_YAK_WAGE_POP | 27 | -0.178876678877 | 0.372007234586 |
| A_YAK_WAGE_URBAN | 27 | 0.714655199191 | 2.81548878771e-05 |
| A_YAK_HC3_LOGINVEST | 27 | 0.0428875848858 | 0.00337065300313 |
| A_YAK_WAGE_2024_2025 | 27 | 0.984126984127 | 2.70967333064e-20 |
| ALT_DFG_WAGE_GRADIENT | 6 | 0.925820099773 | 0.00804989310084 |
| ALT_DFG_ADJUSTED | 6 | 0.193625605717 | 0.0888693008064 |
| KHAB_A_G_WAGE | 15 | 0.409090909091 | 0.279853479853 |
| CHU_A_WAGE_2024 | 4 | 185074.3 | NA (descriptive) |
| CHU_A_WAGE_2025 | 4 | 213819.7 | NA (descriptive) |

## Interpretation and limits

A / Yakutia: within A (n=27), wage/investment association is positive, including HC3 OLS conditional on log population and urban share. HC3 uses normal-reference p-values (use_t=False). This is association, not an investment effect. The nonsignificant wage/population correlation does not demonstrate population independence or show that population has no explanatory role. Selected A includes varied municipality sizes; a large-city-only or mining-only interpretation is not established.

A / Chukotka: four A municipalities provide descriptive wage medians only. Nominal wages, northern price levels and employee coverage limit income interpretations. Sector mechanisms, extraction/mining and household prosperity are NOT_ESTABLISHED. The 2024/2025 Yakutia wage correlation describes wage ranks, not persistence of network labels.

D-F-G / Altai: D2/F1/G3, n=6. Coding G=1, F=2, D=3 makes positive rho mean higher wages toward D. Medians D=73525.45, F=65317.7, G=55749.4 rubles. The unadjusted gradient is consistent with a transition interpretation in this selected regional sample. The tied-rank asymptotic Spearman p is not an exact small-sample permutation result. Adjusted OLS retains beta=0.193626 but p=0.088869, with only two residual degrees of freedom; uncertainty must not be omitted. No national or causal D-to-G transition claim follows.

Khabarovsk: A11/G4; Cliff delta=0.409091, Mann-Whitney p=0.279853. The direction is moderate, uncertainty substantial. Wages are not established as a sufficient external A/G separator. This negative/uncertain result is retained.

F: internal Atlas shows low autonomous consensus membership and strong D/G proximity, alongside entropy, margin, destination and leave-one-family-out diagnostics below. The limited external gradient is consistent with F as a boundary/transition population. This is combined interpretation evidence, not equal standing as an autonomous robust economic archetype and not a change to prior robustness status.

B-E: external B=0 and E=0. Internal balanced/algorithm cross-coassignment is reported separately below. It supports an internal structural-family hypothesis; the metropolitan-like economic interpretation remains EXTERNALLY_UNVALIDATED. C: four selected Altai observations do not establish independent substantive structure; contextual/unresolved. Historical rejection of C as a beyond-context archetype remains in force.

All inferential p-values are exploratory, unadjusted and conditional on the recovered selected sample; geographic clustering, selection, multiple testing and sparse group sizes limit inference. External measurements did not tune alpha, k, omega, resolution, labels or Atlas classes. Total/category additivity and the denominator remain unresolved.

Local cashless demand contains network-temporal regimes with unequal stability: persistent cores, uncertain boundaries, nested and contextual areas. Independent socioeconomic observations corroborate parts of that interpretation in limited regions; they do not establish seven equal universal economic archetypes.


## Existing internal diagnostics (not external validation)

```json
{
  "scope": "existing internal evidence; no new external B/E observations",
  "BE_balanced_cross_coassignment": 0.49722084403038025,
  "BE_algorithm_cross_coassignment": 0.9838709831237793,
  "F_n": 327,
  "F_consensus_counts": {
    "A": 8,
    "D": 160,
    "F": 35,
    "G": 124
  },
  "F_stability_counts": {
    "transition": 327
  },
  "F_median_entropy": 0.637961360359647,
  "F_median_margin": 0.0936442156650048,
  "F_median_peer_coassignment": 0.6468711656441718,
  "F_median_destination_precision": 0.4352510000693783,
  "F_median_destination_jaccard": 0.3602193053495128,
  "F_lofo_all_class_match_share": 0.5871559633027523
}
```

## Reproducibility and provenance

Methods, filters, transformations, ranking and inference settings are fixed in `configs/round17_external_validation.yaml`. `statistical_tests.csv` records each test's variables, n, transformation, direction and scope. The regression intercept is explicit; no values are rounded before calculation. No missing-value imputation is performed.

`source_manifest.csv` records reported original filenames and hashes; `source_provenance.csv` maps every available indicator to selected extract records. Raw documents, source page/cell locations and the historical workbook are unavailable. Their extraction and source hashes cannot be independently verified from this repository. Population source URL was not supplied. The normalized extract and all statistics replay offline. The recovered manifest's Atlas hash is a Git blob SHA1, explicitly typed separately from SHA256.

`RECOVERY_AUDIT.md`, `atlas_join_audit.csv`, input/output inventories and the final `COMPLETED.json` seal define the integration gates. The original package is retained byte-for-byte under `reference/round17_external_validation/recovered/`; its narrative is historical, not an instruction or a replacement for this conservative report.
