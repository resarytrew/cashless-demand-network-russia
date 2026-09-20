# Leiden findings — Round 14

The exact graph is preserved but the partition changes materially: full-supra ARI=0.440289, NMI=0.595032; December temporal ARI=0.707550, NMI=0.731498. Leiden gives 14 supra communities and 10 December communities. The clean swap weakens exact algorithm-independence; it does not remove all broad structure.

Static comparison (one consistent metric implementation):

| algorithm | K | SW | CHn | MQ | Q_resolution_0_5 | AVI | AVU |
| --- | --- | --- | --- | --- | --- | --- | --- |
| louvain | 9 | 0.169645 | 0.459672 | 0.767448 | 0.839654 | 0.907450 | 0.506291 |
| leiden | 8 | 0.211978 | 0.514736 | 0.753881 | 0.843325 | 0.918221 | 0.521288 |

Leiden improves some feature and optimized-objective metrics while conventional static MQ decreases. S_Dbw is undefined for both under the documented zero-denominator rule. No single ranking follows.

Temporal persistence:

| algorithm | mean_switches | median_switches | share_zero_switches | share_le2_switches | mean_adjacent_ARI | mean_adjacent_NMI |
| --- | --- | --- | --- | --- | --- | --- |
| louvain | 1.338761 | 1.000000 | 0.250000 | 0.852941 | 0.877904 | 0.889729 |
| leiden | 1.934349 | 2.000000 | 0.050420 | 0.822479 | 0.874990 | 0.883828 |

Reference December profiles:

| archetype | retention | precision | Jaccard | within_pair_coassignment |
| --- | --- | --- | --- | --- |
| A | 0.957447 | 0.964286 | 0.924658 | 0.917123 |
| B | 1.000000 | 0.346290 | 0.346290 | 1.000000 |
| C | 0.620690 | 1.000000 | 0.620690 | 0.487685 |
| D | 0.986928 | 0.474843 | 0.471875 | 0.974028 |
| E | 0.983871 | 0.646643 | 0.639860 | 0.967974 |
| F | 0.495413 | 0.509434 | 0.335404 | 0.486426 |
| G | 0.998964 | 0.845614 | 0.844873 | 0.997927 |

| pair | cross_coassignment |
| --- | --- |
| A/D | 0.013999 |
| B/E | 0.983871 |
| D/F | 0.488937 |
| F/G | 0.491845 |

A's December membership remains close under this swap. B and E largely coassign, strengthening the nested/overlapping boundary caveat. D has high retention but low precision inside a larger D/F destination. F splits toward D and G; its exact-boundary claim remains weak. G retains a broad core with additional members. C is not rehabilitated: algorithmic retention cannot override failed context controls. Existing population/density, geography and causal-language caveats are unchanged. These are exploratory results for this reference specification and one fixed algorithm seed.
