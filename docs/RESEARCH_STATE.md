# Research State — Distilled Project Context

## Current override — Rounds 14 and 15 completed

Read the latest audits/findings in `outputs/leiden_robustness/` and `outputs/perturbation_v2/`; matrix version 2.2.0 is in `outputs/evidence_v2_2_0/`. The earlier context below is retained with this explicit supersession: historical canonical n=5 is **SUPERSEDED_NON_REPRODUCIBLE_HISTORICAL_PILOT**, not quantitative evidence. Any below-reference to pilot evidence or a pending high-rep task is historical and superseded by the provenance resolution and v2 results. Do not transfer old n=5 conclusions as confirmed claims.

Leiden on identical graphs: full-supra ARI=0.440289, December ARI=0.707550, 14 supra communities. B/E cross-coassignment=0.983871; D/F=0.488937; F/G=0.491845. Core retention and exact-boundary stability are distinct.

Canonical sorted-edge perturbation v2 passed same-process, fresh-process and reversed-insertion checks, then completed all 50 seeds. Mean full-supra ARI=0.498355; mean December ARI=0.675736 (minimum=0.016244). D mean retention=0.975817 but mean precision=0.511661; F mean retention=0.702813, q10=0.492355, mean precision=0.476762. B/E cross mean=0.465586, D/F=0.434798, F/G=0.317798, A/D=0.230527. G retention q10=0.622902 limits any claim of uniformly stable broad membership. C remains unsupported beyond context; no seven-archetype claim is reinstated.

No reference parameters were changed. Old outputs remain intact. The full historical master matrix was not supplied; the new version explicitly combines available Round 13 status and new numerical evidence without reconstructing missing historical columns. Reproduction commands: `docs/ROBUSTNESS_V2_COMMANDS.md`.

## 1. Data and sample accounting

Spending data cover Jan-2023 through Dec-2024, 24 months, approximately 303,126 raw rows and 2,118 unique textual municipality labels.

Strict-panel accounting:

- 2,118 textual labels observed;
- 49 duplicated/ambiguous multiple territorial series;
- 1,952 complete 24×6 histories;
- 166 incomplete-name histories;
- 48 complete but ambiguous;
- 1 ambiguous + incomplete;
- final safe strict panel: **1,904 municipalities**.

The strict panel is an analytical panel. It has not been established as a statistically representative sample of all Russian municipalities.

## 2. Feature construction

Five named categories are used together with residual `Other`:

- Food;
- Health;
- Catering;
- Marketplace;
- Transport;
- `Other = Total - Food - Health - Catering - Marketplace - Transport`.

`Other` is a technical residual and must not be described as a coherent economic sector.

Composition is represented with CLR/Aitchison geometry.

Spending level uses `log(Total)` and monthly robust z-scores based on median and `1.4826*MAD`.

The two feature blocks are normalized by their median pairwise distances and combined as:

`X = [sqrt(alpha) * CLR/ms, sqrt(1-alpha) * level/ml]`.

Reference alpha is 0.70/0.30. Alpha sensitivity has now been tested at 0.50, 0.70, 0.90. Alpha=0.70 remains a balanced reference specification, not an optimum.

## 3. Graph construction

Monthly graph:

- weighted, undirected mutual-kNN;
- reference k=20;
- adaptive RBF weight `exp(-d^2/(sigma_i sigma_j))`;
- `sigma_i` is kth-neighbor distance;
- static Dec-2024 graph applies nearest-neighbor isolate fallback;
- temporal monthly layers do not apply isolate fallback.

k=20 is a **post-hoc structural reference specification**: it was the first tested point where the Dec-2024 static graph became fully connected after fallback. Never call it mathematically optimal.

Temporal network:

- 1,904 × 24 = 45,696 municipality-month copies;
- identity edges connect the same municipality in adjacent months;
- identity weight = `omega × global median intralayer weight`;
- reference omega=2;
- NetworkX Louvain, resolution=0.5, seed=0.

Omega=2 is a reference, not an optimum.

## 4. Static Dec-2024 benchmark context

Reference Aitchison+level mutual-k20 baseline had approximately:

- K=9 static communities in the benchmark partition;
- SW ~0.176 in the original static benchmark calculation;
- CH/N ~0.468;
- S_Dbw ~0.635;
- AVI ~0.909;
- AVU ~0.469;
- MQ ~0.765.

Static algorithm comparisons showed no universal winner. KMeans/Ward can look better on pure attribute compactness while network methods can look better on graph modularity/isolation. Do not collapse metric tradeoffs into a single ranking.

## 5. k sensitivity

Topology changes materially with k.

Reference values previously observed:

- k10: fragmented after fallback; K≈16;
- k15: near-connected; K≈11;
- k20: connected after fallback; K≈9;
- k30: K≈8;
- k50: K≈7.

Partition similarity decreases as k moves away from 20. Fine boundaries are not invariant.

