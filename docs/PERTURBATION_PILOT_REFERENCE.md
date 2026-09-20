# Perturbation pilot reference pack

This pack contains the accepted n=5 perturbation evidence referenced in the research context.
It is intended to unblock the reproducibility gate before the n=50 high-repetition run.

## Canonical perturbation procedure

The accepted runner `reference_code/run_supra_perturbation_consensus.py` reconstructs the baseline graph first and checks ARI=1.0 against the saved reference labels.

For each perturbation seed:

- RNG: `np.random.default_rng(20260918 + seed)`
- perturb only intralayer edges;
- independently drop each intralayer edge with probability 0.05;
- for retained intralayer edges multiply the weight by `exp(N(0, 0.02))`;
- temporal identity edges are unchanged;
- Louvain resolution = 0.5;
- Louvain seed = perturbation seed;
- reference feature construction remains alpha=0.70, k=20, omega=2.

Accepted pilot seeds: 0, 1, 2, 3, 4.

## Canonical run-level pilot values

See `reference_outputs/supra_same_object_stability_run_summary.csv` and use rows with `mode=perturb`.
Expected full-supra ARI values for seeds 0..4:

- 0: 0.461664
- 1: 0.405639
- 2: 0.434314
- 3: 0.423048
- 4: 0.542771

Expected Dec-2024 ARI values:

- 0: 0.782163
- 1: 0.676889
- 2: 0.664693
- 3: 0.924049
- 4: 0.719863

The gate should compare recomputed values against the full-precision values in the CSV, not the rounded values above.

## B/E pilot boundary evidence

`reference_outputs/BE_boundary_instability_by_perturbation.csv` is canonical pilot evidence for the five seeds.
B/E cross-coassignment values are approximately:

- seed 0: 0.091398
- seed 1: 0.994624
- seed 2: 0.091398
- seed 3: 0.000000
- seed 4: 0.596774

This extreme variation is why n=5 is descriptive only and the boundary distribution remains unresolved.

## Important distinction

`dec2024_graph_perturbation_consensus_A_to_G.csv` is retained as historical evidence from an earlier perturbation audit. Do not assume it is identical to the supra-graph perturbation procedure above unless code/provenance demonstrates that identity. The n=50 expansion requested now must reproduce the supra pilot first.

## Configuration rule

Do NOT edit the reference `baseline.yaml` to change a historical target of 30 runs.
Create a new dedicated configuration, e.g. `configs/perturbation_highrep.yaml`, with `n_repetitions: 50` and explicit seeds 0..49.

## Required gate

Before seeds 5..49 are accepted:

1. Reconstruct the unperturbed reference and verify full-supra and Dec ARI/NMI = 1.
2. Re-run perturbation seeds 0..4 using the canonical procedure.
3. Compare run-level ARI/NMI and A-G retention/coassignment to these reference outputs within declared numerical tolerances.
4. If they do not reproduce, stop and write the failure report instead of adapting the perturbation model.
