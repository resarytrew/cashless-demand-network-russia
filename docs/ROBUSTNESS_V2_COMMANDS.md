# Reproducing rounds 14 and 15

Run from the repository root with `src` on PYTHONPATH. The supplied working copy has no git metadata; manifests therefore store null git commit plus source SHA256 values.

PowerShell:

```powershell
$env:PYTHONPATH = 'src'
python -m pytest -q
python -m sbernet.robustness.leiden --config configs/leiden.yaml
python -m sbernet.robustness.perturbation_v2 gate --config configs/perturbation_v2.yaml
python -m sbernet.robustness.perturbation_v2 run --config configs/perturbation_v2.yaml
```

The Leiden output and v2 gate directories must be new: these commands refuse to overwrite them. For a new material run, create a distinct YAML/output directory. The v2 `run` command resumes an existing experiment and validates/skips completed seed checkpoints. `--force` explicitly permits recalculation and archives the prior completed seed directory. Do not use it merely to refresh summaries. A config, source or environment mismatch stops a resumed run.

The active perturbation config is `configs/perturbation_v2.yaml`; `configs/perturbation_highrep.yaml` is preserved from the historical-pilot gate attempt and is not the v2 protocol. `configs/baseline.yaml` remains unchanged with historical target=30 metadata. `project.evidence_version` inherited in experiment configs identifies the reference evidence; new matrix versions are recorded in outputs/evidence_v2_2_0.

Baseline graph cache is read only from the earlier accepted reproduction gate and compared to stored graph/reference/config hashes before use. A fresh baseline reconstruction can be written to a new directory with:

```powershell
python -m sbernet.robustness.reproduction_gate --output outputs/reproducibility_gates/new_attempt
```

Point any new experiment's `experiment.baseline_gate_dir` to that passed gate. Never point reproduction outputs at outputs/baseline. Graph conversion must preserve nodes, edges and weights exactly.

Evidence reports are generated only after all 50 seeds are complete:

```powershell
python scripts/build_robustness_evidence.py
python scripts/plot_robustness_v2.py
```

The evidence builder refuses to replace its evidence-version directory. Historical pilot CSVs, the historical runner, the old failure report and prior status files must remain intact. Read docs/PERTURBATION_PILOT_PROVENANCE_RESOLUTION.md before interpreting any historical pilot value.
