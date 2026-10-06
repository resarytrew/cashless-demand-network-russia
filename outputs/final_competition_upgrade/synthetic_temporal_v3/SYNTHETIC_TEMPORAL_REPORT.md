# Synthetic temporal benchmark

A controlled benchmark used the reference-style composition (five centred composition coordinates) plus level block, mutual-kNN graphs, Louvain resolution .5, and a preregistered omega grid 0/.25/.5/1/2/4. It is not fitted to Russian data. Six scenarios and 20 independently seeded panels per scenario are recorded in `seed_metrics.csv`.
The mixed scenario has disjoint node roles fixed before simulation: 10% true switches, 10% boundary-only nodes, 10% temporary-shock-only nodes, and 70% stable nodes. Only true-switch nodes change latent truth.

Across scenarios, maximum mean partition ARI occurs at omega=4; maximum switch F1 at omega=0; and minimum false-switch rate at omega=4. The transparent equal-weight balanced reporting utility is highest at omega=2. Scenario-specific results and CIs are in `omega_aggregate.csv` and `pareto_summary.csv`; a universal omega is not inferred.

Reference omega=2 is reported as one fixed trade-off specification. A calibrated specification is only reported where a scenario's preregistered utility is higher; it does not replace historical reference outputs.
