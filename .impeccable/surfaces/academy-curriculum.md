# Student curriculum — approved prototype promoted to local product

Operate / Read. Vietnamese-speaking teens and adults learning Chinese. The
user approved the standalone illustrated list/map prototype and instructed:
“ok đẹp rồi thiết kế như vậy đi”. Implement on the main local site, without
deploying to cloud, changing lesson publication or writing learning progress.

## Direction contract

THESIS: immediate lesson access through illustrated blocks; the optional 2D
Great Wall motivates and orients, without controlling a 3D avatar or camera.
OWN-WORLD: preserve the real academy's Noto typography, jade/ivory reading
surfaces, existing pine sidebar, Bo and the approved painted map artwork.
STORY: choose HSK, open a real available lesson, revisit completed work, locate
the current gate or continue through the summit to the next HSK. Server state
and IDs govern every link. Unpublished/locked/planned items never grant access.
FIRST VIEWPORT: list shows illustrated pronunciation and measure-word blocks,
then HSK/view selectors, compact real progress, search/filter and lesson covers.
Map omits the summary, large foundation blocks and scenic introduction; retain
locate and the climbing scene. Pronunciation remains a prerequisite for HSK 1
only. Measure words are freely accessible supplementary reading.
FORM: implementation of the user's explicitly approved interactive prototype;
no new concept roll or comp selection. Main sidebar/account controls remain
native to the real application. Adapt synthetic preview state to real API data.
FINISH: inspect desktop/mobile captures of the main routes, test actual IDs,
publication/access rules, 15/10/15 slots, periodic tests and next-HSK links.
Build/type/lint checks and read-only finish review precede final handoff.

## Evidence

Approved prototype: `tmp/modern-academy-preview/clean-map-1440.png` and
`curriculum-1440.png`; mobile variants in the same folder. Product captures
and fixture-based browser report: `tmp/academy-curriculum/`.
Generated map/tower provenance and exact prompts remain in
`frontend/public/academy/great-wall/academy-2d-v1/`.

## Finish result

Main local frontend rebuilt/refreshed at port 5173. Browser checks passed at
1440px and 390px with zero learning writes; 106 relevant unit/integration tests
passed, production build passed, and scoped lint/type checks passed. Review
found cold-loading background images in the initial captures and ordinal
cover fallbacks. Captures now await decoded CSS imagery; title-based art with
a neutral fallback replaces ordinal art. Both fixes were rescored from the
same production captures: **disposition: ship**. Production rules recorded in
DESIGN.md; details in `docs/design/academy-curriculum-production.md`.

## Foundation and cover refinement

The user requested an additional measure-word block, an illustrated
pronunciation block, redesign of the supplied header and more diverse covers
for lessons with content. The five current titles/vocabulary were checked
against the local database with read-only queries. A nine-scene generated
panda atlas now supplies both foundation subjects, five distinct topic covers
and neutral artwork; exact prompts are in `public/academy/curriculum-v2/`.

`/measure-words` provides ten authored classifier reading entries, example
phrases, sentences, usage notes and device phrase audio (including context for
只). Item position lives in the URL; it neither claims completion nor changes
HSK state. Latest header and reading captures live in `tmp/academy-curriculum`.
113 relevant tests, type/lint and main-route desktop/mobile browser checks
passed; no learning writes. Final main frontend refreshed at port 5173.
Read-only finish review: **disposition: ship**. No cloud deployment.

## Superseding direction: list only and contextual Bo

The user explicitly removed the 2D Great Wall. Main curriculum imports and
controls no longer expose it; old map queries show the lesson list. Preserve
the foundation blocks, covers, real progress and server access boundaries.
LessonEntryLink now shares return-transition cloud timing for study entry,
with repeat-click protection, native modified clicks and shared reduced-motion
handling. Bo guides the curriculum, thinks beside empty results/usage notes,
encourages practice preparation and celebrates successful review. Never float
Bo over study text. Main Docker frontend refreshed at port5173;105 related
tests, type/lint, build and browser desktop/mobile flows passed. Entry/exit
cover/reveal sequences tested with normal motion, no learning writes.

## Current approved navigation and cast

User approved removing the separate student dashboard and large cast page,
moving cast introduction into Profile, giving all three characters roles,
and adding background where useful. Main default is curriculum. Sidebar
and mobile bar: Gi?o tr?nh, H? s?, existing logout/account. Old dashboard
and cast routes redirect without breaking saved links. Resume uses real
dashboard/lesson/progress data to find incomplete theory or practice. Profile
contains a collapsed cast section with Bo expressions; legacy hash opens it.
Bo guides and celebrates; Tr?c explains technical notes; B?t supports practice
and review, including its happy pose. Native landscape art fills whitespace,
with opaque content/form planes. Main frontend refreshed at5173, browser
verification passeddesktop/mobile nolearningwrites;61route/cloud/casttests
and82learning/auth/unit tests passed, type/scopedlintclean, buildpassed.
