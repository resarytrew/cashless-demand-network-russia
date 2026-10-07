# ICVI v2 report

This is a diagnostic reevaluation of fixed partitions. It does not select a method, change a graph, or tune any parameter.

## Canonical fixed partitions

| method | K | SW | CH | S_Dbw | AVI | AVU | ANUI | MQ | Q |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Louvain | 9 | 0.169645 | 875.215310 | 0.829453 | 0.916111 | 0.505117 | 0.626297 | 8.244997 | 0.767448 |
| Greedy | 6 | 0.187672 | 507.850331 | 1.197384 | 0.858058 | 0.346550 | 0.661387 | 5.148345 | 0.526520 |
| Spectral | 9 | 0.187111 | 835.435220 | 0.773622 | 0.916688 | 0.468518 | 0.641272 | 8.250195 | 0.722377 |
| KMeans | 9 | 0.204507 | 1124.442279 | 0.807575 | 0.854039 | 0.535999 | 0.585855 | 7.686351 | 0.729446 |
| Ward | 9 | 0.172481 | 958.997385 | 0.918942 | 0.853730 | 0.492979 | 0.600850 | 7.683566 | 0.725785 |

MQ is TurboMQ; Q is weighted Newman–Girvan modularity. Their scales are not comparable.

## Edge grid

See `edge_icvi_v2.csv`. Every replayed v1 row passed the saved-table gate; mutual-k20 has ARI=NMI=1 against the unchanged static reference. The grid is not a tuning exercise.
