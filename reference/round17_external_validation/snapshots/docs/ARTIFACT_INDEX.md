# Artifact Index — What Codex Should Look At

## Current state — Round16 evidence and Atlas 2.2.1 engineering release

The machine-readable pointer is `docs/CURRENT_STATE.json`. Evidence v2.3.0 and
Atlas v2.2.1 are separate versions. Scientific A–G statuses and the reference
specification are unchanged. Round16 computational work is complete, but full
acceptance remains limited by unavailable contextual inputs. Read
`outputs/round16_evidence/ROUND16_FINAL_PRESUBMISSION_AUDIT.md` and
`docs/ENGINEERING_HARDENING_20260922.md` before the historical context below.

Context controls (geography, population/density, residualization) remain
historical-only where their source inputs are unavailable. The descriptive B
within-stratum comparison is separately reproducible. Total's denominator and
category additivity remain unestablished. Consensus agreement does not remove
these limits or establish geographic meanings for A–G.

Use `python scripts/verify_current_artifacts.py` for the current checkout.
The old standalone verifiers retain their historical scope and original bytes.
Atlas v2.2.1 preserves v2.2 arithmetic on recorded inputs and adds configuration,
input integrity, verified resume and explicit unresolved handling; it is not a
new clustering experiment. See `docs/ATLAS_REPRODUCTION.md`.

## Historical context — retained with the current scope above

## Latest evidence — completed Rounds 14 and 15

- `docs/PERTURBATION_PILOT_PROVENANCE_RESOLUTION.md`: historical n=5 superseded; no quantitative reuse. Its files listed below remain historical reference only.
- `docs/PERTURBATION_V2_PROTOCOL.md`: new sorted-edge protocol and byte serialization.
- `configs/leiden.yaml`, `configs/perturbation_v2.yaml`: executed configs. Prior `configs/perturbation_highrep.yaml` belongs to the failed historical-pilot attempt.
- `outputs/leiden_robustness/`: `LEIDEN_ROBUSTNESS_AUDIT.md`, `LEIDEN_FINDINGS.md`, raw labels, graph identity checks, requested metrics and `archetype_status_round14_leiden.csv`.
- `outputs/perturbation_v2/`: `PERTURBATION_V2_REPRODUCIBILITY_GATE.md`, `PERTURBATION_HIGHREP_AUDIT.md`, `PERTURBATION_HIGHREP_FINDINGS.md`, four `perturbation_v2_50_*.csv` primary outputs, all raw seed checkpoints, and `archetype_status_round15_perturbation_v2.csv`.
- `outputs/perturbation_v2/perturbation_v2_distributions.png` and `.svg`: descriptive plots, all 50 seeds.
- `outputs/evidence_v2_2_0/`: new matrix versions v2.1.0 (Leiden) and v2.2.0 (plus v2 n=50), claim changes and manifest. Scope explicitly limited to available Round 13 status plus new rounds because the full historical master matrix is missing.
- `docs/ROBUSTNESS_V2_COMMANDS.md`: execution and checkpoint/resume commands.

The historical-pilot gate instructions later in this index are superseded by the explicit provenance resolution above. They must not block Leiden or replace the v2 hash gate.

## Repository-native baseline artifacts

- `configs/baseline.yaml` — reference config.
- `outputs/baseline/supra_labels.csv` — saved baseline temporal labels.
- `outputs/baseline/static_dec2024_labels.csv` — saved reference static labels.
- `outputs/baseline/run_manifest.json` — baseline manifest.

## Alpha sensitivity

Primary directory: `outputs/alpha_sensitivity/`.

Key files:

- `ALPHA_SENSITIVITY_AUDIT.md`
- `ALPHA_SENSITIVITY_FINDINGS.md`
- `alpha_sensitivity_master_summary.csv`
- `alpha_sensitivity_static_metrics.csv`
- `alpha_sensitivity_static_topology.csv`
- `alpha_sensitivity_temporal_summary.csv`
- `alpha_sensitivity_archetype_retention.csv`
- `alpha_sensitivity_archetype_pair_coassignment.csv`
- `archetype_status_round13_alpha.csv`

## Existing docs already in repository

- `docs/methodology.md`
- `docs/reproducibility.md`
- `docs/evidence_governance.md`
- `docs/spatial_region_robustness.md`
- `docs/spatial_block_robustness.md`
- `docs/alpha_sensitivity.md`

## External/context artifacts from prior research rounds

These may not all be committed to GitHub. If the task needs them, require the user/environment to provide them rather than inventing values.

Important historical artifacts include:

- `MASTER_PROFILE_EVIDENCE_MATRIX.csv`
- `GLOBAL_CLAIMS_LEDGER_V2.csv`
- `STATUS_TAXONOMY.csv`
- `CASCADE_IMPACT_MATRIX.csv`
- `CLAIM_EVIDENCE_DEPENDENCIES.csv`
- `EVIDENCE_CHANGE_CONTROL_PROTOCOL.md`
- `EVIDENCE_SNAPSHOT_v2.0.1_SHA256.csv`
- `archetype_status_round12_population_density.csv`
- population/density and spatial-control audit outputs;
- OKTMO crosswalk and spatial geometry joins;
- pilot perturbation artifacts, especially per-seed A–G retention and B/E coassignment.

## Raw data expected by current repository

- `data/raw/spending.csv.zip`
- `data/raw/mobility.csv.zip`

Additional external inputs used in later research rounds may include Rosstat OKTMO snapshots, municipal population spreadsheets, and GeoJSON boundaries. Do not assume they are present just because this context document mentions them.

## Rule

If an artifact required for a new claim is missing, stop that branch or clearly mark the result unavailable. Do not recreate historical evidence by guessing from prose summaries.

## Canonical perturbation pilot reference (now repository-native)

Primary directory: `outputs/perturbation_pilot_reference/`.

Files:

- `supra_same_object_stability_run_summary.csv` — canonical run-level reference values; use `mode=perturb`, seeds 0..4 for the pilot reproduction gate.
- `supra_same_object_stability_archetype_details.csv` — per-seed A–G destination/retention/coassignment details.
- `BE_boundary_instability_by_perturbation.csv` — canonical five-seed B/E boundary evidence.
- `PERTURBATION_EXPANSION_STATUS.md` — status explaining why n=5 is pilot-only and the previous expansion attempt was not accepted.
- `reference/perturbation_pilot/run_supra_perturbation_consensus.py` — preserved historical runner documenting the accepted perturbation distribution/procedure.
- `docs/PERTURBATION_PILOT_REFERENCE.md` — exact perturbation semantics and gate instructions.

Historical instruction, superseded: this pilot is not a gate for v2. Use the canonical v2 protocol and its saved hash gates.

The historical `configs/baseline.yaml` contains `perturbation_runs_target: 30`. Preserve that baseline file unchanged. The current requested expansion target is 50 and belongs in a new dedicated high-rep config.
