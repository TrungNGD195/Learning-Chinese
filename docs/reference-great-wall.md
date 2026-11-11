# Original illustrated journey (local)

Historical static implementation. The user clarified that the three pictures
must form a continuous climbing action; current behavior is documented in
`illustrated-climb.md`. The pixel comparisons below apply to the archived static
capture, not the active animation.

The current learner journey uses the user's approved original illustration,
replacing the active Three.js renderer. The user chose visual fidelity and a
sequence of original painted scenes. All three lower pictures and their
captions are retained; the external draft heading is omitted.

`frontend/public/academy/great-wall/reference-v1/approved-layout.png` is the
unchanged user attachment, SHA-256
`04c66c28c04b066ffe1e26c5c7bb5d3aa4ea417bad9ec09235256a319ec03d59`.
`referenceArtData.ts` records exact source coordinates for the main image,
three phase images, three captioned cards and the sidebar Bo. SVG crops leave
the source file intact. No image was regenerated for this implementation.

`ReferenceWallJourney.tsx` provides native lesson links, navigation, all lesson
slots, overview and scene choices. The API still controls actual access and
completion. Visual position is optional, non-secret tab storage; it has no
effect on learning progress. Opening lessons and locating the current lesson
use the existing silent cloud transition; reduced motion bypasses it.

The native footer follows the same image coordinates when the sidebar changes
width. Mobile uses a wider crop around Bo and the gateway, and a compact
native footer that follows and covers the original painted controls. Dynamic gate labels
replace only text inside the original plaque. All three original cards are
visible on desktop and reachable by horizontal scrolling on mobile.

Dynamic plaques use self-hosted Noto Serif bold with Vietnamese glyphs; native
interface labels retain Noto Sans. Font source: Google Fonts Noto Serif v33;
the SIL Open Font License is included beside `noto-serif-bold.ttf`.

The main painting is 1216×604. The three source phases are 448×207: displaying
them larger necessarily softens detail. This is an illustrated crossfade
sequence, not continuous 3D character animation, and is not a claim of identical
pixels for responsive layouts or native text/control overlays.

Validation: focused interaction/security tests, TypeScript, scoped lint and
`frontend/scripts/verify-reference-journey.mjs` against the local frontend.
Browser captures and source-image comparison are stored in
`.impeccable/review/reference-journey/` and `.impeccable/review/diff/hero/`.
No deployment, curriculum publication or progress writes are part of this work.
