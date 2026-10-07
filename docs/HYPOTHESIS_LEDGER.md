# Hypothesis and Claims Ledger — Current Scientific Status

## Round21 structural sensitivity (evidence v2.8.0)

- **Omega change as pure shuffle:** weakened. December change is predominantly
  coarsening, but not perfectly nested.
- **Merge pattern independent of effective K:** only partly supported. B/E
  persists at matched K; C/D/F/G does not.
- **Atlas omega check:** omega was absent from Atlas families, so this is a
  held-out sensitivity axis; 1/824 stable versus 348/388 transition changes.
- **Adjusted sector support:** small but detectable observational association
  remains after size/region controls (partial R² .0361, p=.0005).
- **Original L2 block robustness:** not supported by Balanced-A/B. Both
  alternatives differ materially; neither replaces original L2.
- Legacy A–G statuses remain unchanged.

## Round20 targeted checks (evidence v2.7.0)

- **Size/region explanation:** weakened. A–G differences remain jointly
  associated with log wage and log employment total after log population and
  region fixed effects (partial R2 0.1758 and 0.2144; within-region
  Freedman–Lane p=0.0005 for both). This is not causal evidence.
- **Exact-boundary omega robustness:** not supported for `omega=1`. December
  ARI=0.4070, NMI=0.5547, K=7 versus reference K=10, and aligned change share
  is 33.14%. All A–G feed mainly into a dominant destination, but B/E and
  C/D/F/G merge; do not report retention alone as profile preservation.
- **Core/boundary Atlas story:** supported for this sensitivity. Stable core
  changes 1/824; transition changes 348/388.
- **L2 block dominance:** employment does not dominate all-pair distance
  (34.54%, versus demand 34.08%), but is the largest local graph-edge term
  (about 52.1%). No post-result weight retuning is authorized.

## Round19 dual-lens additions (evidence v2.6.0)

### H18 — Adding broader economic attributes leaves the L1 partition unchanged

**Status: rejected for exact boundaries; L1 itself remains unchanged.**

The separate L2 partition has December ARI=.431917 and NMI=.471727 against L1 on
1,876 common municipalities. This is material lens dependence, not a reason to replace
L1 or retune its parameters.

### H19 — L2 establishes five robust universal local-economy types

**Status: not established.**

Five communities exceed the fixed 2% reporting threshold and cover 95.3% of L2, but
the temporal December partition contains 41 communities, many linked to intralayer
isolates, and its silhouette is negative. The five are descriptive major profiles.

### H20 — L2 profiles admit economic interpretation

**Status: supported descriptively with scope limitations.**

A fixed shallow rule tree predicts the five major profiles with CV accuracy=.856 and
balanced accuracy=.845. Suggested names are generated from included population, wage,
market-access and employment attributes. They are interpretable summaries, not
independent validation and not causal mechanisms.

### H21 — Rosstat variables independently validate L2

**Status: rejected by design for included variables.**

Population, wage and employment structure enter L2, as does hackathon market access.
They remain independent of L1 construction but cease to be independent evidence for L2.
Mobility is held out, yet its exact-name coverage is selected (268/1,876), so the large
exploratory group effect does not establish national validation.

## Current state — Round18 representation evidence (v2.5.0)

Round18 is completed. Five-part CLR and observed-level alternatives retain
recognizable broad structure but change exact boundaries materially (temporal
December ARI=0.821695 and 0.707693 respectively). This strengthens the existing
qualification against representation-invariant exact clusters. It does not change
the reference specification or any A–G scientific status. See
`outputs/round18_representation/ROUND18_AUDIT.md` and
`outputs/evidence_v2_5_0/ROUND18_EVIDENCE_UPDATE.md`.

## Preserved Round17 external interpretation evidence (v2.4.0)

Round17 adds 58 exact matches in four regions to current Atlas v2.2.1; it is an
external interpretation layer, not a new clustering or a robustness-status upgrade.
External measurements were not used to build or tune the original network.
The selected sample is not nationally representative (A43/C4/D2/F2/G7; B/E absent).
All ten recovered statistics reproduce, including the uncertain Khabarovsk A/G
comparison and adjusted Altai result. Altai D2/F1/G3 supports only a limited
regional wage gradient. Yakutia A wage/investment association is conditional and
noncausal; employee wages are not household income and mining is not established.
B–E remains internally supported but externally unassessed. C remains contextual /
unresolved. F's transition interpretation gains limited external corroboration;
prior boundary-stability qualifications remain. Seven equal universal economic
archetypes remain rejected.

