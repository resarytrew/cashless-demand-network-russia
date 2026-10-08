"""Profile-card presentation data must reconcile to frozen research artifacts."""
import json
import math
from pathlib import Path

import pandas as pd
import yaml

from scripts.build_profile_cards import SECTOR_COLUMNS, build, display_name, sha256


ROOT = Path(__file__).resolve().parents[1]
CARDS = json.loads((ROOT / "site/data/profile_cards.json").read_text(encoding="utf-8"))
FEATURES = pd.read_csv(ROOT / "outputs/round16_competition/december_municipality_features.csv")
EXTERNAL_PATH = ROOT / "outputs/final_competition_upgrade/external_validation_national_20261006_r6/external_validation_joined.csv"
EXTERNAL = pd.read_csv(EXTERNAL_PATH)


def card(profile: str) -> dict:
    return next(item for item in CARDS["cards"] if item["profile"] == profile)


def test_profile_card_contract_counts_and_public_statuses():
    cards = CARDS["cards"]
    assert CARDS["schema"] == 4
    assert CARDS["reference_month"] == "2024-12"
    assert [item["profile"] for item in cards] == list("ABCDEFG")
    assert [item["status"] for item in cards] == [
        "SUPPORTED", "PRELIMINARY", "UNRESOLVED", "SUPPORTED",
        "PRELIMINARY", "TRANSITION", "SUPPORTED",
    ]
    assert {item["profile"]: item["n"] for item in cards} == {
        "A": 141, "B": 98, "C": 29, "D": 153, "E": 186, "F": 327, "G": 965,
    }
    assert sum(item["n"] for item in cards) == 1899
    assert CARDS["major_profile_n"] == 1899
    assert CARDS["technical_micro_n"] == 5
    assert abs(CARDS["major_profile_share"] - 1899 / 1904) < 1e-15
    assert all(len(item["headline_territories"]) == 5 for item in cards)
    assert all(len(item["representatives"]) == 3 for item in cards)


def test_d_headline_is_curated_but_representatives_are_algorithmic():
    d = card("D")
    assert [item["display_name"] for item in d["headline_territories"][:3]] == [
        "Оренбург", "Магнитогорск", "Тамбов",
    ]
    assert all(item["representative_role"] == "central representative" for item in d["representatives"])
    assert [item["centrality_rank"] for item in d["representatives"]] == [1, 2, 3]


def test_representative_policies_match_profile_meaning():
    labels = FEATURES.set_index("municipality").profile.to_dict()
    for profile in "ABDEG":
        representatives = card(profile)["representatives"]
        assert len({item["name"] for item in representatives}) == 3
        assert all(labels[item["name"]] == profile for item in representatives)
        assert all(item["consensus_class"] == profile for item in representatives)
        assert all(item["lofo_all_class_match"] for item in representatives)
    for profile in "ADG":
        assert all(
            item["stability_class"] in {"stable_core", "expansive_core"}
            for item in card(profile)["representatives"]
        )
    assert card("C")["representatives_heading"] == "Иллюстративные случаи"
    assert {item["representative_role"] for item in card("C")["representatives"]} == {"uncertainty case"}
    assert {item["representative_role"] for item in card("F")["representatives"]} == {
        "D-leaning", "G-leaning", "maximally transitional",
    }


def test_counterexamples_are_context_matched_and_prefer_robust_cases():
    forms = FEATURES.set_index("municipality").admin_form.to_dict()
    for item in CARDS["cards"]:
        counter = item["counterexample"]
        assert counter["comparison_profile"] != item["profile"]
        assert forms[counter["anchor_name"]] == forms[counter["comparison_name"]]
        assert counter["same_admin_form"] is True
        assert counter["strength"] in {"robust", "transition_fallback"}
        assert counter["match_quality"] in {"strong", "moderate", "weak"}
        expected_max = max(abs(counter[key]) for key in (
            "population_difference_pct", "wage_difference_pct", "employment_difference_pct",
        ))
        assert counter["max_scale_difference_pct"] == expected_max
        for key in (
            "anchor_population", "anchor_wage", "anchor_employment_total",
            "comparison_population", "comparison_wage", "comparison_employment_total",
        ):
            assert counter[key] > 0
    assert card("A")["counterexample"]["match_quality"] == "weak"
    assert card("A")["counterexample"]["max_scale_difference_pct"] > 80


def test_public_names_only_use_verified_or_safe_shortening():
    assert display_name("городской округ Магнитогорский") == "Магнитогорск"
    assert display_name("городской округ Миасский") == "Миасс"
    assert display_name("городской округ Уссурийский") == "Уссурийск"
    assert display_name("городской округ Ногликский") == "Городской округ Ногликский"
    assert display_name(
        "внутригородская территория города федерального значения поселок Рязановское"
    ) == "Поселок Рязановское"


