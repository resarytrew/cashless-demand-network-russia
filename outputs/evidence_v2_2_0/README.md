# Evidence v2.2.0 — completed Rounds 14 and 15

Both experiments completed without changing reference features, graph construction, baseline YAML or historical evidence files. This directory contains new matrix versions, not a replacement of old evidence. The unavailable full historical master matrix is an explicit scope limitation: available Round 13 profile statuses are combined with new numerical results; absent old columns are not invented.

- [Master matrix v2.1.0 — Leiden](MASTER_PROFILE_EVIDENCE_MATRIX_v2.1.0.csv)
- [Master matrix v2.2.0 — Leiden and canonical v2 n=50](MASTER_PROFILE_EVIDENCE_MATRIX_v2.2.0.csv)
- [Claim changes](CLAIM_CHANGES_v2.2.0.csv)
- [Leiden findings](../leiden_robustness/LEIDEN_FINDINGS.md) and [audit](../leiden_robustness/LEIDEN_ROBUSTNESS_AUDIT.md)
- [Round 14 status](../leiden_robustness/archetype_status_round14_leiden.csv)
- [V2 findings](../perturbation_v2/PERTURBATION_HIGHREP_FINDINGS.md) and [audit](../perturbation_v2/PERTURBATION_HIGHREP_AUDIT.md)
- [V2 gate](../perturbation_v2/PERTURBATION_V2_REPRODUCIBILITY_GATE.md)
- [Round 15 status](../perturbation_v2/archetype_status_round15_perturbation_v2.csv)
- [50 run results](../perturbation_v2/perturbation_v2_50_runs.csv)
- [350 profile rows](../perturbation_v2/perturbation_v2_50_archetype_retention.csv)
- [1050 pair rows](../perturbation_v2/perturbation_v2_50_pair_coassignment.csv)
- [Full distribution summaries](../perturbation_v2/perturbation_v2_50_summary.csv)
- [Distribution plot](../perturbation_v2/perturbation_v2_distributions.png)
- [Raw-label/checkpoint verification](../perturbation_v2/ARTIFACT_VERIFICATION.json)
- [Resume verification](../perturbation_v2/RESUME_VERIFICATION.json)
- [Historical pilot provenance resolution](../../docs/PERTURBATION_PILOT_PROVENANCE_RESOLUTION.md)
- [Protocol v2](../../docs/PERTURBATION_V2_PROTOCOL.md)
- [Reproduction commands](../../docs/ROBUSTNESS_V2_COMMANDS.md)

Historical pilot status: SUPERSEDED_NON_REPRODUCIBLE_HISTORICAL_PILOT (matrix field: SUPERSEDED_NON_REPRODUCIBLE). It supplies no quantitative evidence. Protocol v2 is not an expanded historical pilot.

Validation: baseline reproduction PASS; graph identity PASS; v2 same/fresh-process and insertion-order gate PASS; all 50 checkpoints verified; resume skipped all 50 seeds without modifying them; 21 tests passed.

Metric limitation: static S_Dbw is undefined under the explicit zero-density-denominator rule, without post-hoc epsilon or formula substitution. Other requested Leiden metrics and monthly diagnostics are recorded; no universal algorithm ranking is made.
