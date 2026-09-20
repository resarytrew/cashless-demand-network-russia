# Canonical perturbation robustness v2, n=50 — findings

All 50 seeds completed under the new canonical protocol after its reproducibility gate passed. The non-reproducible historical pilot contributes no quantitative evidence. These distributions characterize the fixed protocol, jointly varying intralayer perturbations and Louvain initialization.

Run-level distributions:

| metric | mean | median | SD | min | q10 | q90 | max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ARI_all_supra | 0.498355 | 0.504580 | 0.071131 | 0.276206 | 0.419254 | 0.579240 | 0.651645 |
| NMI_all_supra | 0.619077 | 0.627284 | 0.047877 | 0.491433 | 0.563425 | 0.666479 | 0.690654 |
| ARI_Dec2024 | 0.675736 | 0.728285 | 0.178480 | 0.016244 | 0.462817 | 0.835893 | 0.890180 |
| NMI_Dec2024 | 0.702292 | 0.730790 | 0.146315 | 0.049215 | 0.639585 | 0.792992 | 0.848447 |
| K_supra | 12.540000 | 12.500000 | 1.541401 | 9.000000 | 10.000000 | 15.000000 | 15.000000 |
| K_Dec2024 | 9.300000 | 9.000000 | 1.054630 | 7.000000 | 8.000000 | 11.000000 | 12.000000 |
| mean_switches | 1.912300 | 1.720588 | 0.592507 | 1.234769 | 1.363866 | 2.572794 | 3.730042 |
| share_le2_switches | 0.746397 | 0.815651 | 0.214982 | 0.011029 | 0.532721 | 0.881513 | 0.918067 |

A-G distributions:

| archetype | mean_retention | q10_retention | min_retention | mean_precision | mean_Jaccard | mean_within_pair |
| --- | --- | --- | --- | --- | --- | --- |
| A | 0.941277 | 0.879433 | 0.652482 | 0.726814 | 0.688205 | 0.892685 |
| B | 0.972041 | 0.988776 | 0.551020 | 0.614578 | 0.601487 | 0.963758 |
| C | 0.718621 | 0.586207 | 0.586207 | 0.839313 | 0.589929 | 0.582167 |
| D | 0.975817 | 0.921569 | 0.823529 | 0.511661 | 0.499305 | 0.954481 |
| E | 0.872688 | 0.623656 | 0.564516 | 0.762888 | 0.683420 | 0.815351 |
| F | 0.702813 | 0.492355 | 0.354740 | 0.476762 | 0.400917 | 0.627286 |
| G | 0.906342 | 0.622902 | 0.509845 | 0.893040 | 0.812764 | 0.868497 |

The distinction between retention and precision/Jaccard is essential: a preserved core can be absorbed into a larger destination. Existing substantive labels remain qualified; no profile is promoted to a universal archetype. C's rejection beyond context is unchanged even if it sometimes persists under this perturbation model.

Priority pair cross-coassignment distributions:

| pair | mean | median | SD | min | q10 | q90 | max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B/E | 0.465586 | 0.395326 | 0.393857 | 0.000000 | 0.009623 | 0.994624 | 1.000000 |
| D/F | 0.434798 | 0.458746 | 0.309889 | 0.011793 | 0.021235 | 0.925070 | 0.981312 |
| F/G | 0.317798 | 0.289431 | 0.235015 | 0.034099 | 0.053117 | 0.587407 | 0.984697 |
| A/D | 0.230527 | 0.018704 | 0.389637 | 0.000278 | 0.006508 | 0.960993 | 0.992908 |

Tail proportions and leave-one-seed-out mean ranges:

| pair | full_mean | leave_one_out_mean_min | leave_one_out_mean_max | share_lt_0_1 | share_gt_0_5 | share_gt_0_9 |
| --- | --- | --- | --- | --- | --- | --- |
| B/E | 0.465586 | 0.454680 | 0.475088 | 0.400000 | 0.480000 | 0.280000 |
| D/F | 0.434798 | 0.423645 | 0.443431 | 0.220000 | 0.360000 | 0.120000 |
| F/G | 0.317798 | 0.304188 | 0.323588 | 0.220000 | 0.180000 | 0.040000 |
| A/D | 0.230527 | 0.214968 | 0.235226 | 0.760000 | 0.220000 | 0.200000 |

The full summaries also include q05/q25/q75/q95 and all retention-threshold fractions. Leave-one-out results describe sensitivity to individual runs; no observations are removed. The new distributions replace the former absence of reproducible perturbation evidence, rather than confirming or refuting the old n=5 numerical claims. Profile-specific interpretations and all contextual caveats are carried in Round 15 and master matrix v2.2.0.

Interpretation of the new evidence:

- D's core persistence is strengthened under this protocol (mean retention 0.975817; q10 0.921569), while its exact-boundary claim remains weak (mean precision 0.511661). F's boundary/refinement interpretation is strengthened: retention q10 0.492355 and mean Jaccard 0.400917.
- B/E has both near-separated and nearly merged realizations: 40% of runs have cross-coassignment below 0.1, 28% above 0.9. Its mean remains between 0.454680 and 0.475088 after leaving out any one seed, so the mixed distribution is not explained by one extreme run.
- A/D usually stays distinct (median cross-coassignment 0.018704), but 20% of runs exceed 0.9. The upper tail must accompany the median; it is not a uniformly stable boundary.
- G remains a broad macroprofile, but uniform membership robustness is weakened by retention q10 0.622902 and minimum 0.509845. A retains a substantial core on average but has meaningful destination contamination. E remains context-sensitive. C's prior rejection beyond context is unchanged.
- Seeds 24 and 39 have very low December ARI (0.021394 and 0.016244); they are retained in every primary summary. Seed 24 places 1864 of 1904 municipalities in one December destination, illustrating that high profile retention can coexist with near-collapse of profile separation.

All 50 checkpoint/raw-label checks passed. A resumed invocation skipped all 50 seeds with unchanged raw-file hashes and modification times. Full test suite: 21 passed. No reference or historical-pack file changed.
