# Final submission audit

## 1. Baseline integrity

The fresh gate in `baseline_gate_before_final/` reproduced the 1,904 × 24 panel and reference labels exactly: full-supra, temporal-December and static-December ARI/NMI are all 1. No reference config, graph, label or sealed Atlas output was rewritten.

## 2. Tests and current CI

`python -m pytest -q` passed: 93 tests. The upgrade-surface Ruff fatal/static check passes. `scripts/verify_presubmission_current.py` is the current presubmission verifier and deliberately does not replace the legacy publication-freeze verifier or its known historic workflow-hash mismatch.

## 3–5. ICVI, representation and edge sensitivity

Existing ICVI, Round18 representation and edge-construction evidence are preserved in `outputs/presubmission_upgrade/`. Round18 shows material exact-boundary dependence; it is not used to tune or replace the reference specification.

## 6. National external validation

The audited independent layer has 1,903 valid OKTMO8 matches: population 1,903, wage 1,890, employment 1,890, sector employment 1,888. Exploratory epsilon-squared values are .468, .633 and .516 respectively. External variables never enter clustering.

## 7–9. Geographic confounding, grouped CV and D/F/G

Region-held-out GroupKFold gives logistic macro-F1=.549 and RF macro-F1=.551. Within-region epsilon-squared is .240 (population), .159 (wage), and .255 (employment), so regional composition does not wholly account for descriptive differences, while the lower held-out performance limits transportability claims. D/F/G ordering remains descriptive, not evidence of fixed exact boundaries.

## 10–11. Synthetic temporal benchmark and omega interpretation

Six predeclared synthetic scenarios × 20 seeds used known latent states. Across scenarios, omega=4 maximizes partition ARI and minimizes false-switch rate; omega=0 maximizes event F1. The transparent balanced utility places omega=4 first and omega=2 second. Thus omega=2 remains the historical reference trade-off; a scenario-dependent calibrated range of 2–4 is reported separately and does not alter historical outputs.

## 12. Profile naming

`profile_naming/profile_evidence_table.csv` and `docs/PROFILE_NAMING_AUDIT.md` give one evidence-bounded name and status per A–G. F is TRANSITION, B/E PRELIMINARY, C UNRESOLVED; no unresolved profile is called robust.

## 13. Current CI

`presubmission-verify.yml` invokes the current verifier. It checks tests, the scoped current Ruff correctness gate, a new baseline reproduction in a temporary directory, required final outputs, national manifests, no external-feature reference in the clustering pipeline, and the story JSON contract.

## 14. Story assets

Eleven JSON assets in `story_data/` are generated from saved outputs. They contain no NaN and reconcile to 1,903 verified municipalities; the unresolved lineage row is excluded.

## 15. Remaining limitations

All inference is exploratory and post-hoc. The strict panel is not established as nationally representative; associations are not causal; Total’s denominator/category additivity remains unresolved; exact boundaries depend on representation, graph construction and temporal coupling; a synthetic calibration cannot identify a single real-world universal omega.
