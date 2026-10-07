# Profile cards audit

The cards are a descriptive presentation layer over frozen A-G labels. No external variable entered clustering, no reference parameter changed, and no scientific status was promoted by computation.

Config: `configs\profile_cards_20261007.yaml`. Reference month: 2024-12. Panel: 1904 municipalities.

Representative and counterexample rules are declared in the YAML config. Orenburg, Magnitogorsk and Tambov are a curated D headline only; D representatives are selected algorithmically.

Expense arrows compare profile medians with the overall 1,904-municipality median. Ratios within 0.98-1.02 are neutral and receive no arrow. External population, wage and employment ratios use the audited national 2024 join.

The canonical scientific sector vocabulary has 18 columns. The saved national join exposes 15: manufacturing, utilities, construction, trade, hospitality, information, finance, real_estate, professional, administrative, public_administration, education, health, arts, other_services. Unavailable in that source: agriculture, mining, transport. No zeros or values were invented for unavailable sectors; the limitation is explicit in the JSON.

Robustness combines frozen Atlas consensus/leave-one-family-out summaries, canonical n=50 perturbations, and the two saved representation variants. High retention is reported separately from destination precision.
For every alternative representation the card reports both reference retention and destination precision. For the n=50 perturbation it also reports the 10th percentile, so the mean cannot hide the lower tail.
F is not represented by three medoids: it deliberately exposes a D-leaning case, a G-leaning case, and the smallest Atlas affinity margin. C labels its examples as illustrative rather than characteristic.
Public names avoid interpreting Total as consumer activity because the denominator of Total is not established.

C remains UNRESOLVED; F remains TRANSITION; B and E remain PRELIMINARY. A, D and G use the user-provided public status SUPPORTED without changing the repository's underlying scientific evidence registry.
