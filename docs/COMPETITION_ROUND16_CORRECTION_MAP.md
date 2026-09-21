# Competition text correction map

The original `reference/round16/competition_source.docx` is preserved unchanged.
This map identifies replacements for a later document edit; it does not claim that the
DOCX has already been rewritten or layout-verified.

| Location in source | Required correction / canonical source |
|---|---|
| Tables 2–3: distance families and algorithms | Use only `outputs/round16_benchmark/canonical_method_benchmark.csv`; retain a missing-provenance note instead of old numerical rows for cosine/correlation/lagged correlation/DTW. Algorithm metadata and the full numerical diff accompany the CSV. |
| Table 5: December profiles | Replace with `outputs/round16_competition/figure_A_profile_matrix.csv`; includes Health, level_z, Total and all six calculated shares. Individual column medians need not sum to one. |
| Temporal methods and stability | Use `docs/TEMPORAL_MODEL_SPECIFICATION.md`. Global supra null model; ordinary modularity, not classical multislice. State omega2/gamma.5 with 1624/1904<=2 switches. Add retrospective/future-layer qualification. |
| Perturbation section | Separate20 optimizer-only,20 graph-only and50 combined runs; use `perturbation_decomposition_summary.csv`. Do not attribute all variability to edge perturbation. |
| Collapse disclosure | Add seed24/39 original and fixed-seed results from `perturbation_collapse_cases.csv`, plus precision/Jaccard and Figure C. No outlier deletion. |
| Resolution sensitivity | Add four-gamma table and A–G ranges; no best gamma or ICVI ranking. |
| Data and socioeconomic wording | Use `docs/DATA_PASSPORT.md`: denominator and category additivity unconfirmed; replace “total municipal volume” with “published Total indicator”. Do not infer income or per-capita expenditure. |
| Controls and reproducibility | Attach the contextual matrix; label missing-input control families historical-only. The original summaries are not newly verified by Round16. |
| B subtype | Use `B_WITHIN_FEDERAL_INTRACITY_PROFILE.csv` (98 versus142). Descriptive Cliff deltas; no fabricated historical p-values. Transport shows little separation. |
| Three cases | Use case CSV,24-month companion and analog table. Third E example is provisional pending individual controls; regions/covariates remain unavailable. Do not describe it as a confirmed context-sensitive territory. |
| Evidence statuses | Use `archetype_status_round16.csv`, unchanged from Round15; read exact-boundary limitations alongside statuses. |
| Practical claims | Peer comparison and prioritization are potential decision support; predictive/monitoring gains are not tested. Expanding-window backtest is future work. |

Figure-ready pairs: A profile heatmap; B retention/precision/Jaccard distributions;
C all50 December ARI/largest-share trajectories highlighting24/39; D four pair distributions;
E three municipal small multiples (third provisional). All PNGs and SVGs are in
`outputs/round16_competition`, with CSV data. No new scientific status is encoded by color.
