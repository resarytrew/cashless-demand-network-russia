# Independent Economic Validation — restored reproducible package

**Status:** restored and computationally reproduced  
**External sample:** 58 municipalities  
**Project state:** Stability Atlas v2.2.1, repository commit `4a5b3c884bcd951134f5cfd5e2797c3d3587c2b8`  
**Atlas blob:** `3dd8cd196f4636f6279cf4c425257b4a0dac5629`

## 1. Purpose

This package reconstructs the independent economic validation previously performed in the chat *«Анализ конкурсной работы»*. External Rosstat indicators were **not used to build the SberIndex similarity network or A–G reference profiles**. They are joined post-clustering to test whether selected network structures have interpretable economic correlates.

The restoration follows a strict rule: a historical number is admitted as reproduced only if it can be recomputed from the recovered source data and the current 58-municipality table. Numbers that are not independently recoverable are not promoted into evidence.

## 2. External sample

The 58 municipalities split as:

| Region | n |
|---|---:|
| Republic of Sakha (Yakutia) | 28 |
| Republic of Altai | 11 |
| Chukotka Autonomous Okrug | 4 |
| Khabarovsk Krai | 15 |

Reference profile counts are **A=43, C=4, D=2, F=2, G=7**. Profiles B and E are absent from the external 58-MO sample.

Current Stability Atlas classes within the sample: `expansive_core`=41, `stable_core`=6, `transition`=7, `unresolved`=4.

The full row-level dataset is `external_validation_58.csv`.

## 3. Reproduced statistical tests

| Test | n | Result | p-value | Status |
|---|---:|---:|---:|---|
| A Yakutia: salary 2024 ~ investment/person | 27 | Spearman ρ = 0.790598 | 9.25e-07 | reproduced |
| A Yakutia: salary 2024 ~ population | 27 | Spearman ρ = -0.178877 | 0.372 | reproduced |
| A Yakutia: salary 2024 ~ urban share | 27 | Spearman ρ = 0.714655 | 2.82e-05 | reproduced |
| A Yakutia: HC3 log(invest) coefficient | 27 | β = 0.042888 | 0.0034 | reproduced |
| A Yakutia: salary 2024 ~ salary 2025 | 27 | Spearman ρ = 0.984127 | 2.71e-20 | reproduced |
| Altai D→F→G rank ~ salary | 6 | Spearman ρ = 0.925820 | 0.00805 | reproduced |
| Altai adjusted D→F→G rank | 6 | log-wage β = 0.193626 | 0.089 | reproduced |
| Khabarovsk A vs G salary | 15 | Cliff's δ = 0.409091 | MW p = 0.2799 | reproduced |
| Chukotka A salary 2024 | 4 | median = 185074.3 ₽ | — | reproduced |
| Chukotka A salary 2025 | 4 | median = 213819.7 ₽ | — | reproduced |

These numbers match the preserved historical workbook `Stability_Atlas_v2.xlsx` to rounding.

## 4. D–F–G gradient: Republic of Altai

The strongest independent check of the D–F–G interpretation is a within-region comparison, which reduces broad regional price-level and institutional heterogeneity.

For the six Altai municipalities belonging to D, F or G:

- **D:** median salary = **73525.5 ₽** (n=2)
- **F:** salary = **65317.7 ₽** (n=1)
- **G:** median salary = **55749.4 ₽** (n=3)

Coding G=1, F=2, D=3 gives **Spearman ρ=0.9258, p=0.00805**.

A small OLS sensitivity model,
`log(salary) ~ DFG_rank + log(population) + urban_share`,
keeps the same direction: rank coefficient **0.1936**, but **p=0.089** with only 2 residual degrees of freedom. Therefore the adjusted result is directional evidence, not confirmatory evidence.

### Interpretation

The external result is consistent with D–F–G being a **continuum or macro-axis rather than three equally discrete types**: D occupies the higher-wage pole, G the lower-wage pole, and F lies between them. This matches the network evidence that F has weak exact-boundary stability and often reallocates toward D/G.

It does **not** establish a universal nationwide socioeconomic ranking of D, F and G.

## 5. Validation of profile A

### 5.1 Yakutia: within-profile heterogeneity and economic correlates

The cleanest A test uses the 27 A municipalities in Yakutia, avoiding between-region comparisons.

Median salary in 2024 is **119812.6 ₽**.

Three findings are jointly important:

1. Salary is strongly associated with investment intensity: **ρ=0.7906, p=9.25e-07**.
2. Salary is not materially associated with population size alone: **ρ=-0.1789, p=0.372**.
3. Salary is strongly associated with urban share: **ρ=0.7147, p=2.82e-05**.

