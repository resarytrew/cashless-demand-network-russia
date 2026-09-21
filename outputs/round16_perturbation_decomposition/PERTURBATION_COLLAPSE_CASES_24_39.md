# Collapse cases 24 and 39

| mode | seed | louvain_seed | K_Dec2024 | largest_community_n_Dec | largest_community_share_Dec | ARI_all_supra | NMI_all_supra | ARI_Dec2024 | NMI_Dec2024 | MQ | Dec_MQ | edges | components | connectivity_changed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| collapse_fixed | 24 | 0 | 10 | 1868 | 0.981092 | 0.507815 | 0.630474 | 0.021709 | 0.064806 | 0.782216 | 0.001295 | 312785 | 1 | False |
| combined | 24 | 24 | 10 | 1864 | 0.978992 | 0.569190 | 0.658243 | 0.021394 | 0.067955 | 0.763961 | 0.001810 | 312785 | 1 | False |
| collapse_fixed | 39 | 0 | 9 | 1874 | 0.984244 | 0.466281 | 0.601774 | 0.019553 | 0.063726 | 0.777963 | 0.001017 | 312490 | 1 | False |
| combined | 39 | 39 | 9 | 1877 | 0.985819 | 0.507489 | 0.634089 | 0.016244 | 0.049215 | 0.783739 | 0.000708 | 312490 | 1 | False |

Raw combined labels confirm 1864/1904 and 1877/1904. Reusing those exact perturbed graphs with Louvain seed=0 gives 1868/1904 and 1874/1904. Collapse therefore does not require the original optimizer seeds24/39. It persists for these graph realizations with optimizer seed0; the limited design does not establish graph-only causality or invariance to every optimizer seed.

high retention can be misleading under near-global community collapse; therefore retention must be interpreted jointly with precision, Jaccard and largest-community share.

`perturbation_collapse_cases.csv` reports full/December quality, degrees, components and weight distributions; `perturbation_collapse_archetypes.csv` and `perturbation_collapse_pairs.csv` retain all requested profile and pair diagnostics. MQ is resolution1; Q_resolution_0_5 is the optimized gamma=.5 quality. December MQ is evaluated on the induced perturbed December layer. Connected-component counts do not change, but unchanged connectivity does not imply unchanged community structure. All edges and weight hashes are recorded in each collapse checkpoint. No seed was removed.
