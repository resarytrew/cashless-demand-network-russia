"""Build evidence-bounded A-G profile cards from saved repository artifacts."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy.spatial.distance import pdist


PROFILES = list("ABCDEFG")
CATEGORY_LABELS = {
    "Food": "Продовольствие",
    "Health": "Здоровье",
    "Catering": "Общепит",
    "Marketplace": "Маркетплейсы",
    "Transport": "Транспорт",
    "Other": "Прочее*",
}
SECTOR_COLUMNS = [
    "agriculture",
    "mining",
    "manufacturing",
    "utilities",
    "construction",
    "trade",
    "transport",
    "hospitality",
    "information",
    "finance",
    "real_estate",
    "professional",
    "administrative",
    "public_administration",
    "education",
    "health",
    "arts",
    "other_services",
]
SECTOR_LABELS = {
    "agriculture": "сельское хозяйство",
    "mining": "добыча полезных ископаемых",
    "administrative": "административная деятельность",
    "arts": "культура и досуг",
    "construction": "строительство",
    "education": "образование",
    "finance": "финансы",
    "health": "здравоохранение",
    "hospitality": "гостиницы и общепит",
    "information": "информация и связь",
    "manufacturing": "обрабатывающие производства",
    "other_services": "прочие услуги",
    "professional": "профессиональная деятельность",
    "public_administration": "государственное управление",
    "real_estate": "операции с недвижимостью",
    "trade": "торговля",
    "transport": "транспорт и хранение",
    "utilities": "энергетика и коммунальная инфраструктура",
}
DISPLAY_ALIASES = {
    # Explicit public-facing form requested by the user; the official source name
    # remains available in every record's ``name`` field.
    "городской округ Магнитогорский": "Магнитогорск",
    "городской округ Миасский": "Миасс",
    "городской округ Уссурийский": "Уссурийск",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bool_col(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().eq("true")


def clean(value):
    if isinstance(value, dict):
        return {str(key): clean(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clean(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return None if not math.isfinite(float(value)) else float(value)
    if pd.isna(value):
        return None
    return value


def display_name(name: str) -> str:
    if name in DISPLAY_ALIASES:
        return DISPLAY_ALIASES[name]
    federal_settlement = re.match(
        r"^внутригородская территория города федерального значения "
        r"(поселок|посёлок|город)\s+(.+)$",
        name,
        flags=re.IGNORECASE,
    )
    if federal_settlement:
        kind, place = federal_settlement.groups()
        kind = "Посёлок" if "ё" in kind.lower() else "Поселок" if kind.lower().startswith("пос") else "Город"
        return f"{kind} {place[:1].upper() + place[1:]}"
    prefixes = (
        "внутригородская территория города федерального значения муниципальный округ ",
        "внутригородская территория города федерального значения муниципальное образование ",
        "внутригородская территория города федерального значения город ",
        "городской округ город ",
        "муниципальный округ ",
        "муниципальное образование город ",
        "муниципальное образование ",
        "муниципальный район ",
    )
    result = name
    for prefix in prefixes:
        if result.lower().startswith(prefix):
            result = result[len(prefix):]
            break
    return result[:1].upper() + result[1:]


def clr(composition: np.ndarray) -> np.ndarray:
    if np.any(composition <= 0):
        raise ValueError("CLR requires strictly positive composition parts")
    logged = np.log(composition)
    return logged - logged.mean(axis=1, keepdims=True)


def reference_matrix(features: pd.DataFrame, parts: list[str], sw: float, lw: float) -> np.ndarray:
    composition = features[parts].to_numpy(dtype=float)
    structure = clr(composition)
    level = features[["level_z"]].to_numpy(dtype=float)
    structure_scale = float(np.median(pdist(structure)))
    level_scale = float(np.median(pdist(level)))
    if structure_scale <= 0 or level_scale <= 0:
        raise ValueError("Reference feature scale must be positive")
    return np.column_stack(
        [np.sqrt(sw) * structure / structure_scale, np.sqrt(lw) * level / level_scale]
    )


def sector_composition(external: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    if set(SECTOR_COLUMNS) != set(SECTOR_LABELS):
        raise ValueError("Scientific sector columns and display labels diverge")
    sectors = [column for column in SECTOR_COLUMNS if column in external.columns]
    unexpected = sorted(
        set(external.columns).intersection(SECTOR_LABELS) - set(SECTOR_COLUMNS)
    )
    if unexpected:
        raise ValueError(f"Unexpected sector columns: {unexpected}")
    if not sectors:
        raise ValueError("No canonical sector columns are available")
    comp = external.loc[external.profile.notna(), ["profile", *sectors]].copy()
    comp[sectors] = comp[sectors].fillna(0)
    totals = comp[sectors].sum(axis=1)
    comp = comp.loc[totals.gt(0)].copy()
    comp[sectors] = comp[sectors].div(comp[sectors].sum(axis=1), axis=0)
    return comp, sectors


def ratio_record(category: str, profile_value: float, overall_value: float) -> dict:
    ratio = profile_value / overall_value
    direction = "up" if ratio > 1.02 else "down" if ratio < 0.98 else "neutral"
    return {
        "category": category,
        "label": CATEGORY_LABELS[category],
        "profile_median_share": profile_value,
        "overall_median_share": overall_value,
        "ratio_to_overall": ratio,
        "difference_pp": 100 * (profile_value - overall_value),
        "direction": direction,
    }


def aggregate_perturbations(raw: pd.DataFrame) -> pd.DataFrame:
    required = {"archetype", "retention", "precision", "Jaccard", "seed"}
    if not required.issubset(raw.columns):
        raise ValueError(f"Canonical perturbation rows lack {sorted(required - set(raw.columns))}")
    grouped = raw.groupby("archetype", sort=True).agg(
        retention_mean=("retention", "mean"),
        retention_q10=("retention", lambda values: values.quantile(0.10)),
        retention_min=("retention", "min"),
        precision_mean=("precision", "mean"),
        jaccard_mean=("Jaccard", "mean"),
        runs=("seed", "nunique"),
    )
    if set(grouped.index) != set(PROFILES) or not grouped.runs.eq(50).all():
        raise ValueError("Expected exactly 50 canonical perturbation runs for every A-G profile")
    return grouped


def build(cfg: dict) -> tuple[dict, list[dict], list[dict], dict[str, Path]]:
    """Build deterministic presentation records without writing to the filesystem."""
    exp = cfg["experiment"]
    inputs = {
        name: Path(exp[name])
        for name in (
            "feature_csv",
            "atlas_csv",
            "external_csv",
            "external_summary_csv",
            "perturbation_csv",
            "atlas_summary_csv",
            "representation_overlap_csv",
            "evidence_matrix_csv",
        )
    }
    missing = [str(path) for path in inputs.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing inputs: {missing}")

    features = pd.read_csv(inputs["feature_csv"])
    atlas = pd.read_csv(inputs["atlas_csv"])
    external = pd.read_csv(inputs["external_csv"])
    external_summary = pd.read_csv(inputs["external_summary_csv"])
    perturbation = aggregate_perturbations(pd.read_csv(inputs["perturbation_csv"]))
    atlas_summary = pd.read_csv(inputs["atlas_summary_csv"]).set_index("reference_profile")
    overlap = pd.read_csv(inputs["representation_overlap_csv"])
    evidence = pd.read_csv(inputs["evidence_matrix_csv"]).set_index("archetype")

    if len(features) != exp["reference_n"] or not set(PROFILES).issubset(set(features.profile)):
        raise ValueError("Feature table does not match the frozen A-G reference panel")
    months = pd.to_datetime(features.month, errors="raise").dt.to_period("M").astype(str).unique()
    if len(months) != 1:
        raise ValueError(f"Expected one feature month, got {months.tolist()}")
    reference_month = str(months[0])
    for profile in PROFILES:
        configured = cfg["profiles"][profile]["evidence_status"]
        if configured != evidence.loc[profile, "round13_status"]:
            raise ValueError(f"Scientific evidence status mismatch for {profile}")
    if not features.municipality.is_unique or not atlas.municipality.is_unique:
        raise ValueError("Municipality keys must be unique")
    merged = features.merge(atlas, on="municipality", how="left", validate="one_to_one")
    if merged.reference_profile.isna().any() or not (merged.profile == merged.reference_profile).all():
        raise ValueError("Feature and Atlas profile labels do not reconcile")

    parts = list(exp["reference_features"]["composition"])
    matrix = reference_matrix(
        features,
        parts,
        float(exp["reference_features"]["structure_weight"]),
        float(exp["reference_features"]["level_weight"]),
    )
    for profile in PROFILES:
        mask = features.profile.eq(profile).to_numpy()
        centre = np.median(matrix[mask], axis=0)
        merged.loc[mask, "feature_distance"] = np.linalg.norm(matrix[mask] - centre, axis=1)
    merged["consensus_matches_reference"] = bool_col(merged["consensus_matches_reference"])
    merged["lofo_all_class_match"] = bool_col(merged["lofo_all_class_match"])

    ext_columns = ["official_name", "population", "wage", "employment_total"]
    ext_lookup = external[ext_columns].rename(columns={"official_name": "municipality"})
    merged = merged.merge(ext_lookup, on="municipality", how="left", validate="one_to_one")
    expected_population_n = int(exp["expected_external_population_n"])
    if merged.population.notna().sum() != expected_population_n:
        raise ValueError(f"Expected {expected_population_n:,} population matches")

    overall_category = features[parts].median()
    scalar_overall = {
        variable: float(external[variable].median())
        for variable in ("population", "wage", "employment_total")
    }
    sector_comp, sectors = sector_composition(external)
    overall_sector = sector_comp[sectors].median()

    cards = []
    representative_rows = []
    boundary_rows = []
    for profile in PROFILES:
        group = merged.loc[merged.profile.eq(profile)].copy()
        group["typicality_percentile"] = group.feature_distance.rank(
            method="max", ascending=False, pct=True
        )
        group["centrality_rank"] = group.feature_distance.rank(
            method="min", ascending=True
        ).astype(int)
        eligible_mask = group.consensus_matches_reference & group.lofo_all_class_match
        if profile in {"A", "D", "G"}:
            eligible_mask &= group.stability_class.isin(["stable_core", "expansive_core"])
        eligible = group.loc[eligible_mask].sort_values(
            [
                "feature_distance",
                f"affinity_share_{profile}",
                "affinity_margin",
                "perturbation_peer_coassignment",
                "panel_index",
            ],
            ascending=[True, False, False, False, True],
        )
        if len(eligible) < exp["representative_count"]:
            raise ValueError(f"Too few eligible representatives for {profile}")
        if profile == "F":
            chosen = []
            roles = []
            for column, ascending, role in (
                ("affinity_share_D", False, "D-leaning"),
                ("affinity_share_G", False, "G-leaning"),
                ("affinity_margin", True, "maximally transitional"),
            ):
                pool = group.loc[~group.municipality.isin(chosen)].sort_values(
                    [column, "panel_index"], ascending=[ascending, True]
                )
                row = pool.iloc[0]
                chosen.append(row.municipality)
                roles.append(role)
            selected = group.set_index("municipality").loc[chosen].reset_index()
            selected["representative_role"] = roles
        elif profile == "C":
            selected = group.sort_values(["affinity_margin", "panel_index"]).head(
                exp["representative_count"]
            )
            selected["representative_role"] = "uncertainty case"
        else:
            selected = eligible.head(exp["representative_count"]).copy()
            selected["representative_role"] = "central representative"

        headline_override = cfg["profiles"][profile].get("headline_override", [])
        if headline_override:
            headline_rows = group.set_index("municipality").loc[headline_override]
            if not headline_rows.profile.eq(profile).all():
                raise ValueError(f"Headline override is outside {profile}")
        headline = list(headline_override)
        for name in selected.municipality:
            if name not in headline:
                headline.append(name)
            if len(headline) >= exp["headline_territory_count"]:
                break
        for name in eligible.municipality:
            if name not in headline:
                headline.append(name)
            if len(headline) >= exp["headline_territory_count"]:
                break
        headline = headline[: exp["headline_territory_count"]]

        representatives = []
        for row in selected.itertuples(index=False):
            record = {
                "name": row.municipality,
                "display_name": display_name(row.municipality),
                "total": float(row.Total),
                "feature_distance": float(row.feature_distance),
                "typicality_percentile": float(row.typicality_percentile),
                "centrality_rank": int(row.centrality_rank),
                "profile_n": int(len(group)),
                "representative_role": row.representative_role,
                "self_affinity_share": float(getattr(row, f"affinity_share_{profile}")),
                "affinity_share_D": float(row.affinity_share_D),
                "affinity_share_G": float(row.affinity_share_G),
                "affinity_margin": float(row.affinity_margin),
                "consensus_class": row.consensus_class,
                "lofo_all_class_match": bool(row.lofo_all_class_match),
                "stability_class": row.stability_class,
                "population": row.population,
                "wage": row.wage,
                "employment_total": row.employment_total,
            }
            representatives.append(clean(record))
            representative_rows.append({"profile": profile, **record})

        pairs = []
        for anchor in selected.itertuples(index=False):
            if any(pd.isna(getattr(anchor, item)) for item in ("population", "wage", "employment_total")):
                continue
            candidates = merged.loc[
                merged.profile.ne(profile)
                & merged.profile.isin(PROFILES)
                & merged.admin_form.eq(anchor.admin_form)
                & merged.population.notna()
                & merged.wage.notna()
                & merged.employment_total.notna()
            ].copy()
            robust_candidates = candidates.loc[
                candidates.consensus_matches_reference
                & candidates.lofo_all_class_match
                & candidates.stability_class.isin(["stable_core", "expansive_core"])
            ]
            strength = "robust"
            if not robust_candidates.empty:
                candidates = robust_candidates.copy()
            else:
                strength = "transition_fallback"
            candidates["context_distance"] = (
                np.log(candidates.population / anchor.population).abs()
                + np.log(candidates.wage / anchor.wage).abs()
                + np.log(candidates.employment_total / anchor.employment_total).abs()
            )
            for candidate in candidates.itertuples(index=False):
                pairs.append((strength, float(candidate.context_distance), anchor, candidate))
        if not pairs:
            raise ValueError(f"No external counterexample candidates for {profile}")
        strength, _, anchor, counter = min(
            pairs,
            key=lambda item: (
                item[0] != "robust",
                item[1],
                item[2].municipality,
                item[3].municipality,
            ),
        )
        counterexample = {
            "anchor_name": anchor.municipality,
            "anchor_display_name": display_name(anchor.municipality),
            "anchor_population": float(anchor.population),
            "anchor_wage": float(anchor.wage),
            "anchor_employment_total": float(anchor.employment_total),
            "anchor_total": float(anchor.Total),
            "anchor_marketplace_share": float(anchor.Marketplace),
            "comparison_name": counter.municipality,
            "comparison_display_name": display_name(counter.municipality),
            "comparison_profile": counter.profile,
            "comparison_population": float(counter.population),
            "comparison_wage": float(counter.wage),
            "comparison_employment_total": float(counter.employment_total),
            "comparison_total": float(counter.Total),
            "comparison_marketplace_share": float(counter.Marketplace),
            "population_difference_pct": 100 * (float(counter.population) / float(anchor.population) - 1),
            "wage_difference_pct": 100 * (float(counter.wage) / float(anchor.wage) - 1),
            "employment_difference_pct": 100
            * (float(counter.employment_total) / float(anchor.employment_total) - 1),
            "context_distance": float(counter.context_distance),
            "same_admin_form": bool(counter.admin_form == anchor.admin_form),
            "strength": strength,
        }
        differences = [
            abs(counterexample["population_difference_pct"]),
            abs(counterexample["wage_difference_pct"]),
            abs(counterexample["employment_difference_pct"]),
        ]
        max_difference = max(differences)
        quality = exp["counterexample_match_quality"]
        if max_difference <= float(quality["strong_max_abs_difference_pct"]):
            match_quality = "strong"
        elif max_difference <= float(quality["moderate_max_abs_difference_pct"]):
            match_quality = "moderate"
        else:
            match_quality = "weak"
        counterexample.update(
            {
                "match_quality": match_quality,
                "max_scale_difference_pct": max_difference,
            }
        )

        category_records = [
            ratio_record(category, float(group[category].median()), float(overall_category[category]))
            for category in parts
        ]
        positive = sorted(
            [item for item in category_records if item["direction"] == "up"],
            key=lambda item: item["ratio_to_overall"], reverse=True,
        )[:2]
        negative = sorted(
            [item for item in category_records if item["direction"] == "down"],
            key=lambda item: item["ratio_to_overall"],
        )[:2]

        values = external_summary.loc[external_summary.profile.eq(profile)].set_index("variable")
        external_values = {}
        for variable in ("population", "wage", "employment_total"):
            median = float(values.loc[variable, "median"])
            external_values[variable] = {
                "median": median,
                "overall_median": scalar_overall[variable],
                "ratio_to_overall": median / scalar_overall[variable],
                "n": int(values.loc[variable, "n"]),
            }
        profile_sector = sector_comp.loc[sector_comp.profile.eq(profile), sectors].median()
        sector_diff = (profile_sector - overall_sector).sort_values()
        sector_down = [
            {
                "sector": sector,
                "label": SECTOR_LABELS[sector],
                "profile_median_share": float(profile_sector[sector]),
                "overall_median_share": float(overall_sector[sector]),
                "difference_pp": 100 * float(sector_diff[sector]),
            }
            for sector in sector_diff.head(2).index
        ]
        sector_up = [
            {
                "sector": sector,
                "label": SECTOR_LABELS[sector],
                "profile_median_share": float(profile_sector[sector]),
                "overall_median_share": float(overall_sector[sector]),
                "difference_pp": 100 * float(sector_diff[sector]),
            }
            for sector in sector_diff.tail(2).index[::-1]
        ]

        weakest = group.sort_values(
            ["lofo_all_class_match", "consensus_matches_reference", "affinity_margin", "panel_index"]
        ).head(3)
        boundary = []
        for row in weakest.itertuples(index=False):
            item = {
                "name": row.municipality,
                "display_name": display_name(row.municipality),
                "consensus_class": row.consensus_class,
                "second_class": row.second_class,
                "self_affinity_share": float(getattr(row, f"affinity_share_{profile}")),
                "affinity_margin": float(row.affinity_margin),
                "lofo_all_class_match": bool(row.lofo_all_class_match),
                "stability_class": row.stability_class,
            }
            boundary.append(item)
            boundary_rows.append({"profile": profile, **item})

        r1 = overlap.loc[
            overlap.representation.eq("r1_fivepart_clr") & overlap.archetype.eq(profile)
        ].iloc[0]
        r2 = overlap.loc[
            overlap.representation.eq("r2_observed_levels") & overlap.archetype.eq(profile)
        ].iloc[0]
        robust = atlas_summary.loc[profile]
        perturb = perturbation.loc[profile]
        robustness = {
            "atlas_consensus_match_share": float(robust.share_consensus_matches_reference),
            "atlas_all_four_lofo_match_share": float(robust.share_all_four_LOFO_match_full),
            "perturbation_retention_mean": float(perturb.retention_mean),
            "perturbation_retention_q10": float(perturb.retention_q10),
            "perturbation_retention_min": float(perturb.retention_min),
            "perturbation_precision_mean": float(perturb.precision_mean),
            "perturbation_jaccard_mean": float(perturb.jaccard_mean),
            "perturbation_runs": int(perturb.runs),
            "r1_fivepart_retention": float(r1.retention),
            "r1_fivepart_precision": float(r1.precision),
            "r1_fivepart_jaccard": float(r1.Jaccard),
            "r1_fivepart_destination_n": int(r1.destination_n),
            "r2_observed_levels_retention": float(r2.retention),
            "r2_observed_levels_precision": float(r2.precision),
            "r2_observed_levels_jaccard": float(r2.Jaccard),
            "r2_observed_levels_destination_n": int(r2.destination_n),
            "boundary_examples": boundary,
        }

        cards.append(
            clean(
                {
                    "profile": profile,
                    "display_name": cfg["profiles"][profile]["display_name"],
                    "scientific_name": cfg["profiles"][profile]["scientific_name"],
                    "short_name": cfg["profiles"][profile]["short_name"],
                    "status": cfg["profiles"][profile]["status"],
                    "evidence_status": cfg["profiles"][profile]["evidence_status"],
                    "status_note": cfg["profiles"][profile]["status_note"],
                    "representatives_heading": cfg["profiles"][profile].get(
                        "representatives_heading", "Наиболее характерные представители"
                    ),
                    "n": int(len(group)),
                    "share": len(group) / exp["reference_n"],
                    "headline_territories": [
                        {"name": name, "display_name": display_name(name)} for name in headline
                    ],
                    "representatives": representatives,
                    "demand": {
                        "total_median": float(group.Total.median()),
                        "overall_total_median": float(features.Total.median()),
                        "total_ratio_to_overall": float(group.Total.median() / features.Total.median()),
                        "categories": category_records,
                        "featured_up": positive,
                        "featured_down": negative,
                    },
                    "external": {
                        **external_values,
                        "sector_up": sector_up,
                        "sector_down": sector_down,
                        "sector_n": int(sector_comp.profile.eq(profile).sum()),
                    },
                    "counterexample": counterexample,
                    "robustness": robustness,
                }
            )
        )

    major_profile_n = sum(card["n"] for card in cards)
    technical_micro_n = int(exp["reference_n"] - major_profile_n)
    payload = {
        "schema": 3,
        "generated_from_saved_artifacts": True,
        "reference_month": reference_month,
        "reference_n": exp["reference_n"],
        "major_profile_n": major_profile_n,
        "technical_micro_n": technical_micro_n,
        "major_profile_share": major_profile_n / exp["reference_n"],
        "provenance": {
            "experiment_id": exp["id"],
            "evidence_matrix": str(inputs["evidence_matrix_csv"]),
            "generator_version": exp["generator_version"],
            "script_sha256": sha256(Path(__file__)),
            "git_commit": git_commit(),
        },
        "external_coverage": {
            "population": int(external.population.notna().sum()),
            "wage": int(external.wage.notna().sum()),
            "employment_total": int(external.employment_total.notna().sum()),
            "sector_employment": int(len(sector_comp)),
            "sector_columns_available": sectors,
            "sector_columns_unavailable": [
                column for column in SECTOR_COLUMNS if column not in sectors
            ],
        },
        "notes": [
            "Названия описывают профили локального безналичного спроса, а не типы экономики.",
            "Прочее — технический остаток, а не однородная отрасль.",
            "Внешние показатели не участвовали в построении профилей; сопоставление описательное и не причинное.",
            "Сходство ядра не означает неизменность точной границы.",
            "Total описывает наблюдаемый уровень безналичного спроса; его знаменатель не установлен.",
            f"A–G охватывают {major_profile_n} территорий; {technical_micro_n} технических микросообществ исключены из карточек.",
        ],
        "cards": cards,
    }

    return payload, representative_rows, boundary_rows, inputs


def git_commit() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else None


def main(config_path: str, force: bool = False) -> None:
    config = Path(config_path)
    cfg = yaml.safe_load(config.read_text(encoding="utf-8"))
    exp = cfg["experiment"]
    out = Path(exp["output_dir"])
    public_json = Path(exp["public_json"])
    if out.exists() and not force:
        raise FileExistsError(f"Refusing to overwrite {out}")

    payload, representative_rows, boundary_rows, inputs = build(cfg)
    out.mkdir(parents=True, exist_ok=force)
    public_json.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(clean(payload), ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    (out / "profile_cards.json").write_bytes(serialized.encode("utf-8"))
    public_json.write_bytes(serialized.encode("utf-8"))
    pd.DataFrame(representative_rows).to_csv(
        out / "representatives.csv", index=False, lineterminator="\n"
    )
    pd.DataFrame(boundary_rows).to_csv(
        out / "boundary_examples.csv", index=False, lineterminator="\n"
    )

    lines = [
        "# Profile cards audit",
        "",
        "The cards are a descriptive presentation layer over frozen A-G labels. No external variable entered clustering, no reference parameter changed, and no scientific status was promoted by computation.",
        "",
        f"Config: `{config}`. Reference month: {payload['reference_month']}. Panel: {exp['reference_n']} municipalities.",
        "",
        "Representative and counterexample rules are declared in the YAML config. Orenburg, Magnitogorsk and Tambov are a curated D headline only; D representatives are selected algorithmically.",
        "",
        "Expense arrows compare profile medians with the overall 1,904-municipality median. Ratios within 0.98-1.02 are neutral and receive no arrow. External population, wage and employment ratios use the audited national 2024 join.",
        "",
        f"The canonical scientific sector vocabulary has 18 columns. The saved national join exposes {len(payload['external_coverage']['sector_columns_available'])}: {', '.join(payload['external_coverage']['sector_columns_available'])}. Unavailable in that source: {', '.join(payload['external_coverage']['sector_columns_unavailable'])}. No zeros or values were invented for unavailable sectors; the limitation is explicit in the JSON.",
        "",
        "Robustness combines frozen Atlas consensus/leave-one-family-out summaries, canonical n=50 perturbations, and the two saved representation variants. High retention is reported separately from destination precision.",
        "For every alternative representation the card reports both reference retention and destination precision. For the n=50 perturbation it also reports the 10th percentile, so the mean cannot hide the lower tail.",
        "F is not represented by three medoids: it deliberately exposes a D-leaning case, a G-leaning case, and the smallest Atlas affinity margin. C labels its examples as illustrative rather than characteristic.",
        "Public names avoid interpreting Total as consumer activity because the denominator of Total is not established.",
        f"A-G cards cover {payload['major_profile_n']} municipalities ({payload['major_profile_share']:.4%}); {payload['technical_micro_n']} technical micro-community cases remain outside A-G.",
        "Counterexample stability and scale-match quality are separate fields. Match quality is based on the maximum absolute population, wage or employment difference, with thresholds declared in YAML.",
        "Public display names only shorten verified city aliases and safe administrative prefixes; unknown urban-district names retain their official form.",
        "",
        "C remains UNRESOLVED; F remains TRANSITION; B and E remain PRELIMINARY. A, D and G use the user-provided public status SUPPORTED without changing the repository's underlying scientific evidence registry.",
    ]
    (out / "PROFILE_CARDS_AUDIT.md").write_bytes(
        ("\n".join(lines) + "\n").encode("utf-8")
    )
    manifest = {
        "status": "COMPLETED_DESCRIPTIVE_PRESENTATION_LAYER",
        "config_sha256": sha256(config),
        "script_sha256": sha256(Path(__file__)),
        "git_commit": git_commit(),
        "runtime": {
            "python": sys.version.split()[0],
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "scipy": importlib.metadata.version("scipy"),
        },
        "input_sha256": {str(path): sha256(path) for path in inputs.values()},
        "outputs": [
            "profile_cards.json",
            "representatives.csv",
            "boundary_examples.csv",
            "PROFILE_CARDS_AUDIT.md",
            str(public_json),
        ],
        "scientific_status_changes": False,
        "reference_specification_changed": False,
    }
    (out / "run_manifest.json").write_bytes(
        (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/profile_cards_20261007.yaml")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    main(args.config, force=args.force)
