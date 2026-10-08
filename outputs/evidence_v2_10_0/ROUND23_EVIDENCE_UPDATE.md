# Evidence v2.10.0 — Round23 economic-mechanism checks

Round23 adds seven fixed exploratory diagnostics over frozen L1/A–G/Atlas inputs. It does not alter the reference specification or any legacy profile status.

The exact claim-level statuses are:

| hypothesis | status |
| --- | --- |
| H24_uncertainty_equals_economic_volatility | NOT_SUPPORTED_BY_FIXED_RULE |
| H25_marketplaces_replace_food_in_FG | NOT_SUPPORTED_BY_FIXED_RULE |
| H26_marketplaces_grow_where_initial_total_is_lower | SUPPORTED_AS_ASSOCIATION_ONLY |
| H27_same_income_population_different_profiles_different_baskets | SUPPORTED_DESCRIPTIVELY |
| H28_digital_convergence_without_level_convergence | NOT_SUPPORTED_BY_FIXED_RULE |
| H29_distant_network_twins | DESCRIPTIVE_RESULT_NO_INFERENTIAL_RULE |
| H30_food_share_inflation_pressure | NOT_SUPPORTED_BY_FIXED_RULE |

All marketplace, matching and volatility results remain observational. Closed-composition correlations cannot identify purchases of groceries through marketplaces. Nominal Total is not welfare, and Food-share changes are not inflation without prices/quantities. Distant graph neighbors are analogues in the fixed demand-feature graph, not universal economic twins.

Machine-readable statistics are in `outputs/round23_economic_mechanisms/round23_summary.json`; raw tables and figures are preserved beside it. Baseline and final frozen-input gates passed. A–G statuses remain unchanged.
