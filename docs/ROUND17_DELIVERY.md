# Round17 integration delivery

The external interpretation layer is evidence v2.4.0; Atlas remains v2.2.1.
Round17 checks passed: 14 recovered checksums, 58 unique municipalities,
A43/C4/D2/F2/G7, four regions, 58 exact Atlas joins and all ten expected statistics.
The full test suite passed **69 tests**, including 15 Round17 tests.
A separate fresh-process replay produced **20 byte-identical stable artifacts**
(all CSVs, reports, inventories and other deterministic files). Runtime manifest
and completion hashes differ because they record execution time.

## Created files

- `src/sbernet/validation/__init__.py`, `external_economic.py`;
  `scripts/run_round17_external_validation.py`;
  `tests/test_round17_external_validation.py`.
- `configs/round17_external_validation.yaml` and the non-executable
  `configs/round18_representation_robustness_plan.yaml`.
- `docs/ROUND17_REPRODUCTION.md`, this delivery record, and
  `docs/ROUND18_REPRESENTATION_ROBUSTNESS_PLAN.md`.
- `outputs/round17_external_validation/`: `README.md`,
  `INDEPENDENT_ECONOMIC_VALIDATION.md`, `DATA_DICTIONARY.md`, `RECOVERY_AUDIT.md`,
  `external_validation_58.csv`, `atlas_join_audit.csv`, `statistical_tests.csv`,
  `dfg_gradient_altai.csv`, `a_validation_cases.csv`, `hypothesis_status.csv`,
  `source_manifest.csv`, `source_provenance.csv`, `expected_results.json`,
  `internal_diagnostics.json`, `gate_results.json`, `reference_replay.txt`,
  `CLAIM_EVIDENCE_MATRIX_v2.4.0.csv`, `MASTER_PROFILE_EVIDENCE_MATRIX_v2.4.0.csv`,
  `input_checksums.csv`, `output_checksums.csv`, `run_manifest.json`, `COMPLETED.json`.
- `reference/round17_external_validation/`: exact 15-file recovered package,
  README, additional dependency pins, snapshots of changed prior files,
  integration manifest and SHA256 sidecar. The manifest enumerates exact paths.
- `outputs/round18_representation_robustness/README.md`: planning placeholder,
  no experimental results or completion seal.

## Changed existing files

README; AGENTS; `pyproject.toml`; `.github/workflows/verify.yml`;
`scripts/verify_current_artifacts.py`; and docs `ARTIFACT_INDEX.md`,
`ATLAS_REPRODUCTION.md`, `CODEX_START_HERE.md`, `CURRENT_STATE.json`,
`HYPOTHESIS_LEDGER.md`, `RESEARCH_STATE.md`.

Their prior bytes are preserved in the explicit integration transition manifest.
Historical engineering and evidence manifests remain unchanged. No previous
outputs, raw data, reference parameters, labels, Atlas classes, perturbation
runs or model source files were edited. All prior master-matrix columns are
retained verbatim as field values in the new version.

## Claim changes and unresolved issues

Added limited external interpretation support for the Altai DFG wage gradient,
Yakutia A wage/investment association, and F's transition interpretation combined
with internal diagnostics. Prior A–G robustness statuses are unchanged. The
adjusted Altai result (p=0.088869) and uncertain Khabarovsk contrast (p=0.279853)
are retained. B/E remain externally unassessed, C contextual/unresolved, and
A's mining mechanism unestablished. No seven-universal-archetype claim is added.

Raw economic documents, original extraction page/cell locations, historical
workbook and crosswalk are unavailable; their hashes are reported provenance,
not locally verified originals. Replay starts from the normalized extract.
Historical panel indices were absent and are assigned from current Atlas.
The selected sample is not national; Altai F has one observation. Missing
investments remain missing outside Yakutia. Nominal employee wages do not
establish household income or purchasing power. Population nonsignificance
does not demonstrate independence. Total/category additivity remains unresolved.

The external data were never used to tune clustering. Baseline was not rerun.
Round18 is a separate plan for fixed R1 five-part CLR and R2 log-level vectors,
both without Other; it has not been executed.

## Main SHA256 hashes

| Artifact | SHA256 |
|---|---|
| Supplied ZIP | `c917d91e59c50dd367ba058b6b7f674325e46a54d54e1d080ccb460abc4a71a3` |
| Canonical external table | `cbd0104565ab5683576355f461ec008bb03f4b99dadfdd93b72675e489ed3e00` |
| Statistical tests | `faf234eba9eb55741cc6d2f2b88ab300f2da525596d48c0c5fd2399104f635f9` |
| Generated report | `980819dddccb3c173237561ab8bf42a538673c22084f7e597eb7305976c366ba` |
| Run manifest | `234fcad218f946ce352d79775daf1996412a0999807bd2185c79bda3ec586e1b` |
| Completion seal | `df45781bb91a219dd3d49f6378fdd58857e9fcc6163c3991e3167ce05699ec66` |

See [replay commands](ROUND17_REPRODUCTION.md),
[generated scientific report](../outputs/round17_external_validation/INDEPENDENT_ECONOMIC_VALIDATION.md),
and [Round18 protocol](ROUND18_REPRESENTATION_ROBUSTNESS_PLAN.md).
