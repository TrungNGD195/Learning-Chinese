# Academy artwork and Vietnamese administration — finish review

Disposition: **ship**. No outstanding material findings in the approved artwork and Vietnamese administration scope.

Reviewed the surface brief, DESIGN.md and craft floor; artwork/context/icon and shared header/state implementation; administration libraries, authoring and documents; localized labels, guard states and question renderer. Inspected rendered evidence at 1440, 1024, 768 and 390 pixels, including learner lessons/pronunciation/journey and administration libraries/editors/previews, empty/error/long/read-only states, unsaved navigation and the 200% equivalent reflow capture. Also inspected mobile statistics, lesson creation and AI generation forms.

## Findings resolved before approval

1. Document mutation recovery now uses Vietnamese while retaining authoritative reload behavior.
2. HSK metadata heading now reads “Thông tin HSK 1”; refreshed curriculum evidence confirms it.
3. Administration session loading/error/retry and forbidden copy now use Vietnamese. Access checks remain intact. Refreshed document captures show the settled library, upload controls and separate processing/review labels.
4. Explicit mobile dashboard grid placement restores full-width heading/body and keeps artwork clear of controls; confirmed in refreshed `admin/dashboard-390.png`.
5. Administration vocabulary preview now preserves square proportions through scoped width, maximum width and aspect ratio; confirmed in refreshed `admin/lesson-preview-390.png`. The compact 92px library glimpse remains proportionate.

## Passing observations

Contextual scene cells select cleanly without adjacent atlas bleed; transparent edges integrate with the existing ivory/sage academy. Greeting, path, practice and library imagery match the displayed content. Header art and companions stay clear of learning text and actions. Hanzi remains the strongest vocabulary text. Narrow headers, forms and action groups reflow without clipping content.

Decorative scenes/icons are hidden from assistive technology, supported word illustrations retain contextual alternatives, and unsupported words receive no substitute. Inspected administration navigation, lifecycle labels, question types, editing/upload controls, dialogs, dates, errors and local question preview controls use Vietnamese; authored source content remains intact.

Raw lesson status reaches `LessonContentSection`, preserving archived read-only and draft-only detach comparisons. Manual and AI lesson-exercise creation retain the 80% default. Mounted item editors, adjacent save failures, unsaved warnings and publication disabling preserve draft protection. Preview interactions remain local and do not submit learner answers.

## Verification and limits

- `student/verification.json`: 44 fixture-only captures across four widths; no errors, unknown requests or failed resources; no real learner progress or attempts changed.
- `admin/verification.json`: 40 captures; no errors or real mutations. Checks cover card/table selection, per-item drafts, failed save/retry, all seven question types, local preview, pending-save deletion protection, empty/error/long/archived states and responsive/keyboard order. Recorded threshold: 80%.
- `admin-extras/verification.json`: six desktop/mobile captures of statistics, lesson creation and AI generation; Vietnamese control check passes; no errors or real mutations.
- `tmp/academy-visual-ship-tests.json`: 402 tests passed, zero failed. Includes archived vocabulary read-only and authoritative lifecycle/history protection coverage.
- `tmp/academy-visual-build.log`: final production build passed in 992ms, with the existing bundle-size warning. Parent reports lint passed with existing effect/refresh warnings.
- Parent's final read-only database audit confirms the original 12 vocabulary entries and 20 question definitions/options unchanged, lesson/exercise still DRAFT, threshold 80%.

This review made no source changes or API mutations. Its disposition covers this approved extension, not unrelated pre-existing workspace changes or a comprehensive redesign of every legacy surface.
