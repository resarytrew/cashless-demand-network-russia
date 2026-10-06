# Landing presentation audit, 2026-10-06

## Scope and design

Presentation-only release in `site/`, with an editorial light palette, locally
hosted Cyrillic Manrope, an animated 1,904-record canvas, profile explorer,
month-end Sankey, geographic atlas, municipality search/passports, evidence
explanation and an automatically exported PDF. Visual design settings: variance 8,
motion 7, density 4. Vanilla HTML/CSS/JS, D3 v7 and d3-sankey; no framework migration.

The supplied reference was inspected for its narrative and interaction structure.
Its code, data and scientific conclusions were not imported. This repository's
1,904-member strict panel and cautious profile terminology remain authoritative.

## Sources and exact method

The source contract is `configs/landing.yaml`; `site/data/manifest.json` records
checksums and runtime. No clustering, tuning, random-seed experiment or evidence
status update was performed. The original visualization and baseline are untouched.

The national external layer and existing geographic artifact were already present
in the workspace. The builder reads them without modifying their files. One
unresolved external match remains missing; all 1,904 reference trajectories remain
available in the search. Map coverage is explicitly 1,903. Exact June/December
labels are counted into Sankey links, including technical communities.

The geographic derivative is simplified for display at a configured 2 km tolerance
and four coordinate decimals. These shapes do not enter research calculations.
The hero threads and core/boundary drawing are conceptual graphic treatments,
clearly distinguished from observed graph edges or the result of a particular run.

## Scientific claim effects

- Strengthened: presentation traceability and access to existing evidence.
- Weakened: none; no scientific experiment was conducted.
- Unchanged: reference model, A–G robustness statuses and every prior evidence round.
- Retained: core/boundary distinction; C unresolved; F boundary sensitivity;
  B/E nesting; context dependence; noncausal external interpretation; Total limits.

No new master scientific evidence matrix is warranted for this presentation work.

## Verification

- Full Python suite: 99 passed.
- Ruff fatal/static correctness checks on new Python code: passed.
- Playwright: 10 passed; profile switching, exact trajectory length, search, empty state,
  micro-community coverage, keyboard entry, data failure/retry, mobile/tablet/
  desktop widths, map coverage/month/layers/play/zoom/selection, motion pause,
  PDF preparation, local downloads, and preserved legacy atlas.
- PDF: rendered with Poppler and visually checked; eight A4 pages, no orphan
  profile row or isolated footnote. Poppler reports two non-fatal Type 3 glyph
  bounding-box warnings; the rendered pages show no visible glyph defect.
- Current submission verifier (`--skip-tests` after the complete suite): PASS.
- Legacy `scripts/verify_current_artifacts.py`: FAIL before numerical replay,
  on `.github/workflows/verify.yml`. Expected frozen SHA256:
  `536ae492c7f5c81e47bbc94b8f437245f75fa6386314e95476c06fc77582f75d`.
  Both HEAD and the untouched working file have:
  `05790361bb40ea266e0a8b81dedcecb62be6fc7a0e2a04dd2df31e084694af22`.
  This predates the landing changes; no manifest or evidence bytes were altered
  to suppress the failure. The repository cannot be described as passing this gate.

The public-pages workflow stages the new landing and preserves the old atlas in
a subdirectory. Local source geometry/lineage prerequisites are documented.
No push, remote publication, research rerun, or changes to unrelated workspace
artifacts were made.
