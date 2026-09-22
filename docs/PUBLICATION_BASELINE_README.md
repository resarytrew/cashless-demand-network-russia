# Сетевая структура локального безналичного потребительского спроса

*Network Structure of Local Cashless Consumer Demand across Russian Municipalities*

## Текущая версия

[Состояние проекта](docs/CURRENT_STATE.json) · [Инженерный аудит](docs/ENGINEERING_HARDENING_20260922.md) ·
[Воспроизведение Atlas](docs/ATLAS_REPRODUCTION.md) · [Atlas CSV](outputs/stability_atlas_v2_2_1/municipality_affinity_atlas.csv).

Evidence v2.4.0 добавляет независимый Round17; прежние статусы устойчивости A–G сохранены. Atlas v2.2.1 добавляет защиту входов и outputs, YAML,
полный manifest и автономный `index.html`; научные статусы не изменены.
Скачайте папку `outputs/stability_atlas_v2_2_1` и откройте `index.html` для поиска
муниципалитета и просмотра неопределённости. Affinity shares — описательные меры,
не вероятности принадлежности. Проверка текущей версии:
`python scripts/verify_current_artifacts.py`.

## Independent economic validation

Round17: 58 муниципалитетов в 4 регионах, 58/58 совпадений с текущим Atlas.
Воспроизведены региональный D–F–G градиент Алтая и связь зарплаты с инвестициями
в якутской подвыборке A. Выборка ограничена: Алтай n=6, F=1; после поправок
p=0.088869. Хабаровский A/G результат остаётся неопределённым (p=0.279853).
B–E поддерживается внутренними данными, но внешних наблюдений нет; C остаётся
контекстным/неразрешённым. Зарплата не равна доходам населения; добывающий механизм A не установлен.

В пространстве локального безналичного спроса наблюдаются режимы неодинаковой
устойчивости: устойчивые ядра, переходные, вложенные и контекстные области.
Внешние данные согласуются с частью этой структуры в отдельных регионах;
оснований для семи равноправных универсальных экономических архетипов нет.

[Отчёт Round17](outputs/round17_external_validation/INDEPENDENT_ECONOMIC_VALIDATION.md) ·
[Происхождение и ограничения](outputs/round17_external_validation/RECOVERY_AUDIT.md) ·
[Воспроизведение](docs/ROUND17_REPRODUCTION.md) ·
[План Round18 — ещё не выполнен](docs/ROUND18_REPRESENTATION_ROBUSTNESS_PLAN.md).

## Round 16 — pre-submission audit

[Итоговый аудит](outputs/round16_evidence/ROUND16_FINAL_PRESUBMISSION_AUDIT.md) ·
[Canonical benchmark](outputs/round16_benchmark/canonical_method_benchmark.csv) ·
[Evidence v2.3.0](outputs/round16_evidence/MASTER_PROFILE_EVIDENCE_MATRIX_v2.3.0.csv) ·
[Карта исправлений DOCX](docs/COMPETITION_ROUND16_CORRECTION_MAP.md).

Свежий baseline: все шесть ARI/NMI=1; признаки и графы совпали побитово.
Выполнены20 optimizer-only и20 graph-only runs, повторно использованы50 combined runs,
проверены gamma=.25/.5/.75/1.0. Collapse seeds24/39 сохраняется при optimizer seed0.
Статусы A–G не изменены. Единственный источник чисел сравнительных таблиц методов —
`outputs/round16_benchmark/canonical_method_benchmark.csv`; четыре невосстановленные
исторические distance families помечены явно, без старых чисел.

**Полная приёмка Round16 пока не закрыта:** отсутствуют исходные contextual joins/controls
для подтверждения третьего муниципального кейса и его региона/ковариат. B within-stratum
восстановлен описательно; исторические p-values недоступны. Знаменатель Total и аддитивность
категорий не установлены из доступных официальных метаданных.
[Data passport](docs/DATA_PASSPORT.md) · [Temporal objective](docs/TEMPORAL_MODEL_SPECIFICATION.md) ·
[Contextual scope](outputs/round16_evidence/CONTEXTUAL_EVIDENCE_REPRODUCIBILITY_MATRIX.csv).

Графики PNG/SVG и исходные CSV: [competition artifacts](outputs/round16_competition/).
Исходный DOCX сохранён; обновлённый DOCX не заявляется как готовый артефакт.