In the HC3 model with log(investment), log(population) and urban share, the log-investment coefficient is **0.0429 (p=0.0034)**. This supports the interpretation of A as a regime associated with high-cost/capital-intensive territorial economies, but does not identify the causal mechanism.

Wage ranks are extremely persistent from 2024 to 2025: **ρ=0.9841**.

### 5.2 Chukotka

All four matched Chukotka municipalities in the external sample are A. Median wage is **185074.3 ₽ in 2024** and **213819.7 ₽ in 2025**. This supports the high-wage/northern characterization but provides no within-region control profile.

### 5.3 Khabarovsk Krai

Khabarovsk gives a limited A-vs-G control: A=11, G=4. The wage effect is in the expected direction, **Cliff's δ=0.4091**, but the two-sided Mann–Whitney p-value is **0.2799**. Thus the evidence is suggestive, not statistically decisive.

### What A is *not* yet proven to be

The validation does **not** prove that A is an extractive/mining cluster. The observed pattern can be generated by combinations of northern wage premia, capital intensity, sector mix, infrastructure, urbanization and cost-of-living. Sectoral municipal data by OKVED are required to distinguish these mechanisms.

## 6. B–E interpretation

The 58-MO external sample contains no B or E municipalities, so **B–E has not been independently economically validated by this package**.

The relevant evidence remains internal robustness/topology:

- perturbation B/E co-assignment: **0.465586**
- alpha-family: **0.177419**
- gamma-family: **0.362007**
- Leiden: **0.983871**
- equal-family balanced mean: **0.497221**

The very high Leiden co-assignment and substantial balanced affinity support the interpretation of B and E as a **nested/overlapping metropolitan or federal-intracity family**, rather than two clean, universally separated national archetypes.

This remains an interpretation, not external validation. The missing test is a comparable independent intra-city dataset for Moscow/St Petersburg territories.

## 7. Profile C

The external sample contains four C municipalities, all in Republic of Altai. In current Atlas v2.2.1 all four are `transition`, not stable cores. The external sample is too small and geographically concentrated to rehabilitate C as a robust nationwide archetype. This is consistent with the project's existing claim status that C is unsupported beyond context.

## 8. Why this validation matters for Stability Atlas

The external evidence is more informative when used to explain **why stability classes differ**, rather than to ask whether seven labels are “true”.

- D and G can represent opposing poles of a broader macrostructure.
- F behaves like a boundary/transition population rather than a clean exact cluster.
- A appears to reflect a different high-wage/capital-intensive/northern regime whose variation is not reducible to population size.
- B/E remain an internally linked nested system awaiting external economic validation.
- C remains contextual/unresolved.

Accordingly, the empirically safer ontology is **stable cores + expansive cores + transition zones + unresolved/contextual cases**, not seven equally real discrete economic types.

## 9. Unsupported or only partially supported hypotheses

See `hypothesis_status.csv`. Key restrictions:

- do not equate A with mining without sectoral evidence;
- do not interpret the A investment association causally;
- do not generalize the Altai D–F–G gradient to all Russia without more regions;
- do not call B/E externally validated;
- do not promote C to a robust archetype;
- do not treat G as homogeneous merely because its broad core is stable;
- do not claim seven equally robust archetypes;
- do not interpret SberIndex `Published Total` as income, wealth, turnover or per-capita spending while its denominator remains unresolved;
- do not call retrospective label changes causal economic transitions.

## 10. Reproducibility contract

Run:

```bash
python -m pip install -r requirements.txt
python reproduce_validation.py
```

The script recomputes every numerical test in `statistical_tests.csv` from `external_validation_58.csv` and compares it to `expected_results.json`. It exits non-zero on mismatch.

The package does not redistribute the original Rosstat files. `source_manifest.csv` records their exact filenames, roles and SHA256 hashes; the restored normalized analytical table is the packaged input. This separates computational reproducibility from third-party source redistribution.

Current network labels are tied to Stability Atlas v2.2.1 at Git commit `4a5b3c884bcd951134f5cfd5e2797c3d3587c2b8` and the recorded Atlas blob SHA. No baseline clustering or frozen project evidence is modified by this package.

## 11. Evidence status

**Reproduced external evidence:** the 10 numerical tests above and the 58-row normalized table.

**Internal contextual evidence:** B/E co-assignment interpretation and current Atlas classes.

**Not established:** causal mechanisms, national representativeness of the external sample, sectoral mechanism for A, nationwide D–F–G ordering, external B/E validation, robust C archetype.

This package should therefore be treated as an **independent external triangulation layer**, not as a new clustering round and not as proof of a seven-type economic taxonomy.
