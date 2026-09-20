# Alpha sensitivity findings — structure vs spending level

## Scope

Only the feature-block weights are changed. All other reference settings are fixed: mutual-kNN k=20, adaptive RBF weights, temporal omega=2, Louvain resolution=0.5, seed=0, static isolate fallback on and temporal isolate fallback off.

Tested specifications:

- alpha=0.50: 50% CLR composition / 50% relative spending level;
- alpha=0.70: 70% CLR composition / 30% level (reference);
- alpha=0.90: 90% CLR composition / 10% level.

The alpha=0.70 rerun reproduces the frozen temporal baseline exactly: full-supra ARI=1.000 and NMI=1.000.

## Main result

Alpha is a material sensitivity axis. The endpoint temporal partitions are not equivalent: alpha=0.50 vs 0.90 gives full-supra ARI=0.436, NMI=0.567; for December 2024 ARI=0.683, NMI=0.666.

The reference 70/30 specification should therefore be described as a **balanced reference specification**, not an optimum.

## Static December 2024

|   alpha |   K |     SW |    CHn |   S_Dbw |    AVI |    AVU |   ANUI |     MQ |   ARI_vs_70 |   NMI_vs_70 |
|--------:|----:|-------:|-------:|--------:|-------:|-------:|-------:|-------:|------------:|------------:|
|     0.5 |   9 | 0.1838 | 0.5862 |  0.5489 | 0.9137 | 0.5427 | 0.6108 | 0.7792 |      0.6487 |      0.7564 |
|     0.7 |   9 | 0.1696 | 0.4597 |  0.6315 | 0.9074 | 0.5063 | 0.6218 | 0.7674 |      1      |      1      |
|     0.9 |  13 | 0.1616 | 0.2872 |  0.4682 | 0.9267 | 0.3091 | 0.7203 | 0.7649 |      0.5361 |      0.6713 |

Topology:

|   alpha |   nodes |   edges |   mean_degree |   isolates_before_fallback |   components_after_fallback |   giant_component_share |   largest_non_giant_component |   bridges |   articulation_points |   avg_clustering |
|--------:|--------:|--------:|--------------:|---------------------------:|----------------------------:|------------------------:|------------------------------:|----------:|----------------------:|-----------------:|
|     0.5 |    1904 |   11966 |       12.5693 |                          8 |                           1 |                  1      |                             0 |        32 |                    30 |           0.402  |
|     0.7 |    1904 |   11787 |       12.3813 |                         12 |                           1 |                  1      |                             0 |        37 |                    36 |           0.3864 |
|     0.9 |    1904 |   11733 |       12.3246 |                         10 |                           5 |                  0.9958 |                             2 |        31 |                    26 |           0.3846 |

Key point: alpha=0.90 produces 5 connected components after the same k=20 static fallback (giant share 0.9958), whereas alpha=0.50 and 0.70 are connected. Thus composition-heavy weighting changes the local graph topology enough that the original k=20 connectivity property no longer holds.

No ICVI gives a universal winner. Alpha=0.50 is stronger on static SW and CH/N; alpha=0.90 is stronger on S_Dbw and AVI/ANUI but has a fragmented k=20 graph; alpha=0.70 sits between these regimes.

## Temporal behavior

|   alpha |   supra_K |   dec_K |   full_ARI_vs_70 |   full_NMI_vs_70 |   mean_monthly_ARI_vs_70 |   min_monthly_ARI_vs_70 |   mean_monthly_NMI_vs_70 |   dec_ARI_vs_70 |   dec_NMI_vs_70 |   mean_adjacent_ARI |   mean_adjacent_NMI |   mean_switches |   median_switches |   share_zero_switch |   share_le2_switch |
|--------:|----------:|--------:|-----------------:|-----------------:|-------------------------:|------------------------:|-------------------------:|----------------:|----------------:|--------------------:|--------------------:|----------------:|------------------:|--------------------:|-------------------:|
|     0.5 |        11 |       8 |           0.5556 |           0.6455 |                   0.5876 |                  0.4044 |                   0.6798 |          0.7366 |          0.7311 |              0.8693 |              0.8845 |          1.4627 |                 1 |              0.2505 |             0.8288 |
|     0.7 |        12 |      10 |           1      |           1      |                   1      |                  1      |                   1      |          1      |          1      |              0.8779 |              0.8897 |          1.3388 |                 1 |              0.25   |             0.8529 |
|     0.9 |        13 |       9 |           0.4795 |           0.612  |                   0.5591 |                  0.3808 |                   0.6477 |          0.7363 |          0.6937 |              0.8432 |              0.8702 |          1.8382 |                 2 |              0.177  |             0.7658 |

