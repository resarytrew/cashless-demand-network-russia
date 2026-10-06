# Data-quality schema correction

The completed ingestion values were unchanged. This patch adds the required
`coverage_n` field, equal to the already reported `reference_coverage_n` (zero),
to meet the published data-quality contract. The source coverage and all raw
checksums are unchanged.
