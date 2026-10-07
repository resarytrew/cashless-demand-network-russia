"""Run the corrective v4 synthetic temporal-network benchmark."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from sbernet.synthetic_temporal import (
    LEGACY_METRIC_NOTE,
    generate_panel,
    infer_labels,
    monthly_partition_metrics,
    score,
)


TRANSITION_SCENARIOS = ("abrupt", "gradual", "mixed")
NO_TRANSITION_SCENARIOS = ("stable", "boundary", "shock")
TRANSITION_COMPONENTS = (
    ("monthly_ari_mean", True),
    ("switch_f1", True),
    ("false_switch_rate", False),
    ("absolute_change_point_delay", False),
)
STABILITY_COMPONENTS = (
    ("monthly_ari_mean", True),
    ("false_switch_rate", False),
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def aggregate(frame: pd.DataFrame, reps: int, seed: int) -> pd.DataFrame:
    """Bootstrap seed-level means within each fixed scenario and omega."""
    rng = np.random.default_rng(seed)
    rows: list[dict[str, float | int | str]] = []
    metric_columns = [
        column for column in frame.columns if column not in {"scenario", "seed", "omega"}
    ]
    for (scenario, omega), group in frame.groupby(["scenario", "omega"], sort=True):
        for metric in metric_columns:
            values = group[metric].dropna().to_numpy(float)
            if not len(values):
                rows.append(
                    {
                        "scenario": scenario,
                        "omega": omega,
                        "metric": metric,
                        "mean": np.nan,
                        "std": np.nan,
                        "ci_low": np.nan,
                        "ci_high": np.nan,
                        "n": 0,
                    }
                )
                continue
            sampled = values[
                rng.integers(0, len(values), size=(reps, len(values)))
            ].mean(axis=1)
            rows.append(
                {
                    "scenario": scenario,
                    "omega": omega,
                    "metric": metric,
                    "mean": values.mean(),
                    "std": values.std(ddof=1) if len(values) > 1 else 0.0,
                    "ci_low": np.quantile(sampled, 0.025),
                    "ci_high": np.quantile(sampled, 0.975),
                    "n": len(values),
                }
            )
    return pd.DataFrame(rows)


def _normalise(values: pd.Series, higher_is_better: bool) -> pd.Series:
    if not np.isfinite(values.to_numpy(float)).all():
        raise ValueError(
            "Utility component is undefined; refusing to average remaining components"
        )
    span = float(values.max() - values.min())
    if span <= 1e-12:
        return pd.Series(np.ones(len(values)), index=values.index, dtype=float)
    scaled = (values - values.min()) / span
    return scaled if higher_is_better else 1.0 - scaled


def _pareto_flags(
    group: pd.DataFrame, components: tuple[tuple[str, bool], ...]
) -> pd.Series:
    values = group[[name for name, _ in components]].to_numpy(float)
    directions = np.array([1.0 if higher else -1.0 for _, higher in components])
    oriented = values * directions
    flags = []
    for index, row in enumerate(oriented):
        other = np.delete(oriented, index, axis=0)
        dominated = bool(
            np.any(np.all(other >= row, axis=1) & np.any(other > row, axis=1))
        )
        flags.append(not dominated)
    return pd.Series(flags, index=group.index, dtype=bool)


def build_tradeoff_summary(wide: pd.DataFrame) -> pd.DataFrame:
    """Build scenario utilities without silently skipping undefined values."""
    result = wide.copy()
    result["transition_tradeoff_utility"] = np.nan
    result["stability_tradeoff_utility"] = np.nan
    result["pareto_efficient"] = False
    definitions = [
        *(
            (scenario, TRANSITION_COMPONENTS, "transition_tradeoff_utility")
            for scenario in TRANSITION_SCENARIOS
        ),
        *(
            (scenario, STABILITY_COMPONENTS, "stability_tradeoff_utility")
            for scenario in NO_TRANSITION_SCENARIOS
        ),
    ]
    for scenario, components, utility_name in definitions:
        mask = result["scenario"].eq(scenario)
        if not mask.any():
            continue
        component_scores = []
        for metric, higher in components:
            column = f"normalised_{metric}"
            result.loc[mask, column] = _normalise(result.loc[mask, metric], higher)
            component_scores.append(column)
        result.loc[mask, utility_name] = result.loc[mask, component_scores].mean(axis=1)
        result.loc[mask, "pareto_efficient"] = _pareto_flags(
            result.loc[mask], components
        )
    return result


def _mean_table(
    summary: pd.DataFrame, scenarios: tuple[str, ...], metrics: list[str]
) -> pd.DataFrame:
    selected = summary[
        summary["scenario"].isin(scenarios) & summary["metric"].isin(metrics)
    ]
    return (
        selected.pivot(index=["scenario", "omega"], columns="metric", values="mean")
        .reset_index()
        .rename_axis(columns=None)[["scenario", "omega", *metrics]]
    )


def _format_markdown(frame: pd.DataFrame, digits: int = 4) -> str:
    display = frame.copy()
    for column in display.select_dtypes(include=[np.number]).columns:
        display[column] = display[column].map(
            lambda value: "NA" if pd.isna(value) else f"{value:.{digits}f}"
        )
    rows = [
        [str(column) for column in display.columns],
        ["---"] * len(display.columns),
        *display.astype(str).values.tolist(),
    ]
    return "\n".join("| " + " | ".join(row) + " |" for row in rows)


def _write_report(out: Path, overall: pd.DataFrame, mixed: pd.DataFrame) -> None:
    omega_two = mixed.loc[np.isclose(mixed["omega"], 2.0)].iloc[0]
    interpretation = (
        "At reference omega=2, state recovery is stronger than event recovery: "
        f"node-state accuracy is {omega_two['node_state_accuracy']:.3f}, while switch F1 is "
        f"{omega_two['switch_f1']:.3f}. Temporal regularisation suppresses false instability "
        "but can miss genuine changes."
    )
    if omega_two["switch_f1"] >= omega_two["node_state_accuracy"]:
        interpretation = (
            "At reference omega=2, event recovery is not weaker than state recovery in this run; "
            "the saved metrics, rather than the prior v3 narrative, govern interpretation."
        )
    report = f"""# Synthetic temporal benchmark v4