Temporal persistence is strongest for the reference among these three fixed specifications: alpha=0.70 has the lowest mean switches (1.339), highest share with <=2 switches (0.853), and highest adjacent-month ARI/NMI. This is descriptive support for using 70/30 as a reference, not evidence of a statistical optimum.

Mean monthly ICVI:

|   alpha |       K |     SW |    CHn |   S_Dbw |    AVI |    AVU |   ANUI |     MQ |   edges |   isolates |
|--------:|--------:|-------:|-------:|--------:|-------:|-------:|-------:|-------:|--------:|-----------:|
|     0.5 |  8.875  | 0.1325 | 0.4089 |  0.5979 | 0.8099 | 0.4562 | 0.5909 | 0.6731 | 11926.1 |    11.7917 |
|     0.7 | 10      | 0.1242 | 0.2859 |  0.5886 | 0.7974 | 0.4073 | 0.5994 | 0.6664 | 11796.7 |    11.9583 |
|     0.9 |  9.7917 | 0.1057 | 0.24   |  0.5845 | 0.7743 | 0.3799 | 0.5984 | 0.646  | 11679.8 |    11.875  |

Again metrics conflict: alpha=0.50 improves mean SW/CH/N and MQ/AVI, while alpha=0.90 lowers S_Dbw and AVU. This is precisely why alpha should not be selected from one validity index.

## A-G sensitivity in December 2024

Retention into the dominant alternative community:

|   alpha | archetype   |   dec_n |   dec_retention |   dec_precision |   dec_jaccard |   global_retention |
|--------:|:------------|--------:|----------------:|----------------:|--------------:|-------------------:|
|     0.5 | A           |     141 |          0.9291 |          0.8291 |        0.7798 |             0.9145 |
|     0.5 | B           |      98 |          0.9898 |          0.6783 |        0.6736 |             0.9641 |
|     0.5 | C           |      29 |          0.8966 |          0.7647 |        0.7027 |             0.7219 |
|     0.5 | D           |     153 |          0.9739 |          0.4838 |        0.4776 |             0.95   |
|     0.5 | E           |     186 |          0.7527 |          0.9396 |        0.7179 |             0.712  |
|     0.5 | F           |     327 |          0.4771 |          0.5065 |        0.3257 |             0.4475 |
|     0.5 | G           |     965 |          0.9969 |          0.8674 |        0.8651 |             0.762  |
|     0.9 | A           |     141 |          0.9362 |          0.7674 |        0.7293 |             0.8093 |
|     0.9 | B           |      98 |          0.9694 |          0.8636 |        0.8407 |             0.7953 |
|     0.9 | C           |      29 |          0.6552 |          1      |        0.6552 |             0.6023 |
|     0.9 | D           |     153 |          0.9673 |          0.3027 |        0.2996 |             0.5542 |
|     0.9 | E           |     186 |          0.7903 |          0.9608 |        0.7656 |             0.9436 |
|     0.9 | F           |     327 |          0.7768 |          0.5194 |        0.452  |             0.671  |
|     0.9 | G           |     965 |          0.9378 |          0.9496 |        0.8934 |             0.6549 |

Boundary diagnostics:

- alpha=0.50: D-F cross-coassignment=0.465; F-G=0.439; B-E=0.252.
- alpha=0.90: D-F cross-coassignment=0.753; F-G=0.153; B-E=0.102.

Interpretation:

- **A:** strong Dec core retention at both endpoints; keep the overlapping-regime caveat.
- **B:** very stable core, but the B/E boundary weakens when spending level receives more weight (alpha=0.50).
- **C:** sensitive at alpha=0.90 and already rejected by stronger geography/population controls; alpha sensitivity does not rescue it.
- **D:** core membership is highly retained, but separation from F is not alpha-robust. High recall with low precision under endpoint specifications means a stable core inside a movable boundary.
- **E:** moderate-high retention with high precision; members peel away under both endpoints, and B/E overlap remains a multiscale/contextual issue.
- **F:** the clearest alpha-sensitive boundary population. It moves toward G/D under 50/50 and very strongly toward D under 90/10.
- **G:** very high Dec retention, but lower global node-month retention shows that its temporal lineage is more sensitive than its Dec cross-section.

## Decision for the project

Keep alpha=0.70 / 0.30 as the **reference specification**, but explicitly report 0.50/0.50 and 0.90/0.10 as sensitivity endpoints. Do not call 0.70 optimal. The defensible claim is that major cores persist to varying degrees across alpha, while fine boundaries—especially D/F and F/G—are specification-sensitive.
