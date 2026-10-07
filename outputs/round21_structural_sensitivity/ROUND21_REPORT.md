# Round 21 — Structural sensitivity and adjusted validation

## 1. What was tested

Structural omega sensitivity, Atlas independence, size/region-adjusted scalar and sector associations, post-hoc merge interpretation, L1/L2 crosswalk and two predeclared block-balanced L2 sensitivities.

## 2. What did not change

L1 data/representation, k=20, resolution=.5, reference omega=2, A–G IDs/statuses, Atlas assignments and original Round19 L2 are unchanged.

## 3. Baseline integrity

Freeze and Round20 reproduction: PASS. The final hash gate is recorded in the manifest.

## 4. omega=2 vs omega=1: shuffle or coarsening?

December ARI=0.4070, NMI=0.5547, K=10→7. Fine-to-coarse micro purity=0.9785, macro purity=0.8783, minimum retention=0.5000. Fine-pair retention=0.9827; coarse-pair precision=0.4888. H(omega1|omega2)=0.1303 bits, H(omega2|omega1)=1.2874 bits, VI=1.4176 bits. Classification: predominantly coarsening, with residual boundary changes.

## 5. Real omega grid

| omega | December K | ARI | NMI | micro purity | pair retention | pair precision |
|---:|---:|---:|---:|---:|---:|---:|
| 0.5 | 5 | 0.2561 | 0.4102 | 0.9926 | 0.9946 | 0.4120 |
| 1.0 | 7 | 0.4070 | 0.5547 | 0.9785 | 0.9827 | 0.4888 |
| 2.0 | 10 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| 4.0 | 13 | 0.6959 | 0.7103 | 0.8346 | 0.7337 | 0.8413 |

Monthly ARI/NMI and transition counts are in `omega_grid.csv` and
`omega_monthly_similarity.csv`. ICVI is diagnostic and does not select omega.

## 6. Matched-K control

Predeclared selected row: resolution=0.80, December K=10, ARI=0.6471, NMI=0.6469. B/E merge preserved=True; C/D/F/G merge preserved=False. Selection used K distance only, never ARI.

## 7. Atlas sensitivity audit

Omega did not enter Atlas construction. This is a held-out sensitivity axis, not statistical out-of-sample validation. Counts and Wilson intervals are in `atlas_omega_sensitivity.csv`.

Stable core changes 1/824 (0.12%; Wilson 95% CI 0.02–0.68%), expansive core
247/374 (66.0%), transition 348/388 (89.7%) and unresolved 35/318 (11.0%).
Transition/stable change risk ratio is 739, with a very wide 95% CI 104–5,242;
the counts, rather than this unstable ratio, are the headline.

## 8. External interpretation of merges

All contrasts are post-hoc. B versus E differs most strongly in wage
(Cliff's delta 0.694) and employment total (0.446); sector composition R2 is
0.0589. The D/F/G omnibus tests are material for population, wage and employment
(Kruskal epsilon-squared 0.398, 0.334 and 0.438) and for sector composition
(R2=0.0666, permutation p=0.0005); pairwise sector R2 ranges 0.0308–0.0702.
All reported scalar and sector contrasts remain after within-family BH correction. Thus omega=1 merges profiles that remain
externally distinguishable, without proving omega=2 true. C receives no promoted
interpretation.

## 9. Size- and region-adjusted external validation

Wage partial R2=0.1758; employment partial R2=0.2144. Sector CLR partial R2=0.0361, pseudo-F=11.2386, permutation p=0.0005. Associations are observational.

## 10. L2 block geometry

Original Round20 contributions reproduce exactly. Demand and employment are comparable globally; employment is largest on local graph edges. Dimensionality is documented but is not claimed as the sole cause.

## 11. L1/L2 crosswalk

The five major original L2 groups combine L1 as follows: L2-1 is 91.2% G;
L2-2 combines G (47.4%), F (35.7%) and D (14.8%); L2-3 combines E (58.7%) and
B (29.0%); L2-4 combines A (55.4%) and F (33.7%); L2-5 is 88.5% D. The table
also has an explicit 88-unit `OTHER_MICRO` row, so it sums to the exact common
N=1,876. Full counts, micro and entropy columns are in `l2_crosswalk_l1.csv`.

## 12. L2 balanced sensitivity

Balanced-A (20% per semantic block) gives December K=27, one major community
covering 96.7%, ARI=0.0345 to original L2 and edge Jaccard=0.4283. Balanced-B
(50% Demand / 50% context) gives K=20, two major communities covering 98.2%,
ARI=0.1772 and edge Jaccard=0.4327. Both are adverse sensitivity results and
show material block-geometry dependence. Neither is selected; original L2 remains
unchanged. The original major-five-only conditional diagnostic has SW=0.1620 on
N=1,788; it is not a replacement K=5 model.

## 13. Scientific change

New evidence distinguishes coarsening from reshuffling, tests an Atlas-held-out sensitivity axis, adds adjusted multivariate sector evidence and quantifies block-weight dependence. No legacy A–G status changes.

## 14. Limitations

Fixed omega, omega×resolution interaction, exact-boundary sensitivity, observational external associations, selective mobility coverage and L2 weighting sensitivity remain explicit.