### Проверка и новые воспроизведения Round16

PowerShell, из корня репозитория:

```powershell
$env:PYTHONPATH = 'src;.;scripts'
$env:PYTHONUTF8 = '1'
python -m pytest -q
python scripts/verify_current_artifacts.py
```

Новый verifier проверяет старые390 frozen files, причём три изменённых инженерных модуля
сопоставляет с сохранёнными исходными байтами в `reference/round16/pre_hardening`.
Все старые outputs проверяются на прежних местах и не изменены. Исходная команда
`canonical_evidence_freeze.py verify` предназначена для checkout старой frozen ревизии:
в рабочем дереве Round16 она закономерно сообщает изменения трёх source dependencies.
Текущий verifier также проверяет raw labels/метрики и отдельный engineering manifest.
Исходный Round16 inventory сохранён: документированные изменения source/docs
сверяются с историческими snapshots, текущие файлы — с отдельными хешами.
Старый `verify_submission_artifacts.py` сохраняет область исторического checkout.

Для повторных вычислений создайте изолированные конфиги. Заменяйте `check` на новый tag
при следующем запуске. Завершённые checkpoints не пересчитываются; несовместимое окружение
или изменённые источники блокируют resume. Для проверки уже готовых runs после инженерных
изменений используйте read-only verifier выше. `--force` архивирует новый, не frozen output;
его не следует использовать для обновления сводок завершённого эксперимента.

```powershell
python scripts/prepare_submission_reproduction.py --tag check
python -m sbernet.robustness.reproduction_gate --output outputs/round16_reproduction_check/baseline
python scripts/rebuild_method_benchmark.py --config configs/round16_reproduction_check/benchmark.yaml
python -m sbernet.robustness.leiden --config configs/round16_reproduction_check/leiden.yaml
python -m sbernet.robustness.perturbation_v2 gate --config configs/round16_reproduction_check/perturbation_v2.yaml
python -m sbernet.robustness.perturbation_v2 run --config configs/round16_reproduction_check/perturbation_v2.yaml
python -m sbernet.robustness.perturbation_v2 gate --config configs/round16_reproduction_check/protocol_gate.yaml
python scripts/run_round16_sensitivity.py decomposition --config configs/round16_reproduction_check/decomposition.yaml
python scripts/run_round16_sensitivity.py resolution --config configs/round16_reproduction_check/resolution.yaml
python scripts/build_competition_artifacts.py --config configs/round16_reproduction_check/competition.yaml
```

Новый50-run v2 в этих командах является отдельным воспроизведением; decomposition по
дизайну использует опубликованный combined n=50. `build_competition_artifacts.py` не запускает
clustering. Старые configs и научные outputs не перезаписываются.

Далее сохранён контекст предыдущей evidence version2.2.0; актуальные ограничения и таблицы — выше.

Анализ 1904 муниципальных образований России за 24 месяца с использованием атрибутированных сетей, temporal community detection, пространственных контролей и многоуровневой проверки устойчивости результатов.

