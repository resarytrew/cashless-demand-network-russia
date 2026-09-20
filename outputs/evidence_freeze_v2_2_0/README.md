# Canonical evidence v2.2.0 — forensic freeze

Canonical artifact: [MASTER_PROFILE_EVIDENCE_MATRIX_v2.2.0.csv](MASTER_PROFILE_EVIDENCE_MATRIX_v2.2.0.csv). This is the canonical forensic revision of evidence version 2.2.0, stored in a new directory so the prior mixed matrix and its freeze remain intact. No new scientific version or profile-status change is asserted.

The matrix admits only Leiden and perturbation-v2 numerical fields replayed from saved raw partitions, with immutable reference inputs and prior gate artifacts. It is not a claim that clustering was freshly rerun: no clustering experiment was executed. 3748 numerical comparisons passed. All seven profiles and all 50 seeds are included without removal of inconvenient runs.

Current scientific statuses are copied verbatim into [SCIENTIFIC_STATUS_REGISTRY_UNCHANGED.csv](SCIENTIFIC_STATUS_REGISTRY_UNCHANGED.csv) as governance annotations. They are deliberately not represented as newly reproduced population/density, spatial, mobility or other contextual evidence. Missing contextual artifacts do not cause status promotion or demotion.

Files:

- [S_Dbw forensic audit](S_DBW_FORENSIC_AUDIT.md), complete pair/cluster traces and six explicitly diagnostic formula variants.
- [Evidence admissibility](EVIDENCE_ADMISSIBILITY.csv): exclusions and scope limitations.
- [Matrix field lineage](MATRIX_FIELD_LINEAGE.csv): input source and derivation mapping.
- VERIFIED_PROFILE_RESULTS.csv, VERIFIED_PAIR_RESULTS.csv, VERIFIED_RUN_RESULTS.csv and CANONICAL_DISTRIBUTIONS.csv: rebuilt numeric basis.
- EVIDENCE_NUMERIC_REPLAY_CHECKS.csv: exact stored/recomputed values and differences.
- EVIDENCE_FREEZE_MANIFEST.json: version, scope, matrix hash, inventory hash, environment, limitations and verification command.
- EVIDENCE_FREEZE_FILES_SHA256.csv: path, bytes, SHA256 and role for the dependency/evidence snapshot.
- EVIDENCE_FREEZE_MANIFEST.sha256: detached manifest digest; the inventory does not contain itself or the manifest, avoiding circular hashing.

The inventory includes excluded historical files for preservation and traceability. Their presence does not admit them as evidence; its role field and EVIDENCE_ADMISSIBILITY.csv distinguish provenance material from admissible quantitative inputs. Historical pilot status remains SUPERSEDED_NON_REPRODUCIBLE. S_Dbw is excluded from numerical ranking because historical implementation provenance is unresolved and the executed Round 14 definition is undefined on these partitions.

Verification from the repository root:

```powershell
$env:PYTHONPATH = 'src;.'
python scripts/canonical_evidence_freeze.py verify
```

Metric replay commands are forensic_sdbw.py and canonical_evidence_freeze.py build. They require a new output directory to avoid overwriting this freeze. The audit config is configs/evidence_freeze_v2_2_0.yaml. Prior source and run manifests remain immutable; the supplied working copy has no git commit metadata.