def test_expense_ratios_external_medians_and_a_values_reconcile():
    for item in CARDS["cards"]:
        group = FEATURES.loc[FEATURES.profile.eq(item["profile"])]
        assert item["demand"]["total_median"] == group.Total.median()
        for category in item["demand"]["categories"]:
            expected = group[category["category"]].median() / FEATURES[category["category"]].median()
            assert abs(category["ratio_to_overall"] - expected) < 1e-12
        ext_group = EXTERNAL.loc[EXTERNAL.profile.eq(item["profile"])]
        for variable in ["population", "wage", "employment_total"]:
            assert item["external"][variable]["median"] == ext_group[variable].median()
            assert item["external"][variable]["n"] == ext_group[variable].notna().sum()
    a_categories = {item["category"]: item for item in card("A")["demand"]["categories"]}
    assert abs(a_categories["Catering"]["ratio_to_overall"] - 1.73222321486221) < 1e-12
    assert abs(a_categories["Marketplace"]["ratio_to_overall"] - 0.6944749979566299) < 1e-12


def test_robustness_is_aggregated_from_raw_runs_and_reports_boundary_metrics():
    a = card("A")["robustness"]
    assert abs(a["perturbation_retention_mean"] - 0.9412765957446808) < 1e-12
    assert abs(a["perturbation_retention_q10"] - 0.8794326241134752) < 1e-12
    assert abs(a["perturbation_retention_min"] - 0.6524822695035462) < 1e-12
    assert abs(a["perturbation_precision_mean"] - 0.7268135437384217) < 1e-12
    assert a["perturbation_runs"] == 50
    assert abs(a["r1_fivepart_retention"] - 0.9645390070921984) < 1e-12
    assert abs(a["r1_fivepart_precision"] - 0.2747474747474747) < 1e-12
    assert abs(a["r1_fivepart_jaccard"] - 0.272) < 1e-12
    assert abs(a["r2_observed_levels_jaccard"] - 0.5720930232558139) < 1e-12
    assert all(len(item["robustness"]["boundary_examples"]) == 3 for item in CARDS["cards"])


def test_scientific_status_and_sector_availability_are_explicit():
    evidence = pd.read_csv(
        ROOT / "outputs/evidence_v2_2_0/MASTER_PROFILE_EVIDENCE_MATRIX_v2.2.0.csv"
    ).set_index("archetype")
    for item in CARDS["cards"]:
        assert item["evidence_status"] == evidence.loc[item["profile"], "round13_status"]
        assert "confidence" not in item
        assert item["scientific_name"]
    available = CARDS["external_coverage"]["sector_columns_available"]
    unavailable = CARDS["external_coverage"]["sector_columns_unavailable"]
    assert set(available) == set(SECTOR_COLUMNS).intersection(EXTERNAL.columns)
    assert set(unavailable) == {"agriculture", "mining", "transport"}
    assert set(available).isdisjoint(unavailable)
    assert set(available) | set(unavailable) == set(SECTOR_COLUMNS)


def test_public_cards_use_readme_names_and_never_imply_a_per_capita_denominator():
    expected_names = {
        "A": "Удалённые территории",
        "B": "Деловые центры Москвы",
        "C": "Горная периферия",
        "D": "Промышленные города",
        "E": "Жилые районы мегаполисов",
        "F": "Малые промышленные города",
        "G": "Сельская бюджетная Россия",
    }
    assert {item["profile"]: item["display_name"] for item in CARDS["cards"]} == expected_names
    assert "на жителя" not in json.dumps(CARDS, ensure_ascii=False).lower()


def test_reader_copy_is_hand_written_and_internal_jargon_is_below_the_fold():
    required = {
        "subtitle", "who", "demand_lead", "interpretation", "counterexample",
        "reliability", "boundary", "use", "avoid", "table_categories",
        "representative_reasons",
    }
    forbidden = [
        "supported", "preliminary", "unresolved", "transition", "reference ",
        "retention", "boundary precision", "jaccard", "5-part", "5-levels", "total",
    ]
    for item in CARDS["cards"]:
        copy = item["public_copy"]
        assert required.issubset(copy)
        assert 3 <= len(copy["table_categories"]) <= 4
        assert "Other" not in copy["table_categories"]
        assert set(copy["representative_reasons"]) == {
            representative["name"] for representative in item["representatives"]
        }
        assert all(representative["public_reason"] for representative in item["representatives"])
        reader_text = " ".join(str(value) for value in copy.values()).lower()
        assert not [token for token in forbidden if token in reader_text]
        assert item["robustness_wording"]["core"] in {
            "ядро устойчиво", "ядро в целом устойчиво", "ядро неустойчиво",
        }
        assert item["robustness_wording"]["boundary"] in {
            "граница размыта", "точная граница проверяется отдельно",
        }


def test_public_payload_provenance_is_self_describing():
    provenance = CARDS["provenance"]
    assert provenance["experiment_id"] == "profile_cards_20261008_v4"
    assert provenance["generator_version"] == 4
    assert provenance["evidence_matrix"].endswith("MASTER_PROFILE_EVIDENCE_MATRIX_v2.2.0.csv")
    assert provenance["script_sha256"] == sha256(ROOT / "scripts/build_profile_cards.py")
    assert provenance["git_commit"]


def test_payload_is_finite_and_pure_build_is_deterministic():
    def walk(value):
        if isinstance(value, dict):
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
        elif isinstance(value, float):
            assert math.isfinite(value)

    walk(CARDS)
    cfg = yaml.safe_load((ROOT / "configs/profile_cards_20261008_v4.yaml").read_text(encoding="utf-8"))
    first = build(cfg)[:3]
    second = build(cfg)[:3]
    assert first == second
