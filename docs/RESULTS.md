# Results

## Round23 — exploratory economic-mechanism checks

Семь заранее заданных механизмов проверены на frozen A–G/Atlas inputs. Связь
`Atlas uncertainty → более высокая экономическая volatility` не получила
ожидаемого порядка: stable core имеет более высокие медианы `sd(Δlog Total)` и
multivariate `sd(ΔCLR)`, чем transition и unresolved. После mean-level,
profile и region controls Atlas state объясняет лишь .0061/.0120 partial R².

Marketplace share растёт быстрее при более низком Dec-2023 Total (`ρ=-.5228`;
adjusted partial R²=.0395, permutation p=.0002), но это наблюдательная связь, не
доказательство отсутствующей локальной торговли. Marketplace–Food correlations
отрицательны в F/G (`ρ=-.3975`) и B/D (`ρ=-.5182`); заявленная специфичность F/G
не поддержана. Межпрофильная дисперсия Marketplace share выросла .0184→.0375,
то есть ожидаемая digital convergence отвергается на этой метрике.

441 cross-profile wage/population-matched pairs имеют median Aitchison distance
.6502 против .5116 у 807 same-profile controls (bootstrap difference CI
.0915–.1933). У top-3 graph neighbors median geographic distance 544 km, 52.3%
выше 500 km. Food share Dec-to-Dec снизилась во всех A–G, сильнее в F/G; это не
инфляционный тест. Референс и статусы A–G не меняются.

## Round22 — attributed-network method benchmark

При фиксированном `K=9` clean-room KEFRiNc на тех же December L1-признаках и
том же reference-графе имеет ARI=.3080, NMI=.4797 и VI=3.1374 bits к static
Louvain. Pairwise seed ARI для seeds 0–9: mean=.5213, min=.3996, max=.7143.
Это показывает material method-class и optimization dependence, а не победу
одного метода.

После глобального alignment с temporal December disagreement составляет 492/824
(59,7%) для stable core, 263/388 (67,8%) для transition и 268/318 (84,3%) для
unresolved. Atlas uncertainty переносится на held-out algorithm family только
частично: transition хуже stable на 8,1 п.п., но абсолютное расхождение stable
core само по себе велико. Сильное broad reproduction across method class не
поддержано. Внешние adjusted partial R² KEFRiN-групп равны .1360 для wage,
.0747 для employment и .0371 для sector CLR (permutation p=.0005); это
post-label observational interpretation, не model selection.

Reference network derived from the same attributes, поэтому Round22 не является
independent information fusion. L1, A–G, Atlas и legacy statuses не менялись.

## Round21 — structural sensitivity and adjusted validation

`ω=2 → 1` даёт December ARI=0,407 и NMI=0,555, но structural decomposition
показывает преимущественное огрубление: micro purity=0,9785, fine-pair
retention=0,9827, coarse precision=0,4888, H(ω1|ω2)=0,1303 и
H(ω2|ω1)=1,2874 бит. При matched K=10 (resolution=0,8) ARI=0,647;
B/E merge сохраняется, C/D/F/G merge — нет. Exact boundaries зависят и от
interaction omega×resolution.

Omega отсутствовала во входных семействах Atlas. На этой независимой оси
чувствительности изменились 1/824 stable core, 247/374 expansive core и 348/388
transition. Это held-out sensitivity check, не статистическое out-of-sample
предсказание. После size/region controls partial R² равны 0,176 для wage, 0,214
для employment total и 0,036 для 15-мерной sector CLR; permutation p=0,0005.

Post-hoc внешние контрасты показывают различия B/E и всех пар D/F/G по scalar и
sector данным: огрубление `ω=1` стирает часть независимо наблюдаемой экономической
неоднородности, но не доказывает истинность `ω=2`. Обе block-balanced L2
sensitivity materially differ from original L2 (ARI=0,035 и 0,177; edge Jaccard
≈0,43). Original L2 не изменена и остаётся specification-dependent.

## Типы локальной потребительской экономики

Reference-анализ 1 904 муниципалитетов за 24 месяца выделяет семь обозначенных A–G профилей как ориентиры сравнения. Это сочетания уровня и структуры наблюдаемого безналичного потребительского спроса, а не полная производственная типология территории. Их размеры, медианы и признаки сохранены в `outputs/presubmission_upgrade/economic_typology/profile_summary.csv`.

## Устойчивые и переходные области

