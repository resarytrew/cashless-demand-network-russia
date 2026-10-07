# Results

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

Для reference Louvain static December: SW=.170, CH=875.215, CH/N=.460, S_Dbw=.829, AVI=.907, AVU=.506, MQ=.767. Сравнение одинаковой feature geometry для Louvain, Greedy, Spectral, KMeans и Ward находится в `outputs/presubmission_upgrade/icvi/canonical_icvi.csv`; показатели не применялись для выбора алгоритма.

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
