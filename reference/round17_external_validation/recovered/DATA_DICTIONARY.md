# Data dictionary

`external_validation_58.csv` contains the 58-municipality external validation sample.

- `profile`: reference A–G profile from the project.
- `consensus`: Stability Atlas v2.2.1 consensus class. It is a descriptive affinity class, not a posterior probability.
- `stability_class`: current Atlas v2.2.1 class (`stable_core`, `expansive_core`, `transition`, `unresolved`).
- `population_2024`: permanent population on 1 January 2024.
- `urban_population_2024`: urban population on 1 January 2024.
- `urban_share_2024`: urban_population_2024 / population_2024.
- `salary_2024`, `salary_2025`: average monthly nominal accrued wage of employees of large and medium enterprises and non-profit organizations, where supplied by the regional Rosstat source.
- `investment_per_capita_2024`: investment in fixed capital excluding budget funds per capita. Available for the Yakutia subset only; missing elsewhere by design.
- `workers_2024`: average number of employees in surveyed organizations; used only for Republic Altai descriptive context.
- `oktmo_2024`: period-aware 2024 OKTMO identifier from the project crosswalk.

Missing values are deliberate. No cross-region imputation is performed.
