"""Create an additive Round18 evidence pointer; never amend prior matrices."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from sbernet.robustness.reproduction_gate import sha256


def main() -> None:
    source = Path("outputs/round17_external_validation/MASTER_PROFILE_EVIDENCE_MATRIX_v2.4.0.csv")
    summary = Path("outputs/round18_representation/round18_summary.json")
    output = Path("outputs/evidence_v2_5_0")
    if output.exists():
        raise FileExistsError(output)
    output.mkdir()
    matrix = pd.read_csv(source)
    values = {item["representation"]: item for item in json.loads(summary.read_text(encoding="utf-8"))["comparison"]}
    matrix["round18_status"] = "REPRESENTATION_DEPENDENCE_OBSERVED_NO_PROFILE_STATUS_CHANGE"
    matrix["round18_r1_temporal_dec_ARI"] = values["r1_fivepart_clr"]["ari"]
    matrix["round18_r2_temporal_dec_ARI"] = values["r2_observed_levels"]["ari"]
    matrix["round18_scope"] = "single fixed seed; no representation/parameter selection; A-G statuses retained"
    matrix.to_csv(output / "MASTER_PROFILE_EVIDENCE_MATRIX_v2.5.0.csv", index=False)
    (output / "ROUND18_EVIDENCE_UPDATE.md").write_text(
        "# Evidence v2.5.0 — Round18 additive update\n\n"
        "Round18 is now computed under its fixed protocol and found material exact-partition dependence on representation without `Other` (temporal December ARI: R1=.821695, R2=.707693). This weakens any claim of representation-invariant exact boundaries. It does not select a representation, revise the reference specification, or change any A–G scientific status. Prior evidence matrices remain unchanged.\n", encoding="utf-8")
    (output / "run_manifest.json").write_text(json.dumps({"evidence_version": "2.5.0", "source_matrix_sha256": sha256(source),
        "round18_summary_sha256": sha256(summary), "scientific_status_changes": False}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
