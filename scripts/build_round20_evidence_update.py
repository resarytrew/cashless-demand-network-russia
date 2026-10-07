"""Create additive evidence v2.7.0 for the fixed Round20 targeted checks."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from sbernet.robustness.reproduction_gate import sha256


def main() -> None:
    source = Path("outputs/evidence_v2_6_0/MASTER_PROFILE_EVIDENCE_MATRIX_v2.6.0.csv")
    round20 = Path("outputs/round20_targeted_checks")
    output = Path("outputs/evidence_v2_7_0")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    completed = json.loads((round20 / "COMPLETED.json").read_text(encoding="utf-8"))
    if completed.get("status") != "COMPLETED":
        raise RuntimeError("Round20 is not complete")
    output.mkdir(parents=True)

    matrix = pd.read_csv(source)
    correspondence = pd.read_csv(round20 / "omega1_profile_correspondence.csv").rename(columns={
        "archetype": "archetype", "n_reference": "round20_omega1_reference_n",
        "retention": "round20_omega1_member_retention", "precision": "round20_omega1_destination_precision",
        "Jaccard": "round20_omega1_jaccard", "n_destinations": "round20_omega1_destinations_n",
    })
    keep = ["archetype", "round20_omega1_reference_n", "round20_omega1_member_retention",
            "round20_omega1_destination_precision", "round20_omega1_jaccard", "round20_omega1_destinations_n"]
    matrix = matrix.merge(correspondence[keep], on="archetype", how="left", validate="one_to_one")
    summary = json.loads((round20 / "round20_summary.json").read_text(encoding="utf-8"))
    residual = pd.read_csv(round20 / "residual_global_tests.csv").set_index("outcome")
    matrix["round20_evidence_version"] = "2.7.0"
    matrix["round20_status"] = "COMPLETED_EXPLORATORY_TARGETED_CHECKS"
    matrix["round20_omega1_dec_ARI"] = summary["omega"]["Dec2024_ARI"]
    matrix["round20_omega1_dec_NMI"] = summary["omega"]["Dec2024_NMI"]
    matrix["round20_omega1_aligned_changed_share"] = summary["omega"]["optimally_aligned_changed_share"]
    matrix["round20_wage_partial_R2_after_size_region"] = residual.loc["wage", "partial_R2_profile"]
    matrix["round20_employment_partial_R2_after_size_region"] = residual.loc["employment_total", "partial_R2_profile"]
    matrix["round20_L1_status_change"] = False
    matrix.to_csv(output / "MASTER_PROFILE_EVIDENCE_MATRIX_v2.7.0.csv", index=False)

    claims = pd.DataFrame([
        {"claim": "A–G external wage contrasts are only municipality-size artifacts", "status": "WEAKENED",
         "evidence": "region-FE log-wage model: profile partial R2=0.1758; HC3 p=2.78e-55; within-region permutation p=0.0005"},
        {"claim": "A–G external employment-total contrasts are only municipality-size artifacts", "status": "WEAKENED",
         "evidence": "region-FE log-employment model: profile partial R2=0.2144; HC3 p=2.56e-36; within-region permutation p=0.0005"},
        {"claim": "Exact December partition is insensitive to temporal coupling", "status": "NOT_SUPPORTED",
         "evidence": "omega 2 vs 1: ARI=0.4070; NMI=0.5547; aligned changed share=33.14%; K 10 vs 7"},
        {"claim": "Atlas stable cores remain stable under omega=1", "status": "SUPPORTED_FOR_THIS_SENSITIVITY",
         "evidence": "1/824 stable-core municipalities changed after one-to-one December alignment"},
        {"claim": "Employment alone dominates all L2 pairwise distance", "status": "NOT_SUPPORTED_ALL_PAIRS",
         "evidence": "mean shares: employment 34.54%, demand 34.08%, market access 15.40%, population 8.27%, wage 7.70%"},
        {"claim": "Employment is the largest contribution among L2 graph-neighbor distances", "status": "SUPPORTED_DESCRIPTIVELY",
         "evidence": "mean share 52.05% on temporal December edges and 52.10% on static December edges; no retuning"},
        {"claim": "Round20 changes L1, A–G labels, omega=2 or L2 weights", "status": "FALSE",
         "evidence": "exact gates passed; additive outputs only"},
    ])
    claims.to_csv(output / "CLAIM_CHANGES_v2.7.0.csv", index=False)
    (output / "ROUND20_EVIDENCE_UPDATE.md").write_text(
        "# Evidence v2.7.0 — Round20 targeted checks\n\n"
        "Round20 is an additive exploratory robustness layer. L1, A–G, reference omega=2 and "
        "the fixed Round19 L2 weights are unchanged. After controlling log population and region "
        "fixed effects, A–G retain material associations with log wage (partial R2=0.1758) and log "
        "employment total (partial R2=0.2144); HC3 and 1,999-replicate within-region Freedman–Lane "
        "tests are both strongly inconsistent with a zero joint profile effect. These are observational "
        "external associations, not causal effects.\n\n"
        "The omega result is adverse for exact-boundary robustness: omega=2 versus omega=1 gives "
        "December ARI=0.4070, NMI=0.5547, K=10 versus 7 and a 33.14% optimally aligned change share. "
        "All A–G have high member retention into a dominant omega=1 destination, but omega=1 merges "
        "B/E and C/D/F/G; high retention is therefore not one-to-one profile preservation. The Atlas "
        "core/boundary conclusion strengthens: only 1/824 stable-core municipalities changes, versus "
        "348/388 transition municipalities.\n\n"
        "For all municipality pairs, mean L2 squared-distance shares are balanced at the coarse-block "
        "level (demand 34.08%, employment 34.54%, remaining socioeconomic coordinates 31.38%). On "
        "the actual December graph edges, employment contributes about 52.1% on average and is the "
        "largest local-neighbor term. This diagnostic was inspected without retuning any weight.\n",
        encoding="utf-8",
    )
    manifest = {"status": "COMPLETED_ADDITIVE_EVIDENCE_UPDATE", "evidence_version": "2.7.0",
                "source_matrix": str(source), "source_matrix_sha256": sha256(source),
                "round20_manifest_sha256": sha256(round20 / "run_manifest.json"),
                "round20_summary_sha256": sha256(round20 / "round20_summary.json"),
                "L1_scientific_status_changes": False, "reference_specification_changed": False,
                "weights_retuned": False}
    (output / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
