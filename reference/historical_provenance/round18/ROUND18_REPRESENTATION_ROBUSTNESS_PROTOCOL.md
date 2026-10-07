# Round18 — representation robustness without Other

**Status: PLAN_ONLY_NOT_RUN.** Prepared after Round17 statistical integration.
There are no Round18 labels, results, p-values or completion seal. The planning
record is `configs/round18_representation_robustness_plan.yaml`; it is not accepted
by an experiment runner. Executing this experiment is separate future work.

## Question and limits

Does the coarse network-temporal geometry survive representations that never
construct `Other = Total - sum(five published categories)`? Category additivity
and the denominator of Total remain unresolved. Removing Other does not resolve
those metadata questions or establish that the five published categories exhaust
Total. Both variants below must be reported, including negative results. This
plan precedes their computation but is not a registered confirmatory protocol.

## Fixed sample and reference gate

Use exactly the stored 1,904-municipality panel, the same municipality order and
24 months (Jan-2023 to Dec-2024). Keep the five published categories in baseline
order: Продовольствие, Здоровье, Общественное питание, Маркетплейсы, Транспорт.
Do not silently enlarge the sample after removing Other. Report nonpositive or
missing values and stop; no pseudocount, clipping, imputation or sample deletion.

Before any alternative run, reproduce the reference in a new isolated gate
directory using the recorded environment. Require the existing exact feature,
node, edge, weight, graph checksum and static/December/full-supra ARI=NMI=1
checks. Record the same-process/fresh-process determinism checks. A failed gate
produces a failure audit and blocks alternatives; do not search package versions,
edge order or RNG settings to fit stored outputs. Do not rerun old perturbation
seeds or alter the historical pilot provenance resolution. This gate is future
work; Round17 did not rerun the baseline.

Pin raw input hashes, baseline labels/graphs, Atlas, Round17 extract and this
protocol before execution. Check node/sample identity for every alternative;
feature and edge/weight hashes are expected to differ from the reference.
Identical-graph requirements apply to algorithm swaps, not representation changes.

## Two fixed alternative representations

For each month, with positive category values x1...x5 and Total T:

**R1 — five-part relative geometry.** Use CLR(x1...x5): log(xj) minus the mean
of the five logs. Closure within those five parts is optional algebraically and
does not imply additivity to Total. Retain the reference robust-z(log T) level
block. Scale each block by its median pairwise Euclidean distance and concatenate
sqrt(0.70) times the CLR block and sqrt(0.30) times the level block, exactly as
the reference block-weight convention. This isolates omission of Other from
the relative block. No extra ILR variant or basis search is planned: a fixed
orthonormal ILR would preserve the same Aitchison distances.

**R2 — five log category levels plus log Total.** Apply monthly robust scaling
separately to each of log(x1)...log(x5) and log(T): subtract the median and divide
by 1.4826*MAD. Treat the five scaled category coordinates as one block, and log
Total as a second block. Divide each block by its median pairwise distance,
then use sqrt(0.70)/sqrt(0.30) weights as above. Stop on zero MAD or zero block
distance. The five-part block now encodes category levels rather than only
relative composition; correlated size information may be repeated. Thus R2 is
a broader representation sensitivity check, not a pure Other ablation.

For both, hold mutual-kNN k=20, adaptive RBF construction, static December isolate
fallback ON, temporal-layer fallback OFF, omega=2 with the reference global
median intralayer-weight convention, Louvain resolution=0.5 and seed=0 fixed.
Use the existing canonical graph order. Only the representation changes.
Seed 0 isolates the reference implementation comparison; it does not establish
optimizer robustness. No search over representations, weights or seeds is allowed.

## Comparisons and reporting

Report separately for static December, temporal December and full supra labels:

1. ARI, NMI (arithmetic normalization), community counts and sizes, isolate and
   edge/weight diagnostics. Calculate pair coassignment Jaccard and agreement
   from contingency-table pair counts, without a dense supra matrix. Empty pair
   unions are reported as undefined. Report both metrics because negative-pair
   agreement can dominate.
2. Reference A–G retention, destination precision and Jaccard. Destination means
   largest reference/destination intersection, ties by smallest numeric destination
   ID; it need not be bijective. Retention alone never establishes boundaries.
   Publish the full overlap table and all merged/split destinations.
3. Fixed pre-experiment Atlas `stability_class == core` subsets: core retention
   and destination precision, with counts and NA for empty cores. Do not select
   new cores after viewing R1/R2. Publish municipality-level destination, reference
   overlap measures, and old core/transition status without overwriting Atlas.
4. A/D/F/G behavior: reference membership migration, D/F and F/G cross-coassignment,
   F within-pair coassignment and allocation across D/G dominant destinations.
   Report D/G collapse, split or loss of F's autonomous destination explicitly.
   One seed yields a partition comparison, not a new consensus/entropy posterior;
   do not mislabel a single-run result as an affinity ensemble.
5. Freeze the Round17 external sample and wages. First report wage summaries by
   alternative communities and the reference A/D/F/G composition of each. For
   an explicitly descriptive secondary DFG rank check, assign each alternative
   community the reference profile with largest intersection over all 1,904
   municipalities (ties A...G; exclude non-A–G technical reference labels).
   This uses no wages, but it is reference-derived rather than independent semantic
   discovery. Restrict to the original Altai DFG six cases, retain all six in the
   audit, and calculate the same G=1/F=2/D=3 Spearman only if all receive D/F/G
   labels and all three ranks are present. Otherwise report NOT_ESTIMABLE with
   the exact collapse/coverage reason. Never force a missing F group or quietly
   drop changed cases. The original Round17 gradient with unchanged reference
   labels is a fixed comparator, not evidence that a new partition survived.

No numerical pass threshold or preferred representation is selected after seeing
results. Present all tables together and assess which qualitative conclusions
are consistent, weakened, unresolved or contradicted. If both representations
retain the relevant geometry, the scoped conclusion is that those features do
not depend on including residual Other under these tested specifications. If
they do not, report representation dependence; do not dismiss the negative case.
Neither outcome establishes general immunity to representation choices.

## Execution and evidence controls for future implementation

- New runner and schema/determinism tests; separate material config/run for R1
  and R2, expanded from this plan before any computation. No calls that fit on
  external wages. Preserve sparse graphs; never allocate 45,696 x 45,696 arrays.
- Per-variant, per-seed raw labels, feature/graph checksums, overlap tables,
  metrics, municipality diagnostics and failure reports. Verified checkpoints
  skip complete seeds; any explicit force action must archive, never overwrite.
- Manifest records Python/packages, commit/dirty state, config/input/source
  hashes and seed. Write completion last only after all required outputs pass.
- New Round18 audit and master evidence version after both variants finish;
  preserve Round17 and all prior artifacts. No status change from planning alone.
- Run the full test suite and fresh-process replay before any claims are updated.

Estimated work is implementation, reference gates, two fixed-representation runs,
metric replay, and a conservative comparative audit. Runtime is not estimated
from unexecuted experiments.
