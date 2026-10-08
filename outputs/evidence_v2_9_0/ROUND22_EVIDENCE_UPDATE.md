# Evidence v2.9.0 — Round22 attributed-network method benchmark

Round22 is additive. A clean-room KEFRiNc implementation was fixed from the
published equations before fitting. The author repository commit is recorded, but
its license is not verifiable from a license file, so no upstream source was used.

Against static December Louvain at fixed K=9, seed-0 KEFRiN has ARI=.3080,
NMI=.4797, VI=3.1374 bits, Hungarian accuracy=.4842, reference-pair retention=.3688
and candidate-pair precision=.4312. Pairwise seed ARI across seeds 0–9 averages
.5213 (range .3996–.7143), showing material optimization dependence.

Atlas uncertainty generalizes only partially. After one global temporal-December
alignment, disagreement is 492/824 (59.7%) in stable cores and 263/388 (67.8%) in
transitions, an 8.1-point difference; unresolved cases disagree 268/318 (84.3%).
Because stable-core disagreement itself is high, Round22 does not support a strong
algorithm-class validation of robust cores. B and D have high dominant-cluster
retention, while F and G have low retention; no legacy profile status changes.

The fixed KEFRiN groups retain observational external structure: adjusted partial
R² is .1360 for wage, .0747 for employment total and .0371 for sector CLR, with
constrained permutation p=.0005. These statistics were computed after labels were
frozen and are not a model-selection comparison with L1.

All frozen L1, A–G, Atlas, ICVI, original L2 and Round21 hashes match. Reference
parameters and scientific A–G statuses remain unchanged.

