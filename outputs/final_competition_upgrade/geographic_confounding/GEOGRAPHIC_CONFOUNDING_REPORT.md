# Geographic confounding and regional generalisation

All analyses use frozen A–G labels and post-hoc external variables; no output returns to clustering. GroupKFold holds entire `region` values out, with a runtime disjointness assertion. Regional prediction metrics: [{'model': 'multinomial_logistic', 'macro_f1': 0.5490070394457921, 'balanced_accuracy': 0.6112948605146296}, {'model': 'random_forest', 'macro_f1': 0.551205651565717, 'balanced_accuracy': 0.5433530488121167}]. The region-only diagnostic is explicitly an unseen-region training-majority baseline, because a one-hot region model cannot identify an unobserved subject.

Within-region centring subtracts the observed regional median before Kruskal–Wallis testing. Results are associations and do not make a causal geography claim. Leave-one-region-out rows below the minimum n are intentionally omitted.
