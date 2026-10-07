# Synthetic temporal v4 audit

## What was found

In `synthetic_temporal_v3`, partition ARI/NMI used `truth.ravel()` against
`inferred.ravel()`. For independently labelled monthly partitions this can mix within-month
partition quality with arbitrary cross-month numeric label identity. A label permutation in
one month can therefore change the flattened diagnostic without changing that month's partition.

## What was corrected

V4 makes mean monthly ARI/NMI the primary partition-quality measures. They are computed directly
within each month and require no label alignment. Hungarian alignment is used only for semantic
state and event metrics. The flattened metrics have explicit `legacy_flattened_*` names and are
excluded from utilities and omega comparisons. Transition and no-transition scenarios receive
separate, fixed-component utilities; any undefined required component is an error rather than a
silently skipped value. Switch F1 is not interpreted as failure when no true event exists.

## What did not change

- synthetic data generator and all generator parameters;
- scenarios, 20-seed grid, omega grid, bootstrap seed, k, and Louvain resolution/seed;
- real-data baseline, real-data omega=2, real clustering outputs, A-G labels, or scientific statuses.

## Reproducibility and scope

- Config: `configs/synthetic_temporal_benchmark_v4.yaml`
- Config SHA256: `72bb1ebe64234a4251e6fd41df5b4eae57cc6d6ab6fd99870e09cb39e4a93e87`
- Seed-level rows: 720
- Month-level partition rows: 8640

V3 remains a historical, methodologically limited result; it is not corrupt or fraudulent. V4
supersedes v3 only for conclusions about synthetic temporal calibration. No real clustering was
recomputed. The benchmark reports metric-specific trade-offs and does not declare a universally
best omega or retune the reference specification.
