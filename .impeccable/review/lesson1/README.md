# HSK1 lesson 1 draft — 2026-11-03

Requested: all lesson-exercise defaults80%, then create the textbook-based lesson-1 draft on the local web app. Periodic tests keep their separate default90%.

## Stored records

- Lesson `d84c81ba-57b3-5132-b15e-dee32ed22bbf`: **DRAFT**, HSK1 lesson1, 你好 · Xin chào.
- Exercise `2185832f-164e-59b8-ae3c-b9ead02e1f64`: **DRAFT**,80%,20questions /20points. Six multiple-choice, six fill-blank, four matching, four reorder tasks.
- Twelve illustrated vocabulary/phrase entries, each with Hanzi, pinyin, Vietnamese meaning, part of speech, example and note. No formal grammar entries because source lesson1 has no separate grammar section. No pronunciation teaching is repeated.
- Source definition: `backend/content/hsk1/lesson-01.json`, referencing local HSK1 textbook PDF3–4,9–10. Glossed example extensions are not examined.
- Repeat-safe importer: `python -m scripts.create_hsk1_lesson1_draft --apply` from backend; validates before writing and creates lesson/content/questions in one transaction. Re-running preserves existing administrator edits and does not create duplicates or publish anything.

## Validation

- Frontend:396tests passed. TypeScript/Vite build and lint completed; existing administrative state-in-effect and bundle-size warnings remain.
- Backend:34focused PostgreSQL tests passed, including type-specific request/generation/ORM/raw-SQL defaults, correct answer keys for all20questions,75%fail/80%pass, atomic/idempotent import, theory-before-exercise API access and progression/history regression flows.
- Migration0014 applied to dedicated test database and local Docker application database. Existing application contained no assessments before the change. All current lesson exercises have80% thresholds. Historical attempt scores were not rewritten.
- `web-verification.json`: actual local Docker API/UI at5173/8001, no intercepted APIs; all12illustrations and examples, four full-page captures at1440/390px, no horizontal overflow or JavaScript errors. Numeric illustrations verified as exactly1/5/8dots. Manual/AI creation defaults80%; periodic creation defaults90%.
- Draft lesson, draft question payload and draft attempts return404 to learners; draft is also absent from their curriculum. Administrator can inspect and edit it normally.
- Visual source assets: five academy rasters, zero missing prompt provenance. Additional sheet `vocabulary-hsk1-extra.png` is built-in imagegen output with exact prompt sidecars and embedded metadata.
- Imagegen output: `frontend/public/academy/vocabulary-hsk1-extra.png` (2172×724, three square cells: 你、好、不). Exact final prompt: `frontend/public/academy/vocabulary-hsk1-extra.prompt.txt`; provenance sidecar: `frontend/public/academy/vocabulary-hsk1-extra.png.json`.
- Fresh scoped finish review: `finish-review.md`, disposition **ship**, no material UI fixes. Existing design-system tokens remain intact; factual illustration coverage is documented after review.

Browser review used existing local account roles with short-lived cookies held only in process memory, without changing passwords, creating users, publishing content or modifying learner progress.
