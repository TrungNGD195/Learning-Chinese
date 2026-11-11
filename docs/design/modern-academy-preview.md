# Modern academy interactive preview

Open **http://127.0.0.1:5174/academy-preview.html** while the preview Vite server is running.

To start from `frontend`: `npx vite --host 127.0.0.1 --port 5174 --strictPort`.
Stop that command with Ctrl+C. This standalone HTML entry is for local review; it does not replace the normal application or add a production route.

## Try the concept

- Home: resume the sample lesson, review familiar words, choose an HSK course.
- Curriculum: switch between lesson blocks and the optional 2D Great Wall, search and filter. HSK 1/2/3 contain 15/10/15 illustrative entries; HSK 1 lesson 3 is the interactive sample.
- Sample lesson: six vocabulary items with audio, examples and useful notes, grammar and a reading dialogue. Complete the three theory sections to open practice.
- Practice: five demonstration questions across multiple choice, gap filling and sentence ordering; explanations, an 80% threshold and repeat attempts.
- Review: recall vocabulary before seeing answers.
- Profile: change the sample name, daily goal and motion preference; see sample attempt results.

This is a concept prototype, not a replacement curriculum. Authored sample learning records are explicitly labeled. Progress lives only in the separate `bo.modern-academy-preview.v1` browser storage key; the reset control clears that sample progress. No authenticated API, real account changes or lesson publication occurs. The standalone entry avoids the application's new-tab session initialization.

Existing Bo, panda, gate and mountain assets retain their current provenance. Styling is scoped to `.ap-preview`. The main design system and production routes are unchanged by this prototype.

The optional map now uses a painted bird's-eye adaptation of the existing local Great Wall art direction. Five measured stone landings per artwork segment carry the native gate assets; labels have small ivory backings while the gates themselves sit directly on the wall. Existing edge-cloud artwork softens segment boundaries without hiding the route. Bo marks the sample lesson. A generated watchtower at the summit links to the next HSK map.

Project-bound artwork is in `frontend/public/academy/great-wall/academy-2d-v1/`: `ascent-map.png` and `watchtower.png`. Both were produced with the built-in Imagegen tool; `prompts.md` records the exact prompts and `provenance.json` records the reference, source files and measured coordinates. Original transparency is preserved. These are prototype assets, not renders exported from the production 3D engine.

## Verification

From `frontend`: `node scripts/verify-academy-preview.mjs`.

The browser verification exercises desktop and mobile learning, theory gating, incorrect-answer explanations, sentence ordering, an 80% pass, review, search, map sizes, profile persistence and reset. It also asserts zero account API calls and no horizontal document overflow. Captures and the report are written to `tmp/modern-academy-preview` at the repository root.

The map follows one winding ascending route: lesson 1 starts at the bottom and every next lesson is higher. A contained vertical viewport opens near the current sample lesson; the locate control returns to it. Mobile uses the same vertical route without horizontal scrolling.

Map-specific validation also checks strictly ascending node positions, current gate visibility, no horizontal overflow and the summit link to HSK 2. Actual viewport captures are `painted-viewport-1440.png`, `painted-viewport-390.png` and the corresponding `summit-viewport-*` files in the verification folder. Use these for reviewing inner-scroll position; Chromium full-page screenshots can repaint a different part of a nested scroller.

The map view now omits the page introduction, course progress summary, demo paragraph and scenic banner to give the map priority beneath the HSK/view selectors. The list view retains its search and filters, but lessons are individual illustrated blocks: three columns on wide screens, two on medium screens and one on phones. Covers reuse the existing vocabulary artwork; the whole sample-lesson block opens the lesson. Non-interactive illustrative entries remain explicitly labeled.
