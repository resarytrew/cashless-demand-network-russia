# Failed run notice

This incomplete `r2` directory is not evidence and must not be consumed. The
run stopped before it wrote `identity_test.json`, `source_manifest.csv`,
`run_manifest.json`, or the lineage audit because `identity` was referenced
before assignment while rendering the audit.

The corrected, complete immutable result is
`../data_sense_lineage_20261006_r3/`. Its manifest records the successful run.
