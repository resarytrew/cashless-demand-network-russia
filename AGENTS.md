# AGENTS.md — SberIndex Attributed Network Research Contract

## Mandatory startup

Before doing any material research or robustness task, read in this order:

1. `docs/CODEX_START_HERE.md`
2. `docs/RESEARCH_STATE.md`
3. `docs/HYPOTHESIS_LEDGER.md`
4. `docs/evidence_governance.md`
5. `docs/ARTIFACT_INDEX.md`
6. the YAML config for the requested run
7. relevant prior audit/findings files under `outputs/`

Do not rely on README alone for scientific context.

## Research identity

This project studies **profiles of local cashless consumer demand** using attributed and temporal networks. Do not rename them as universal “types of economy.”

The current reference specification is a **reference**, not an optimum:

- strict balanced panel: 1904 municipalities;
- Jan-2023 through Dec-2024, 24 months;
- six-part composition with residual `Other`;
- CLR / Aitchison composition block;
- robust-z log spending-level block;
- alpha = 0.70 composition / 0.30 level;
- mutual-kNN, k=20;
- temporal coupling omega=2;
- Louvain resolution=0.5, seed=0;
- static Dec-2024 isolate fallback ON;
- temporal layer isolate fallback OFF.

## Scientific discipline

Never silently tune parameters after seeing results. One material change = one explicit config/run. Preserve baseline outputs and prior evidence rounds.

Distinguish:

- internal cohesion;
- boundary stability;
- algorithmic robustness;
- perturbation robustness;
- temporal persistence;
- geographic/urban-context dependence.

High retention does not imply stable exact boundaries. Statistical significance does not imply a large effect. Exploratory p-values are not confirmatory.

Do not use the words/claims `proved`, `validated`, `true clusters`, `optimal`, `seven robust archetypes`, or equivalent unless an explicit project decision changes this rule.

Use the project terminology documented in `docs/RESEARCH_STATE.md` and `docs/HYPOTHESIS_LEDGER.md`.

## Evidence rules

When a new test materially changes a claim:

1. save raw per-run results;
2. save a concise summary;
3. save an audit markdown documenting exact method and deviations;
4. create a new evidence/status round instead of overwriting an old one;
5. update the master evidence matrix in a new version;
6. state what strengthened, weakened, or remained unchanged.

Do not delete negative or inconvenient results.

## Reproducibility gates

Before a robustness test that depends on the baseline, reproduce the baseline first. If ARI/NMI or other required checks fail, stop the downstream robustness run and emit a failure report. Do not “fix” stored outputs by hand.

For algorithm-swap tests, verify that the input graph is identical: same nodes, edges, weights, checksums, and config except for the algorithm being swapped.

The historical n=5 pilot is SUPERSEDED_NON_REPRODUCIBLE_HISTORICAL_PILOT and is not quantitative evidence. The explicit user-authorized provenance resolution replaces its old reproduction gate; see `docs/PERTURBATION_PILOT_PROVENANCE_RESOLUTION.md`. It does not block independently gated Leiden.

For canonical perturbation protocol v2, require exact same-process, fresh-process and insertion-order graph checksum gates before high-rep runs. Read `docs/PERTURBATION_V2_PROTOCOL.md` and the saved v2 gate report. Do not search package versions/RNG/edge orders to fit historical CSVs.

## Coding rules

- No hidden hyperparameters in Python; use YAML.
- Preserve sparse graph representations.
- Never construct a dense 45,696 × 45,696 matrix.
- Checkpoint long-running seed-based experiments.
- A rerun should skip completed seeds unless `--force` is explicit.
- Add tests for deterministic behavior and output schemas.
- Record Python/package versions, git commit, config hash, and seed in manifests.
- Run the full test suite before finishing.

## Current next tasks

Leiden Round 14 and canonical perturbation robustness v2 n=50 Round 15 are completed in `outputs/leiden_robustness/` and `outputs/perturbation_v2/`. Read their audits/findings and `outputs/evidence_v2_2_0/MASTER_PROFILE_EVIDENCE_MATRIX_v2.2.0.csv` before further research. The full historical master matrix was unavailable: the new matrix explicitly carries repository Round 13 status plus new evidence, without invented historical columns.

Do not rerun completed seeds without explicit `--force`. Do not treat the old expansion instructions in `prompts/LEIDEN_HIGHREP_TASK.md` as overriding the user-authorized v2 protocol. Reference parameters remain unchanged.
