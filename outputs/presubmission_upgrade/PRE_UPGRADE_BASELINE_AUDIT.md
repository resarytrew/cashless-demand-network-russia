# Pre-upgrade baseline audit

Date: 2026-10-05 (Asia/Yekaterinburg)  
Repository commit: `e461949b71d39ad8a6b2d15ae630ad225b529293`  
Working tree before implementation: clean.

## Reference pipeline

The immutable reference is `configs/baseline.yaml`: the strict 1,904-municipality,
24-month panel; six-part technical composition (five published categories plus
`Other = Total - sum(categories)`); CLR plus robust log-Total level block;
70/30 block weights; mutual-kNN `k=20`; adaptive RBF; omega=2 supra-graph;
and Louvain at resolution 0.5, seed 0.  The frozen reference labels are
`outputs/baseline/static_dec2024_labels.csv` and
`outputs/baseline/supra_labels.csv`.

## Canonical artifact inventory

| Artifact | SHA-256 |
| --- | --- |
| `configs/baseline.yaml` | `3a3aadc0c8e174a5388999e1a1b8ea472600b186c0d22f392f4c91ecddeb12d2` |
| `outputs/baseline/supra_labels.csv` | `7cac1146f94c61cd1d6cdcfb6600796c1d95e05d94edd570c53a38251243192a` |
| `outputs/baseline/static_dec2024_labels.csv` | `879f91094746e6e47d1346b5e2169369ebf6f28e1c437d7f8ddb597ba6b4fb09` |
| `outputs/baseline/run_manifest.json` | `d693781287e4118b90031983e7f2f45249abd6e0ab2c01994cff68565d6eafd5` |
| `outputs/round16_benchmark/canonical_method_benchmark.csv` | `269acd22fbe653f6ba07a695491fbe70245ec72b0edfa943619918d158e2e989` |
| `outputs/round17_external_validation/CLAIM_EVIDENCE_MATRIX_v2.4.0.csv` | `2930488e1adf3754e35a7242b06b475e2b70b515ff204a2e5997cfc37d72efac` |
| `outputs/stability_atlas_v2_2_1/COMPLETED.json` | `e4ef220469ff1f76564dba1f50f2e8039070aa29fcba4e8464c1211b077756eb` |

## Checks executed before implementation

- `PYTHONPATH=src;.;scripts python -m pytest -q`: **74 passed**.
- `python -m sbernet.robustness.reproduction_gate --config configs/baseline.yaml --output outputs/presubmission_upgrade/baseline_gate`: **passed**. The strict panel was 1,904 by 24; static and supra graph fingerprints were written in the gate; full supra, December temporal, and static December ARI/NMI were all exactly 1.0 against the frozen reference labels.
- `python scripts/verify_current_artifacts.py`: **failed before any implementation change** on an integrity mismatch for `.github/workflows/verify.yml`. This is an existing checkout/freeze-manifest mismatch, not a failed numerical baseline reproduction. It must remain explicit until the provenance registry is reconciled; the file was not altered.
- A first bare `python -m pytest -q` failed collection because the repository uses the `src/` layout and the package was not installed. The documented `PYTHONPATH` command above is the valid test invocation.

## Historical/unreproducible components preserved

- The historical perturbation `n=5` pilot is `SUPERSEDED_NON_REPRODUCIBLE_HISTORICAL_PILOT`; it is not quantitative evidence.
- Historical cosine, correlation, lagged-correlation and DTW benchmark families remain `UNREPRODUCIBLE_HISTORICAL_BENCHMARK_COMPONENT`.
- Contextual controls whose source inputs are unavailable remain historical-only.
- Round18 is plan-only at this audit point; no Round18 outputs are treated as prior evidence.

No baseline configuration, frozen output, legacy experiment config, or historical evidence artifact was modified by this audit.
