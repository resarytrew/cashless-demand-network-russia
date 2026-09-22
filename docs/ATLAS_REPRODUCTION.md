# Atlas 2.2.1 — reproduction and artifact contract

This engineering release preserves the numerical v2.2 design on the authenticated
recorded inputs. It is a deterministic saved-label aggregation, not new clustering
or a new scientific evidence round. Evidence remains v2.3.0.

## Run in the recorded environment

From the repository root, PowerShell:

```powershell
python -m pip install -r outputs/evidence_v2_2_0/requirements-used.txt
python -m pip install -e . --no-deps
$env:PYTHONPATH = 'src;.;scripts'
$env:PYTHONUTF8 = '1'
python -m pytest -q
python scripts/verify_current_artifacts.py
python scripts/build_soft_consensus_v2_2.py --config configs/stability_atlas_v2_2_1.yaml --output-dir outputs/atlas_local_check
```

Use a new output name if the environment or source has changed. Repeating the
same command with compatible inputs verifies hashes and skips the completed build.
No clustering seeds are rerun. `--force` archives only an output positively marked
as managed by this Atlas runner; it cannot replace a historical/non-managed output.
Partial or corrupted outputs do not count as completed results.

The default config points to the committed `outputs/stability_atlas_v2_2_1` artifact.
After a checkout/environment change, inspect its completed hashes directly rather
than trying to rewrite it. Build into a new directory for an independent replay.

## Input provenance

`reference/engineering_20260922/atlas_inputs.json` authenticates the 56 saved runs,
reference labels, profile map and municipality stability table against historical
freeze inventories. It binds the registered NPY bytes to the historical ordered
panel and calendar; NPY format itself contains no municipality IDs. This is an
explicit inherited ordering contract, not a new empirical ordering discovery.
CSV labels select the configured month by name and align unique municipality keys.

Input hash failures abort before output creation. New/permuted input files cannot
be admitted merely by matching array dimensions. New experiment inputs require
separate, reviewed provenance and a new protocol/config. Current engineering code
supports the recorded equal weights across four families; it does not silently
turn an edited weight grid into a new scientific result.

## Output provenance

`run_manifest.json` records resolved YAML and hash, actual source hashes, Python and
package versions, Git revision and dirty flag, reference order/calendar hashes,
input registry hash and scientific scope. `COMPLETED.json` seals every generated
file and is written atomically last. Resuming verifies the exact file set, content
hashes and context fingerprint. The Git dirty flag describes the build context;
source hashes identify exact implementation bytes even before a commit exists.

Open `index.html` locally for a searchable, offline report, or consume
`municipality_affinity_atlas.csv` and `DATA_DICTIONARY.md`. The viewer makes no
external network requests and does not infer geographic joins. The figure shown
as a temporal trajectory contains saved community IDs, not spending growth.

## Interpretation

Equal family weights give a single Leiden run 25% of the aggregate, while each of
50 perturbations receives 0.5%. These are chosen descriptive weights, not estimates
of evidence reliability. LOFO and anchor sensitivity already exist. A new weight
or anchor-grid experiment needs its own protocol, gates, audit and evidence round.

Zero total affinity produces `unresolved` and undefined entropy. Exact positive
ties use configured stable profile order and have zero margin. Micro-community
comparisons remain descriptive; their threshold stability class is unresolved.
LOFO side agreement uses affinity-balance sign; D/G direction uses family votes.
They must not be reported as the same statistic. A–G scientific statuses are unchanged.
