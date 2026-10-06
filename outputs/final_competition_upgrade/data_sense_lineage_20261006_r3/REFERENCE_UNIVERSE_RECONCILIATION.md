# Reference-universe reconciliation

The official Data -> Sense file has one `territory_id` per fixed territory, while the legacy input has only a textual `mo`. Both have the same number of value records, but duplicate textual labels can combine multiple official territory trajectories. Counts below are calculated from the two supplied files, not inferred from names.

| measure                                          |   count | reason                                                                             |
|:-------------------------------------------------|--------:|:-----------------------------------------------------------------------------------|
| official territory_id total                      |    2190 | all official Data -> Sense consumption IDs                                         |
| official complete 24x6 territory_id              |    2016 | 144 records: 24 months x 6 categories                                              |
| reference unique fingerprint candidates          |    1904 | unique exact 24-month x 6-category trajectory; before directory compatibility gate |
| reference retained                               |    1903 | unique exact fingerprint plus exact directory-name compatibility                   |
| reference name-conflict                          |       1 | unique fingerprint but directory name differs; excluded pending review             |
| complete official IDs inside ambiguous raw names |     112 | full official trajectories occur only in names with duplicate month/category rows  |
| unaccounted complete official IDs                |       0 | must be zero; otherwise no inference                                               |
| reference excluded by strict-panel ambiguity     |      49 | textual mo has duplicate category/month observations                               |
| reference excluded by incomplete history         |     166 | not all required 24x6 observations                                                 |

`complete official IDs inside ambiguous raw names` uses an exact multiset containment check over all 144 month/category/value records; it does not use municipal names as a key.
