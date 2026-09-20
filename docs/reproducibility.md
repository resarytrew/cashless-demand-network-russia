# Воспроизводимость

## Baseline

```bash
sbernet run --config configs/baseline.yaml --mode both
```

## Обязательные артефакты запуска

Каждый запуск создаёт:

- resolved config;
- config SHA-256;
- git commit;
- panel audit;
- graph statistics;
- community labels.

## Главное правило

Нельзя заменить `k=20` на `k=30` в Python-коде и снова запустить тот же output.

Нужно:

```text
configs/k30.yaml
outputs/k30/
```

Это сохраняет baseline и делает сравнение воспроизводимым.

## Минимальный набор финальных robustness-runs

- baseline k20 / omega2 / alpha70-30;
- k30;
- k50 static;
- omega4;
- alpha50-50;
- alpha90-10;
- seed sensitivity;
- supra edge perturbations;
- Leiden;
- admin/urban/spatial controls.
