# Perturbation sensitivity decomposition

Optimizer-only: seeds0..19 on the unmodified reference supra graph. Graph-only: v2 graph seeds0..19 with Louvain seed=0. Combined: all existing v2 seeds0..49 replayed from raw labels; no reclustering. Collapse-specific graph seeds24/39 are separate diagnostics and are not added to the 20-run graph-only distribution.

Fresh baseline passed all six ARI/NMI checks exactly. Features reproduced bitwise; graph hashes are identical. A fresh v2 gate passed same-process, fresh-process and reversed insertion tests. Each graph-only graph hash matches the corresponding Round15 graph. Raw labels precede metrics and checksummed completion markers. Resume verified 42 checkpoints and rewrote no results.

| mode | n | mean | median | SD | min | max | q10 | q90 |
|---|---|---|---|---|---|---|---|---|
| combined | 50 | 0.675736 | 0.728285 | 0.178480 | 0.016244 | 0.890180 | 0.462817 | 0.835893 |
| graph_only | 20 | 0.733165 | 0.724098 | 0.093360 | 0.504745 | 0.888572 | 0.658377 | 0.843100 |
| optimizer_only | 20 | 0.756267 | 0.747786 | 0.131112 | 0.434924 | 1.000000 | 0.666247 | 0.878193 |

Sample SD uses ddof=1; quantiles use NumPy linear interpolation. All run metrics, A–G retention/precision/Jaccard/within-pair and 21 cross-pairs have mean/median/SD/min/max/q05/q10/q25/q75/q90/q95. No seed is discarded.

These are optimizer-only sensitivity, graph-perturbation sensitivity and combined sensitivity. The 20/20/50 design is not a factorial causal variance decomposition. Graph-only includes the canonical v2 graph insertion order, whereas optimizer-only retains the exact baseline object order. This operational distinction is documented, not silently attributed to edge noise alone. Comparisons describe this algorithm/protocol, not population sampling uncertainty.
