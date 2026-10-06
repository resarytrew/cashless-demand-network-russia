# Official Data -> Sense package scope

The publisher archive is preserved unchanged under `data/external/raw/sberindex_data_sense/`; its extracted inventory is `official_package_inventory.csv`. The archive contains `consumption.parquet`, `market_access.parquet`, `connection.parquet`, and one methodology PDF. It contains no population, wage, employment, migration, or BDMO files.

`data_sense_raw_audit.csv` records the observed schemas. The methodology calls the consumption measure `consumption`, whereas the actual parquet field is `value`; this discrepancy is reported rather than silently renamed in the raw audit.
