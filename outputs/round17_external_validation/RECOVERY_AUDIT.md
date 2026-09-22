# Round17 recovery/integration audit

Original ZIP SHA256: c917d91e59c50dd367ba058b6b7f674325e46a54d54e1d080ccb460abc4a71a3.
All 14 entries in the supplied SHA256SUMS.txt were checked before integration. All 15 package files are preserved byte-for-byte in reference/round17_external_validation/recovered. The reference Python implementation ran successfully; all 10 tests match the supplied expected values at tolerance 1e-10 * max(1, abs(expected)). Region/profile counts and DFG medians are gated too.

58 exact municipality-name joins match current reference profile, consensus and stability; current Atlas bytes match the historical Git blob. No fuzzy matching or silent relabeling. Historical panel_index was NOT supplied: assigned from current Atlas, never described as historically verified. The recovered source_manifest hash column mislabeled the Atlas Git blob SHA1 as sha256; the derived manifest explicitly types it, and current Atlas SHA256 is recorded separately. Recovered input files are not corrected.

Original Rosstat documents, historical workbook, crosswalk file and row/page extraction locations are not packaged; reported raw-source SHA256 values cannot be verified locally. Normalized data/statistics replay offline, but original source extraction and historical workbook recovery do not. Population-source URL is missing in recovery and remains missing. source_provenance.csv maps every nonmissing normalized indicator to its reported source and canonical data-record position. Investments are available for 28 Yakutia cases only; 30 missing values are preserved. No proxy substitution.

Independent package code reproduces the reference methods explicitly: two-sided Spearman with asymptotic p-values; Yakutia logsalary on intercept/loginvestment/logpopulation/urban share with HC3 normal inference; Altai logsalary on intercept/ordinal rank/logpopulation/urban share with conventional t inference; two-sided Mann-Whitney auto method and continuity correction with signed Cliff delta; descriptive medians. No fitting of clustering models or baseline rerun occurs.

Interpretation deviations from recovery narrative are deliberate and conservative: nonsignificant population correlation does not establish independence; nominal employee wages are not household income; Altai F has n=1 and adjusted p=0.088869; Khabarovsk p=0.279853 retained; B/E have no external validation; C remains contextual; mining mechanism is unestablished. Old A-G robustness statuses and reference parameters are unchanged. New claims are interpretation support with scope limitations, not confirmatory tests.

Round18 is planned separately and has no results here. Output completion is written last; any integration failure produces FAILURE_AUDIT.json with no completion seal. Sealed output is never overwritten.


Gates: {
  "checksums_verified": 14,
  "atlas_git_blob_sha1": "3dd8cd196f4636f6279cf4c425257b4a0dac5629"
}
