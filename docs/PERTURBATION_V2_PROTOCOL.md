# Canonical perturbation robustness v2, n=50

Protocol version 2; configuration: configs/perturbation_v2.yaml. This new experiment supersedes the historical n=5 as perturbation evidence; it does not reproduce or expand it.

Reference remains alpha=0.70/0.30, k=20, omega=2, Louvain resolution=0.5, 1904 municipalities and 24 months. Use the baseline graph from the passed reproduction gate, verified by its node and edge-weight hashes before use. No features, graph weights, temporal coupling or resolution are retuned.

Canonicalization happens before randomness: orient every intralayer edge u<v, sort lexicographically by (u,v), and store (u,v,weight). Serialization is consecutive 24-byte records: signed int64 little-endian u, signed int64 little-endian v, IEEE754 float64 little-endian weight; no padding or header. SHA256 covers precisely those bytes.

For run s, use np.random.default_rng(20260918+s), draw keep=rng.random(n_edges)>=0.05, then jitter=exp(rng.normal(0,0.02,keep.sum())). Multiply retained weights in canonical order by jitter in its generated order. Never reorder jitter. Keep-mask serialization is one uint8 (0/1) per base edge; jitter serialization is float64 little-endian in generated order.

Temporal edges retain exact endpoints and weights. For deterministic graph insertion, insert sorted nodes, then retained canonical intralayer edges, then temporal edges ordered by (u,v). Ordering temporal edge records does not change any edge or weight. Both the canonical temporal-array hash and full graph hashes are verified.

Per run save seed, base-edge SHA256, keep-mask SHA256, jitter-array SHA256, perturbed intralayer SHA256, temporal-edge SHA256, final supra edge-weight SHA256, and final supra graph SHA256 (sorted int64 node bytes followed by sorted edge record bytes). Node count is also recorded, including isolates. Louvain uses seed=s and resolution=0.5. No rescaling after perturbation.

Gate: seed 0 twice in one process, once in a fresh process, plus a reversed-insertion source graph test. All six requested hashes must agree exactly. A failure blocks n=50. Baseline and Leiden completion are also checked. Historical CSV values are never compared as a reproduction gate.

Seeds 0..49 use two independent worker processes. Each seed writes raw labels, graph hashes, metrics, A-G retention/precision/Jaccard/within-pair coassignment and all 21 pair cross-coassignments before its atomic completion checkpoint. Existing completed seeds are verified and skipped unless --force is explicit. No summaries until all 50 checkpoints are complete. Incomplete files are not accepted as completed evidence.

Profiles are the reference temporal December A-G mapping. Best match maximizes reference intersection (ties choose smallest destination ID); retention=intersection/reference size, precision=intersection/destination size, Jaccard=intersection/union. Within-pair coassignment uses unordered distinct pairs; cross-coassignment uses every cross-profile pair. These do not require alignment of arbitrary cluster IDs.

Report mean, median, sample SD (ddof=1), min/max, q05/q10/q25/q75/q90/q95 (NumPy linear interpolation). Retention also reports fractions >=0.90/0.80/0.70/0.50. Seeds combine edge perturbation and algorithm initialization variability; they do not isolate those two sources. Empirical quantiles describe this fixed protocol, not confidence bounds or confirmatory inference. High retention alone is not stable exact boundaries.