Important examples:

- D remains a substantive compact group but its exact boundary is k-sensitive;
- F is strongly boundary-sensitive, especially toward G and D;
- the historical 685-member broad movement from one community to another reproduced directionally under k30 but not with exact boundary identity.

## 6. omega sensitivity

Omega sensitivity showed a sharp change in temporal persistence:

- omega 0.25/0.5/1 lead to many more switches;
- omega=2 yields median ~1 switch and ~85% of municipalities with <=2 switches;
- omega=4 yields similar persistence but a meaningfully different partition.

Omega2 vs omega4 is only moderately similar; exact communities are not invariant. Do not call omega=2 optimal.

## 7. Alpha sensitivity — Round 13

Alpha=0.70 reproducibility gate passed exactly: full-supra and Dec-2024 ARI/NMI = 1 against saved baseline.

Key comparison:

- alpha=0.50: stronger static SW/CH; full-supra ARI vs 0.70 ~0.556; Dec ARI ~0.737;
- alpha=0.70: reference; strongest temporal persistence of the tested three;
- alpha=0.90: full-supra ARI ~0.479; Dec ARI ~0.736; Dec graph has 5 connected components after fallback rather than one.

Interpretation:

- alpha is material;
- 0.70 is not statistically selected as best;
- large cores often survive, but fine boundaries change strongly;
- F is especially alpha-sensitive;
- D/F and F/G boundaries change substantially;
- B/E overlap remains a multiscale issue.

Use `outputs/alpha_sensitivity/` as the numerical source of truth.

## 8. Temporal baseline

At omega=2 baseline:

- ~12 supra communities overall;
- ~10 communities/month on average;
- mean switches ~1.339, median 1;
- 476 municipalities with zero switches;
- 1,624/1,904 with <=2 switches;
- mean monthly SW ~0.124.

April/May 2024 have notably weak silhouette values. Temporal persistence is not equivalent to feature separation.

## 9. A–G profile definitions at reference Dec-2024

Public labels map to reference temporal community IDs:

- A = 1, n=141;
- B = 3, n=98;
- C = 7, n=29;
- D = 8, n=153;
- E = 9, n=186;
- F = 10, n=327;
- G = 11, n=965.

Three additional tiny communities (2, 2, 1 members) are treated as micro-communities / technical anomalies, not archetypes.

Do not say “seven robust archetypes.” A–G are reference profiles with different evidence status.

## 10. Current profile evidence status

### A
Candidate overlapping network regime, not a clean archetype.

Evidence:

- poor metric separation; silhouette around -0.185 in a dedicated audit;
- strong network isolation/internal strength;
- beyond-admin/spatial compactness exists but is moderate;
- population/density controls weaken compactness toward null;
- alpha sensitivity shows the broad core is fairly retained, but interpretation remains overlapping.

### B
Candidate federal-intracity subtype.

Evidence:

- 98/98 reference members are federal-intracity territories;
- B represents about 40.8% of the federal-intracity stratum, not “all federal cities”;
- strong within-stratum separation relative to other federal-intracity territories;
- B/E exact boundary can be unstable;
- population/density/admin controls weaken the residual compactness strongly;
- alpha core retention is high, but B should remain a nested subtype rather than nationwide archetype.

### C
Rejected as a robust beyond-context archetype.

Evidence:

- admin-stratified compactness not significant/strong;
- region×admin null removes compactness;
- spatial block ratios cross 1 across plausible specifications;
- continuous population/density controls push compactness to ~1 or above;
- alpha=0.90 retention weakens further.

C may be spatially nonrandom; spatial autocorrelation alone does not rehabilitate it.

### D
Candidate profile with strong internal compactness but unstable exact boundary.

Evidence:

- very strong compactness under admin and spatial matched nulls;
- not merely one geographic contiguous patch;
- residualization and continuous population/density controls weaken effect substantially;
- alpha sensitivity shows a stable core but strong D/F boundary dependence, especially at alpha=0.90;
- k30 can merge meaningful parts of D with A/F depending specification.

Interpret core stability separately from boundary stability.

### E
Candidate nested/context-sensitive profile.

Evidence:

- strong baseline compactness;
- spatial clustering substantial;
- geography explains part of the effect;
- admin + population/density controls bring residual compactness close to null;
- B/E can merge under perturbations/specifications;
- treat as nested/overlapping rather than a universal archetype.

### F
Boundary/refinement population; weak as an exact archetype.

Evidence:

- compactness persists after several controls;
- exact membership is highly sensitive to k, alpha, residualization, and perturbations;
- k30 splits roughly between G-dominated and A/D-dominated destinations;
- alpha=0.50 mixes F strongly with G and D; alpha=0.90 strongly with D;
- do not claim a reproducible exact split until high-rep perturbation says more.

### G
Broad macroprofile.

Evidence:

