# Round 23 — Economic-mechanism hypothesis checks

## Scope

Seven user-proposed mechanisms were tested under the frozen YAML before results were inspected. This is an additive exploratory round. It does not retune L1, relabel A–G, or establish causality.

## Status summary

| hypothesis | status |
| --- | --- |
| H24_uncertainty_equals_economic_volatility | NOT_SUPPORTED_BY_FIXED_RULE |
| H25_marketplaces_replace_food_in_FG | NOT_SUPPORTED_BY_FIXED_RULE |
| H26_marketplaces_grow_where_initial_total_is_lower | SUPPORTED_AS_ASSOCIATION_ONLY |
| H27_same_income_population_different_profiles_different_baskets | SUPPORTED_DESCRIPTIVELY |
| H28_digital_convergence_without_level_convergence | NOT_SUPPORTED_BY_FIXED_RULE |
| H29_distant_network_twins | DESCRIPTIVE_RESULT_NO_INFERENTIAL_RULE |
| H30_food_share_inflation_pressure | NOT_SUPPORTED_BY_FIXED_RULE |

## H24 — Atlas uncertainty and economic volatility

| metric | atlas_state | N | mean | median | q25 | q75 |
| --- | --- | --- | --- | --- | --- | --- |
| total_volatility | stable_core | 824 | 0.097175 | 0.096512 | 0.087997 | 0.105563 |
| total_volatility | expansive_core | 374 | 0.085821 | 0.078005 | 0.072030 | 0.086339 |
| total_volatility | transition | 388 | 0.091482 | 0.088020 | 0.079706 | 0.099591 |
| total_volatility | unresolved | 318 | 0.087152 | 0.085148 | 0.077894 | 0.094343 |
| composition_volatility | stable_core | 824 | 0.109319 | 0.101204 | 0.083720 | 0.124910 |
| composition_volatility | expansive_core | 374 | 0.066632 | 0.056225 | 0.050847 | 0.063772 |
| composition_volatility | transition | 388 | 0.076742 | 0.068842 | 0.062110 | 0.081760 |
| composition_volatility | unresolved | 318 | 0.080539 | 0.074432 | 0.054795 | 0.090574 |

Adjusted association after mean log Total, reference profile and region controls:

| metric | N | partial_R2_atlas_state | permutation_p | controls |
| --- | --- | --- | --- | --- |
| total_volatility | 1898 | 0.006150 | 0.030200 | mean_log_total+profile+region |
| composition_volatility | 1898 | 0.011963 | 0.000400 | mean_log_total+profile+region |

Pairwise tests are Holm-adjusted in `uncertainty_volatility_pairwise.csv`. Atlas classes are methodological diagnostics; association with observed volatility does not prove that uncertainty is economic rather than algorithmic.

## H25 — Marketplace/Food substitution

| group | N | spearman_rho | p_holm | mean_delta_marketplace_share | mean_delta_food_share | mean_delta_log_marketplace_food_ratio |
| --- | --- | --- | --- | --- | --- | --- |
| FG | 1292 | -0.397538 | 0.000000 | 0.043549 | -0.038873 | 0.337952 |
| BD | 251 | -0.518162 | 0.000000 | 0.023294 | -0.021178 | 0.217603 |
| B | 98 | -0.245924 | 0.043952 | 0.015116 | -0.018516 | 0.171598 |
| D | 153 | -0.451141 | 0.000000 | 0.028532 | -0.022883 | 0.247070 |
| F | 327 | -0.303233 | 0.000000 | 0.036694 | -0.033196 | 0.323547 |
| G | 965 | -0.383261 | 0.000000 | 0.045872 | -0.040797 | 0.342833 |

FG-minus-BD correlation contrast: 0.1206; one-sided permutation p=0.9844. A negative closed-composition correlation cannot identify grocery purchases through marketplaces; transaction merchant taxonomy would be required.

## H26 — Marketplace growth and initial Total

| group | N | spearman_rho | p_holm |
| --- | --- | --- | --- |
| ALL | 1899 | -0.522794 | 0.000000 |
| A | 141 | -0.283428 | 0.005940 |
| B | 98 | -0.470658 | 0.000014 |
| C | 29 | -0.350739 | 0.186350 |
| D | 153 | -0.236137 | 0.019784 |
| E | 186 | -0.587220 | 0.000000 |
| F | 327 | -0.132937 | 0.080774 |
| G | 965 | -0.159428 | 0.000010 |

| N | log_total_coefficient | HC3_se | HC3_p | partial_R2_log_total | within_profile_permutation_p | controls |
| --- | --- | --- | --- | --- | --- | --- |
| 1898 | -0.030125 | 0.004303 | 0.000000 | 0.039462 | 0.000200 | baseline_marketplace_share+profile+region |

The association cannot by itself establish absent local retail; baseline share, region and profile are controlled only observationally.

## H27 — Wage/population matched municipalities

| cross_profile_pairs | same_profile_control_pairs | cross_profile_median_aitchison | same_profile_median_aitchison | median_difference | bootstrap_ci_low | bootstrap_ci_high | bootstrap_one_sided_p |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 441.000000 | 807.000000 | 0.650199 | 0.511639 | 0.138560 | 0.091469 | 0.193267 | 0.000200 |

Selected examples use a declared rule, not manual curation:

