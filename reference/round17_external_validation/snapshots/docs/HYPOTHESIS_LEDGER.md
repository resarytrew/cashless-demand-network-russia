# Hypothesis and Claims Ledger — Current Scientific Status

## Current state — Round16 evidence and Atlas 2.2.1 engineering release

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
