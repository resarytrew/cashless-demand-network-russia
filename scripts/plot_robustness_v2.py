"""Publication-exportable descriptive distributions; all 50 seeds included."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

root = Path('outputs/perturbation_v2')
profiles = pd.read_csv(root / 'perturbation_v2_50_archetype_retention.csv')
pairs = pd.read_csv(root / 'perturbation_v2_50_pair_coassignment.csv')
assert profiles.seed.nunique() == 50
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                     'axes.spines.top': False, 'axes.spines.right': False})
fig, axes = plt.subplots(1, 3, figsize=(12, 4.7), layout='constrained')
for ax, metric, title in [(axes[0], 'retention', 'Reference-core retention'),
                          (axes[1], 'precision', 'Destination precision')]:
    values = [profiles.loc[profiles.archetype.eq(a), metric] for a in 'ABCDEFG']
    ax.boxplot(values, tick_labels=list('ABCDEFG'), whis=(5, 95), showmeans=True,
               meanprops={'marker':'o', 'markersize':3, 'markerfacecolor':'#1c5f91', 'markeredgecolor':'#1c5f91'},
               medianprops={'color':'#ba4a00'}, flierprops={'marker':'.', 'markersize':3})
    ax.set_title(title, loc='left', weight='bold')
priority = ['B/E', 'D/F', 'F/G', 'A/D']
axes[2].boxplot([pairs.loc[pairs.pair.eq(p), 'cross_coassignment'] for p in priority],
                tick_labels=priority, whis=(5, 95), showmeans=True,
                meanprops={'marker':'o', 'markersize':3, 'markerfacecolor':'#1c5f91', 'markeredgecolor':'#1c5f91'},
                medianprops={'color':'#ba4a00'}, flierprops={'marker':'.', 'markersize':3})
axes[2].set_title('Cross-profile coassignment', loc='left', weight='bold')
for ax in axes:
    ax.set_ylim(-0.025, 1.025)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1])
    ax.grid(axis='y', alpha=.2)
fig.suptitle('Canonical perturbation robustness v2 | 50 seeds', fontsize=15, weight='bold')
fig.supxlabel('Boxes: q25–q75; whiskers: q05–q95; orange: median; blue dot: mean.\nDescriptive fixed-protocol distributions; historical n=5 excluded.', fontsize=9)
fig.savefig(root / 'perturbation_v2_distributions.png', dpi=180)
fig.savefig(root / 'perturbation_v2_distributions.svg')
