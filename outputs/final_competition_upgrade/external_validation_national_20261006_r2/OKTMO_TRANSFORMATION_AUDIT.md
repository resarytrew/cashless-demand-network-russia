# OKTMO 11→8 transformation audit

Reference universe: 1,904. Verified lineage: 1,903. Excluded unresolved lineage: 1. Validated OKTMO8: 1903.

The directory code is held as text, hyphens are formatting only, and leading zeroes remain strings. A candidate is permitted only when the verified SberIndex municipality record has 11 digits, suffix `000`, and its first eight digits occur in the independently ingested upper-level BDMO municipal-code universe. Duplicate candidates are rejected as many-to-one conflicts. No names are used as a join key.

Official semantic references: https://rosstat.gov.ru/opendata/7708234640-oktmo?print=1 and https://69.rosstat.gov.ru/storage/mediabank/%D0%9E%D0%9A%D0%A2%D0%9C%D0%9E2023.pdf. Rosstat describes digits 1–8 as identifying a municipality and digits 9–11 as identifying a locality; municipality reporting can use the 11-digit representation ending `000`.
