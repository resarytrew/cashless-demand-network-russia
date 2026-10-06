# Final presubmission audit

## Baseline integrity

`configs/baseline.yaml` and every frozen historical output were left unchanged.
The post-upgrade reproduction gate in `baseline_gate_post_upgrade/` passed with
the exact 1,904×24 panel, unchanged static/supra graph fingerprints, and ARI/NMI
of exactly 1 for full supra, temporal December and static December reference
labels. The original pre-upgrade hashes are recorded in
`PRE_UPGRADE_BASELINE_AUDIT.md`.

## Test status

`PYTHONPATH=src;.;scripts python -m pytest -q` completed with **78 passed**.
The project-wide artifact verifier remains blocked before and after this work by
the pre-existing mismatch of `.github/workflows/verify.yml` against its historic
freeze inventory. This implementation did not alter that file. The independent
numerical baseline gate passed twice.

## New computational evidence

- **ICVI:** `icvi/canonical_icvi.csv` adds raw CH, CH/N, SW, documented new
  S_Dbw, AVI, AVU and MQ on a common December geometry. It does not reuse the
  historical finite S_Dbw.
- **Round18:** reference exactly reproduced; R1 temporal-December ARI/NMI is
  .821695/.763635 and R2 is .707693/.649036. Exact boundaries therefore depend
  materially on representation. `outputs/evidence_v2_5_0/` records this as an
  additive evidence update without an A–G status change.
- **Edge sensitivity:** at k=20 mutual has 11,787 edges, density .006506,
  K=9 and reference ARI=1. Union has 19,115 edges, density .010551, K=8 and
  ARI=.596928. Full fixed-grid results are in `edge_sensitivity/`.
- **Temporal sensitivity:** share with at most two switches is .000525 at
  omega=.25, .852941 at omega=2, and .888130 at omega=4. Full-supra ARI at
  omega=4 is .470711. This is a joint data-and-regularization result, not an
  intrinsic stability claim.

## Interpretation and visualization

`economic_typology/profile_summary.csv` supplies descriptive size, level,
feature and Atlas-stability fields. `external_validation/` republishes the
Round17 matched coverage without fitting on external variables. The typology
keeps F as a D/G transition area, B/E preliminary, and C unresolved.

The sealed Stability Atlas was not changed. Its companion data now include
24-month municipality trajectories and half-year alluvial-flow input in
`visualization/`; a future viewer integration should be a separate engineered
release rather than an unreviewed edit of the sealed artifact.

## Reproduction

Run the following on a fresh checkout (or copy the Round18 configs and change
only their `paths.output_dir` to new directories):

```powershell
$env:PYTHONPATH='src;.;scripts'
$env:PYTHONUTF8='1'
python -m pytest -q
python -m sbernet.robustness.reproduction_gate --config configs/baseline.yaml --output outputs/presubmission_upgrade/new_baseline_gate
python scripts/run_presubmission_experiments.py round18 --config configs/round18_reference.yaml
python scripts/run_presubmission_experiments.py round18 --config configs/round18_r1_fivepart_clr.yaml
python scripts/run_presubmission_experiments.py round18 --config configs/round18_r2_observed_levels.yaml
python scripts/run_presubmission_experiments.py aggregate-round18
python scripts/run_presubmission_experiments.py edge
python scripts/run_presubmission_experiments.py omega
python scripts/build_presubmission_tables.py
python scripts/build_round18_evidence_update.py
python scripts/build_temporal_visualization_data.py
```

All commands that write results refuse existing output directories. The two
archived folders in Round18/presubmission output record an early status-format
attempt and an empty failed omega attempt; neither is used as evidence.
