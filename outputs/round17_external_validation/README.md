# Round17 external economic validation

Offline replay of 58 normalized observations, matched to current Atlas v2.2.1.
Read INDEPENDENT_ECONOMIC_VALIDATION.md and RECOVERY_AUDIT.md for scope.

From repository root (installed package):

```sh
python scripts/run_round17_external_validation.py
python scripts/run_round17_external_validation.py --output-dir /path/to/empty/replay
```

The first command verifies a completed package; the second computes a fresh replay.
No original Rosstat files or internet are required after dependency installation.
Completed or partial evidence is never overwritten. Partial runs require a new directory.
run_manifest.json seals all outputs including inventories; COMPLETED.json seals that manifest.
CSV/statistics/report are deterministic; runtime manifests record timestamp and environment.
Source recovery is preserved separately under reference/round17_external_validation/recovered/.
