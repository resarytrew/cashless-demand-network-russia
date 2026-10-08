# Round24 — graph semantics, fixed before candidate results

This additive exploratory experiment preserves reference L1, union-k20, A–G,
Atlas, all historical artifacts and all scientific profile statuses. It selects
no winner. L1 means the repository demand-only lens, **not Manhattan distance**:
the reference uses Euclidean distance on scaled CLR plus robust-z log Total.
The executable specification is `configs/round24_graph_semantics.yaml`.

## Gate and scope

Reproduce the full baseline in a fresh process, requiring exact ARI=NMI=1 for
static December, temporal December and the full supra partition, and identical
saved graph fingerprints. Failure blocks both new graphs. Replay union-k20
unchanged and check its saved ICVI-v2 row. All candidate graphs have the same
1,904 municipalities. Only static partitions are newly estimated, using fixed
Louvain resolution .5, seed 0. No temporal candidate network or omega search is
part of this experiment.

## Global threshold

Compute all unordered December distances in the unchanged L1 representation.
Set epsilon to the 11,787th smallest distance **before evaluating candidate
partitions**. Include every pair with d <= epsilon, including boundary ties.
Report the actual edge count and any excess from ties; do not break ties to
improve ARI or ICVI. No isolate fallback: it would violate the threshold rule.
Use the same adaptive-RBF formula and the same kth-neighbor bandwidths as the
reference. Thus the indicator specifies adjacency support, with reference
weights on included edges. Disconnected components and isolates are outcomes,
not grounds for tuning. This controls edge count, not degree distribution,
connectedness or total edge weight. Reference fallback remains on as originally
specified; its contribution is reported explicitly.

## Co-dynamics

For each municipality, reconstruct the six unscaled CLR composition features
(five named categories plus residual Other) for Jan-2023 through Dec-2024.
Use 23 first differences, Pearson correlation over those aligned differences
for each component, and an equal mean over six components. Total is excluded:
this operationalization asks about co-movement of the spending composition,
not nominal spending growth. Differencing occurs **before monthly block
normalization**, avoiding changes in monthly scaling as artificial dynamics.

Fail if any component's centered difference norm is <= 1e-12; never silently
replace undefined correlations or use pair-specific denominators. Define
d_delta = sqrt(2(1-s_delta)). Select each node's 20 closest others, excluding
self explicitly and resolving ties by ascending frozen panel index. Keep only
mutual nominations, with no fallback. Weight using adaptive RBF of d_delta and
the corresponding 20th-neighbor bandwidths. Negative similarities remain
eligible by rank; their selected-edge frequency is reported. RBF weights are
nonnegative, so signed Louvain is not silently introduced.

The result is one full-period co-dynamics graph. Compare separately to static
December and temporal December reference labels; A–G refers only to the latter.
No duplicated temporal layers, rolling windows, seasonality removal or national
shock residualization. Common seasonality, CLR closure and only 23 differences
limit interpretation. Agreement is descriptive, not independent validation or
causal evidence, and disagreement does not by itself refute reference profiles.

## Artifacts and interpretation

Save exact epsilon calibration, raw sparse edges and weights, features/axes,
labels, graph fingerprints, connectedness/degree statistics, ARI/NMI, edge
overlap, ICVI-v2 diagnostics in a common December state space, per-profile
retention **and** precision/Jaccard, crosswalks and a new evidence matrix.
ICVI graph metrics across different graphs are not a winning-method ranking.
Checkpoint completed fixed-seed runs, verify their hashes on resume, and never
overwrite historical outputs. Record config/source/input hashes, runtime
versions, Git revision and seed. Run the full test suite and repository checks.
