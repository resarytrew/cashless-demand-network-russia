# KEFRiN provenance

## Method and publication

- Method: **K-Means Extended to Feature-Rich Networks (KEFRiN)**; Round22 uses
  the cosine-distance variant **KEFRiNc**.
- Authors: Soroosh Shalileh and Boris Mirkin.
- Publication: *Community Partitioning over Feature-Rich Networks Using an
  Extended K-Means Method*, Entropy 24(5), 626 (2022).
- DOI: <https://doi.org/10.3390/e24050626>.
- Open full text: <https://pmc.ncbi.nlm.nih.gov/articles/PMC9142054/>.

## Author upstream and license gate

- Author repository: <https://github.com/Sorooshi/KEFRiN>.
- Pinned inspected commit: `f9f96b1a778cb8d2e5ba85baae452dc813c4f110`.
- Repository ownership: the GitHub account identifies Soroosh Shalileh and the
  paper's data-availability statement points to this repository.
- License status: **UNCLEAR / NOT VERIFIED**. At the pinned commit the Git tree
  contains no `LICENSE` or `COPYING` file and GitHub's repository API reports no
  detected license. The README says “MIT”, but that statement is not accompanied
  by license text. It is therefore not treated as permission to copy source.

No upstream source file, package, function, notebook or competitor implementation
is copied, imported, installed or vendored in Round22. The repository is recorded
only as author/upstream provenance and as the paper's declared data/code location.

## Independent implementation from the paper

Round22 implements only the published mathematical procedure:

1. Quantitative L1 columns use paper preprocessing option Z: subtract each column
   mean and divide by its population standard deviation.
2. The weighted reference adjacency uses paper option M:
   `P_ij <- P_ij - P_i+ P_+j / P_++`.
3. Feature and network cosine distances receive the paper's equal weights
   `rho=xi=1`.
4. The first seed is a random node fixed by the run seed. Each later seed is the
   remaining node maximizing the sum of combined distances to selected seeds.
5. Nodes are assigned by minimum combined distance; feature and network centers
   are within-cluster means; iteration stops when assignments no longer change.
6. Empty clusters, non-finite values, zero-norm vectors, failure to return exact
   K, or hitting the YAML safety cap are explicit failures.

Round22 fixes `K=9`, uses seed 0 as the canonical partition, and reports seeds
0–9 separately. It does not select a seed or parameter by L1 agreement, ICVI or
external data. The 1,000-iteration cap is an operational failure guard declared
in YAML, not an alternative stopping rule.

## Components used and not used

Used: published equations, published Z/M preprocessing, published equal weights,
published cosine variant and published initialization/stopping rules.

Not used: upstream source code, upstream data, upstream empirical per-dataset
preprocessing choices, competitor code, temporal KEFRiN extensions, automatic K
selection, external variables, geography, market access, mobility or Rosstat
during fitting.

Local compatibility code is isolated under `src/sbernet/benchmarks/kefrin.py` and
`src/sbernet/kefrin_benchmark.py`; it does not modify baseline clustering classes.

## Attribute-induced graph dependence

The reference network is derived from the same behavioral feature geometry that
supplies the KEFRiN attribute block. Graph and attributes are therefore not
statistically independent information sources. Round22 tests sensitivity to a
held-out algorithmic formulation; it is not independent-data validation.

