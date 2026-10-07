# ICVI v2: определения и границы сопоставимости

| Метрика | Семейство | Определение | Направление |
|---|---|---|---:|
| SW | attribute | mean Euclidean silhouette | ↑ |
| CH | attribute | Calinski–Harabasz variance ratio | ↑ |
| S_Dbw | attribute | documented repository Halkidi–Vazirgiannis variant | ↓ |
| AVI | graph | weighted adjacency share | ↑ |
| AVU | graph | weighted adjacency overlap | ↓ |
| ANUI | graph | combined AVI/AVU diagnostic | ↑ |
| MQ | graph | TurboMQ / Modularization Quality | ↑ |
| Q | graph | weighted Newman–Girvan modularity | ↑ |

ICVI v2 оценивает только уже заданные разбиения. Эти метрики не используются для выбора representation, K, k, graph rule, resolution или алгоритма. Канонические числа находятся в `outputs/final_competition_upgrade/icvi_v2/`.

## Graph ICVI

Для неориентированного weighted graph строится симметричная block matrix

`S[i,j] = sum(weight(u,v))`,

где каждое ребро добавляется в обе ячейки `[i,j]` и `[j,i]`. Поэтому `S[i,i]` дважды учитывает вес внутренних рёбер. При отсутствии атрибута `weight` используется 1; нечисловые, отрицательные и бесконечные веса запрещены.

Для сообщества `i`:

- `AVI_i = S[i,i] / sum_j S[i,j]`; сообщество с нулевой силой вносит 0, итоговый AVI — среднее по сообществам;
- `out_i = sum_j S[i,j] - S[i,i]`;
- для `j != i`, `AVU_ij = S[i,j] / (out_i + in_j - S[i,j])`, а нулевой знаменатель даёт 0; `AVU = sum_i(sum_j!=i AVU_ij) / K`;
- `ANUI = 1 / (AVU + 1/AVI)`, если `AVI != 0`, иначе 0.

`AVI_unweighted` и `AVU_unweighted` сохраняют прежние block-count definitions только как legacy diagnostics. Они не подменяют weighted AVI/AVU.

### MQ и Q — разные показатели

В ICVI v2 `MQ` — это TurboMQ. Для сообщества:

- `mu_i = S[i,i] / 2`;
- `epsilon_i = sum_j S[i,j] - S[i,i]`;
- `CF_i = mu_i / (mu_i + 0.5 * epsilon_i)` при наличии связей, иначе 0;
- `MQ = sum_i CF_i`.

TurboMQ не ограничен диапазоном `[0,1]`. Для `K` хорошо связанных сообществ без межкластерных рёбер `MQ = K`.

`Q` — weighted Newman–Girvan modularity при `resolution=1.0`, рассчитанная `networkx.community.modularity`. MQ и Q имеют разные null/normalization conventions и разные шкалы; сравнивать их значения напрямую нельзя.

Исторические таблицы до v2 не переписаны. В них поле `MQ` означало weighted Newman–Girvan Q. В API это явно сохранено как `legacy_MQ_newman_girvan`, а старый `evaluate_partition` оставлен без изменения.

## S_Dbw

Используется текущий repository canonical variant формулы Halkidi–Vazirgiannis (2001):

- `S_Dbw = Scat + Dens_bw`;
- дисперсия — coordinatewise population standard deviation (`ddof=0`);
- `Scat` — средняя норма внутрикластерной дисперсии, делённая на норму глобальной дисперсии;
- общий radius — среднее норм внутрикластерных дисперсий;
- density считается внутри замкнутого евклидова шара;
- midpoint density использует точки только рассматриваемой пары кластеров;
- `0/0` для pair density трактуется как 0, `positive/0` получает явный undefined status.

Формула и тесты не менялись в ICVI v2. В репозитории не найдено отдельного официального competition/rubric определения S_Dbw, поэтому численная тождественность с любой внешней реализацией не заявляется.

## Почему ICVI разных исследований нельзя сравнивать напрямую

Значения ICVI нельзя напрямую сопоставлять между проектами, если различаются:

- graph construction и sparsification;
- edge weights;
- feature representation и distance geometry;
- K и N;
- time slice;
- partition algorithm;
- точная реализация метрики и её zero/undefined conventions.

Особенно нельзя сопоставлять TurboMQ с Newman–Girvan Q или weighted AVI/AVU с их unweighted legacy-версиями. ICVI v2 не утверждает, что reference configuration «лучше» другой конфигурации.

## Reproduction

```powershell
$env:PYTHONPATH='src'
python scripts/run_icvi_v2.py --config configs/icvi_v2.yaml
```

Runner отказывается перезаписывать output. Перед расчётом он требует точный baseline reproduction gate, сверяет v1-метрики пяти сохранённых fixed partitions со старой canonical table и сверяет все десять воспроизведённых edge-grid rows с исторической v3 table. Mutual-k20 дополнительно обязан иметь ARI=NMI=1 относительно baseline partition.