Устойчивость неоднородна. G имеет широкое ядро, A содержит устойчивые области с overlap caveat, B/E требуют предварительной интерпретации, C остаётся неразрешённым вне контекста. F — переходная область между D и G: все 327 reference F в Atlas имеют класс `transition`. Exact boundaries не следует выдавать за одинаково устойчивые.

## Временная динамика

При reference omega=2 85.3% муниципалитетов имеют не более двух смен метки. Это joint effect similarity и temporal regularization. При omega=.25 эта доля составляет 0.05%, при omega=4 — 88.8%, а full-supra ARI относительно omega=2 равен .471. Поэтому редкие смены не являются самостоятельным доказательством стабильности экономики.

## Полный ICVI

Для reference Louvain static December в текущем ICVI v2: SW=.170,
CH=875.215, CH/N=.460, S_Dbw=.829, weighted AVI=.916, weighted AVU=.505,
ANUI=.626, TurboMQ=8.245 и weighted Newman–Girvan Q=.767. Сравнение одной
feature geometry для Louvain, Greedy, Spectral, KMeans и Ward находится в
`outputs/final_competition_upgrade/icvi_v2/canonical_icvi_v2.csv`; показатели
не применялись для выбора алгоритма. Историческая таблица v1 сохранена, но её
поле `MQ` означало Newman–Girvan Q, а AVI/AVU были невзвешенными, поэтому её
нельзя подменять текущей таблицей.

## Проверка без `Other`

Round18 сравнивает две заранее объявленные альтернативы с reference. Temporal December R1 (five-part CLR) даёт ARI=.822/NMI=.764, R2 (observed log-levels) — ARI=.708/NMI=.649. Следовательно, основные broad patterns можно сопоставлять, но exact partition materially depends on representation; отрицательный результат не скрывается. Полные overlap и ICVI — в `outputs/round18_representation/`.

## Внешняя интерпретация и неопределённость

Round17 сохраняет 58 exact matches в четырёх регионах и не использовался при кластеризации. B/E в этой выборке отсутствуют; D/F/G представлены слишком малым числом случаев для национальных выводов. Для A ограниченно поддержана wage/investment interpretation с явно заданным scope; mining mechanism не установлен. См. `outputs/round17_external_validation/` и Round17 audit.
# Results — current competition synthesis

## Typology

The reference result is a typology of local cashless consumer-demand profiles, not a universal classification of local economies. Human-readable labels, technical A–G labels, bounded statuses, and their evidence are in [the naming audit](PROFILE_NAMING_AUDIT.md). F remains a transition profile; B/E are preliminary; C is unresolved.

## National independent validation

Population, wage, and employment were not used in network construction. After labels were frozen, 1,903 municipalities were available for population and 1,890 for wage/employment. Exploratory effect sizes are population ε²=.468, wage ε²=.633, and employment ε²=.516. The full provenance, coverage, and limitations are in `outputs/final_competition_upgrade/external_validation_national_20261006_r6/`.

## D/F/G transition and regional generalisation

D, F and G preserve the descriptive D > F > G ordering for wage, population and employment in the national external layer. This does not establish stable exact boundaries. Region-held-out CV still carries signal (logistic macro-F1=.549; RF=.551), while its performance is lower than ordinary stratified CV; within-region effects remain material but smaller. See `outputs/final_competition_upgrade/geographic_confounding/`.

## External predictability

With stratified folds and fold-contained imputation/scaling, logistic macro-F1 is .592 and RF macro-F1 is .647; the label-permuted diagnostic has mean macro-F1 about .091. These are post-hoc association diagnostics, not deployment claims.

## Temporal dynamics and synthetic calibration

At reference omega=2, 85.3% of municipalities have no more than two profile changes in 24 months. Sensitivity shows that persistence depends strongly on regularisation. A corrective synthetic benchmark v4 reports monthwise partition, event and delay trade-offs on six controlled scenarios; it does not select a new historical omega. Across all scenarios, mean monthly ARI rises from .880 at omega=0 to .897 at omega=2 and .912 at omega=4, while transition-scenario switch F1 falls from .520 to .388 and .275 respectively. In the mixed scenario at omega=2, node-state accuracy is .942 but switch F1 is .246: accurate current-state recovery is not equivalent to accurate event detection. See `outputs/final_competition_upgrade/synthetic_temporal_v4/SYNTHETIC_TEMPORAL_REPORT.md`.

## Robustness and remaining uncertainty

ICVI, representation, edge, algorithm and perturbation results remain separate evidence families. Exact boundaries are specification-dependent, regional/external tests remain observational and exploratory, and no causal claim follows from these associations.
