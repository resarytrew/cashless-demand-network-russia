# Spatial robustness — region × administrative-form null

## Status

This is a **region-level spatial robustness test**, not a polygon-based spatial bootstrap.
It uses the completed 1904-row OKTMO crosswalk to control the exact subject-of-Russia
composition of every A–G profile.

## Data

- Strict panel: 1,904 municipalities.
- Period: December 2024.
- Feature geometry: reference 70/30 CLR + relative-level geometry.
- Community labels: reference temporal Louvain partition, A–G major profiles.
- Geography: `subject_name_2024` from the historical OKTMO crosswalk.

## Null model

For each A–G profile, a random comparison group is forced to contain exactly the same
number of municipalities from every `subject_name_2024 × admin_form` stratum as the
observed profile.

The expected null mean pairwise distance is computed **exactly** from stratum-specific
within- and between-stratum distance means. A 3,000-draw Monte Carlo experiment is used
only as descriptive uncertainty support; its p-values remain exploratory.

## Verification

Before the new region test, the same code reproduces the previously published
admin-stratified exact null means to floating-point precision. This verifies that the
December-2024 feature geometry and distance calculation are identical to the earlier
robustness rounds.

## Main result

| Profile | Admin-only ratio | Region+admin ratio | Reading |
|---|---:|---:|---|
| A | 0.869 | 0.847 | moderate residual compactness remains; poor feature separation still applies |
| B | 0.764 | 0.751 | compactness remains even within the same federal-city composition |
| C | 0.903 | 1.034 | no residual compactness beyond region+admin composition |
| D | 0.368 | 0.431 | very strong residual compactness remains |
| E | 0.384 | 0.570 | substantial compactness remains, but geography explains a meaningful part |
| F | 0.550 | 0.623 | substantial residual compactness remains; boundary instability is unchanged |
| G | 0.737 | 0.846 | only modest residual compactness remains after geographic control |

Lower ratios mean stronger compactness relative to the matched null. A ratio near or
above 1 means the group is no more compact than the matched random expectation.

The 3,000-draw lower-tail empirical p-value is at the Monte Carlo floor (1/3001) for
A, B, D, E, F and G. For C it is approximately 0.768. Because this project is
exploratory across many rounds, these p-values are **not** project-wide confirmatory
claims; effect-size ratios are primary.

## Crosswalk uncertainty sensitivity

Four historical name matches are explicitly flagged PROVISIONAL in the crosswalk.
Repeating the region+admin calculation after excluding all four changes the ratios only
minimally:

- A: 0.847 → 0.847
- B: 0.751 → 0.752
- C: 1.034 → 1.035
- D: 0.431 → 0.432
- E: 0.570 → 0.569
- F: 0.623 → 0.622
- G: 0.846 → 0.846

Therefore the new region-level conclusion is not driven by those four crosswalk choices.

## Interpretation update

This test materially strengthens one conclusion and weakens several others:

- **C:** rejection is strengthened. Once exact region and administrative composition are
  preserved, C is not compact relative to the matched null at all.
- **D:** remains the strongest beyond-region profile by this effect-size diagnostic,
  though its separate k-sensitivity and residualization caveats remain.
- **E and F:** retain clear residual structure, but geographic composition explains part
  of their original compactness.
- **B:** remains a within-federal-city subtype candidate; it is not merely a Moscow/
  St Petersburg/Sevastopol mixture artifact.
- **G:** remains graph-coherent, but its attribute compactness beyond geography and admin
  form is modest. Its huge sample size must not be confused with a large effect.
- **A:** retains moderate matched-null compactness, but this does not fix its negative
  silhouette / overlap problem.

## What this does NOT solve

This is not yet a full spatial-dependence correction. Subject-level stratification does
not model adjacency, distance decay, local spatial autocorrelation or municipality-level
population/density. Polygon geometry or centroids are still required for Moran/LISA,
spatial block resampling and distance-based sensitivity checks.

## External spatial source located

SberIndex documents a versioned municipality reference containing `territory_id`, OKTMO,
region code, municipality type, administrative-centre coordinates and a separate spatial
polygon layer. The reference was built from Rosstat and OpenStreetMap and is explicitly
intended for year-specific municipal analysis.

Primary description:
https://habr.com/ru/companies/sberbank/articles/849682/

Dataset landing page:
https://sberindex.ru/ru/research/dataset-borders-and-changes-of-municipalities

A public project mirror containing a `municipalities.geojson` derived from the SberIndex
municipality layer was also located:
https://github.com/YuliyaTorgasheva/spo_map

The large GeoJSON itself could not be materialized through the current execution
network, so polygon-based tests are deliberately not claimed as completed.
