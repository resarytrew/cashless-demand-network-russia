# Round24 — global distance threshold and co-dynamics

Additive exploratory comparisons on 1,904 municipalities. L1 denotes the unchanged CLR+level demand lens with Euclidean distance, not Manhattan distance.

Epsilon=0.20487134020155773, selected as the 11,787th unordered December distance before candidate evaluation; actual edges=11787, boundary ties=1. Adaptive-RBF weights use the same reference kth-neighbor bandwidths. No epsilon fallback edges are added.

| variant | edges | components | isolates | K | ARI_static | NMI_static | ARI_temporal_december | reference_edge_jaccard |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| reference_mutual20 | 11787 | 1 | 0 | 9 | 1.000000 | 1.000000 | 0.339012 | 1.000000 |
| union20 | 26305 | 1 | 0 | 6 | 0.553326 | 0.677713 | 0.370312 | 0.448090 |
| epsilon_L1 | 11787 | 422 | 368 | 431 | 0.413953 | 0.561342 | 0.305127 | 0.379726 |
| dynamics_mutual20 | 2670 | 1089 | 974 | 1098 | 0.089146 | 0.429009 | 0.015667 | 0.048825 |

At equal edge count, epsilon has static ARI=0.413953, 368 isolates and 422 components. This documents dependence on local versus global neighborhood construction, including fragmentation: equal density does not imply equal degree distribution or coverage.

Co-dynamics has static ARI=0.089146 and temporal-December ARI=0.015667. Its full-period composition co-movement partition addresses a different relation from December state similarity. Neither comparison is independent validation or a reason to replace reference L1.

Strengthened: the qualification that exact boundaries depend on graph construction and on the meaning of similarity. Weakened: an unqualified claim of invariant partitions across these relations. Unchanged: the reference specification, union-k20, A–G definitions and scientific statuses, Atlas, and all earlier evidence. No winner is selected. Retention must be read with precision/Jaccard.

Co-dynamics uses the equal mean of six component Pearson correlations across 23 first differences of unscaled CLR features. It excludes Total and does not remove national seasonality/common shocks. Mutual-k20 uses sqrt(2(1-s)) and adaptive RBF. It is one full-period graph, not a monthly supra network. Negative similarities are eligible by rank; selected-edge counts are in comparison.csv.

All ICVI feature metrics use the same December L1 matrix, including for dynamics. Thus they describe state separation of dynamic groups, not native dynamic separation. Graph ICVI uses each candidate graph and is not comparable as a method ranking. K includes singleton isolates. A–G overlap compares to temporal December; ARI_static compares to the separate static partition.

See profile_overlap.csv for dominant-destination retention, precision, Jaccard and within-pair coassignment; runs/* for raw labels, weighted sparse edges, node degrees/components, crosswalks and exact graph fingerprints. Single fixed-seed results are descriptive, with no p-values or causal interpretation.
