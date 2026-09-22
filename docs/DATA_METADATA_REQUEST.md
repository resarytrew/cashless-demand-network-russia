# Metadata questions and unresolved external dependencies

Checked 2026-09-22: the official Data Sense dataset URL referenced in
`DATA_PASSPORT.md` returned HTTP 502 through the available browser fetch. Targeted
searches did not recover an authoritative definition of this file's denominator.
This is an access limit, not evidence that metadata do not exist.

No message was sent to the data owner. The following questions are ready for the
owner/author to answer with version-specific documentation.

| Field/relationship | Required clarification | Current permitted scope |
|---|---|---|
| `value`, Total | Sum, per-resident, per-client, per-active-buyer or modeled denominator? | Published indicator in rubles only |
| Category values vs Total | Same population, weights and denominator? Mutually exclusive? | Conditional composition geometry |
| `Other` | Are five categories additively subtractable from Total? | Technical model residual |
| Municipality | Residence, purchase location, merchant registration or another rule? | Published textual key |
| Sample/coverage | Included instruments, clients, weights and extrapolation? | Analytical strict panel, not national representativeness |
| `obs_status`, missing values | Suppression, minimum counts, imputation and revisions? | No inferred suppression threshold |
| Release version | Exact export date, methodology version and redistribution terms? | Source bytes preserved; rights not presumed |

For each answer record source URL/document, version/date, retrieval date, a permitted
snapshot/checksum and the affected claim IDs. If additivity is contradicted, retain
the old reference and design a separate feature-model experiment; do not quietly
change the baseline. No additional division by population is justified yet.

Historical contextual recovery still requires the exact files listed in
`CONTEXTUAL_EVIDENCE_RECOVERY.md`, including manual/provisional matching decisions.
Rounded narrative results or current name matching cannot substitute for these.
The third contextual case and beyond-context geographic interpretations remain
unresolved. Code/data licensing and citation authorship need owner-supplied facts;
no license or author list is invented in this engineering release.
