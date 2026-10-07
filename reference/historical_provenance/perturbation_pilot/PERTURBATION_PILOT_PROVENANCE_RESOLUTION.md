# Historical perturbation pilot provenance resolution

Status: **SUPERSEDED_NON_REPRODUCIBLE_HISTORICAL_PILOT**.

This explicit user-authorized methodological decision supersedes the earlier requirement to reproduce the historical n=5 before Leiden or protocol v2. Baseline and graph identity gates remain mandatory. Historical files and failure reports remain untouched.

The reference Louvain baseline reproduces exactly (full-supra and December ARI=NMI=1). The preserved historical runner also reconstructs the same graph checksum and unperturbed partition. Its seed 0 produces K_supra=13, ARI=0.45349215671565724, NMI=0.5873910678631652; December K=9, ARI=0.7364737312917007, NMI=0.7572197472434098; B/E cross-coassignment=0.2435813034891376. These differ materially from the former canonical CSVs.

The user reports an independent execution in another environment reproducing all these values exactly, including B within-pair=0.6263412581527457 and E within-pair=0.989247311827957. This external replication is user-provided evidence; its environment manifest was not supplied here. The mismatch therefore cannot be treated as specific to this Codex execution. Its underlying cause remains unestablished.

The old CSVs and saved runner are not a demonstrated reproducible computational chain. The historical n=5 is no longer quantitative evidence, and its conclusions must not be inherited into a new master evidence matrix as confirmed findings. The matrix uses historical_perturbation_pilot_status=SUPERSEDED_NON_REPRODUCIBLE. No package/RNG/edge-order search is authorized to fit the old CSVs.

Protocol v2 is a new canonical analysis, not an expansion of that pilot. Historical seed values are NON-COMPARABLE/SUPERSEDED; they are not a v2 reproduction target. Leiden is independently authorized by its passed baseline and graph gates.

Local evidence: ../outputs/reproducibility_gates/attempt_20260919_01/pilot/seed_00_raw.json, pilot_comparisons.csv, and PERTURBATION_PILOT_REPRODUCIBILITY_FAILURE.md.