Read [Round17 report](../outputs/round17_external_validation/INDEPENDENT_ECONOMIC_VALIDATION.md),
[audit](../outputs/round17_external_validation/RECOVERY_AUDIT.md),
[claim matrix](../outputs/round17_external_validation/CLAIM_EVIDENCE_MATRIX_v2.4.0.csv)
and [current pointers](CURRENT_STATE.json). Raw source documents and source row/page
locations are unavailable; normalized analytical data and statistics replay offline.
No baseline, Round16, perturbation or existing Atlas outputs were changed.
A–G scientific robustness statuses and the reference specification are unchanged.
At the Round17 freeze, Round18 had not yet been executed. Its archived protocol is
under `reference/historical_provenance/round18/`; the completed outputs above supersede
that planning status.

## Preserved prior state — Round16 evidence and Atlas 2.2.1 engineering release

The machine-readable pointer is `docs/CURRENT_STATE.json`. Evidence v2.3.0 and
Atlas v2.2.1 are separate versions. Scientific A–G statuses and the reference
specification are unchanged. Round16 computational work is complete, but full
acceptance remains limited by unavailable contextual inputs. Read
`outputs/round16_evidence/ROUND16_FINAL_PRESUBMISSION_AUDIT.md` and
`docs/ENGINEERING_HARDENING_20260922.md` before the historical context below.

Context controls (geography, population/density, residualization) remain
historical-only where their source inputs are unavailable. The descriptive B
within-stratum comparison is separately reproducible. Total's denominator and
category additivity remain unestablished. Consensus agreement does not remove
these limits or establish geographic meanings for A–G.

Use `python scripts/verify_current_artifacts.py` for the current checkout.
The old standalone verifiers retain their historical scope and original bytes.
Atlas v2.2.1 preserves v2.2 arithmetic on recorded inputs and adds configuration,
input integrity, verified resume and explicit unresolved handling; it is not a
new clustering experiment. See `docs/ATLAS_REPRODUCTION.md`.

## Historical context — retained with the current scope above

This file is a compact narrative ledger. Numeric artifacts and latest explicit evidence-round CSVs remain the source of truth.

## H1 — There is nontrivial network structure in local cashless demand

**Status: supported descriptively / robustly, not causal.**

Reason: multiple graph constructions and algorithms reveal nonrandom structure, but exact partitions differ. Static and temporal organization is reproducible at coarse levels while fine boundaries are parameter-sensitive.

## H2 — A–G are seven robust archetypes

**Status: rejected.**

Use A–G as reference profiles with heterogeneous evidence. Tiny communities are technical/micro cases. C is not supported as a beyond-context archetype. F is boundary-sensitive. A is overlapping. B is a nested subtype. G is broad macroprofile.

## H3 — k=20 is the optimal neighborhood parameter

**Status: rejected wording.**

k=20 is the post-hoc structural reference specification: the first tested k where the Dec static graph becomes connected after fallback. k30/k50 materially alter boundaries and K.

## H4 — omega=2 is optimal

**Status: rejected wording.**

omega=2 is a temporal reference with strong persistence; omega4 yields similar persistence but materially different partitions. Smaller omega values lead to many more switches.

## H5 — alpha=0.70 is optimal

**Status: rejected wording.**

Round 13 showed alpha is material. 0.70 is a balanced reference specification and preserves useful temporal persistence, but no universal ICVI winner exists.

## H6 — D is merely geographic/administrative clustering

**Status: weakened / not supported in that simple form.**

D retains strong compactness under region/admin/spatial matched nulls, and it is not one contiguous geographic patch. However, continuous population/density controls substantially weaken its effect. Best current interpretation: real internal structure with meaningful dependence on urban scale/context and unstable exact boundary.

## H7 — E is an independent clean profile

**Status: weakened.**

E is compact at baseline and spatially structured, but admin + population/density controls bring residual compactness close to null, and B/E boundaries can merge. Treat as nested/context-sensitive.

## H8 — F is a stable exact archetype

**Status: not supported.**

