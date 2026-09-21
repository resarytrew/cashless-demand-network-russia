# Resolution sensitivity audit

Four predeclared values .25/.50/.75/1.00; seed0; unchanged features, static/supra graphs, weights, alpha=.70, k20, omega2. Static December and temporal December are separate partitions. Raw labels and monthly diagnostics are checkpointed; requested A–G diagnostics and all 21 pair relations are saved. Gamma=.5 reproduces ARI=NMI=1. No best gamma is selected.

| gamma | static_K | static_SW | static_CHn | static_AVI | static_AVU | static_MQ | K_supra | K_Dec2024 | mean_switches | share_le2_switches | ARI_all_supra | ARI_Dec2024 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.250000 | 7 | 0.211617 | 0.500461 | 0.922969 | 0.450625 | 0.715842 | 7 | 6 | 0.879202 | 0.949055 | 0.508157 | 0.733900 |
| 0.500000 | 9 | 0.169645 | 0.459672 | 0.907450 | 0.506291 | 0.767448 | 12 | 10 | 1.338761 | 0.852941 | 1.000000 | 1.000000 |
| 0.750000 | 14 | 0.132894 | 0.366195 | 0.871023 | 0.498509 | 0.790501 | 16 | 11 | 1.935399 | 0.747374 | 0.535307 | 0.631656 |
| 1.000000 | 14 | 0.131953 | 0.366206 | 0.869509 | 0.498367 | 0.789246 | 22 | 15 | 2.238445 | 0.615021 | 0.518615 | 0.857288 |

S_Dbw undefined under the fixed Round-14 implementation; no alternative variant was used for ranking. MQ uses resolution1; static_Q_resolution uses each run gamma. This is scale/granularity sensitivity.
