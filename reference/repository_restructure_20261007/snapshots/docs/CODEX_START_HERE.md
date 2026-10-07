# Codex Start Here

## Current state — Round17 external interpretation evidence (v2.4.0)

Round17 adds 58 exact matches in four regions to current Atlas v2.2.1; it is an
external interpretation layer, not a new clustering or a robustness-status upgrade.
External measurements were not used to build or tune the original network.
The selected sample is not nationally representative (A43/C4/D2/F2/G7; B/E absent).
All ten recovered statistics reproduce, including the uncertain Khabarovsk A/G
comparison and adjusted Altai result. Altai D2/F1/G3 supports only a limited
regional wage gradient. Yakutia A wage/investment association is conditional and
noncausal; employee wages are not household income and mining is not established.
B–E remains internally supported but externally unassessed. C remains contextual /
unresolved. F's transition interpretation gains limited external corroboration;
prior boundary-stability qualifications remain. Seven equal universal economic
archetypes remain rejected.

Read [Round17 report](../outputs/round17_external_validation/INDEPENDENT_ECONOMIC_VALIDATION.md),
[audit](../outputs/round17_external_validation/RECOVERY_AUDIT.md),
[claim matrix](../outputs/round17_external_validation/CLAIM_EVIDENCE_MATRIX_v2.4.0.csv)
and [current pointers](CURRENT_STATE.json). Raw source documents and source row/page
locations are unavailable; normalized analytical data and statistics replay offline.
No baseline, Round16, perturbation or existing Atlas outputs were changed.
A–G scientific robustness statuses and the reference specification are unchanged.
Round18 is [planned separately](ROUND18_REPRESENTATION_ROBUSTNESS_PLAN.md), not executed.

## Preserved prior state — Round16 evidence and Atlas 2.2.1 engineering release

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

This repository is the executable core of a longer research project. The chat history is **not** the source of truth; this context pack is the distilled research state that should travel with the code.

## What to trust, in order

For executable behavior: YAML config → source code → run manifest/output.

For scientific status: latest explicit status/evidence files → `docs/HYPOTHESIS_LEDGER.md` → latest audit/findings for the relevant test.

For project-wide rules: root `AGENTS.md` and `docs/EVIDENCE_GOVERNANCE.md`.

If two narrative files conflict, prefer the newer evidence round and the underlying numeric artifact. Never reconcile a conflict by guessing.

## The research question

Competition task: identify territorial economic structure from attributed networks. Operationally, this project asks whether municipalities exhibit reproducible **profiles of local cashless consumer demand**, how those profiles are organized in a network, and which apparent communities remain after algorithmic, temporal, geographic, administrative, population-density, and parameter-sensitivity checks.

The project deliberately avoids claiming that communities are universal “types of local economy.”

## Current state

Latest update: Leiden Round 14 and canonical perturbation robustness v2 n=50 Round 15 are complete. Read `outputs/leiden_robustness/LEIDEN_FINDINGS.md`, `outputs/perturbation_v2/PERTURBATION_HIGHREP_FINDINGS.md` and master matrix v2.2.0 under `outputs/evidence_v2_2_0/`. Historical n=5 is superseded non-reproducible evidence, excluded from quantitative claims; see `docs/PERTURBATION_PILOT_PROVENANCE_RESOLUTION.md`.

The baseline pipeline is reproducible. Sensitivity/robustness already completed includes k, omega, algorithm families in static benchmarks, temporal sensitivity, administrative-form controls, crosswalk/OKTMO audit, region/spatial controls, polygon spatial diagnostics, population/density controls, and alpha sensitivity.

The former two open tasks have been completed as a same-graph Leiden swap and a newly canonical sorted-edge v2 experiment. The latter is not an expansion or reproduction of historical n=5. The unavailable full historical master matrix remains an explicit provenance limitation of the new repository matrix.

## Do not restart solved work

Do not rebuild the OKTMO crosswalk, redo spatial geometry ingestion, or re-select k/omega/alpha unless the user explicitly asks. Those branches have already been audited. Use existing results as context and preserve their caveats.

## Important caution

Many results are post-hoc exploratory robustness. The goal is to measure dependence of claims on modeling choices, not to search for the combination that makes communities look best.