F has reproducible signal but unstable exact boundary across k, alpha, residualization and pilot perturbations. Treat as boundary/refinement population; completed Round15 high-rep and Round16 evidence retain this status.

## H9 — G is only a meaningless residual/default bin

**Status: too strong / not supported.**

G has high graph cohesion and spatial structure, and broad membership is often stable. But its residual effect becomes modest after geography/admin/population-density controls. Current label: broad macroprofile with default/background caveat.

## H10 — C is a robust low-spending marketplace/transport archetype

**Status: rejected.**

C loses compactness under admin/region/spatial and continuous controls; some plausible spatial specifications produce ratio >=1. Spatial autocorrelation alone does not rescue it.

## H11 — B is a nationwide service-intensive archetype

**Status: rejected framing.**

B is best described as a high-spending federal-intracity subtype. All 98 reference members are federal-intracity, but only ~40.8% of that stratum is in B. Use within-stratum comparisons rather than nationwide socioeconomic labels.

## H12 — Marketplace is a proven causal driver of transitions

**Status: not supported.**

Marketplace is an important discriminating feature and rose strongly nationally, but transition/lead-lag results do not establish causal diffusion. A broad movement can be described, not causally attributed.

## H13 — Mobility validates the partition externally

**Status: rejected wording.**

Mobility coverage is selected and uneven. Corrected fold-aware testing found only a small, statistically uncertain increment from community information. Use mobility as auxiliary triangulation only.

## H14 — The 685-member transition is an exact robust event

**Status: partially supported only at broad directional level.**

The broad movement reproduced under k30, but exact membership/precision did not. Headline wording must distinguish broad movement from exact transition boundary.

## H15 — The 229-member transition is robust

**Status: rejected as headline.**

It is k/residualization-sensitive and should remain exploratory.

## H16 — Pilot perturbation n=5 establishes boundary stability

**Status: SUPERSEDED_NON_REPRODUCIBLE_HISTORICAL_PILOT; excluded as quantitative evidence.**

The historical runner and former canonical CSVs do not form a demonstrated reproducible chain. Its mismatch reproduced independently according to the user; the cause is not established. No old n=5 conclusion is carried as confirmed evidence. Canonical sorted-edge protocol v2 is a new experiment: all 50 seeds completed after exact hash gates. See Round 15 and the v2 findings; do not pool or compare old seeds as reproduction targets.

## H17 — Louvain-specific structure is algorithm-independent

**Status: exact invariance not supported by the completed fixed same-graph Leiden swap.**

Round 14: full-supra ARI=0.440289, December ARI=0.707550. A/G retain substantial December cores; B/E nearly coassign, D/F mix, and F splits toward D/G. Some internal structure survives, but exact partitions and boundaries depend on the algorithm. No universal winning algorithm is selected. Profile claims must incorporate Round 15 v2 distributions as well as context controls; any earlier mention of historical pilot evidence above is superseded by H16.

## Round17 claim-level additions (prior statuses above retained)

| Claim | Round17 status | Scope |
|---|---|---|
| D–F–G wage gradient | SUPPORTED_IN_EXTERNAL_REGIONAL_VALIDATION | Altai n=6, F1; adjusted p=0.088869 |
| F boundary/transition population | SUPPORTED_BY_COMBINED_INTERNAL_AND_EXTERNAL_EVIDENCE | Internal F327; external F2; no causal or national claim |
| A wage/investment intensity | SUPPORTED_WITH_SCOPE_LIMITATIONS | Yakutia A27, Chukotka A4; Khabarovsk contrast uncertain |
| A extractive/mining mechanism | NOT_ESTABLISHED | No sector mechanism tested |
| B–E structural family | SUPPORTED_INTERNALLY | Existing coassignment, not independent economic evidence |
| B–E economic interpretation | EXTERNALLY_UNVALIDATED | B0/E0 |
| C substantive archetype | UNRESOLVED | C4; prior unsupported-beyond-context status retained |
| Seven equal universal archetypes | REJECTED | Heterogeneous robustness and limited external coverage |

The nonsignificant wage/population correlation does not establish independence
from population. Wages are not household income. No historical robustness status
is promoted by these interpretation claims. See the machine-readable claim matrix
for methods, statistics, effect sizes, exploratory p-values and limitations.