- largest reference group, n=965 (~51%);
- strong graph cohesion and spatial autocorrelation;
- residual effect after admin/spatial controls is moderate rather than extreme;
- continuous population/density controls move compactness close to null;
- broad membership retains well under several parameter changes;
- default-category / broad-background interpretation remains a caveat.

## 11. Administrative-form analysis

Sber textual admin forms were parsed into:

- federal_intracity;
- urban_okrug;
- municipal_raion;
- municipal_okrug.

Admin form predicts A–G only partially; it is not sufficient to explain the partition.

Important: administrative form is a coarse proxy for urbanization/settlement/infrastructure. Residualizing it does not identify causal effects.

## 12. OKTMO crosswalk and geography

A period-aware crosswalk was built from historical Rosstat OKTMO snapshots.

Final operational state:

- 1,887/1,904 deterministic historical matches;
- 13 high-confidence manual resolutions;
- 4 provisional ambiguous-region resolutions, explicitly flagged;
- operational crosswalk covers 1,904/1,904.

Spatial geometry:

- polygon coverage: 1,903/1,904 (~99.95%);
- missing polygon: `городской округ город Первомайск`, LNR, reference G;
- spatial robustness conclusions are not sensitive to excluding the four provisional crosswalk rows.

## 13. Spatial robustness

Polygon-based diagnostics and block controls have been performed.

Global Moran I of profile membership was positive for all A–G, but spatial clustering alone is not evidence of a valid archetype.

Spatial block matched-null tests across multiple block sizes/shifts showed approximately:

- A: moderate effect, spatial-scale dependent;
- B: residual compactness remains;
- C: weak/specification-dependent, ratios can cross 1;
- D: strong residual compactness;
- E: substantial residual compactness with geographic contribution;
- F: substantial compactness but unstable boundary;
- G: stable but moderate residual effect.

## 14. Population and density controls

Municipal population was joined from Rosstat Jan-01-2024 and Jan-01-2025 data. Geometry-derived area provides density.

Coverage for the relevant continuous-control analysis is effectively 1,903/1,904 because of the missing LNR polygon/covariate case.

Population+density explain a large share of several Dec-2024 feature components descriptively. These are associations, not causal effects.

Exact spatial500 matched-null compactness after continuous controls showed approximately:

- A: residual ratio ~0.92–0.94;
- B: ~0.91–0.95;
- C: ~1.05–1.09;
- D: ~0.87–0.88;
- E: population+density ~0.74, with admin also ~0.97;
- F: ~0.83–0.85;
- G: ~0.95–0.96.

This materially weakens claims that B/E/G and part of D are independent of urban scale/density.

## 15. Mobility

Mobility is auxiliary triangulation with selected coverage, not external validation.

Coverage is highly nonuniform across profiles/admin forms. An earlier transductive mobility-AUC analysis had leakage and was withdrawn.

Corrected fold-aware analysis with train-only graph + centroid out-of-sample proxy found only a very small AUC increment for adding community information; bootstrap CI included zero and p was non-significant. This does not prove “no signal,” because the OOS proxy is not native Louvain prediction.

Never describe mobility as independent external validation of the clusters.

## 16. Flow / lead-lag / seasonality

Temporal transition and lead-lag analyses are post-selected/exploratory.

A broad 685-case movement was directionally robust under k30 but exact boundary identity was not. A 229-case movement did not survive key sensitivity checks and should not be a headline claim.

Marketplace share increased strongly over the period at the national median, but this is descriptive and not causal. Common-category multiplicative monthly effects largely cancel under within-month CLR distance; region-specific inflation/local seasonality is not thereby controlled.

Lead-lag edge counts under the tested construction were not globally enriched versus circular-shift null; observed counts were actually lower than null. Do not claim diffusion or contagion.

## 17. Multiplicity and inference language

Project-wide p-values are exploratory due to extensive multiplicity and post-selection. Use Holm/BH only where a clearly defined local family is explicitly stated.

Do not transform exploratory significance into causal or confirmatory language.

## 18. Perturbation pilot provenance now available in repository

The previously missing n=5 supra perturbation provenance has been recovered and committed under `outputs/perturbation_pilot_reference/` and `reference/perturbation_pilot/`.

Canonical perturbation semantics for the expansion gate:

- perturb intralayer edges only;
- independent edge drop probability = 0.05;
- retained intralayer weight multiplier = `exp(N(0, 0.02))`;
- temporal identity edges unchanged;
- RNG for perturbation seed `s`: `np.random.default_rng(20260918 + s)`;
- Louvain resolution = 0.5 and Louvain seed = `s`;
- pilot seeds = 0..4.

The five-run pilot is descriptive only. In particular, B/E cross-coassignment varies from near 0 to near 1 across the five seeds, so its boundary distribution remains unresolved until the n=50 expansion is completed.

Do not confuse the recovered supra-perturbation pilot with other historical static perturbation summaries unless provenance establishes they used the identical experiment.