[![Tests and evidence integrity](https://github.com/resarytrew/cashless-demand-network-russia/actions/workflows/verify.yml/badge.svg)](https://github.com/resarytrew/cashless-demand-network-russia/actions/workflows/verify.yml)
[![Evidence v2.2.0](https://img.shields.io/badge/evidence-v2.2.0-245c46)](outputs/evidence_freeze_v2_2_0/README.md)
[![Python 3.13](https://img.shields.io/badge/Python-3.13-3776AB)](pyproject.toml)

**1904 территории · январь 2023 — декабрь 2024 · 45 696 узлов муниципалитет–месяц · 50 perturbation runs**

[Результаты](#основные-результаты) · [Метод](#метод) · [Evidence freeze](#доказательная-база-и-её-границы) · [Воспроизводимость](#быстрый-старт)

## Исследовательский вопрос

Какие профили локального безналичного потребительского спроса проявляются в муниципальных данных, как они организованы в сети и насколько их ядра и границы сохраняются при изменении алгоритма, параметров и входного графа?

Проект объединяет композиционное представление расходов, сети сходства и временные связи. Главный результат — измеренная устойчивость структуры вместе с её ограничениями. Обнаруженные сообщества не интерпретируются как универсальные «типы экономики».

## Основные результаты

| Проверка | Full-supra ARI к reference | ARI декабря 2024 |
|---|---:|---:|
| Точное воспроизведение Louvain baseline | 1,0000 | 1,0000 |
| Leiden на идентичном графе | 0,4403 | 0,7075 |
| Canonical perturbation v2, среднее 50 runs | 0,4984 | 0,6757 |

**Сохранение ядра не означает устойчивость точной границы.** Например, у профиля D средний retention составляет 0,9758, но precision — 0,5117: участники ядра часто оказываются внутри более крупного сообщества. Для F эти показатели равны 0,7028 и 0,4768. Cross-coassignment B/E меняется от 0 до 1 между runs.

![Распределения retention, precision и cross-coassignment для 50 seeds](outputs/perturbation_v2/perturbation_v2_distributions.png)

*Распределения описывают конкретный протокол возмущений. Это не доверительные интервалы для генеральной совокупности муниципалитетов.*

- [Leiden: результаты и интерпретация](outputs/leiden_robustness/LEIDEN_FINDINGS.md)
- [Canonical perturbation robustness v2, n=50](outputs/perturbation_v2/PERTURBATION_HIGHREP_FINDINGS.md)
- [Каноническая evidence matrix v2.2.0](outputs/evidence_freeze_v2_2_0/MASTER_PROFILE_EVIDENCE_MATRIX_v2.2.0.csv)
- [Неизменённый реестр научных статусов A–G](outputs/evidence_freeze_v2_2_0/SCIENTIFIC_STATUS_REGISTRY_UNCHANGED.csv)

## Метод

```mermaid
flowchart LR
    A[Муниципальные расходы] --> B[Строгая панель: 1904 × 24]
    B --> C[CLR-композиция + уровень расходов]
    C --> D[Ежемесячные mutual-kNN графы]
    D --> E[Временная supra-сеть]
    E --> F[Louvain reference]
    F --> G[Leiden и perturbation v2]
    G --> H[Аудиты и evidence freeze]
```

| Компонент | Reference specification |
|---|---|
| Состав расходов | Продовольствие, здоровье, общепит, маркетплейсы, транспорт и остаток `Other` |
| Композиция | CLR / Aitchison geometry |
| Уровень расходов | `log(Total)`, месячный robust-z по median / MAD |
| Веса блоков | 0,70 композиция / 0,30 уровень; нормировка медианными расстояниями |
| Ежемесячный граф | Взвешенный неориентированный mutual-kNN, k=20, adaptive RBF |
| Временная связь | omega=2 × глобальная медиана внутрислойных весов |
| Reference partition | Louvain, resolution=0,5, seed=0 |
| Изоляты | Fallback включён только в отдельном статическом графе декабря |

Параметры заданы в [baseline.yaml](configs/baseline.yaml). Это reference specification; её оптимальность не заявляется. Отдельное статическое разбиение декабря и декабрьский срез временной сети — разные объекты анализа.

В protocol v2 удаляется 5% внутрислойных рёбер, оставшиеся веса умножаются на `exp(N(0, 0.02))`, временные рёбра сохраняются. До генерации случайных чисел рёбра канонически сортируются. Проверены совпадение checksums внутри процесса, в fresh process и после перестановки insertion order. Каждый seed имеет raw labels, hashes и checkpoint.

[Методология](docs/methodology.md) · [Протокол v2](docs/PERTURBATION_V2_PROTOCOL.md) · [Исследовательский контекст](docs/RESEARCH_STATE.md)

## Доказательная база и её границы

Канонический пакет расположен в **[outputs/evidence_freeze_v2_2_0](outputs/evidence_freeze_v2_2_0/README.md)**. При forensic freeze прошли 3748 численных сравнений по сохранённым raw partitions; инвентарь фиксирует SHA256 390 файлов. Сам freeze не является повторным запуском clustering.

- **Допущенная численная evidence:** показатели Leiden и 50 runs protocol v2, проверенные по сохранённым меткам.
- **Исторический perturbation n=5:** `SUPERSEDED_NON_REPRODUCIBLE`; файлы сохранены, но не используются количественно. [Решение по provenance](docs/PERTURBATION_PILOT_PROVENANCE_RESOLUTION.md).
- **S_Dbw:** forensic audit воспроизвёл undefined для всех 50 строк Round 14. Происхождение старых конечных значений не установлено; они исключены из канонической численной evidence. [Аудит](outputs/evidence_freeze_v2_2_0/S_DBW_FORENSIC_AUDIT.md).
- **Пространственные, административные и population/density controls:** описаны в исследовательском контексте. Полный набор исторических внешних артефактов отсутствует в данной поставке; эти результаты не представлены как заново воспроизведённые поля канонической матрицы.
- **Статусы A–G:** сохранены как отдельные научные аннотации. Наличие файла в freeze inventory само по себе не означает допуск его содержимого в evidence.

Строгая панель не установлена как репрезентативная выборка всех муниципалитетов России. `Other` — технический остаток, а не самостоятельная отрасль. Анализ исследовательский: ни причинные эффекты, ни универсальные архетипы, ни независимая внешняя валидация через mobility не заявляются.

[Правила evidence](docs/evidence_governance.md) · [Реестр claims](docs/HYPOTHESIS_LEDGER.md) · [Допуск и исключения](outputs/evidence_freeze_v2_2_0/EVIDENCE_ADMISSIBILITY.csv)

## Быстрый старт

Для среды, близкой к зафиксированному запуску, используйте Python 3.13; исторические вычисления выполнены на Python 3.13.6 / Windows. Полные версии пакетов сохранены в [environment_versions.json](outputs/evidence_v2_2_0/environment_versions.json).

```bash
git clone https://github.com/resarytrew/cashless-demand-network-russia.git
cd cashless-demand-network-russia
python -m venv .venv
```

Активация: `.venv\Scripts\Activate.ps1` в PowerShell или `source .venv/bin/activate` в macOS/Linux.

```bash
python -m pip install -r outputs/evidence_v2_2_0/requirements-used.txt
python -m pip install -e . --no-deps
python -m pytest -q
python scripts/verify_current_artifacts.py
```

Для тестов, импортирующих forensic scripts, при необходимости задайте `PYTHONPATH`: `$env:PYTHONPATH = 'src;.'` в PowerShell или `export PYTHONPATH=src:.` в macOS/Linux.

Round16 проверка: **34 tests passed**. Итоговый журнал — `outputs/round16_evidence/tests.log`.
Проверка freeze и metric replay не запускают новых кластеризаций.

### Новый запуск без перезаписи evidence

```bash
python -m sbernet.robustness.reproduction_gate --output outputs/reproducibility_gates/new_attempt
```

Команда создаёт новую папку и требует точного совпадения reference labels. Не запускайте baseline pipeline с записью в замороженный `outputs/baseline`. Каждый новый эксперимент должен иметь отдельный конфиг и output; завершённые seeds не пересчитываются без явного `--force`.

[Подробные команды и resume](docs/ROBUSTNESS_V2_COMMANDS.md)

## Состав репозитория

| Каталог | Содержание |
|---|---|
| `src/sbernet/` | Подготовка панели, признаки, графы, временная модель, robustness |
| `configs/` | Reference и отдельные спецификации экспериментов |
| `data/raw/` | Архивы расходов и mobility, использованные в анализе |
| `outputs/` | Метки, raw results, checkpoints, аудиты и версии evidence |
| `outputs/evidence_freeze_v2_2_0/` | Каноническая матрица, forensic audit, freeze manifest |
| `docs/` | Методология, контекст, provenance и научные ограничения |
| `reference/` | Сохранённый исторический runner |
| `scripts/` | Построение отчётов, forensic replay и проверка freeze |
| `tests/` | Проверки метрик, детерминизма, схем и целостности |

Исходные муниципальные данные — SberIndex; преобразования и состав панели описаны в документации. Права на сторонние данные не переопределяются этим репозиторием. Условия повторного использования следует проверять у источника данных.

Исторические manifests с `git_commit=null` сохранены без изменений: они созданы до помещения рабочей копии под Git. Git-история публикации и побайтовые SHA256-манифесты выполняют разные функции provenance.

## Как ссылаться на результаты

Указывайте название проекта, URL репозитория, конкретный Git commit и evidence version **2.2.0 / canonical_forensic_1**. Для отдельного результата добавляйте путь к его CSV и соответствующему audit. Авторы и DOI не подставляются автоматически: эти сведения должны соответствовать фактическому авторству и публикации.
