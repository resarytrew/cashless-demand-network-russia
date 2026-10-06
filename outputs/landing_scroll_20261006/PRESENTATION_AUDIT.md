# Presentation audit — scroll chapters, 2026-10-06

Scope: presentation only. No calculations, model parameters, evidence statuses or
scientific claims changed. Data hashes match the preceding autoplay presentation
release; see data_integrity.json.

- Replaced timed autoplay with GSAP scroll-position steps, including reverse scroll.
- Retained direct tabs and manual selection until the next scroll step.
- Pinned fitting desktop graphics, preserving native scrolling on smaller screens.
- Preserved the hero grouping pin and intentional user-triggered month playback.
- Increased body text, captions, legends, controls and comparison values.
- Reduced-motion users retain direct selection; print removes all chapter pins.
- Frozen scientific limitations remain next to their relevant figures.

Checks: 100 Python tests passed; 16 Playwright tests passed. Targeted browser tests
rerun after script renaming and the mobile reduced-motion condition correction.
Visual review: 1280×720 hero, profiles, external comparisons and map; 390px mobile
profiles and map. At 1280×720 all three desktop graphic stages fit and are pinned.
The external plot exposes all seven rows without clipping. PDF export remains
12 A4 pages; all pages rendered and checked in pdf-contact.png.

Known responsive behavior: on smaller screens scroll steps follow the section
without pinning; users can also select any tab directly. There are no timed category
advances. Decorative map watermark and symbol-only transport controls retain their
own smaller sizes; substantive HTML labels use at least 14px on screen.