This is an additive methodological correction to `synthetic_temporal_v3`. It uses the same
generator, scenarios, 20 seeds, model grid, and bootstrap seed. It does not use or alter the
real municipality data, the baseline clustering, or the reference omega=2.

The primary partition-quality measures are label-permutation-invariant monthly ARI and NMI,
summarised across months. `legacy_flattened_ari` and `legacy_flattened_nmi` are retained only
for forensic comparison with v3 and never enter an omega comparison or utility. {LEGACY_METRIC_NOTE}

## Mean monthly ARI across all scenarios

{_format_markdown(overall)}

## Mixed scenario

{_format_markdown(mixed)}

{interpretation}

Transition and no-transition scenarios are evaluated separately. The former use monthly ARI,
switch F1, false-switch rate, and absolute delay; the latter use monthly ARI and false-switch
rate. `tradeoff_summary.csv` contains scenario-local equal-weight descriptive utilities and
Pareto flags. They are not combined into a universal score, and v4 does not select a best omega.

The historical v3 result remains preserved. V4 supersedes it only for synthetic temporal
calibration claims. No real-data result or A-G status changed.
"""
    (out / "SYNTHETIC_TEMPORAL_REPORT.md").write_text(report, encoding="utf-8")


def _write_audit(
    out: Path, config_path: Path, config_hash: str, seed_rows: int, monthly_rows: int
) -> None:
    audit = f"""# Synthetic temporal v4 audit

## What was found

In `synthetic_temporal_v3`, partition ARI/NMI used `truth.ravel()` against
`inferred.ravel()`. For independently labelled monthly partitions this can mix within-month
partition quality with arbitrary cross-month numeric label identity. A label permutation in
one month can therefore change the flattened diagnostic without changing that month's partition.

## What was corrected

V4 makes mean monthly ARI/NMI the primary partition-quality measures. They are computed directly
within each month and require no label alignment. Hungarian alignment is used only for semantic
state and event metrics. The flattened metrics have explicit `legacy_flattened_*` names and are
excluded from utilities and omega comparisons. Transition and no-transition scenarios receive
separate, fixed-component utilities; any undefined required component is an error rather than a
silently skipped value. Switch F1 is not interpreted as failure when no true event exists.

## What did not change

- synthetic data generator and all generator parameters;
- scenarios, 20-seed grid, omega grid, bootstrap seed, k, and Louvain resolution/seed;
- real-data baseline, real-data omega=2, real clustering outputs, A-G labels, or scientific statuses.

## Reproducibility and scope

- Config: `{config_path.as_posix()}`
- Config SHA256: `{config_hash}`
- Seed-level rows: {seed_rows}
- Month-level partition rows: {monthly_rows}

