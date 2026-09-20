# Spatial block robustness

## Purpose

This analysis asks whether the Dec-2024 A–G profiles remain compact in the economic feature space after explicitly conditioning on **coarse geographic location** as well as SberIndex administrative form.

It is stronger than the previous subject-level stratified null in one sense (it uses actual geometry rather than subject labels) and complementary in another (grid blocks do not coincide exactly with federal subjects).

## Geometry

The spatial layer is joined to the 1,904-municipality crosswalk by historical OKTMO. Current coverage is 1,903/1,904; one LNR municipality has no polygon in the supplied layer.

The feature space is still the original reference Dec-2024 geometry. Scaling is computed on the full 1,904 panel **before** dropping the municipality without geometry.

## Spatial null

For each grid specification, municipalities are assigned to equal-area square blocks in EPSG:6933.

Block sizes:

- 300 km
- 500 km
- 750 km
- 1,000 km

Each size is evaluated with four grid origins:

- (0, 0)
- half-cell x shift
- half-cell y shift
- half-cell x + y shift

This yields 16 spatial specifications.

For each A–G profile, the null preserves the **exact number of profile members inside every spatial-block × administrative-form stratum**. The null expectation of mean pairwise feature-space distance is computed analytically.

Primary effect:

\[
R = \frac{\text{observed within-profile mean distance}}
         {\text{matched-null expected mean distance}}
\]

`R < 1` means that the profile is more compact than expected after the spatial/admin constraint.

## Why the resampling is without replacement

A conventional with-replacement cluster bootstrap would duplicate entire spatial blocks. Because the outcome is based on pairwise distances, duplicated municipalities would create artificial zero-distance pairs.

Therefore robustness is assessed using **80% spatial-block subsampling without replacement** (1,000 replicates) plus a 500-km leave-one-block-out analysis.

This should be called spatial block subsampling / block robustness, not a classical i.i.d. bootstrap.

## Interpretation rules

- Use the effect-size ratio first; do not turn these exploratory repetitions into confirmatory project-wide p-values.
- A profile is spatially robust only if its conclusion is stable across block sizes/origins and block subsampling.
- A profile that crosses `R=1` under reasonable spatial specifications is not treated as having established residual compactness beyond geography.
- This test does not prove causal spatial mechanisms and does not replace future population/density/urbanization controls.
