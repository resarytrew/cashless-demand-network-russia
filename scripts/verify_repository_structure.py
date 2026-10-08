"""Verify the canonical repository surface after the 2026-10-07 restructure."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED = (
    "docs/CURRENT_STATE.json",
    "docs/METHODOLOGY.md",
    "docs/TECHNICAL_APPENDIX.md",
    "outputs/baseline",
    "outputs/perturbation_v2/seeds",
    "outputs/leiden_robustness",
    "outputs/round16_competition",
    "outputs/round17_external_validation",
    "outputs/round18_representation",
    "outputs/round19_dual_lens_l2",
    "outputs/round20_targeted_checks",
    "outputs/round21_structural_sensitivity",
    "outputs/round22_kefrin_benchmark",
    "outputs/round23_economic_mechanisms",
    "outputs/round24_graph_semantics",
    "outputs/evidence_v2_11_0",
    "outputs/evidence_v2_5_0",
    "outputs/evidence_v2_6_0",
    "outputs/evidence_v2_7_0",
    "outputs/evidence_v2_8_0",
    "outputs/evidence_v2_9_0",
    "outputs/evidence_v2_10_0",
    "outputs/stability_atlas_v2_2_1",
    "outputs/final_competition_upgrade/baseline_gate_before_v3_corrections",
    "outputs/final_competition_upgrade/data_sense_lineage_20261006_r3",
    "outputs/final_competition_upgrade/edge_sensitivity_v3",
    "outputs/final_competition_upgrade/icvi_v2",
    "outputs/final_competition_upgrade/external_validation_national_20261006_r6",
    "outputs/final_competition_upgrade/profile_cards_20261007_v3",
    "outputs/final_competition_upgrade/story_data_v3",
    "outputs/final_competition_upgrade/synthetic_temporal_v3",
    "outputs/final_competition_upgrade/synthetic_temporal_v4",
    "reference/historical_provenance",
    "site/index.html",
    "site/methodology.html",
)

RETIRED = (
    "docs/CURRENT_SUBMISSION_STATE.json",
    "docs/public/METHODOLOGY.md",
    "configs/public_visual_style.yaml",
    "configs/external_validation_national_20261006.yaml",
    "configs/external_validation_national_20261006_r4.yaml",
    "configs/external_validation_national_20261006_r5.yaml",
    "configs/round18_representation_robustness_plan.yaml",
    "scripts/build_public_visuals.py",
    "src/sbernet/visualization/public.py",
    "outputs/public_visualization",
    "outputs/engineering_20260922",
    "outputs/final_competition_upgrade/baseline_gate_before_final",
    "outputs/final_competition_upgrade/baseline_gate_before_v2_corrections",
    "outputs/final_competition_upgrade/story_data",
    "outputs/final_competition_upgrade/story_data_v2",
    "outputs/final_competition_upgrade/synthetic_temporal",
    "outputs/final_competition_upgrade/synthetic_temporal_v2",
    "outputs/final_competition_upgrade/data_sense_lineage_20261006",
    "outputs/final_competition_upgrade/data_sense_lineage_20261006_r2",
    "outputs/final_competition_upgrade/edge_sensitivity_v2",
    "outputs/final_competition_upgrade/profile_cards_20261007",
    "outputs/final_competition_upgrade/profile_cards_20261007_v2",
    "outputs/round18_representation/reference_archived_status_formatting_20261005",
    "outputs/landing_20261006",
    "outputs/landing_autoplay_20261006",
    "outputs/landing_hero_evidence_20261006",
    "outputs/landing_scroll_20261006",
    "outputs/landing_ux_v2_20261006",
)

STATE_POINTERS = (
    "current_evidence_matrix",
    "scientific_status_registry",
    "latest_research_audit",
)


def check_paths(root: Path, required: tuple[str, ...], retired: tuple[str, ...]) -> None:
    missing = [path for path in required if not (root / path).exists()]
    present_retired = [path for path in retired if (root / path).exists()]
    if missing:
        raise FileNotFoundError(f"Missing canonical paths: {missing}")
    if present_retired:
        raise ValueError(f"Retired paths remain in current tree: {present_retired}")


def verify(root: Path = ROOT) -> dict[str, object]:
    root = root.resolve()
    check_paths(root, REQUIRED, RETIRED)
    methodology_names = [
        path.name for path in (root / "docs").iterdir()
        if path.is_file() and path.name.lower() == "methodology.md"
    ]
    if methodology_names != ["METHODOLOGY.md"]:
        raise ValueError(f"Expected one canonical docs/METHODOLOGY.md: {methodology_names}")

    state = json.loads((root / "docs/CURRENT_STATE.json").read_text(encoding="utf-8"))
    if state.get("schema_version") != 2 or state.get("evidence_version") != "2.11.0":
        raise ValueError("CURRENT_STATE does not identify schema 2 / evidence 2.11.0")
    if state.get("latest_research_round") != 24:
        raise ValueError("CURRENT_STATE does not identify Round24 as latest")
    if state.get("scientific_status_changes") is not False:
        raise ValueError("current additive rounds must not be recorded as an A-G status change")

    pointers = [state[key] for key in STATE_POINTERS]
    pointers.extend(state["round17_external_validation"][key] for key in ("config", "report", "audit", "claim_evidence_matrix"))
    pointers.extend(state["round18_representation_robustness"][key] for key in ("reference_config", "r1_config", "r2_config", "summary", "audit", "evidence_update"))
    pointers.extend(state["round19_dual_lens_l2"][key] for key in ("config", "report", "audit", "summary", "profile_table", "evidence_update"))
    pointers.extend(state["round20_targeted_checks"][key] for key in ("config", "report", "audit", "summary", "distance_contributions", "evidence_update"))
    pointers.extend(state["round21_structural_sensitivity"][key] for key in ("config", "report", "audit", "summary", "baseline_freeze", "checksums", "profile_evidence_matrix", "evidence_update"))
    pointers.extend(state["round22_kefrin_benchmark"][key] for key in ("config", "report", "audit", "summary", "baseline_freeze", "checksums", "profile_evidence_matrix", "evidence_update"))
    pointers.extend(state["round23_economic_mechanisms"][key] for key in ("config", "report", "audit", "summary", "baseline_freeze", "checksums", "profile_evidence_matrix", "evidence_update"))
    pointers.extend(state["round24_graph_semantics"][key] for key in ("config", "protocol", "report", "audit", "summary", "baseline_freeze", "completion", "profile_evidence_matrix", "evidence_update"))
    pointers.extend(state["synthetic_temporal_benchmark"][key] for key in ("current_config", "current_report", "current_audit", "supersedes_for_synthetic_evaluation"))
    pointers.extend(state["icvi_reporting"][key] for key in ("config", "documentation", "output_dir"))
    pointers.extend(state["current_submission"].values())
    pointers.extend(state["engineering"].values())
    missing_pointers = [path for path in pointers if not (root / path).exists()]
    if missing_pointers:
        raise FileNotFoundError(f"Broken CURRENT_STATE pointers: {missing_pointers}")

    return {
        "status": "PASS",
        "schema_version": state["schema_version"],
        "evidence_version": state["evidence_version"],
        "latest_research_round": state["latest_research_round"],
        "required_paths": len(REQUIRED),
        "retired_paths_absent": len(RETIRED),
        "current_state_pointers": len(pointers),
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
