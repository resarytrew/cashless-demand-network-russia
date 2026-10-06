# Public Atlas UX and GSAP presentation audit — 2026-10-06

This is a product presentation revision, not a research evidence round.

## Scope

- Public scenario: Исследовать / Профили / Изменения / Атлас / Методология.
- Territory search, 1,903 geographic shapes, all 1,904 municipality profiles,
  original 24-month sequences, layer selection, zoom and exact half-year flows.
- Technical codes and uncertainty details remain accessible through disclosures
  and the separate preserved `methodology.html` research exhibition.
- Local Literata + Manrope, editorial typography, multicolour scientific encoding,
  continuous page canvas without boxed section backgrounds.
- Actual GSAP 3.15.0 ScrollSmoother / ScrollTrigger / ScrollToPlugin. No CDN.
- Pinned story uses actual counts: 476 without a switch; 1,624 with at most two;
  280 with at least three. Animated graphic positioning is illustrative only.

## Integrity and verification

- All three `site/data/` hashes exactly match `data_before.json`.
- No numerical calculations, parameters, saved memberships, configurations or
  scientific statuses were modified for the UX revision.
- Full Python suite: 99 passed.
- Playwright: 10 passed, including GSAP navigation, pinning, live reduced-motion
  cleanup, search, map controls, geometry failure/retry, print and methodology.
- Screens inspected at 1440 × 1000 and 390 × 844; overflow checks additionally at
  768 and 1280 px. Desktop and mobile GSAP screenshots are saved in this folder.
- Automatic PDF: seven A4 pages; all seven rendered pages visually inspected.
- GitHub Pages staging supports root and /site aliases; legacy atlas preserved.
- No publication, push or deployment performed.

## Motion behaviour

Desktop smoothing is 1.35 s. Anchor travel is interruptible and keyboard focus is
preserved. Below 900 px scrolling is native, retaining the mobile sticky graphic.
Reduced motion and print disable GSAP effects; no chart values are animated as
invented counters. Pausing the hero stops ambient drift; scrolling still explains
the relationship between geography and the explicitly conceptual group layout.

## Existing independent integrity issue

The previous presentation audit records a pre-existing frozen-manifest mismatch
for `.github/workflows/verify.yml`. That file matches HEAD and was not modified or
resealed. This UX audit does not assert that the legacy artifact gate passed.
