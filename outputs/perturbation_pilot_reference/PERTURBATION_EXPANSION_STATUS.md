# Expanded supra-perturbation status

Target: >=20 runs; preferred 30–50.

Current accepted evidence: 5 completed perturbation runs from the prior audit. This is insufficient to characterize the distribution of B/E boundary collapse. The previously reported mean/max are descriptive pilot statistics only.

A 20-run parallel attempt in the current runtime did not complete within the execution limit: only one worker finished before timeout. No partial result is incorporated into the evidence ledger.

Therefore the B/E boundary-distribution claim remains `UNRESOLVED_METHOD`.

The reproducible runner is `run_supra_perturbation_consensus.py`. It first verifies reconstruction ARI=1.0 and then runs the same 5% intralayer edge-drop + 2% weight-jitter experiment.

Decision outputs required before status can change:
- full distribution of B/E cross-coassignment (median, IQR, q10/q90, tail shares >0.5 and >0.9);
- run-level K and ARI;
- per-profile retention/coassignment distributions;
- sensitivity of conclusions to excluding any extreme run.
