# Stability Atlas v2.2 — robustness findings

## What changed from v2.1

v2.2 keeps the same family-balanced co-assignment construction but makes the
interpretation stricter and adds two sensitivity layers.

- The normalized A–G quantities are named **affinity shares**, not probabilities.
- The **hard consensus class** is kept separate from the **D–G transition direction**.
- Four leave-one-family-out (LOFO) consensuses are recomputed, omitting one of:
  perturbation, alpha, gamma, or algorithm/Leiden.
- A consensus-core-anchor sensitivity analysis recomputes A–G affinities using
  only the top 25% of each reference profile by full-consensus own-profile affinity.
  This is a boundary-dilution sensitivity check, not independent validation.

The four experiment families retain equal weight in the full consensus.

## Main profile robustness

| Reference profile | n | Consensus matches reference | All 4 LOFO runs match full | Anchor class matches full | Median entropy | Median margin |
|---|---:|---:|---:|---:|---:|---:|
| A | 141 | 96.45% | 95.74% | 97.16% | 0.386 | 0.735 |
| B | 98 | 100.00% | 100.00% | 100.00% | 0.423 | 0.317 |
| C | 29 | 93.10% | 72.41% | 72.41% | 0.305 | 0.842 |
| D | 153 | 98.69% | 98.69% | 100.00% | 0.528 | 0.344 |
| E | 186 | 90.86% | 97.85% | 100.00% | 0.461 | 0.288 |
| F | 327 | 10.70% | 58.72% | 58.41% | 0.638 | 0.094 |
| G | 965 | 100.00% | 99.59% | 100.00% | 0.537 | 0.428 |

The central asymmetry survives the stronger checks: F is uniquely diffuse at
the macro scale, while B, D, and G behave as strong reference cores. C remains
small and sensitivity-prone.

## Leave-one-family-out

Across all 1904 municipalities:

| Omitted family | Match full consensus | Match reference |
|---|---:|---:|
| perturbation | 98.48% | 81.72% |
| alpha | 97.79% | 83.82% |
| gamma | 98.74% | 81.78% |
| algorithm/Leiden | 93.07% | 88.50% |

The algorithm family has the largest effect on the full hard consensus.
Because the reference partition itself is Louvain, the higher reference match
after omitting Leiden is expected and must not be interpreted as evidence that
Louvain is intrinsically superior.

For reference-F only:

| Omitted family | Match full consensus | Remains F | D side | G side |
|---|---:|---:|---:|---:|
| perturbation | 95.11% | 5.81% | 49.54% | 50.46% |
| alpha | 90.83% | 16.82% | 49.85% | 50.15% |
| gamma | 95.41% | 6.12% | 49.85% | 50.15% |
| algorithm/Leiden | 63.00% | 43.12% | 56.88% | 43.12% |

Thus a **D–G transition interpretation persists under these tested family omissions**, but the exact hard
class assigned to individual F municipalities is meaningfully
algorithm-sensitive. This is precisely why v2.2 separates transition direction
from hard class.

## F transition result

Reference F contains 327 municipalities.

Hard family-balanced consensus classes:

- D: 160
- G: 124
- F: 35
- A: 8

D–G family-vote direction:

- D-leaning: 160
- G-leaning: 161
- mixed: 6

LOFO hard-class stability:

- 4/4 omissions match the full class: 192 municipalities
- 3/4: 99
- 2/4: 25
- 1/4: 11

Therefore 291/327 (88.99%) retain the full hard class under at least three of
the four family omissions. At the same time, only 35/327 retain F as the full
consensus class. These facts support interpreting F as a broad transition zone
rather than as a peer macro-regime comparable to B, D, or G.

## Anchor sensitivity

Consensus-core anchors are the top 25% within each reference profile by
full-consensus raw affinity to that same profile. This choice is deterministic
and is explicitly a sensitivity analysis, not a new external validation.

The hard class is unchanged relative to all-reference-member affinities for:

- A: 97.16%
- B: 100%
- C: 72.41%
- D: 100%
- E: 100%
- F: 58.41%
- G: 100%

Again, F and C are the profiles most sensitive to how reference boundaries are
defined. D and G remain unchanged at the hard-class level.

## Interpretation

The evidence does **not** support seven equally robust economic types.

A better representation is a topology:

- **B–E**: overlapping reference profiles, with B retaining a strong consensus core; geographic/metropolitan interpretation requires verified contextual joins;
- **D–F–G**: the main macro-continuum, where D and G retain strong consensus reference cores and F is
  the transition belt;
- **A**: reference profile with strong but not perfect consensus stability; a northern/Far-Eastern interpretation is not established by this atlas;
- **C**: small unresolved/contextual fragment whose interpretation should remain
  cautious.

The normalized affinity shares are descriptive consensus affinities, not
posterior probabilities and not evidence of causal economic mechanisms.

## Engineering release 2.2.1

The current build uses `configs/stability_atlas_v2_2_1.yaml`. Numerical v2.2
results are preserved on the registered inputs; the release adds provenance,
verified resume, an offline viewer and explicit unresolved zero-affinity handling.
Strong consensus cores do not establish exact-boundary or beyond-context robustness.
C retains its existing unsupported-beyond-context status. No new evidence status
is inferred from consensus. LOFO D/G side (affinity sign) and family-vote direction
are different statistics. See `docs/ATLAS_REPRODUCTION.md`.
