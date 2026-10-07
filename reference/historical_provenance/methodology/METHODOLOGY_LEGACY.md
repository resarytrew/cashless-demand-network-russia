# Методология

## Объект

Исследуются профили локального **безналичного потребительского спроса**, а не универсальные типы локальной экономики.

## Strict panel

- 24 месяца;
- Total + 5 выбранных категорий;
- неоднозначные текстовые названия исключаются;
- полная история обязательна.

Reference panel текущего исследования: 1904 МО.

## Composition

Шесть частей:

1. Продовольствие
2. Здоровье
3. Общественное питание
4. Маркетплейсы
5. Транспорт
6. Прочее = Total − сумма пяти категорий

Используется CLR.

## Spending level

Для каждого месяца:

```text
z = (log(Total) - median(log(Total))) / (1.4826 * MAD(log(Total)))
```

## Combined representation

Reference:

```text
X = [sqrt(0.7) * CLR / median_pair_distance_CLR,
     sqrt(0.3) * level_z / median_pair_distance_level]
```

70/30 — reference specification, а не статистический optimum.

## Monthly network

- mutual-kNN;
- baseline k=20;
- adaptive RBF edge weights;
- static Dec graph: isolate fallback включён;
- temporal monthly layers: isolate fallback выключен.

## Temporal coupling

Одна территория соединяется с собой в соседнем месяце.

```text
temporal_weight = omega * global_median(intralayer_edge_weights)
```

Reference omega=2.

## Community detection

- NetworkX Louvain;
- resolution=0.5;
- seed=0.

Все содержательные выводы должны сопровождаться sensitivity analysis.
