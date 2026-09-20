# S_Dbw forensic audit — fixed partitions only

No clustering algorithm, new robustness run, parameter selection or scientific-status change was performed. The audit reconstructed features from the raw input and evaluated already saved partitions. Calls to Louvain/Leiden clustering were blocked in the audit entry points. All pre-existing outputs, configs, source and status documents are hash-protected and remain untouched.

## Findings

All 24 reconstructed baseline feature matrices equal the cached matrices bitwise. The current Round 14 S_Dbw implementation is independently reproduced for both static partitions and all 48 temporal algorithm-month rows: 50/50 checks pass. Every one of these 50 S_Dbw results is undefined under its declared strict rule. This is a mathematical zero-denominator condition, not a CSV-formatting failure or lost finite value.

| Static partition | K | radius | zero-density clusters | 0/0 pairs | positive/0 pairs |
|---|---:|---:|---:|---:|---:|
| Louvain alpha=.70 | 9 | 0.099523 | 6 | 12 | 3 |
| Leiden alpha=.70 | 8 | 0.104961 | 4 | 5 | 1 |

The radius is sqrt(sum of cluster variance-vector norms)/K; variance uses ddof=0. Center densities count points inside/on the radius within the corresponding cluster; midpoint densities count the union of the two clusters. The denominator is max(center density i, center density j). Every pair is audited, rather than stopping at the first undefined pair as the original metric implementation does. Exact cluster counts, distances, pair numerators/denominators and radii are saved in S_DBW_CLUSTER_DIAGNOSTICS.csv and S_DBW_PAIR_DIAGNOSTICS.csv.

Simply defining 0/0 as zero cannot fix the reference static result: positive/0 pairs remain. A denominator floor or a larger radius changes the metric definition. Such choices must not be introduced silently to obtain finite results.

## Source and formula ambiguity

The [Shalileh et al. article](https://link.springer.com/article/10.1134/S1064562425700589), equations 11–17, states the variance-based radius used by Round 14, but its displayed indicator counts points outside the radius. Round 14 explicitly used inside-radius counts. The distinction is material and documented; this audit does not claim that the printed equation is the historical project implementation. The authors' earlier [Halkidi et al. review](https://explorer.cs.umn.edu/fuzzy%20clustering/p19-halkidi.pdf) was located as additional background, but no source was recovered that establishes the code behind the project's old finite CSV values.

The historical alpha audit gives S_Dbw=.5489124793760968, .6315311638606655 and .46815959798879053 for alpha .50/.70/.90. Its generating metric implementation is absent from the supplied repository. Matching labels, SW or CH/N does not establish S_Dbw provenance.

Six diagnostic variants were declared in configs/evidence_freeze_v2_2_0.yaml before execution: strict Round 14; only 0/0 mapped to zero; denominator floor one; sqrt(mean variance norms) radius with strict/floor-one denominators; and the printed outside-radius indicator. These were evaluated on the same saved partitions, not chosen as replacement evidence. None reproduces the historical static S_Dbw values within atol=1e-12. The smallest absolute discrepancies among these diagnostics are .157100 (alpha .50), .221513 (.70) and .129864 (.90). This finite list cannot identify or rule out every possible historical implementation.

For alpha .70 Louvain, illustrative diagnostic scores are .351218 with denominator floor one, .410018 with the larger RMS radius, and 1.691687 with the printed outside indicator. They are non-comparable variants, not corrections to the historical .631531. No variant is promoted to canonical evidence or used to rank algorithms.

## Disposition

- Round 14 undefined results are reproducible as metric diagnostics. They convey no S_Dbw ordering between algorithms.
- Historical finite S_Dbw values have unresolved implementation provenance and are excluded from the canonical quantitative evidence matrix.
- Alternative diagnostic variants remain audit-only, explicitly non-admissible as historical reproduction.
- No scientific profile or hypothesis status changes. No baseline, label, prior report or historical file is overwritten.

Raw outputs: S_DBW_VARIANT_DIAGNOSTICS.csv, S_DBW_CLUSTER_DIAGNOSTICS.csv, S_DBW_PAIR_DIAGNOSTICS.csv, HISTORICAL_S_DBW_COMPARISON.csv, ROUND14_S_DBW_REPLAY_CHECK.csv and FEATURE_REPRODUCTION_CHECK.csv. The audit concerns metric reproducibility; it does not establish a unique universally applicable S_Dbw convention.
