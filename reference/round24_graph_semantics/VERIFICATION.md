# Round24 engineering verification

- `python -m pytest -q`: 152 passed (19.32 seconds).
- `python scripts/verify_current_artifacts.py`: PASS; 390 historical and 353 Round16 frozen files; 46 saved runs, 10,937 numerical comparisons; 24 reconstructed feature months bitwise equal.
- `python scripts/verify_repository_structure.py`: PASS; schema 2, Round24, evidence 2.11.0; 83 current pointers checked.
- `python scripts/verify_presubmission_current.py --skip-tests`: PASS.
- Ruff fatal/static checks on new graph helpers, runner and tests: PASS.
- Repeated `python scripts/run_round24_graph_semantics.py`: sealed outputs verified; all completed seeds skipped, no repeated optimization.
- Fresh baseline gate: exact ARI=NMI=1 in all three scopes and identical historical graph fingerprints.
- Historical reference and union-k20 ICVI-v2 rows reproduced within configured numeric tolerances.

The new protocol, reference/current-state documentation and verifier integration are additive. Pre-existing site, README and profile-card working changes were left intact. No reference configuration, historical evidence, A-G scientific status or Atlas artifact was modified.

Run: `python scripts/run_round24_graph_semantics.py --config configs/round24_graph_semantics.yaml` with `PYTHONPATH=src;.;scripts` on Windows. Results and checksums are in `outputs/round24_graph_semantics/`; the baseline pickle is a local replay cache bound by the completion manifest. The full-period dynamics interpretation is explicitly limited to six CLR composition components without Total and does not remove common seasonal shocks.
