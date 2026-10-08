# Final submission audit

## 1. Baseline integrity

The fresh gate in `baseline_gate_before_final/` reproduced the 1,904 × 24 panel and reference labels exactly: full-supra, temporal-December and static-December ARI/NMI are all 1. No reference config, graph, label or sealed Atlas output was rewritten.

## 2. Tests and current CI

The current verifier runs the full test suite and a scoped current-surface Ruff fatal/static gate. `scripts/verify_presubmission_current.py` complements the legacy publication-freeze verifier; both are expected to pass. The gate is explicitly scoped and is not presented as project-wide Ruff cleanliness.

## 3–5. ICVI, representation and edge sensitivity

Existing ICVI and Round18 representation evidence are preserved in `outputs/presubmission_upgrade/`. The first edge-rule comparison is preserved but superseded: its union-kNN implementation dropped one-sided nominations. The corrected v3 comparison is `edge_sensitivity_v3/`, gated by `baseline_gate_before_v3_corrections/`. At k=20, corrected union-kNN has 26,305 edges, K=6, and ARI=.553326 against the reference static partition; it remains a descriptive sensitivity, not a parameter-selection exercise. Round18 shows material exact-boundary dependence; it is not used to tune or replace the reference specification.

## 6. National external validation

The audited independent layer has 1,903 valid OKTMO8 matches: population 1,903, wage 1,890, employment 1,890, sector employment 1,888. Exploratory epsilon-squared values are .468, .633 and .516 respectively. External variables never enter clustering.

## 7–9. Geographic confounding, grouped CV and D/F/G

Region-held-out GroupKFold gives logistic macro-F1=.549 and RF macro-F1=.551. Within-region epsilon-squared is .240 (population), .159 (wage), and .255 (employment), so regional composition does not wholly account for descriptive differences, while the lower held-out performance limits transportability claims. D/F/G ordering remains descriptive, not evidence of fixed exact boundaries.

## 10–11. Synthetic temporal benchmark and omega interpretation

Synthetic temporal v4 is the current calibration artifact. It evaluates partition
quality by mean monthly ARI/NMI and keeps flattened ARI/NMI only as forensic legacy
diagnostics. Transition and no-transition trade-offs are reported separately; no
universal best omega is selected. V3 remains preserved for history but is not used
as primary omega-selection evidence. The real-data baseline, reference omega=2 and
A–G statuses are unchanged.

## 12. Profile naming

`profile_naming/profile_evidence_table.csv` and `docs/PROFILE_NAMING_AUDIT.md` give one evidence-bounded name and status per A–G. F is TRANSITION, B/E PRELIMINARY, C UNRESOLVED; no unresolved profile is called robust.

## 13. Current CI

`presubmission-verify.yml` invokes the current verifier. It checks tests, the scoped current-surface Ruff correctness gate, a new baseline reproduction in a temporary directory, required v3 outputs, national manifests, no external-feature reference in the clustering pipeline, and the v3 story JSON contract.

## 14. Story assets

Eleven JSON assets in `story_data_v3/` are generated from saved outputs. They contain no NaN and reconcile to 1,903 verified municipalities; the unresolved lineage row is excluded.

## 15. Remaining limitations

All inference is exploratory and post-hoc. The strict panel is not established as nationally representative; associations are not causal; Total’s denominator/category additivity remains unresolved; exact boundaries depend on representation, graph construction and temporal coupling; a synthetic calibration cannot identify a single real-world universal omega.

## 16. Round21 structural sensitivity and separate L2 lens

Round21 is additive evidence v2.8.0. Omega=1 is predominantly a coarse merge of
the omega=2 December partition, while the matched-K control shows a material
omega×resolution interaction. The held-out Atlas sensitivity changes 1/824 stable
core municipalities and 348/388 transition municipalities. Adjusted wage,
employment and sector associations remain observational. Original L2 is a separate
1,876-case lens; both predeclared block-balanced alternatives differ materially
from it and neither is selected. These results do not alter L1, k=20, omega=2,
A–G IDs/statuses or Atlas assignments.

## 17. No retuning

No ICVI, synthetic, Round18, L2, Round20 or Round21 result was used to retune the
reference L1 specification. Negative representation, temporal-coupling and L2
block-geometry sensitivities remain part of the evidence record.

## 18. Round22 attributed-network benchmark

Round22 adds clean-room KEFRiNc at fixed December K=9 without changing the
reference. Seed-0 agreement with static Louvain is ARI=.3080/NMI=.4797; ten-seed
pairwise ARI averages .5213. Stable-core disagreement is 492/824 versus 263/388
for transition and 268/318 for unresolved, so Atlas uncertainty generalizes only
partially and exact method-class dependence is material. Adjusted KEFRiN external
associations are descriptive and were computed after labels were frozen. The
author upstream is pinned, but its license is not verifiable from a license file;
no upstream source code was used. Final L1/A–G/Atlas/L2/Round21 hash gate: PASS.

## 19. Round23 economic-mechanism checks

Round23 freezes seven exploratory diagnostics before computation and passes a
fresh exact baseline replay. The proposed ordering from stable core to higher
economic volatility is not observed; Marketplace/Food substitution is not
specific to F/G; Marketplace-share dispersion rises rather than falls; and Food
share falls Dec-to-Dec in every A–G profile. Two descriptive associations survive
their fixed rules: lower initial Total predicts faster Marketplace-share growth,
and cross-profile wage/population-matched pairs have larger December Aitchison
distances than same-profile controls. Distant graph neighbors are common but
descriptive. No result establishes causality, inflation, welfare, merchant-level
grocery substitution or absent local retail. L1 and A–G statuses are unchanged.
