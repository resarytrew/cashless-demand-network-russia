# Round 16 final pre-submission audit

Status: **COMPUTATIONAL WORK COMPLETED; FULL ACCEPTANCE BLOCKED BY MISSING CONTEXTUAL INPUTS**.
Round16 is not declared fully complete: the third contextual case lacks individual controls and verified region/covariates.
Historical trajectory methods are explicitly unavailable under the permitted benchmark exception.

## 1. What changed
The supplied DOCX and reviewer text are archived in reference/round16 with extracted tables.
Baseline was freshly reconstructed: six ARI/NMI=1; 1904 municipalities, exact24-month calendar;
24 feature matrices bitwise identical; static/supra graph hashes identical. Before any research changes,
the original freeze verified all390 files. New artifacts occupy separate Round16 directories.
Five static algorithms,20 optimizer-only runs,20 graph-only runs,two collapse seed0 reruns,
four resolutions and five figure-ready PNG/SVG sets were produced. Combined n=50 was replayed, not reclustered.

## 2. Benchmark reconciliation
The only allowed source for method comparison numbers is
`outputs/round16_benchmark/canonical_method_benchmark.csv`.
Reference Louvain: SW=.169645, CH/N=.459672, AVI=.907450, AVU=.506291, MQ=.767448.
DOCX rounded values were .176/.468/.909/.469/.765. AVU changes materially.
All five algorithms now share feature/metric provenance; explicit Round16 settings do not establish
the identity of undocumented old settings. Historical cosine/correlation/lagged-correlation/DTW
are UNREPRODUCIBLE_HISTORICAL_BENCHMARK_COMPONENT, with blank canonical numbers.
The diff CSV covers every metric in both historical comparison tables. No old finite S_Dbw is reused.
The historical cause of mismatch remains unestablished; matching old scores was not a tuning target.

## 3. Perturbation decomposition
| mode | n | mean | median | SD | min | max | q10 | q90 |
|---|---|---|---|---|---|---|---|---|
| combined | 50 | 0.675736 | 0.728285 | 0.178480 | 0.016244 | 0.890180 | 0.462817 | 0.835893 |
| graph_only | 20 | 0.733165 | 0.724098 | 0.093360 | 0.504745 | 0.888572 | 0.658377 | 0.843100 |
| optimizer_only | 20 | 0.756267 | 0.747786 | 0.131112 | 0.434924 | 1.000000 | 0.666247 | 0.878193 |

Combined sensitivity has lower mean December agreement than either separate20-run regime.
Optimizer-only and graph-only both materially alter boundaries; this design cannot allocate causal
variance or identify a universally dominant source. Unequal run counts and graph insertion-order
semantics are explicit. All tails, including collapse, remain in evidence.

## 4. Collapse runs
Combined seed24/39 has largest December groups1864/1877; on identical perturbed graphs with
optimizer seed0 these become1868/1874. Collapse persists without the original optimizer seeds.
High retention during near-global merging is insufficient: precision, Jaccard and largest-group share
are required. Graph connectivity is unchanged; per-edge weights/degrees/component diagnostics and
full/December modularity are saved. No causal decomposition is claimed.

## 5. Resolution sensitivity
| gamma | static_K | static_SW | static_CHn | static_AVI | static_AVU | static_MQ | K_supra | K_Dec2024 | mean_switches | share_le2_switches | ARI_all_supra | ARI_Dec2024 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.250000 | 7 | 0.211617 | 0.500461 | 0.922969 | 0.450625 | 0.715842 | 7 | 6 | 0.879202 | 0.949055 | 0.508157 | 0.733900 |
| 0.500000 | 9 | 0.169645 | 0.459672 | 0.907450 | 0.506291 | 0.767448 | 12 | 10 | 1.338761 | 0.852941 | 1.000000 | 1.000000 |
| 0.750000 | 14 | 0.132894 | 0.366195 | 0.871023 | 0.498509 | 0.790501 | 16 | 11 | 1.935399 | 0.747374 | 0.535307 | 0.631656 |
| 1.000000 | 14 | 0.131953 | 0.366206 | 0.869509 | 0.498367 | 0.789246 | 22 | 15 | 2.238445 | 0.615021 | 0.518615 | 0.857288 |

