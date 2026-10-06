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

Six predeclared synthetic scenarios × 20 seeds used known latent states. The prior synthetic run is retained but superseded because its mixed scenario overlaid switch, boundary and shock roles. In v3 these roles are disjoint (10% true switches, 10% boundary-only, 10% temporary-shock-only, 70% stable). Across scenarios, omega=4 maximizes partition ARI (.905442) and minimizes false-switch rate (.008926); omega=0 maximizes event F1 (.259793). The transparent balanced utility is highest at omega=2 (.622792; omega=4: .600375). Thus omega=2 remains the historical reference trade-off and is supported by this fixed synthetic compromise; no universal real-world optimum is inferred.

## 12. Profile naming

`profile_naming/profile_evidence_table.csv` and `docs/PROFILE_NAMING_AUDIT.md` give one evidence-bounded name and status per A–G. F is TRANSITION, B/E PRELIMINARY, C UNRESOLVED; no unresolved profile is called robust.

## 13. Current CI

`presubmission-verify.yml` invokes the current verifier. It checks tests, the scoped current-surface Ruff correctness gate, a new baseline reproduction in a temporary directory, required v3 outputs, national manifests, no external-feature reference in the clustering pipeline, and the v3 story JSON contract.

## 14. Story assets

Eleven JSON assets in `story_data_v3/` are generated from saved outputs. They contain no NaN and reconcile to 1,903 verified municipalities; the unresolved lineage row is excluded.

## 15. Remaining limitations

All inference is exploratory and post-hoc. The strict panel is not established as nationally representative; associations are not causal; Total’s denominator/category additivity remains unresolved; exact boundaries depend on representation, graph construction and temporal coupling; a synthetic calibration cannot identify a single real-world universal omega.