V3 remains a historical, methodologically limited result; it is not corrupt or fraudulent. V4
supersedes v3 only for conclusions about synthetic temporal calibration. No real clustering was
recomputed. The benchmark reports metric-specific trade-offs and does not declare a universally
best omega or retune the reference specification.
"""
    (out / "SYNTHETIC_TEMPORAL_V4_AUDIT.md").write_text(audit, encoding="utf-8")


def _checkpoint_paths(out: Path, scenario: str, seed: int) -> tuple[Path, Path]:
    stem = f"{scenario}_seed_{seed:03d}"
    return (
        out / "checkpoints" / f"{stem}_metrics.csv",
        out / "checkpoints" / f"{stem}_monthly.csv",
    )


def _run_seed(
    out: Path,
    scenario: str,
    seed: int,
    generator: dict,
    model: dict,
    force: bool,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    metrics_path, monthly_path = _checkpoint_paths(out, scenario, seed)
    if metrics_path.exists() and monthly_path.exists() and not force:
        return pd.read_csv(metrics_path), pd.read_csv(monthly_path)
    panel = generate_panel(
        scenario,
        seed,
        **{key: value for key, value in generator.items() if key != "scenarios"},
    )
    metric_rows = []
    monthly_rows = []
    for omega in model["omega_grid"]:
        inferred = infer_labels(
            panel, omega, model["k"], model["resolution"], model["louvain_seed"]
        )
        metric_rows.append(
            {"scenario": scenario, "seed": seed, "omega": omega, **score(panel, inferred)}
        )
        partition = monthly_partition_metrics(panel.truth, inferred)
        monthly_rows.extend(
            {
                "scenario": scenario,
                "seed": seed,
                "omega": omega,
                "month": month + 1,
                "monthly_ari": partition["monthly_ari"][month],
                "monthly_nmi": partition["monthly_nmi"][month],
            }
            for month in range(panel.truth.shape[0])
        )
    metrics = pd.DataFrame(metric_rows)
    monthly = pd.DataFrame(monthly_rows)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_temp = metrics_path.with_suffix(".tmp")
    monthly_temp = monthly_path.with_suffix(".tmp")
    metrics.to_csv(metrics_temp, index=False)
    monthly.to_csv(monthly_temp, index=False)
    metrics_temp.replace(metrics_path)
    monthly_temp.replace(monthly_path)
    return metrics, monthly


def main(path: str, force: bool = False) -> None:
    config_path = Path(path)
    config_bytes = config_path.read_bytes()
    config_hash = hashlib.sha256(config_bytes).hexdigest()
    cfg = yaml.safe_load(config_bytes)
    out = Path(cfg["experiment"]["output_dir"])
    out.mkdir(parents=True, exist_ok=True)
    marker = out / "RUN_CONFIG_SHA256"
    if marker.exists() and marker.read_text(encoding="utf-8").strip() != config_hash:
        raise ValueError(f"Refusing to resume {out} with a different config")
    marker.write_text(config_hash + "\n", encoding="utf-8")
    completed_manifest = out / "run_manifest.json"
    if completed_manifest.exists() and not force:
        manifest = json.loads(completed_manifest.read_text(encoding="utf-8"))
        if (
            manifest.get("status") == "COMPLETED"
            and manifest.get("config_sha256") == config_hash
        ):
            print(f"Completed output already exists; nothing to rerun: {out}")
            return

    generator = cfg["generator"]
    model = cfg["model"]
    experiment = cfg["experiment"]
    seed_frames = []
    monthly_frames = []
    for scenario in generator["scenarios"]:
        for offset in range(experiment["seeds"]):
            seed = experiment["seed_start"] + offset
            metrics, monthly = _run_seed(
                out, scenario, seed, generator, model, force
            )
            seed_frames.append(metrics)
            monthly_frames.append(monthly)

    seeds = pd.concat(seed_frames, ignore_index=True).sort_values(
        ["scenario", "seed", "omega"]
    )
    monthly = pd.concat(monthly_frames, ignore_index=True).sort_values(
        ["scenario", "seed", "omega", "month"]
    )
    seeds.to_csv(out / "seed_metrics.csv", index=False)
    monthly.to_csv(out / "monthly_partition_metrics.csv", index=False)
    pd.DataFrame(
        [{**generator, "scenario": item} for item in generator["scenarios"]]
    ).drop(columns="scenarios").to_csv(out / "scenario_parameters.csv", index=False)

    summary = aggregate(
        seeds,
        cfg["statistics"]["bootstrap_reps"],
        cfg["statistics"]["bootstrap_seed"],
    )
    summary.to_csv(out / "omega_aggregate.csv", index=False)
    seeds[
        [
            "scenario",
            "seed",
            "omega",
            "switch_precision",
            "switch_recall",
            "switch_f1",
            "false_switches",
            "missed_switches",
            "false_switch_rate",
            "false_persistence",
            "false_instability",
        ]
    ].to_csv(out / "switch_detection.csv", index=False)
    seeds[
        [
            "scenario",
            "seed",
            "omega",
            "absolute_change_point_delay",
            "signed_change_point_delay",
        ]
    ].to_csv(out / "change_point_delay.csv", index=False)

    mixed_metrics = [
        "monthly_ari_mean",
        "monthly_nmi_mean",
        "node_state_accuracy",
        "switch_precision",
        "switch_recall",
        "switch_f1",
        "false_switch_rate",
        "false_switches",
        "missed_switches",
        "absolute_change_point_delay",
    ]
    mixed = _mean_table(summary, ("mixed",), mixed_metrics).drop(columns="scenario")
    mixed.to_csv(out / "mixed_scenario_summary.csv", index=False)
    transition_metrics = [
        *mixed_metrics,
        "signed_change_point_delay",
    ]
    transition = _mean_table(summary, TRANSITION_SCENARIOS, transition_metrics)
    transition.to_csv(out / "transition_scenarios_summary.csv", index=False)
    no_transition_metrics = [
        "monthly_ari_mean",
        "monthly_nmi_mean",
        "node_state_accuracy",
        "false_switch_rate",
        "false_switches",
        "false_instability",
    ]
    no_transition = _mean_table(
        summary, NO_TRANSITION_SCENARIOS, no_transition_metrics
    )
    no_transition.to_csv(out / "no_transition_scenarios_summary.csv", index=False)

    wide = summary.pivot(
        index=["scenario", "omega"], columns="metric", values="mean"
    ).reset_index()
    wide.columns.name = None
    tradeoff = build_tradeoff_summary(wide)
    tradeoff.to_csv(out / "tradeoff_summary.csv", index=False)

    omega_values = sorted(seeds["omega"].unique())
    overall_rows = []
    for omega in omega_values:
        at_omega = seeds[np.isclose(seeds["omega"], omega)]
        transition_at_omega = at_omega[
            at_omega["scenario"].isin(TRANSITION_SCENARIOS)
        ]
        stable_at_omega = at_omega[
            at_omega["scenario"].isin(NO_TRANSITION_SCENARIOS)
        ]
        overall_rows.append(
            {
                "omega": omega,
                "mean_monthly_ari": at_omega["monthly_ari_mean"].mean(),
                "transition_switch_f1": transition_at_omega["switch_f1"].mean(),
                "transition_false_switch_rate": transition_at_omega[
                    "false_switch_rate"
                ].mean(),
                "transition_delay": transition_at_omega[
                    "absolute_change_point_delay"
                ].mean(),
                "no_transition_false_switch_rate": stable_at_omega[
                    "false_switch_rate"
                ].mean(),
            }
        )
    overall = pd.DataFrame(overall_rows)
    overall.to_csv(out / "omega_cross_scenario_summary.csv", index=False)
    _write_report(out, overall, mixed)
    _write_audit(out, config_path, config_hash, len(seeds), len(monthly))
    (out / "config_used.yaml").write_bytes(config_bytes)

    packages = {}
    for package in (
        "numpy",
        "pandas",
        "scipy",
        "scikit-learn",
        "networkx",
        "PyYAML",
    ):
        packages[package] = importlib.metadata.version(package)
    artifact_files = sorted(
        item
        for item in out.iterdir()
        if item.is_file() and item.name != "run_manifest.json"
    )
    manifest = {
        "experiment_id": experiment["id"],
        "config": config_path.as_posix(),
        "config_sha256": config_hash,
        "status": "COMPLETED",
        "seeds": experiment["seeds"],
        "seed_start": experiment["seed_start"],
        "scenarios": generator["scenarios"],
        "omega_grid": model["omega_grid"],
        "bootstrap_reps": cfg["statistics"]["bootstrap_reps"],
        "bootstrap_seed": cfg["statistics"]["bootstrap_seed"],
        "git_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "git_dirty": bool(
            subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()
        ),
        "python": sys.version,
        "packages": packages,
        "source_sha256": {
            "src/sbernet/synthetic_temporal.py": _sha256(
                Path("src/sbernet/synthetic_temporal.py")
            ),
            "scripts/run_synthetic_temporal_benchmark.py": _sha256(Path(__file__)),
        },
        "artifact_sha256": {item.name: _sha256(item) for item in artifact_files},
        "legacy_metric_note": LEGACY_METRIC_NOTE,
        "real_data_recomputed": False,
        "reference_specification_changed": False,
    }
    completed_manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", default="configs/synthetic_temporal_benchmark_v4.yaml"
    )
    parser.add_argument("--force", action="store_true")
    arguments = parser.parse_args()
    main(arguments.config, arguments.force)
