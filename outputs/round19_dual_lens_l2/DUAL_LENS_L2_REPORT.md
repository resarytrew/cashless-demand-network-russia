# Round19 dual-lens L2 report

L1 remains the unchanged reference discovery result: demand-only features, mutual-kNN20, temporal omega=2, Louvain resolution=.5/seed=0, A–G, followed by independent external interpretation. P0 gates passed before L2 and are saved in `P0_RELEASE_GATE.json`.

L2 is a separate attributed-network experiment on 1876 complete-case municipalities. It combines three predeclared, equally weighted and separately distance-normalised blocks: L1 features; log population/log wage/log market access; and CLR employment structure. Urban share was unavailable nationally and was neither imputed nor proxied. The complete-case rule excluded 28 municipalities.

No K or macrotype names were fixed in advance. Louvain produced 41 December communities in the temporal solution, of which 5 have at least 2% of the L2 sample. L1/L2 agreement on the common universe is ARI=0.431917, NMI=0.471727. Municipality-level cross-lens reassignment is a contingency diagnostic, not a temporal move.

The temporal December partition contains many micro-communities; the five major communities cover 95.3% of the sample, while the separately evaluated static December graph has 10 communities. This gap and the negative temporal-December silhouette prevent reading every temporal community as an economic type.

Population, wage, employment structure and market access cease to be independent evidence for L2 because they enter its features. Mobility was excluded from every feature, graph, clustering and naming step. Exact-name holdout coverage is 268/1876 (14.3%); the selected-coverage limitation remains material. L2 holdout Kruskal epsilon-squared is 0.6300 with exploratory p=1.295e-33. This is auxiliary validation, not causal evidence.

The shallow rule tree over contextual inputs has cross-validated accuracy=0.856, balanced accuracy=0.845. Economic names are emitted only for major communities whose CV recall passes the fixed gate; otherwise names are withheld. These names describe included attributes and are not independent validation.
