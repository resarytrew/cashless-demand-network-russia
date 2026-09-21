# Temporal model specification

The approach is a **weighted supra-graph with intralayer similarity edges and interlayer
identity edges, followed by ordinary modularity community detection on the expanded graph**.
**This is not identical to classical multislice modularity with an independent null model per layer.**

Each node is a municipality–month copy, indexed `t*1904+i`: 45,696 nodes in total.
Each of 24 monthly layers uses the reference seven-dimensional CLR+level geometry,
mutual-kNN20 and `exp(-d²/(sigma_i*sigma_j+1e-12))` weights. sigma is kth-neighbor distance.
Temporal monthly layers have no isolate fallback. The standalone static December graph does.

Identity edges join the same municipality in adjacent months. Every such edge has weight
`omega * median(all intralayer weights across all months)`, omega=2. These links are symmetric;
no temporal direction or causal propagation is encoded. No dense supra distance matrix is used.

For supra weighted adjacency W, global node strength s and total undirected weight m,
NetworkX Louvain optimizes

`Q_gamma = (1/(2m)) * sum_uv [W_uv - gamma*s_u*s_v/(2m)] * 1(c_u=c_v)`.

Resolution gamma=.5 and seed=0 are reference settings. Strength includes identity edges,
and the null expectation uses the entire expanded graph, including pairs in different layers.
There are no independent layer-specific null models. Conventional reported MQ uses gamma=1;
the optimized objective at the run's gamma must be labelled separately.

The construction encourages persistence and represents cross-time similarity in one graph.
Its global normalization, temporal coupling and resolution affect granularity and community
boundaries. A layer's labels can depend on future months. IDs are arbitrary; switching counts
refer to one joint supra partition, not independently numbered monthly clusterings.

Correct wording: **under the reference temporal regularization omega=2 and resolution=.5,
85.3% have <=2 label switches** (1624/1904). This is conditional model persistence;
it is not a claim that these municipalities are intrinsically stable. Low switching is not
independent evidence of feature separation.

Round16 changes only gamma in [.25, .50, .75, 1.00], keeping the graph, weights, seed,
alpha, k and omega fixed. This measures scale/granularity sensitivity, without choosing best gamma.
Expanding-window monitoring and historical-label revision after new observations are future work;
the existing retrospective fit is not a validated real-time monitoring or prediction experiment.
