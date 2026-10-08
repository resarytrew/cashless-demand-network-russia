# Evidence v2.11.0 — Round24 graph semantics

| variant | edges | components | isolates | K | ARI_static | NMI_static | ARI_temporal_december | reference_edge_jaccard |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| reference_mutual20 | 11787 | 1 | 0 | 9 | 1.000000 | 1.000000 | 0.339012 | 1.000000 |
| union20 | 26305 | 1 | 0 | 6 | 0.553326 | 0.677713 | 0.370312 | 0.448090 |
| epsilon_L1 | 11787 | 422 | 368 | 431 | 0.413953 | 0.561342 | 0.305127 | 0.379726 |
| dynamics_mutual20 | 2670 | 1089 | 974 | 1098 | 0.089146 | 0.429009 | 0.015667 | 0.048825 |

At equal edge count, epsilon has static ARI=0.413953, 368 isolates and 422 components. This documents dependence on local versus global neighborhood construction, including fragmentation: equal density does not imply equal degree distribution or coverage.

Co-dynamics has static ARI=0.089146 and temporal-December ARI=0.015667. Its full-period composition co-movement partition addresses a different relation from December state similarity. Neither comparison is independent validation or a reason to replace reference L1.

Strengthened: the qualification that exact boundaries depend on graph construction and on the meaning of similarity. Weakened: an unqualified claim of invariant partitions across these relations. Unchanged: the reference specification, union-k20, A–G definitions and scientific statuses, Atlas, and all earlier evidence. No winner is selected. Retention must be read with precision/Jaccard.
