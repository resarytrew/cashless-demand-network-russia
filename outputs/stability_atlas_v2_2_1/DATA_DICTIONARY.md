# Atlas 2.2.1 data dictionary

This artifact describes the recorded December 2024 reference panel. It does not
estimate population probabilities or establish causal/geographic economic types.

| Field | Meaning |
|---|---|
| municipality / panel_index | Published textual key / position in authenticated reference order |
| reference_profile | Original A–G profile; micro for five small-community members |
| consensus_class / second_class | Largest / second affinity share; deterministic profile-order ties; unresolved if total affinity is zero |
| raw_affinity_A … G | Mean pair coassignment with members of each reference profile, excluding self |
| affinity_share_A … G | Raw affinities divided by their row sum; descriptive, not probabilities |
| affinity_entropy | Entropy of shares divided by log(7); undefined for zero-affinity rows |
| affinity_margin | Largest minus second share; zero does not establish a unique class |
| family_votes_D_over_G / G_over_D | Number of four families with greater raw affinity to the named side |
| D_G_transition_direction | For reference F, at least 3/4 family votes for D or G; otherwise mixed |
| D_G_balance | (share_D − share_G) / (share_D + share_G); 0 if denominator is zero |
| B_E_balance / transition_direction | Analogous descriptive B/E comparisons |
| lofo_class_match_count | Number of four family omissions preserving the full hard class |
| lofo_DG_side_match_count | Omissions preserving the sign of affinity balance; NOT the family-vote direction statistic |
| anchor_consensus_class | Class using top-25% own-affinity members of each reference profile, at least two |
| perturbation_peer_coassignment | Mean within-reference-profile peer coassignment across 50 recorded perturbations |
| destination_precision / destination_jaccard | Recorded municipality-level destination diagnostics; distinguish core retention from boundary quality |
| stability_class | Descriptive threshold category defined in the YAML; micro always unresolved |

Other CSVs report family affinities, four LOFO variants, anchor comparisons,
profile summaries and F/B–E subsets. Micro-community affinities are descriptive
comparisons only and do not promote these cases into A–G substantive profiles.
The viewer's 24-month trajectory is the saved temporal community ID, not a
continuous spending measure and not proof of an economic transition.

Sources: input_checksums.csv, run_manifest.json and COMPLETED.json. Historical
contextual controls are not reproduced here. Total denominator, geographic joins
and category additivity remain unresolved; no map or income inference is supplied.
