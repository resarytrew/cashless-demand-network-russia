"""Create the additive evidence-v2.6.0 layer for Round19 without rewriting prior rounds."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from sbernet.robustness.reproduction_gate import sha256


def main() -> None:
    source = Path("outputs/evidence_v2_5_0/MASTER_PROFILE_EVIDENCE_MATRIX_v2.5.0.csv")
    round19 = Path("outputs/round19_dual_lens_l2")
    output = Path("outputs/evidence_v2_6_0")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    if not (round19 / "COMPLETED.json").is_file():
        raise RuntimeError("Round19 is not complete")
    output.mkdir(parents=True)

    matrix = pd.read_csv(source)
    migration = pd.read_csv(round19 / "l1_l2_municipality_migration.csv")
    summary = json.loads((round19 / "round19_summary.json").read_text(encoding="utf-8"))
    overlap = []
    for profile in "ABCDEFG":
        group = migration.loc[migration.L1_profile.eq(profile)]
        counts = group.L2_community.value_counts()
        overlap.append({
            "archetype": profile,
            "round19_common_n_profile": len(group),
            "round19_dominant_L2_community": int(counts.index[0]) if len(counts) else None,
            "round19_share_in_dominant_L2": float(counts.iloc[0] / len(group)) if len(group) else None,
        })
    overlap = pd.DataFrame(overlap)
    matrix = matrix.merge(overlap, on="archetype", how="left", validate="one_to_one")
    matrix["round19_evidence_version"] = "2.6.0"
    matrix["round19_dual_lens_status"] = "COMPLETED_SEPARATE_ADDITIVE_L2"
    matrix["round19_common_n"] = summary["L1_vs_L2_Dec2024"]["n_common"]
    matrix["round19_L1_L2_ARI"] = summary["L1_vs_L2_Dec2024"]["ARI"]
    matrix["round19_L1_L2_NMI"] = summary["L1_vs_L2_Dec2024"]["NMI"]
    matrix["round19_L1_status_change"] = False
    matrix["round19_scope"] = (
        "L2 includes population, wage, employment structure and market access; these cease "
        "to be independent L2 evidence; mobility holdout selected 268/1876; no L1 status change"
    )
    matrix.to_csv(output / "MASTER_PROFILE_EVIDENCE_MATRIX_v2.6.0.csv", index=False)

    claims = pd.DataFrame([
        {"claim": "L1 remains the reference research result", "status": "UNCHANGED",
         "evidence": "exact P0 baseline hashes and ARI/NMI gates"},
        {"claim": "L2 is a separate broader local-economy lens", "status": "SUPPORTED_DESCRIPTIVELY",
         "evidence": "1876 complete cases; fixed additive config; no K preselection"},
        {"claim": "L1 and L2 have identical exact boundaries", "status": "REJECTED",
         "evidence": f"ARI={summary['L1_vs_L2_Dec2024']['ARI']:.6f}; NMI={summary['L1_vs_L2_Dec2024']['NMI']:.6f}"},
        {"claim": "L2 has five robust universal economic types", "status": "NOT_ESTABLISHED",
         "evidence": "five major temporal-December communities cover 95.3%, but 41 total communities, micro-fragmentation and negative silhouette"},
        {"claim": "L2 major communities admit descriptive economic labels", "status": "SUPPORTED_WITH_SCOPE_LIMITATIONS",
         "evidence": f"shallow-tree CV balanced accuracy={summary['tree']['balanced_accuracy']:.3f}; labels use included variables"},
        {"claim": "Population/wage/employment/market access independently validate L2", "status": "REJECTED_BY_DESIGN",
         "evidence": "these variables enter L2 features"},
        {"claim": "Mobility independently validates L2 nationally", "status": "NOT_ESTABLISHED",
         "evidence": "held out from model, but exact-name coverage is only 268/1876 and selected"},
    ])
    claims.to_csv(output / "CLAIM_CHANGES_v2.6.0.csv", index=False)
    (output / "ROUND19_EVIDENCE_UPDATE.md").write_text(
        "# Evidence v2.6.0 — Round19 additive dual-lens update\n\n"
        "Round19 adds a separate L2 attributed-network experiment and does not alter L1, A–G, "
        "the reference graph, k=20, omega=2 or any A–G scientific status. On 1,876 complete "
        "cases, temporal December L1/L2 agreement is ARI=0.431917 and NMI=0.471727. The exact "
        "partition therefore depends materially on adding socioeconomic and employment attributes.\n\n"
        "Five L2 communities exceed the fixed 2% reporting threshold and cover 95.3% of the L2 "
        "sample; the full temporal December partition has 41 communities and negative silhouette. "
        "The five are descriptive major profiles, not five proven universal types. A shallow rule "
        "tree reaches balanced accuracy 0.845 on these major profiles, supporting interpretable "
        "descriptors but not independent validation because the descriptors use L2 inputs.\n\n"
        "Population, wage, employment structure and market access cease to be independent for L2. "
        "Mobility remains held out, but only 268/1,876 exact-name matches are available; its large "
        "exploratory group effect is auxiliary evidence on a selected subset, not national or causal "
        "validation. Urban share was unavailable and was not proxied.\n",
        encoding="utf-8",
    )
    manifest = {
        "status": "COMPLETED_ADDITIVE_EVIDENCE_UPDATE",
        "evidence_version": "2.6.0",
        "source_matrix": str(source),
        "source_matrix_sha256": sha256(source),
        "round19_manifest_sha256": sha256(round19 / "run_manifest.json"),
        "round19_summary_sha256": sha256(round19 / "round19_summary.json"),
        "L1_scientific_status_changes": False,
        "reference_specification_changed": False,
    }
    (output / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