The fixed grid changes granularity and switching substantially. Gamma=.5 remains the reference.
No ICVI-based selection or status promotion is performed. Profile-specific retention, precision,
Jaccard and pair distributions accompany the audit.

## 6. Data passport
The CSV establishes rubles and monthly frequency. The official dataset page could not be retrieved
(502 and timeout). DENOMINATOR_NOT_ESTABLISHED_FROM_AVAILABLE_OFFICIAL_METADATA.
Total/category common normalization and mutual additivity remain unconfirmed. Other is a technical
model residual, not an established economic sector. Turnover/per-capita/income/wealth/purchasing-power
interpretations are unsupported. The source and transformations are in docs/DATA_PASSPORT.md.

## 7. Reproducibility scope
Baseline, new sensitivity experiments and descriptive B comparison are reproducible from supplied
artifacts under the recorded environment. Crosswalk, geometry join, residual labels, population/density
covariates and historical control generators/results remain absent. The supplied DOCX adds historical
claims, not executable contextual evidence. Nearby project ZIP inventories were checked and did not
contain those inputs. Contextual matrix and recovery instructions document exact limits.
Within-stratum B comparison covers98 versus142: Transport Cliff delta=-.070997; historical p-values
and multiplicity corrections are unavailable. No new significance test was substituted.

## 8. Scientific statuses
All A–G statuses copy Round15 verbatim; changed=false for all7. Matrix v2.3.0 is a new file with
separate optimizer/graph/combined fields and limitations. The earlier v2.2.0 freeze remains intact.
Historical pilot n=5 remains SUPERSEDED_NON_REPRODUCIBLE and contributes no quantitative evidence.

## 9. Competition implications
### What was found
- Reference demand profiles differ in level and six calculated category shares; Health is restored to the profile matrix.
- Within federal-intracity territories, B differs descriptively in several features; Transport has little separation.
- Cores and exact boundaries differ: high retention can coexist with weak precision, particularly under merging.
- Both gamma and optimizer/graph changes affect the observed partition; no seven-equally-robust-type claim is supported.

### Why we can trust it
- Fresh baseline reproduces six partition metrics exactly, with bitwise feature and graph checks.
- All50 existing combined partitions and all new raw labels remain available with checkpoints.
- Separate sensitivity axes, collapse cases and full distributions replace reliance on means alone.
- Old mismatching benchmark numbers and finite historical S_Dbw are excluded from canonical comparison.

### How to use it
- Build descriptive peer comparisons with both feature distance and pair coassignment, checking community size.
- Prioritize municipal cases for manual review using boundary uncertainty, without automatic investment decisions.
- Compare observed category profiles and retrospective trajectories; separate indicator changes from label changes.
- Use sensitivity outputs to communicate uncertainty of segmentation. Live monitoring remains future work.

## 10. Remaining limitations
- Verified contextual inputs and individual attenuation are absent. Two case studies are fully descriptive;
  the third is a transparent provisional E candidate, not a demonstrated context-sensitive territory.
- All three cases lack verified regional/covariate joins. These were not inferred from names.
- Four historical distance families have unrecoverable definitions in the supplied state.
- Denominator, additivity and publication/suppression rules require official clarification.
- Historical B significance/correction output is missing; only descriptive effects are recovered.
- The original DOCX is preserved unchanged. Canonical replacement tables, figures and a correction map are provided;
  an edited, layout-verified submission DOCX is not claimed as an output of this round.
- Expanding-window monitoring and predictive utility remain future work, as required by the task.

Engineering: baseline outputs now reject silent overwrite; --force archives non-frozen outputs and cannot
overwrite frozen evidence. Strict panel checks exact calendar dates. Changed source files have byte-identical
pre-hardening snapshots so the old390-file freeze can be verified against its original dependencies.
See ROUND16_VERIFICATION.json for the final test and integrity results.
