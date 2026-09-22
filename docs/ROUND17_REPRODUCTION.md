# Round17 external economic interpretation — replay contract

Round17 is evidence v2.4.0. Atlas remains v2.2.1; the reference model and the
Round16 scientific robustness status registry are unchanged. The input is the
recovered normalized external extract, not a new scrape or a reconstructed
historical workbook. All 58 current Atlas joins and all ten supplied statistics
are required gates. No clustering or baseline rerun is involved.

## Offline replay

Install dependencies once (installation needs packages available locally or online):

```powershell
python -m pip install -r outputs/evidence_v2_2_0/requirements-used.txt
python -m pip install -r reference/round17_external_validation/requirements-replay.txt
python -m pip install -e . --no-deps
$env:PYTHONPATH = 'src;.;scripts'
$env:PYTHONUTF8 = '1'
python scripts/run_round17_external_validation.py
python scripts/run_round17_external_validation.py --output-dir "$env:TEMP/round17-independent-replay"
python -m pytest -q
python scripts/verify_current_artifacts.py
```

Use an empty replay destination. A completed destination is verified without
rewriting it. An incomplete destination is preserved and rejected: inspect its
failure audit and use a different path. There is deliberately no overwrite/force
option for Round17. CSVs, statistics and the report are deterministic in the
recorded environment; manifests additionally record runtime timestamp, commit,
dirty state, versions and hashes. No network is used during replay.

The YAML fixes all samples, methods, log transforms, ordinal G=1/F=2/D=3 coding,
HC3 normal inference, conventional adjusted Altai t inference, Mann–Whitney
settings and tolerances. Recovered Spearman p-values use SciPy's asymptotic
method, not an exact tied-rank permutation test. All p-values are exploratory.
Any method change needs a separate config/evidence round, not replacement of
the sealed Round17 output.

## Files and integrity chain

- `reference/round17_external_validation/recovered/`: 15 exact files from the
  supplied ZIP, including the original reference program and 14 checksums.
- `configs/round17_external_validation.yaml`: pinned input hashes, methods,
  interpretation scopes and report text.
- `src/sbernet/validation/external_economic.py`: independent implementation.
- `outputs/round17_external_validation/`: normalized current-Atlas table,
  explicit join audit, indicator provenance, statistics, generated report,
  claim matrix and new master matrix retaining all Round16 columns unchanged.
- `run_manifest.json`: inputs, implementation/config hashes, versions and every
  derived output hash, including `output_checksums.csv`.
- `COMPLETED.json`: written last by atomic rename; seals the run manifest.
  The output inventory excludes itself and its enclosing manifest/seal to avoid
  circular hashes; the manifest seals the inventory and completion seals the manifest.
- `reference/round17_external_validation/INTEGRATION_MANIFEST.json` and its
  SHA256 sidecar: repository integration files, exact snapshots of changed
  prior documentation/tooling, and current hashes. Historical manifests are not
  modified. The current verifier checks all prior evidence at its original path.

Git review remains the trust boundary for these local manifests; they are
integrity records, not external digital signatures. Source transitions cannot
redirect old outputs, datasets or model source to snapshots.

## Scientific and provenance limitations

The sample has A43/C4/D2/F2/G7, no B/E, and only four regions. Altai DFG is
D2/F1/G3. The adjusted Altai p=0.088869 and Khabarovsk p=0.279853 are retained.
Population nonsignificance is not evidence of independence. Nominal employee
wages do not measure household income or real purchasing power. A's sector or
mining mechanism is not established. C remains contextual/unresolved; F gains
limited interpretation support without any upgrade to exact-boundary stability.

Original source files and historical source row/page locations were not supplied.
Their reported SHA256 values and crosswalk extraction cannot be independently
verified. Replay begins with the packaged normalized extract. The historical
panel index was absent; the current Atlas supplies it. The recovered Atlas hash
is a Git blob SHA1, explicitly distinguished from a file SHA256. These are
recorded limitations, not silently repaired data. Missing investments remain
missing outside Yakutia. External data never enter model construction/tuning.
