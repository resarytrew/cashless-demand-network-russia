# Hero pinning and public evidence expansion — 2026-10-06

## Scope and user outcome

The opening desktop scene remains stationary from the first scroll until the
geographic dots reach their illustrative profile anchors. The final arrangement
is held for the final 30/130 of the timeline, then normal scrolling resumes.
On smaller viewports the figure pins once it is fully visible. Reduced motion
remains native and unpinned. Diagram coordinates now preserve aspect ratio.

New public exhibits expose existing evidence rather than fit any new model:

1. Structure / level weighting (70/30), reciprocal 20-neighbour selection and
   45,696 municipality-month observations. Weights are explicitly not budget shares.
2. Independent population, wage and employment comparison across seven profiles.
   Dots show medians and bands show 25th–75th percentiles of municipal indicators.
   Counts are indicator-specific; wage is not household income. D/F/G ordering is
   descriptive and does not promote the transition profile's boundary stability.
3. Regional held-out Random Forest macro-F1 .551205651565717 vs training-majority
   .0963025797115912. The alternative mixed split shows .6473151196544146 vs
   shuffled-label mean .09139025392600739. Different controls are labelled explicitly.
   The score is on 0–1, never mislabelled as percentage accuracy. Sample: 1,898,
   73 regional groups, five folds. Geographical transportability remains limited.
4. Three largest saved affinity shares on each municipality passport, labelled
   with public profile names. These shares are descriptive, not probabilities.

These additions surface the study's methodology, interpretation and uncertainty;
no claim of guaranteed competition success or new research evidence is made.

## Evidence examined

Startup research/evidence-governance documents, CURRENT_SUBMISSION_STATE.json,
configs/landing.yaml, configs/geographic_confounding.yaml,
configs/external_validation_national_20261006_r6.yaml, and the latest submission
and correction audits were read. Historic Round17's selected 58 municipalities
were not confused with the later national interpretation layer.

- outputs/final_competition_upgrade/FINAL_SUBMISSION_AUDIT.md
- outputs/final_competition_upgrade/CORRECTION_AUDIT_v3.md
- outputs/final_competition_upgrade/external_validation_national_20261006_r6/NATIONAL_EXTERNAL_VALIDATION.md
- outputs/final_competition_upgrade/external_validation_national_20261006_r6/external_profile_summary.csv
- outputs/final_competition_upgrade/geographic_confounding/GEOGRAPHIC_CONFOUNDING_REPORT.md
- outputs/final_competition_upgrade/story_data_v3/regional_generalization.json
- outputs/final_competition_upgrade/story_data_v3/external_prediction.json
- docs/public/METHODOLOGY.md and docs/ATLAS_REPRODUCTION.md

The repository URL requested by the user was also inspected:
https://github.com/resarytrew/cashless-demand-network-russia
Numeric display values come from local saved artifacts, not README prose.

## Reproduction and integrity

`python scripts/build_landing_evidence.py` copies selected saved records according
to configs/landing_evidence.yaml. It performs no statistical estimation. The new
site/data/evidence.json embeds input paths and SHA-256 hashes. Its deterministic
contract test reconciles every displayed median to existing site profiles and
verifies quartile ordering and exact source provenance.

The three existing site/data files remain byte-for-byte unchanged. No baseline,
configuration of a scientific run, clustering label or status was altered.
No historical output was overwritten and no research experiment was rerun.

Validation: 100 Python tests; 12 Playwright tests; scoped Ruff correctness gate.
The browser test explicitly checks equal hero position before/after the grouping
and subsequent release, as well as both external comparisons. The PDF now has
10 A4 pages and includes the metric definition and caveats in print. All pages
were rendered and visually reviewed. New media and evidence assets stage at both
root and /site aliases. No publication or push was performed.

The previously documented legacy freeze mismatch for verify.yml was not resealed
or presented as resolved by this presentation change.
