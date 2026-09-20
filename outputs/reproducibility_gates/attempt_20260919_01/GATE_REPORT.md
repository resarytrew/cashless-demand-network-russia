# Reproducibility gate report

Status: STOPPED at canonical pilot seed 0. No scientific evidence/status round was advanced.

## Baseline

Full-supra ARI=NMI=1; temporal Dec-2024 ARI=NMI=1; standalone static Dec-2024 ARI=NMI=1. All deviations from 1 are zero. Historical build_shared also reproduced the unperturbed reference exactly.

## Graph identity

Static and supra graphs passed exact NetworkX-to-igraph roundtrip checks, including isolated nodes and binary float64 edge weights. No Leiden optimization was run. Historical canonical graph checksum also equals the repository supra checksum.

- static: nodes=1904, edges=11787, edge-weight SHA256=fa1e228b2ef7f2ffb0dedcb5446f729ff898b2c49113e11d13fcde47f00090d8
- supra: nodes=45696, edges=326912, edge-weight SHA256=3292eea68c2506af407c8348b1dcbc80486658d231c8a858319b500a0deca1a8

Baseline file SHA256: 3a3aadc0c8e174a5388999e1a1b8ea472600b186c0d22f392f4c91ecddeb12d2
Resolved config SHA256: f6b3960c997c4e7f050f4779f2df59c59ab6fd659319c3ea92195da3507ae228 (matches saved baseline manifest).

## Canonical pilot

Seed 0 failed 28/37 comparisons; atol=1e-12, rtol=0.0. Seeds 1..4 were not run after this failure. Raw seed output was saved before comparisons.

| Metric | Reference | Reproduced | Delta (reproduced-reference) |
|---|---:|---:|---:|
| K_supra | 10 | 13 | 3 |
| ARI_all_supra | 0.4616639704361159 | 0.45349215671565718 | -0.0081718137204586008 |
| NMI_all_supra | 0.63951306616828019 | 0.58739106786316519 | -0.052121998305114901 |
| ARI_Dec2024 | 0.78216310993936866 | 0.73647373129170068 | -0.045689378647667901 |
| NMI_Dec2024 | 0.75199998164270676 | 0.75721974724340979 | 0.0052197656007029998 |
| K_Dec2024 | 8 | 9 | 1 |
| BE_cross_coassignment | 0.091397849462365593 | 0.24358130348913759 | 0.152183454026772 |
| B_within_pair_coassignment | 1 | 0.62634125815274566 | -0.37365874184725428 |
| E_within_pair_coassignment | 0.83301365882011047 | 0.989247311827957 | 0.1562336530078465 |

All A-G differences are in pilot/pilot_comparisons.csv; the failure report is pilot/PERTURBATION_PILOT_REPRODUCIBILITY_FAILURE.md.

Cause of the mismatch is not established. Do not substitute these results for the canonical pilot or adjust the experiment to match old results.

## Environment

- python: 3.13.6 (tags/v3.13.6:4e66535, Aug  6 2025, 14:36:00) [MSC v.1944 64 bit (AMD64)]
- executable: C:\Python313\python.exe
- numpy: 2.4.4
- pandas: 2.3.3
- scipy: 1.16.3
- scikit-learn: 1.7.2
- networkx: 3.6.1
- PyYAML: 6.0.3
- igraph: 1.0.0
- leidenalg: 0.12.0

Working copy has no .git; git commit is unavailable (null).

## Implementation and verification

Created configs/perturbation_highrep.yaml with target 50, seeds 0..49 and the documented canonical procedure. Added non-destructive reproduction/pilot gate modules and tests. Historical runner functions were called unchanged; only input paths were staged locally. No experiment implementation beyond gates was launched.

Full test suite: 12 passed. Baseline config, baseline labels, canonical reference CSVs and historical runner remain unchanged (input_integrity_check.json).

The reference pack byte-level SHA256 comparisons are recorded in input_integrity_check.json; any distribution-format discrepancy is recorded without modifying the pack.
