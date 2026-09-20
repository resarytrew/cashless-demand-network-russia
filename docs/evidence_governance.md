# Evidence governance

Round-by-round текст не является источником истины.

Источник истины:

1. config;
2. output artifacts;
3. master evidence matrix;
4. claims ledger.

## Новый material test

Любой новый тест должен:

1. получить отдельный YAML / test ID;
2. сохранить отдельный output;
3. получить run manifest;
4. сравниваться с baseline;
5. пометить зависимые claims как требующие пересмотра;
6. обновить master evidence matrix;
7. только после этого изменить narrative.

## Запрещено

- перезаписывать baseline;
- менять старый config после просмотра результата;
- удалять неудобные robustness-runs;
- называть post-hoc решение preregistered.

## Версионирование evidence

- MAJOR — изменилась общая онтология/headline;
- MINOR — изменился статус значимого профиля/claim;
- PATCH — исправление отчётности без изменения evidence.
