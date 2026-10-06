# Pre-merge correction audit v3

## Scope

This audit corrects two comparative experiments only. The reference mutual-kNN
clustering, baseline configuration, labels and sealed Atlas were not changed.
The fresh gate in `baseline_gate_before_v3_corrections/` reproduces all required
reference ARI/NMI checks exactly at one.

## Union-kNN correction

The earlier union-kNN branch incorrectly filtered a directed nomination when
its neighbour had a lower index. That filter is valid only for reciprocal
mutual-kNN edges. `src/sbernet/graph.py` now deduplicates union edges by existing
undirected edge rather than index order. `tests/test_graph.py` fixes a
one-sided-nomination example and requires `E_mutual` to be a subset of
`E_union`.

`outputs/presubmission_upgrade/edge_sensitivity/` is retained for provenance but
is superseded and must not be used for conclusions. The replacement in
`edge_sensitivity_v3/` uses the same fixed grid and baseline gate. At k=20 the
corrected union graph has 26,305 edges, six communities and ARI .553326 to the
reference static partition (mutual remains 11,787 edges, nine communities and
ARI 1 by construction).

## Synthetic mixed-role correction

The earlier mixed scenario reused one candidate pool for true switches,
boundary cases and shocks. Its outputs are retained but superseded. The v3
configuration fixes disjoint roles before simulation: 10% true switches, 10%
boundary-only, 10% temporary-shock-only and 70% stable nodes. Only the first
group changes latent truth. A deterministic test verifies disjointness and the
declared truth changes.

On the unchanged six-scenario, 20-seed, fixed omega grid, v3 reports maximum
mean ARI at omega=4 (.905442), maximum switch F1 at omega=0 (.259793), minimum
false-switch rate at omega=4 (.008926), and maximum equal-weight reporting
utility at omega=2 (.622792; omega=4: .600375). This supports omega=2 only as
the pre-existing reference trade-off in this benchmark; it does not establish a
universal optimum.

## Freeze and packaging

`docs/ARTIFACT_INDEX.md`, `docs/CODEX_START_HERE.md` and
`docs/CURRENT_STATE.json` were returned to their authenticated `origin/main`
bytes. Current-submission pointers live in `docs/CURRENT_SUBMISSION_STATE.json`
instead. The legacy freeze and current presubmission verifiers are both required
to pass before merge.
