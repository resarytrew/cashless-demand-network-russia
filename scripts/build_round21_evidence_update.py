"""Build additive evidence v2.8.0 from completed Round21 artifacts."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from sbernet.robustness.reproduction_gate import sha256


def main() -> None:
    source=Path("outputs/evidence_v2_7_0/MASTER_PROFILE_EVIDENCE_MATRIX_v2.7.0.csv")
    r21=Path("outputs/round21_structural_sensitivity"); out=Path("outputs/evidence_v2_8_0")
    if out.exists(): raise FileExistsError(f"refusing to overwrite {out}")
    if json.loads((r21/"COMPLETED.json").read_text(encoding="utf-8"))["status"]!="COMPLETED": raise RuntimeError("Round21 incomplete")
    out.mkdir()
    matrix=pd.read_csv(source); profile=pd.read_csv(r21/"profile_evidence_matrix.csv")
    profile=profile.rename(columns={c:f"round21_{c}" for c in profile.columns if c!="profile"}).rename(columns={"profile":"archetype"})
    matrix=matrix.merge(profile,on="archetype",how="left",validate="one_to_one")
    summary=json.loads((r21/"round21_summary.json").read_text(encoding="utf-8")); sector=summary["adjusted_sector"]
    matrix["round21_evidence_version"]="2.8.0"; matrix["round21_status"]="COMPLETED_ADDITIVE_STRUCTURAL_SENSITIVITY"
    matrix["round21_omega1_micro_purity"]=summary["omega1"]["micro_purity"]
    matrix["round21_omega1_fine_pair_retention"]=summary["omega1"]["fine_pair_retention"]
    matrix["round21_omega1_coarse_pair_precision"]=summary["omega1"]["coarse_pair_precision"]
    matrix["round21_sector_adjusted_partial_R2"]=sector["partial_R2"]
    matrix["round21_sector_permutation_p"]=sector["permutation_p"]
    matrix["round21_L1_status_change"]=False
    matrix.to_csv(out/"MASTER_PROFILE_EVIDENCE_MATRIX_v2.8.0.csv",index=False)
    claims=pd.DataFrame([
        {"claim":"omega=1 change is predominantly a coarsening of omega=2 December groups","status":"SUPPORTED_DESCRIPTIVELY_WITH_BOUNDARY_CAVEAT","evidence":"micro purity=.9785; fine-pair retention=.9827; coarse precision=.4888; conditional entropies .1303 vs 1.2874 bits"},
        {"claim":"the same merge pattern survives matched K","status":"PARTIAL","evidence":"omega1 resolution=.8 reaches K=10; B/E merge persists, C/D/F/G joint merge does not"},
        {"claim":"Atlas states anticipate omega sensitivity on an independent axis","status":"SUPPORTED_FOR_HELD_OUT_SENSITIVITY_AXIS","evidence":"omega absent from Atlas inputs; stable 1/824 vs transition 348/388; RR=739 with very wide CI"},
        {"claim":"sector composition differences disappear after size and region controls","status":"NOT_SUPPORTED","evidence":"partial R2=.0361; pseudo-F=11.2386; within-region permutation p=.0005"},
        {"claim":"omega1 merges economically indistinguishable profiles","status":"NOT_SUPPORTED_POSTHOC","evidence":"B/E and every D/F/G scalar and sector contrast remain distinguishable; D/F/G sector omnibus R2=.0666, p=.0005; interpretation is post-hoc"},
        {"claim":"original L2 is robust to semantic block balancing","status":"NOT_SUPPORTED","evidence":"Balanced-A ARI=.0345 and Balanced-B ARI=.1772 versus original L2; edge Jaccard about .43; no model selected"},
        {"claim":"Round21 changed L1, A-G, Atlas assignments, omega=2 or original L2","status":"FALSE","evidence":"before/after freeze hashes identical and full audit records no changes"},
    ])
    claims.to_csv(out/"CLAIM_CHANGES_v2.8.0.csv",index=False)
    (out/"ROUND21_EVIDENCE_UPDATE.md").write_text(
        "# Evidence v2.8.0 — Round21 structural sensitivity\n\n"
        "Round21 is additive. Frozen L1, A–G, Atlas assignments, reference omega=2 and original L2 hashes are unchanged. "
        "Omega=1 is predominantly a coarsening in December (micro purity .9785; fine-pair retention .9827; coarse-pair "
        "precision .4888; H(omega1|omega2)=.1303 versus H(omega2|omega1)=1.2874 bits), but matched K shows a material "
        "omega×resolution interaction: B/E remains merged while C/D/F/G does not remain one group.\n\n"
        "Omega was absent from Atlas construction, so this is a held-out sensitivity axis rather than statistical "
        "out-of-sample validation. Stable core changes 1/824 and transition changes 348/388. Adjusted sector CLR remains "
        "associated with A–G after population and region controls (partial R2=.0361, permutation p=.0005), a small but "
        "precisely detected observational association. Post-hoc B/E and D/F/G contrasts show that omega=1 merges profiles "
        "that remain externally distinguishable; the D/F/G sector omnibus has R2=.0666 and permutation p=.0005.\n\n"
        "Both predeclared block-balanced L2 alternatives materially differ from original L2 (ARI .0345 and .1772). This "
        "negative result makes original L2 conclusions specification-dependent; neither alternative is selected and original "
        "L2 remains unchanged.\n",encoding="utf-8")
    manifest={"status":"COMPLETED_ADDITIVE_EVIDENCE_UPDATE","evidence_version":"2.8.0","source_matrix":str(source),
              "source_matrix_sha256":sha256(source),"round21_manifest_sha256":sha256(r21/"run_manifest.json"),
              "round21_checksums_sha256":sha256(r21/"checksums.sha256"),"L1_scientific_status_changes":False,
              "reference_specification_changed":False,"original_L2_changed":False}
    (out/"run_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")


if __name__=="__main__": main()
