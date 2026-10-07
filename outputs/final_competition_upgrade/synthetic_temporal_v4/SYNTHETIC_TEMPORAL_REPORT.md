# Synthetic temporal benchmark v4

This is an additive methodological correction to `synthetic_temporal_v3`. It uses the same
generator, scenarios, 20 seeds, model grid, and bootstrap seed. It does not use or alter the
real municipality data, the baseline clustering, or the reference omega=2.

The primary partition-quality measures are label-permutation-invariant monthly ARI and NMI,
summarised across months. `legacy_flattened_ari` and `legacy_flattened_nmi` are retained only
for forensic comparison with v3 and never enter an omega comparison or utility. These metrics are retained only for forensic comparability with synthetic_temporal_v3 and are not used as the primary partition-quality metric or for omega comparison.

## Mean monthly ARI across all scenarios

| omega | mean_monthly_ari | transition_switch_f1 | transition_false_switch_rate | transition_delay | no_transition_false_switch_rate |
| --- | --- | --- | --- | --- | --- |
| 0.0000 | 0.8804 | 0.5196 | 0.0329 | 0.2729 | 0.0401 |
| 0.2500 | 0.8628 | 0.4555 | 0.0641 | 0.2486 | 0.0816 |
| 0.5000 | 0.8804 | 0.4705 | 0.0482 | 0.2896 | 0.0567 |
| 1.0000 | 0.8931 | 0.4977 | 0.0299 | 0.3604 | 0.0332 |
| 2.0000 | 0.8965 | 0.3877 | 0.0154 | 0.6354 | 0.0055 |
| 4.0000 | 0.9121 | 0.2748 | 0.0146 | 0.9330 | 0.0032 |

## Mixed scenario

| omega | monthly_ari_mean | monthly_nmi_mean | node_state_accuracy | switch_precision | switch_recall | switch_f1 | false_switch_rate | false_switches | missed_switches | absolute_change_point_delay |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.0000 | 0.7845 | 0.8066 | 0.9351 | 0.0651 | 0.5375 | 0.1155 | 0.0734 | 96.0500 | 5.5500 | 0.5250 |
| 0.2500 | 0.7538 | 0.7917 | 0.8816 | 0.0562 | 0.6458 | 0.1015 | 0.1299 | 169.9500 | 4.2500 | 0.4167 |
| 0.5000 | 0.7837 | 0.8096 | 0.9051 | 0.0613 | 0.5583 | 0.1080 | 0.0916 | 119.8500 | 5.3000 | 0.5375 |
| 1.0000 | 0.8052 | 0.8224 | 0.9243 | 0.0840 | 0.4833 | 0.1408 | 0.0535 | 69.9500 | 6.2000 | 0.6500 |
| 2.0000 | 0.8115 | 0.8313 | 0.9423 | 0.1758 | 0.4458 | 0.2460 | 0.0205 | 26.8000 | 6.6500 | 0.6958 |
| 4.0000 | 0.8141 | 0.8353 | 0.9282 | 0.1921 | 0.3208 | 0.2281 | 0.0175 | 22.8500 | 8.1500 | 0.9343 |

At reference omega=2, state recovery is stronger than event recovery: node-state accuracy is 0.942, while switch F1 is 0.246. Temporal regularisation suppresses false instability but can miss genuine changes.

Transition and no-transition scenarios are evaluated separately. The former use monthly ARI,
switch F1, false-switch rate, and absolute delay; the latter use monthly ARI and false-switch
rate. `tradeoff_summary.csv` contains scenario-local equal-weight descriptive utilities and
Pareto flags. They are not combined into a universal score, and v4 does not select a best omega.

The historical v3 result remains preserved. V4 supersedes it only for synthetic temporal
calibration claims. No real-data result or A-G status changed.
