# National external validation

This is an external interpretation layer using frozen A–G labels; it neither constructs nor tunes the network or clustering. Reference universe: 1,904; verified data lineage: 1,903; unresolved lineage excluded: 1; valid gated OKTMO8: 1903.

Core coverage is population 1903/1903 (100.00%), wage 1890/1903 (99.32%), total employment 1890/1903 (99.32%), and sector employment 1888/1903 (99.21%). Investment is limited: the largest tested annual coverage is 1.00%, so investment is excluded from the central national analysis.

Global profile differences are in `external_global_tests.csv`; their epsilon-squared effects are population=0.468, wage=0.633, employment_total=0.516. Sector composition PERMANOVA on CLR Euclidean distances has pseudo-F=62.357, p=0.001, n=1883. D/F/G medians and monotonic checks are in `dfg_transition.csv`; they are descriptive external consistency checks, not a claim of stable exact boundaries.

Prediction uses pipeline-contained imputation/scaling and stratified CV. Metrics are in `external_prediction_metrics.csv`; `permutation_label_baseline.csv` is the deliberately label-shuffled diagnostic. All inferential results are exploratory and susceptible to coverage/selection effects documented in the selection-bias tables.
