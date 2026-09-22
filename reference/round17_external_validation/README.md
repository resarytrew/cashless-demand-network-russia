# Round17 immutable integration provenance

`recovered/` retains all 15 files from the user-supplied
`independent_economic_validation_reproducible.zip`, without text conversion.
Archive SHA256: `c917d91e59c50dd367ba058b6b7f674325e46a54d54e1d080ccb460abc4a71a3`.
The 14 checksums in `recovered/SHA256SUMS.txt` cover all other recovered files.

Recovery narratives are historical source material. The generated Round17 report
and claim matrix record the current conservative interpretation and limitations.
Reported original Rosstat/source-workbook hashes do not mean that those absent
raw documents were checked during this integration.

`snapshots/` preserves pre-integration bytes for changed documentation and
tooling at base commit `4a5b3c884bcd951134f5cfd5e2797c3d3587c2b8`.
`INTEGRATION_MANIFEST.json` lists explicit old/current hashes and new files;
its sidecar seals that manifest. This extends the integrity chain without
rewriting any prior manifest or evidence artifact. Git history is the trust
anchor; the hash sidecar is not a cryptographic signature.

`requirements-replay.txt` adds the regression dependencies without modifying
historical recorded requirements. Full package versions are in the run manifest.
