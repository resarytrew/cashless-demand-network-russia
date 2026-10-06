"""Build non-destructive ICVI, typology, and external-coverage tables."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from sbernet.icvi import evaluate_partition, flat_metrics
from sbernet.pipeline import _prepare
from sbernet.robustness.reproduction_gate import sha256

PROFILE_MAP = {"A": 1, "B": 3, "C": 7, "D": 8, "E": 9, "F": 10, "G": 11}


def ensure_new(path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}")
    path.mkdir(parents=True)


def main() -> None:
    root = Path("outputs/presubmission_upgrade")
    cfg, names, _, months, matrices = _prepare("configs/baseline.yaml")
    keys = [str(pd.Timestamp(value).date()) for value in months]
    benchmark = Path("outputs/round16_benchmark")
    icvi_dir = root / "icvi"
    if not icvi_dir.exists():
        ensure_new(icvi_dir)
        rows = []
        for method in ["Louvain", "Greedy", "Spectral", "KMeans", "Ward"]:
            labels = pd.read_csv(benchmark / f"{method}_labels.csv").set_index("mo").loc[names, "community"].to_numpy()
            # All methods are evaluated in the identical stored reference graph.
            import pickle
            with open("outputs/presubmission_upgrade/baseline_gate/baseline_graphs.pkl", "rb") as handle:
                graph = pickle.load(handle)["static"]
            row = {"method": method, **flat_metrics(evaluate_partition(matrices[keys[-1]], labels, graph))}
            rows.append(row)
        pd.DataFrame(rows, columns=["method", "K", "N", "SW", "CH", "CH_per_N", "S_Dbw", "AVI", "AVU", "MQ", "status", "notes"]).to_csv(icvi_dir / "canonical_icvi.csv", index=False)
        (icvi_dir / "README.md").write_text(
            "# Canonical ICVI\n\nAll methods use fixed December-2024 reference features and the same stored mutual-kNN20 graph for graph-based indices. CH is raw; CH/N is diagnostic. S_Dbw uses the documented Halkidi--Vazirgiannis population-standard-deviation variant in `sbernet.icvi`, not any historical finite value.\n", encoding="utf-8")

    labels = pd.read_csv("outputs/baseline/supra_labels.csv", index_col=0).loc[names, keys]
    ref = labels.iloc[:, -1].to_numpy()
    atlas = pd.read_csv("outputs/stability_atlas_v2_2_1/municipality_affinity_atlas.csv").set_index("municipality").loc[names]
    raw = pd.read_csv("outputs/round16_competition/december_municipality_features.csv").set_index("municipality").loc[names]
    numeric = raw.select_dtypes(include="number").columns.tolist()
    switch = np.sum(labels.to_numpy().T[1:] != labels.to_numpy().T[:-1], axis=0)
    output = root / "economic_typology"; ensure_new(output)
    summary = []
    for profile, cid in PROFILE_MAP.items():
        mask = ref == cid; subset = raw.loc[mask]
        centered = subset[numeric].mean() - raw[numeric].mean()
        positives = ", ".join(centered.sort_values(ascending=False).head(3).index)
        negatives = ", ".join(centered.sort_values().head(3).index)
        destinations = labels.to_numpy()[mask, :].ravel()
        values, counts = np.unique(destinations, return_counts=True)
        destination = int(values[np.argmax(counts)])
        summary.append({"profile": profile, "community_id": cid, "size": int(mask.sum()), "share_of_1904": float(mask.mean()),
                        "median_Total": float(subset["Total"].median()), "IQR_Total": float(subset["Total"].quantile(.75) - subset["Total"].quantile(.25)),
                        "median_features_json": json.dumps({column: float(subset[column].median()) for column in numeric}, ensure_ascii=False),
                        "top_positive_features": positives, "top_negative_features": negatives,
                        "stable_core_share": float(atlas.loc[mask, "stability_class"].eq("stable_core").mean()),
                        "transition_share": float(atlas.loc[mask, "stability_class"].eq("transition").mean()),
                        "mean_temporal_switches": float(switch[mask].mean()), "most_common_temporal_community": destination})
    pd.DataFrame(summary).to_csv(output / "profile_summary.csv", index=False)

    external_dir = root / "external_validation"; ensure_new(external_dir)
    external = pd.read_csv("outputs/round17_external_validation/external_validation_58.csv")
    external.to_csv(external_dir / "validation_table.csv", index=False)
    fields = [field for field in ["salary_2024", "population_2024", "urban_share_2024", "investment_per_capita_2024"] if field in external]
    coverage = []
    for profile in "ABCDEFG":
        subset = external[external["reference_profile"].eq(profile)]
        for field in fields:
            values = subset[field].dropna()
            coverage.append({"profile": profile, "indicator": field, "N": int(len(values)),
                             "median": float(values.median()) if len(values) else None,
                             "IQR": float(values.quantile(.75) - values.quantile(.25)) if len(values) else None,
                             "status": "descriptive_only" if len(values) else "not_available"})
    pd.DataFrame(coverage).to_csv(external_dir / "coverage_summary.csv", index=False)
    (external_dir / "README.md").write_text(
        "# External-validation coverage\n\nThis table republishes the sealed Round17 matched sample without entering any external variable into clustering or fitting new profile labels. Coverage is 58 selected municipalities and is not nationally representative; B/E have no matched cases. Statistical tests and effect sizes remain in the sealed Round17 artifacts.\n", encoding="utf-8")

    docs = Path("docs/ECONOMIC_TYPOLOGY.md")
    docs.write_text(
        "# Типы локальной потребительской экономики\n\n"
        "В этой работе тип локальной потребительской экономики — это устойчивое сочетание уровня и структуры наблюдаемого безналичного потребительского спроса муниципалитета. Сводка по A–G приведена в `outputs/presubmission_upgrade/economic_typology/profile_summary.csv`.\n\n"
        "Типология описывает потребительскую сторону локальной экономики, а не полное описание производственной структуры муниципалитета. A–G имеют неодинаковую степень устойчивости: F следует читать как переходную область между D и G, B/E — как предварительную интерпретацию с недостаточной внешней проверкой, а C остаётся неразрешённым вне контекста.\n\n"
        "Внешние показатели применяются только post-hoc. Их покрытие и медианы сохранены отдельно; отсутствие наблюдений не заменяется догадками.\n", encoding="utf-8")
    (root / "table_manifest.json").write_text(json.dumps({"baseline_config_sha256": sha256("configs/baseline.yaml"), "status": "completed"}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
