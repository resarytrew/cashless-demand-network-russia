# Aborted benchmark attempt — not evidence

The first run stopped at SpectralClustering because its ARPACK path rejects CSR int64 indices.
The canonical implementation now explicitly casts sparse index/indptr arrays to int32 without
changing edge weights or graph topology. The incomplete directory was archived with explicit
`--force`; no old research output was replaced. Only `outputs/round16_benchmark` is canonical.
