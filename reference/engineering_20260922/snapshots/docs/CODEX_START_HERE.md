# Codex Start Here

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
