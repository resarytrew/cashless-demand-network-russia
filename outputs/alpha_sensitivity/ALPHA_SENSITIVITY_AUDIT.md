# Alpha sensitivity audit

## Frozen elements

Only alpha changes. Fixed: panel=1904, 24 months, six-part composition with technical Other residual, CLR, monthly robust-z log total, block scaling by monthly median pairwise distance, k=20 mutual-kNN, adaptive RBF, static isolate fallback only, omega=2 x global median intralayer weight, Louvain resolution=0.5, seed=0.

## Reproducibility check

The rerun of alpha=0.70 reproduces `/mnt/data/supra_labels_omega_2.0.csv` exactly: full-supra ARI=1.0, NMI=1.0 and December ARI=1.0.

The static ICVI values in this alpha audit are freshly recomputed under one unified implementation for all three alphas. They are therefore intended for **within-alpha sensitivity comparison** and do not replace older frozen static benchmark tables produced by an earlier metric script (for example the older SW=0.176481 vs current unified sensitivity SW=0.169645 at alpha=0.70). The partition-reproducibility check is exact; raw ICVI implementations/audit vintages should not be silently mixed.

## Metrics

Feature space: Silhouette Width (higher), CH/N (higher), S_Dbw (lower). Network space: AVI (higher), AVU (lower), ANUI (higher) and weighted Newman-Girvan modularity MQ (higher). AVI/AVU use the unweighted adjacency definitions for isolability/unifiability; MQ uses graph weights.

## Interpretation guardrails

1. Alpha is a modeling sensitivity axis, not a hyperparameter optimized against mobility or any external target.
2. No single ICVI is used to select alpha; the indices disagree by construction/domain.
3. Retention is not identity. High retention with low precision indicates a retained core inside a merged alternative community.
4. Alpha=0.70 remains a reference specification because it is intermediate and temporally persistent, not because a formal optimum was established.
5. Endpoint failures of fine boundaries must be propagated to substantive claims, especially D/F and F/G.
