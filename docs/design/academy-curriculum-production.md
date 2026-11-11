# Local student curriculum

## Current navigation and cast consolidation

The learner's default landing page is now `/pronunciation` (Giáo trình). The sidebar and mobile navigation contain only Giáo trình and Hồ sơ plus the existing logout/account controls. The old `/dashboard` redirects to the curriculum; `/companions` redirects to `/profile#companions`. Login, registration, authenticated public-page redirects and the brand link use the same curriculum landing. No standalone overview or cast gallery remains in the product navigation.

The curriculum's resume action reads the real dashboard target and, for lesson targets, the lesson/progress APIs. It links to the first unread vocabulary item, then incomplete grammar/readings or practice, retaining the existing server gates. The profile includes a collapsed native details section for the cast and Bo's six expression buttons; the old cast URL opens it. Account, progress and password behavior remain intact.

Bo leads the curriculum and celebrates a passed result. Trúc covers technical notes, pronunciation, vocabulary, grammar and measure words. Bút supports practice preparation, active-question guidance and retry review; its happy pose accompanies successful-review advice. Existing illustrations are reused. A restrained landscape background occupies curriculum/profile whitespace while opaque study/form surfaces retain readability; no new images or floating mascots were added.

## Current update: list-only learning and Bo

The user subsequently removed the 2D Great Wall. The main curriculum now always renders lesson blocks; map selectors and production map imports/styles have been removed. Legacy `?view=map` URLs also show the list. Historical map implementation notes below describe the previous version, not current navigation.

Lesson entry from blocks, dashboard resume, pronunciation/measure-word subjects and practice uses `LessonEntryLink` with the same cloud cover, hold and reveal as returning from a lesson. Modified clicks, new-tab targets and direct links preserve native behavior. Repeated activation cannot bypass an active transition. The shared provider handles reduced motion and Escape; pathname matching ignores destination queries correctly.

Bo is contextual: guide at the curriculum heading, thinking beside empty searches and measure-word notes, encouraging at practice preparation/retries, celebrating successful reviews. No floating overlay interrupts the study text. Existing dashboard/sidebar companions remain. Validation covers entry and exit phase sequences on desktop/mobile and the absence of map controls, in addition to the real access-rule checks.

The user approved the standalone academy prototype and requested implementation on the main local web application. The main routes `/pronunciation` and `/hsk/:hskLevel` now show the approved illustrated lesson list by default, with a `?view=map` option for the painted 2D Great Wall. Existing home, admin and lesson study screens remain outside this change.

## Product behavior

- Data comes from the existing HSK curriculum, pronunciation and learner progress APIs. The product never imports the prototype's synthetic records or local storage.
- Available published units link directly to the real lesson or assessment ID. Completed lessons remain available for review. Locked, unpublished and planned entries explain their state without opening content.
- HSK 1 still requires pronunciation completion. HSK 2 and HSK 3 can be selected independently. A real pronunciation entry stays available above HSK 1 content.
- The lesson list supports search and status filtering. Cards use supported artwork matched to recognizable title topics; unmatched, unpublished, planned and assessment entries use a neutral book illustration. Images are not inferred from ordinal lesson numbers.
- The 2D map orders all units from bottom to top, fits mobile width, opens near the current available unit and supports returning to that location. Gates link directly into learning. The summit continues to the next HSK map; it does not claim the course was completed.
- Planned counts remain 15/10/15 lessons; periodic assessments retain their backend order alongside lessons. Placeholders are clearly marked as content in preparation and never imply published content or progress.
- List/map choice is represented in the URL. The existing accessible sidebar, account controls and logout remain part of the real learner shell. No 3D canvas or arrow-key walking controls mount on the curriculum page.

## Implementation

`GreatWallJourneyPage.tsx` retains the existing API/query behavior and renders the new curriculum. `AcademyClimbMap.tsx` is the production counterpart of the approved map; `academy-curriculum.css` styles only this surface. `journeyData.ts` remains the publication/access boundary and now distinguishes unpublished targets for accurate explanations. `LearnerLayout.tsx` uses its ordinary workspace rather than the retired 3D scene's viewport treatment.

Artwork stays in `frontend/public/academy/great-wall/academy-2d-v1/` with the original prompt and provenance records. Existing native Bo, gate, cloud and vocabulary illustrations remain in use.

## Verification

Run from `frontend`:

```text
npx vitest run src/features/journey/AcademyCurriculum.test.tsx src/features/journey/journeyData.test.ts src/features/step43-learning.test.tsx src/app/router/routes.test.tsx src/app/router/session-routes.test.tsx
node scripts/verify-academy-curriculum.mjs
npm run build
```

The browser verification runs at 1440px and 390px against the main local route, with authenticated learner APIs supplied by a read-only fixture. It verifies actual ID routing, locked access, foundation gating, planned slots, covers, search, map order/location and summit navigation, and asserts no learning writes or unexpected API calls. The report and viewport captures are under `tmp/academy-curriculum/`. CSS background-image decoding is awaited before captures so cold-loading atlases are reviewed fully rendered.

The local Docker frontend was rebuilt and refreshed at port 5173. This task does not deploy to Railway/Vercel, publish lessons, migrate the database, commit or push changes.

## Foundation subjects and content-specific covers

The curriculum header now contains two illustrated subject blocks: pronunciation and measure words. Pronunciation completion is still read from the API. The new measure-word subject is a freely accessible supplementary reading page at `/measure-words`; it does not add an HSK prerequisite. The old full-width pronunciation strip and large green summary have been replaced by subject blocks and a compact course-progress row. These large blocks remain outside map mode.

The measure-word page teaches 个、本、张、只、条、杯、瓶、辆、位、口 with usage, phrases, full example sentences, pinyin, Vietnamese translations and practical notes. Audio reads a displayed example phrase, which supplies context for polyphonic characters such as 只 in 一只猫. The selected item is represented by the `word` query parameter. “Mục n/10” is a reading position, not a completed-learning counter. Next/back targets the article rather than the page introduction, and reduced-motion preferences are respected. This supplementary material is frontend-authored reading content; it has no backend lesson completion, grading or admin editing API in this change.

New full-scene cover artwork lives in `frontend/public/academy/curriculum-v2/covers.png`. The nine-tile atlas was generated with the built-in Imagegen tool using the native panda artwork as a style reference. Exact prompts and the row/column contract are recorded in `prompts.md` beside the image. Five distinct lesson scenes follow the actual published lesson titles/vocabulary checked in the local database: greetings; introductions; nationality/professions; family/counting; dates and food. Selection remains semantic, with a neutral study image for unavailable or unmatched content. The original lesson content and publication state were not changed.

The browser verifier additionally checks both subject blocks, all lesson covers, measure-word navigation, boundaries and reload. Header and supplementary-reading captures are `header-*` and `measure-words-*` in `tmp/academy-curriculum/`.