| municipality_a | profile_a | municipality_b | profile_b | wage_relative_difference | population_relative_difference | aitchison_dec2024 |
| --- | --- | --- | --- | --- | --- | --- |
| Барун-Хемчикский муниципальный район | C | Залегощенский муниципальный район | G | 0.0060 | 0.0084 | 2.1581 |
| Нижнеколымский муниципальный район | A | Шимановский муниципальный округ | F | 0.0188 | 0.1804 | 2.1208 |
| Варгашинский муниципальный округ | G | Тандинский муниципальный район | A | 0.0024 | 0.0253 | 1.9732 |
| Булунский муниципальный район | A | внутригородская территория города федерального значения поселок Песочный | E | 0.0009 | 0.1937 | 1.8358 |
| Варнавинский муниципальный округ | G | муниципальный округ Струго-Красненский | F | 0.0044 | 0.0195 | 1.6390 |
| Большеулуйский муниципальный район | G | внутригородская территория города федерального значения поселок Лисий Нос | E | 0.0723 | 0.0262 | 1.5075 |
| внутригородская территория города федерального значения муниципальный округ Красненькая речка | E | городской округ Партизанский | F | 0.0041 | 0.0214 | 1.2986 |
| Эвенкийский муниципальный район | A | внутригородская территория города федерального значения муниципальный округ Посадский | B | 0.0356 | 0.1742 | 1.2949 |
| Камышловский муниципальный район | D | муниципальный округ Старицкий | G | 0.0024 | 0.0144 | 1.2687 |
| Могочинский муниципальный округ | F | внутригородская территория города федерального значения муниципальный округ Лиговка-Ямская | B | 0.0021 | 0.0662 | 1.1970 |

These pairs illustrate conditional differences; they do not isolate income causally and wages are not household income.

## H28 — Digital convergence without level convergence

| metric | theil_sen_slope | bootstrap_ci_low | bootstrap_ci_high | start | end |
| --- | --- | --- | --- | --- | --- |
| marketplace_share_sd | 0.000789 | 0.000665 | 0.000899 | 0.018376 | 0.037515 |
| mean_log_total_sd | 0.000346 | 0.000174 | 0.000573 | 0.333786 | 0.349410 |

`Total` is nominal and its denominator is unresolved. The calculation concerns dispersion in mean log Total, not welfare.

## H29 — Geographically distant network neighbors

| selection | pairs | median_km | share_above_500km | share_above_1000km | nodes_with_fewer_than_3_graph_neighbors |
| --- | --- | --- | --- | --- | --- |
| directed_top3 | 5614 | 544.2978 | 0.5230 | 0.3267 | 62 |
| unique_pairs | 3956 | 564.7823 | 0.5331 | 0.3319 | 62 |

| municipality | profile | neighbor | neighbor_profile | feature_distance | geographic_km |
| --- | --- | --- | --- | --- | --- |
| городской округ город Стрежевой | A | муниципальный район Печора | A | 0.062 | 1122.446 |
| городской округ город Курган | D | городской округ город Усолье-Сибирское | D | 0.062 | 2480.341 |
| Сухобузимский муниципальный район | G | муниципальный округ Гайнский | G | 0.066 | 2328.170 |
| Кондопожский муниципальный район | F | городской округ Нижняя Салда | F | 0.080 | 1553.715 |
| городской округ Тавдинский | F | городской округ город Бородино | G | 0.094 | 1790.511 |
| городской округ Чайковский | F | городской округ город Новоалтайск | D | 0.100 | 1901.446 |
| городской округ город Тюмень | D | внутригородская территория города федерального значения муниципальный округ Пороховые | E | 0.108 | 2032.683 |
| городской округ город Архангельск | A | городской округ город Тобольск | D | 0.125 | 1624.835 |
| Лужский муниципальный район | E | городской округ город Урай | A | 0.146 | 1965.427 |
| городской округ город Мурманск | E | городской округ Дубна | E | 0.154 | 1374.690 |

Representative-point distance is descriptive and does not mean the territories are economically identical.

## H30 — Food-share change by profile

| profile | N | mean_change | median_change | mean_ci_low | mean_ci_high | p_holm |
| --- | --- | --- | --- | --- | --- | --- |
| A | 141 | -0.024897 | -0.026164 | -0.027959 | -0.021660 | 0.000000 |
| B | 98 | -0.018516 | -0.017721 | -0.019516 | -0.017552 | 0.000000 |
| C | 29 | -0.017453 | -0.018942 | -0.027953 | -0.006761 | 0.010532 |
| D | 153 | -0.022883 | -0.022059 | -0.023960 | -0.021819 | 0.000000 |
| E | 186 | -0.019355 | -0.019265 | -0.020205 | -0.018533 | 0.000000 |
| F | 327 | -0.033196 | -0.032414 | -0.034923 | -0.031449 | 0.000000 |
| G | 965 | -0.040797 | -0.039718 | -0.042165 | -0.039442 | 0.000000 |

This tests basket-share movement, not inflation. No price index, real expenditure, quantity, or household-income measure enters the analysis.

## Reproducibility

The fresh baseline gate reproduced full supra, temporal December and static December labels at ARI=NMI=1. Config, municipality-level results, exact pairs, figures, manifest, final hash gate and checksums are saved with this report.
