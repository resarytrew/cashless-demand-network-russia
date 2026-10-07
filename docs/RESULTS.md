# Results

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

At reference omega=2, 85.3% of municipalities have no more than two profile changes in 24 months. Sensitivity shows that persistence depends strongly on regularisation. A preregistered synthetic ground-truth benchmark therefore reports partition, event and delay trade-offs on six controlled scenarios; it does not select a new historical omega. See `outputs/final_competition_upgrade/synthetic_temporal_v3/SYNTHETIC_TEMPORAL_REPORT.md`.

## Robustness and remaining uncertainty

ICVI, representation, edge, algorithm and perturbation results remain separate evidence families. Exact boundaries are specification-dependent, regional/external tests remain observational and exploratory, and no causal claim follows from these associations.
