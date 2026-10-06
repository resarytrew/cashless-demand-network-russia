# Research landing: presentation release, 2026-10-06

The presentation Atlas is the published entrypoint at `/`, `/atlas/` and
`/site/index.html`. The older repository visualization remains preserved in
`outputs/public_visualization`, but is not staged as a public route. This is not a
new research round: all reference parameters, saved labels and prior evidence
remain unchanged.

## Preview

From the repository root:

```powershell
npm ci
python scripts/stage_landing.py
python -m http.server 8765 --bind 127.0.0.1 --directory dist
```

Open `http://127.0.0.1:8765/`. Use an HTTP server: fetching compact JSON is not
supported by a direct `file://` opening. `dist/` is disposable staging, not evidence.

## Data and provenance

```powershell
python scripts/build_landing_data.py
```

This optional regeneration requires the local artifacts listed in
`configs/landing.yaml`, including the verified lineage and municipal geometry
artifacts. These pre-existing local inputs are not fetched or recreated by the
landing builder. The shipped site includes the complete derived data and needs
no Python runtime or external data API in a browser. GitHub Pages CI uses those
committed derivatives, so it does not depend on local-only source archives.

- `site/data/research.json`: 1,904 reference records with exact saved monthly IDs;
  1,903 external population matches; 1,890 nonmissing wages.
- `site/data/municipalities.geojson`: 1,903 matched shapes. Display-only
  simplification at 2 km in EPSG:6933, then EPSG:4326 coordinates rounded to four
  decimals. Clockwise rings for D3 spherical rendering. No numerical research
  quantities are derived from simplified geometry.
- `site/data/manifest.json`: input hashes, output hashes, configuration hash,
  Python/package versions, git revision and seed.
- Half-year flows use the exact June/December saved month-end labels, not majority
  memberships. Every layer conserves all 1,904 records. Letters A–G name the final
  reference snapshot only; earlier labels remain original community IDs.
- National external interpretation comes from the current competition `story_data_v3`
  artifacts, separate from the historical 58-municipality Round17 freeze.

The hero uses all 1,904 records. Its anchors, curved threads and jitter are editorial
geometry. Threads are not estimated graph edges. The public hero moves from geographic centroids to illustrative group anchors as
the visitor scrolls. Its grouped layout is neither an embedding nor observed
temporal movement. The municipality without geometry appears in the conceptual
layout only. The methodology page preserves the earlier affinity illustration.
The core/boundary exhibit is explicitly a conceptual illustration, not one run.

## PDF and browser verification

```powershell
npx playwright install chromium
npm run pdf
python scripts/stage_landing.py
npm run test:site
```

On a Windows machine with installed Chrome, `PLAYWRIGHT_CHANNEL=chrome` is supported:

```powershell
$env:PLAYWRIGHT_CHANNEL = 'chrome'
npm run pdf
npm run test:site
```

PDF export uses a temporary localhost server and headless Chromium. It waits for
data, local fonts and map geometry; includes all seven profiles and expanded
limitations; emits `site/assets/research-brief.pdf` and `social-cover.png`.
The static PDF is linked directly from the page. Regenerate it after content edits.

The public-pages workflow installs locked JS dependencies, builds the PDF, stages
the site, runs Playwright and then deploys on its configured push/manual triggers.
Pull requests only verify. No deployment or git push was performed by this task.

## Interaction and accessibility

Canvas drawing pauses outside the viewport or in a hidden tab. Reduced-motion
preferences stop ambient movement and transitions; manual month selection remains
available. Map playback starts only on explicit request and stops when out of view.
Keyboard users can reach every municipality through search and native buttons;
the map is an additional pointer view, not the only selection method. All map
layers have legends and a text equivalent in the selected municipal passport.

D3 7.9.0, d3-sankey 0.12.3, GSAP 3.15.0, Manrope and Literata are hosted locally
with copyright and license notices. No CDN,
analytics, framework, external font request or runtime service is required.
Geometry attribution and CC BY-SA 4.0 are retained on the page.

## Verification scope

See `outputs/landing_20261006/PRESENTATION_AUDIT.md`. The legacy artifact verifier
has a pre-existing integrity mismatch in `.github/workflows/verify.yml`; the
working file exactly matches HEAD. The mismatch is reported, not resealed.

## Public Atlas / methodology separation — UX revision

The public route follows Explore → Profiles → Changes → Atlas. The first-screen
CTA jumps directly to territory search. `methodology.html` retains the detailed
research exhibition, scientific labels, checks and limitations. A–G, retention
and precision remain inside methodological details, rather than public headings.
Both routes exist under `/` and `/site/`; the frozen legacy atlas stays at `/atlas/`.

