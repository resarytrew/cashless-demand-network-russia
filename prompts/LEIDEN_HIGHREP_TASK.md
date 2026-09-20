# Codex Task — Leiden + High-Rep Perturbation Robustness

> Current user-authorized amendment: Leiden Round 14 and canonical perturbation v2 Round 15 are completed. The historical n=5 expansion instructions below are superseded by `docs/PERTURBATION_PILOT_PROVENANCE_RESOLUTION.md` and `docs/PERTURBATION_V2_PROTOCOL.md`. Historical perturbation failure does not block independently gated Leiden. V2 uses sorted canonical edges and exact same/fresh-process checksum gates; it is not an expansion of the superseded pilot. Latest results are in `outputs/leiden_robustness/`, `outputs/perturbation_v2/`, and `outputs/evidence_v2_2_0/`. The original task text is preserved below as historical context.

Read root `AGENTS.md` and all required research context before executing this task.

## Goal

Complete two clean robustness rounds without retuning the model:

1. Louvain → Leiden algorithmic robustness.
2. Expand the existing perturbation pilot from n=5 to n=50 using the exact existing perturbation distribution and magnitude.

## Fixed reference specification

- alpha=0.70 / 0.30
- k=20
- omega=2
- resolution=0.5
- seed=0 for reference runs
- 1904 municipalities
- 24 months

Do not modify feature construction, graph construction, temporal coupling, or reference config except where the task explicitly swaps Louvain for Leiden.

## Reproducibility gate

Before anything else, reproduce saved baseline labels. Require full-supra ARI=NMI=1 and Dec-2024 ARI=NMI=1. If not, stop and write `REPRODUCIBILITY_FAILURE_REPORT.md`.

## Leiden

Use weighted undirected graph, preferably `python-igraph` + `leidenalg.RBConfigurationVertexPartition`, `resolution_parameter=0.5`, deterministic seed where supported.

Do not tune resolution to match Louvain K.

Compute static Dec-2024 and temporal supra results, including:

- K / supra-community count;
- modularity/MQ, SW, CH/N, S_Dbw, AVI, AVU as applicable;
- graph topology unchanged checks;
- full-supra ARI/NMI vs Louvain;
- 24 monthly ARI/NMI distributions;
- Dec ARI/NMI;
- temporal switches and adjacent-month persistence;
- A–G best-match retention, precision, Jaccard;
- pair-boundary evidence, especially B/E, D/F, F/G.

Required outputs:

- `LEIDEN_ROBUSTNESS_AUDIT.md`
- `LEIDEN_FINDINGS.md`
- `leiden_static_metrics.csv`
- `leiden_temporal_summary.csv`
- `leiden_monthly_similarity.csv`
- `leiden_archetype_retention.csv`
- `leiden_pair_coassignment.csv`
- `archetype_status_round14_leiden.csv`

## High-rep perturbation

Find the existing n=5 pilot. Do not invent a new noise model. Reproduce the original five runs first. If they do not reproduce, stop and emit `PERTURBATION_PILOT_REPRODUCIBILITY_FAILURE.md`.

Then run n=50, preferably seeds 0..49 if consistent with the pilot.

Checkpoint every seed/batch. Do not recompute completed seeds unless `--force` is set.

For each seed save:

- full-supra ARI/NMI;
- Dec ARI/NMI;
- supra community count / Dec K;
- mean/median switches and <=2-switch share;
- A–G retention, precision, Jaccard;
- A–G pair coassignment matrix or at minimum A/D, B/E, D/F, F/G.

Summaries must include mean, median, SD, min, max, q05, q10, q25, q75, q90, q95. For A–G retention also report shares >=0.90, >=0.80, >=0.70, >=0.50.

Required outputs:

- `PERTURBATION_HIGHREP_AUDIT.md`
- `PERTURBATION_HIGHREP_FINDINGS.md`
- `perturbation_50_runs.csv`
- `perturbation_50_archetype_retention.csv`
- `perturbation_50_pair_coassignment.csv`
- `perturbation_50_summary.csv`
- `archetype_status_round15_highrep.csv`

## Evidence update

Create a new, non-destructive `MASTER_PROFILE_EVIDENCE_MATRIX_UPDATED.csv` adding Leiden and perturbation50 columns. Do not overwrite historical evidence matrices/status rounds.

## Implementation

Add appropriate modules/configs/tests/CLI commands consistent with repository architecture. Suggested names:

- `src/sbernet/robustness/leiden.py`
- `src/sbernet/robustness/perturbation_highrep.py`
- `configs/leiden.yaml`
- `configs/perturbation_highrep.yaml`

Add tests for baseline reproduction, graph identity before algorithm swap, deterministic seeds, pilot reproduction, and output schemas.

Run the complete test suite before finishing.

## Final research summary

Report what changed and what did not. Do not select a “best algorithm,” do not auto-change the reference specification, and do not claim seven robust archetypes.
