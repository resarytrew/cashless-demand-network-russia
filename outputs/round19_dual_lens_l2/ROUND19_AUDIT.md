# Round19 dual-lens audit

## Method

Separate additive L2 experiment under `configs/round19_dual_lens_l2.yaml`; L1 files are read-only inputs. No K selection, resolution tuning, graph-rule tuning or post-result parameter change occurred. L2 keeps k=20, omega=2, resolution=.5 and seed=0 for controlled comparison, but it is not a replacement baseline.

## Inputs and exclusions

Verified national population/wage/employment and official hackathon market access are included. Urban share is unavailable nationally and is explicitly absent. Complete cases: 1876; exclusions: 28. Mobility is a holdout only.

## Independence accounting

See `external_independence_accounting.csv`. Variables entering L2 cannot validate L2 independently. Mobility remains independent but selected and incomplete (268 exact matches).

## What changed

An additional L2 partition, comparison tables, profile diagnostics, rule audit and holdout analysis were created.

## What did not change

Baseline data/features/graphs/labels, A–G mapping, k=20, omega=2, resolution=.5, L1 external results and A–G scientific statuses are unchanged. L2 does not promote A–G to universal economic types.