`assets/atlas-motion.js` owns GSAP ScrollSmoother, ScrollTrigger and ScrollToPlugin.
Desktop scrolling uses 1.35 s smoothing; anchor navigation uses an interruptible
1.55 s power3 transition. Scroll position controls the conceptual hero layout,
chapter entrances, a pinned comparison of observed transition counts, and Sankey
reveal. The background changes on the whole document; sections have no hard colour
seams. Public headings and charts retain a flat editorial composition.

Below 900 px, native scrolling preserves touch and sticky graphics. Reduced motion
removes all GSAP effects and smoothing. Wheel/touch/scroll keys interrupt anchor
animation; focused links transfer keyboard focus. Printing reverts GSAP pinning and
transforms. The print export includes all seven profiles and methodological limits.

Official integration reference: https://gsap.com/docs/v3/Plugins/ScrollSmoother/

No preprocessing or research run was executed for this UX revision. SHA-256 values
of all three files in `site/data/` match the snapshot before the redesign. See
`outputs/landing_ux_v2_20261006/verification.json` and `PRESENTATION_AUDIT.md`.

## Hero pin and evidence expansion

The initial desktop scene is pinned while geography transforms into illustrative
profile groups, including a final hold before release. Below 900 px, the figure
pins only once visible; touch scrolling otherwise remains native. A browser test
verifies position, completion and release at 1280 × 720.

The public page adds a 70/30 reading key, an external comparison of municipal
wage/population/employment distributions, regional-vs-mixed prediction diagnostics,
and the selected municipality's three largest saved descriptive affinity shares.
These exhibits reuse existing numerical results. The additional display data is
built with `python scripts/build_landing_evidence.py`, using
`configs/landing_evidence.yaml`. No other site/data file is regenerated.

PDF export now has ten pages, including metric definitions. Verification for this
revision: `outputs/landing_hero_evidence_20261006/PRESENTATION_AUDIT.md` (100 Python
and 12 browser tests). Earlier release audits remain as historical records.

## Automatic tours and practical interpretation

`assets/auto-tours.js` controls three independent GSAP clocks: profiles every nine
seconds, external indicators every eight seconds, and map layers every eight
seconds. A cycle runs only while its observed content is at least 35% visible,
the document is visible and its data are ready. Progress and pause/resume controls
are next to the content. Manual pointer or keyboard interaction pauses that tour;
resuming is explicit. Reduced motion disables automatic start. The timer does not
scroll the page, change map months or change saved data. Print pauses all tours.

Profile text uses a GSAP crossfade rather than an asynchronous document View
Transition, avoiding a focus/selection race when immediately resuming playback.
The external comparison animates existing median and quartile positions; map layer
changes update the legend and valid controls together. Default profile is the
first public category, high spending; selecting a municipality still selects its
actual saved profile.

User-supplied narrative was distributed across introduction, comparison, external
interpretation, business and administration use cases, and the explicit public
scope block. Practical uses are hypotheses for initial territory research, not
validated growth forecasts or guarantees of product fit. Profile transitions are
changes in model-based spending similarity, not proof of economic development.
The wage epsilon-squared display is copied from the unchanged compact evidence.

The PDF includes these sections and now spans twelve A4 pages. Audit and rendered
pages: `outputs/landing_autoplay_20261006/`. All four data files remain unchanged.

## Scroll chapters and readable infographic — 2026-10-06

This presentation revision supersedes the timed autoplay described above.
`site/assets/scroll-chapters.js` uses GSAP ScrollTrigger progress to select the
seven profiles, three external indicators and three map layers. There are no
category timers or pause/resume controls. Scrolling backward reverses the sequence;
manual selection persists until the next scroll step. The user can stop scrolling
to read. Desktop panels that fit the viewport remain pinned during the sequence.
Smaller viewports keep native document scrolling rather than clipping a tall panel.
Reduced-motion mode retains manual tabs; print destroys the scroll controllers.
The separately requested map-month Play control remains user initiated.

Screen body explanations are 17px; captions, evidence qualifications, technical
notes and legend labels have a 14px floor. Navigation and primary controls are
16px, and comparison values are enlarged. Print typography remains independently
specified. All four frozen data files retain their previous SHA-256 hashes.

Verification: full Python suite, 100 passed; browser suite, 16 passed, including
bidirectional scroll sequences, manual selection, reduced-motion cleanup, readable
labels and responsive navigation. Renamed script and reduced-motion mobile fallback
were checked again afterward. PDF remains 12 A4 pages and was rendered for review.
Evidence and screenshots: `outputs/landing_scroll_20261006/`.
