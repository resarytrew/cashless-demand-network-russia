# ICVI v2 audit

## Что обнаружено

Предыдущий canonical ICVI layer использовал поле MQ для weighted Newman–Girvan modularity. AVI/AVU считались по unweighted adjacency blocks.

## Почему это важно

MQ является неоднозначным сокращением. В reporting v2 MQ означает TurboMQ, Q означает weighted Newman–Girvan modularity, а AVI/AVU используют weighted adjacency.

## Что исправлено

Добавлены отдельные weighted block matrix, AVI, AVU, ANUI, TurboMQ и Q. Legacy AVI/AVU публикуются как `AVI_unweighted`/`AVU_unweighted`; историческое значение MQ доступно программно как `legacy_MQ_newman_girvan`. Все пять fixed method partitions прочитаны из сохранённых labels. Edge-grid был детерминированно воспроизведён, потому что его labels отдельно не сохранялись; каждая строка прошла gate против исторической v3-таблицы.

## Что НЕ изменено

Data, features, graph definitions, fixed labels, clustering methods, baseline, A–G, temporal model, omega=2, resolution=0.5 и scientific statuses не изменены. Новые метрики не использовались для выбора K, k, graph rule или метода.

## Historical compatibility

Старые CSV сохранены без изменений. В них `historical MQ column = Newman–Girvan Q`. Старый `evaluate_partition` оставлен как legacy v1 API; новый слой реализован отдельными `weighted_graph_icvi` и `evaluate_partition_v2`.

## S_Dbw

Формула не менялась: repository canonical variant — Halkidi–Vazirgiannis (2001) `Scat + Dens_bw`, coordinatewise population standard deviations, общий radius как среднее норм дисперсий, density в замкнутом евклидовом шаре и midpoint density только по двум рассматриваемым кластерам. Конвенция 0/0→0 и positive/0→undefined документирована в коде. Отдельного competition/rubric определения S_Dbw в репозитории не найдено; поэтому межреализационная численная эквивалентность не заявляется. Внутреннего unresolved discrepancy нет.

## Scientific consequence

Новые значения graph ICVI меняют обозначения и определения сетевых validity metrics, но не меняют partitions. TurboMQ и Q имеют разные шкалы; TurboMQ может превышать 1 и не сравнивается численно с Q.
