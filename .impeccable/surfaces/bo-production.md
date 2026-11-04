# Approved academy integration

User approved the illustrated academy prototype for production on 2026-11-03, with two revisions: easier font/size and main dragon named Bo. User requires a pronunciation prerequisite derived from the local HSK1 textbook, completed before unlocking HSK1.

## Direction contract

THESIS: Carry the approved illustrated learning academy into real authenticated workflows. Resume, progress, availability, exercises and unlocking use server data; prototype sample content and local progress must not become production records.

OWN-WORLD: Pine sidebar, jade actions, ivory reading surfaces, painted mountain academy, six expressive Bo states, Trúc explanatory notes, Bút practice. Replace ornate Vietnamese display lettering with locally served Noto Sans, larger body copy and controls; Chinese uses Noto Sans SC with full coverage rather than the prototype's small subset.

STORY: Login, resume the pronunciation prerequisite, complete initials/finals/tones in server order, confirm completion, unlock HSK1, continue real lessons. Chinese dominates vocabulary; examples and notes stay adjacent. The user can adjust reading size.

FIRST VIEWPORT: Approved pine navigation rail and quiet header, real continue-learning action over the painted academy with Bo, progress/context beside it. Pronunciation uses a large sound and Hanzi example, short articulation guidance, relevant source-page references and contextual companions; mobile navigation and controls remain readable.

FORM: User-approved prototype at /journey-test.html is visual reference. Preserve its composition and imagery; approved font/name changes apply. Existing API step counts21/36/5, completion contract, authorization, backend gates and administrator capabilities remain intact. New documentation supersedes the prototype-only status for this production adoption. No new direction tournament is required.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

Inherited direction record: seed:1b6b264dfc109692, recorded in `.impeccable/questions/roll.json` and the approved journey-test brief. This is code-led adoption of the user-approved prototype, with no bitmap comp or quality-bar card replacing that approval.

## Source evidence

`docs/HSK1 3.0 Hanu 24.6.26.pdf`,149 pages, inspected text and rendered pages. PDF4 (printed2) initial11 sounds and basic15finals; PDF6–7 (printed4–5) tones, composition, spelling, third-tone/不 changes; PDF17–18 (printed15–16) j/q/x, additional finals, neutral tone and spelling; PDF27–29 (printed25–27) z/c/s/zh/ch/sh/r, special-i and er, u-series and spelling. Condense explanations and link to precise references; do not redistribute the source PDF as a public asset. Fix obvious extraction errors by visual comparison, not blind copying.

## Validation

Frontend build/lint and relevant tests; backend pronunciation and progression-gate integration tests on the dedicated test database. Render real frontend routes with API fixtures at1440,768,390px and exercise pronunciation/resume/complete/gating. Update the existing Docker frontend at the local application URL after checks pass, preserving database and backend state.
