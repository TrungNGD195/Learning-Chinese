# Academy artwork and Vietnamese administration

Implemented in the main local frontend at http://127.0.0.1:5173.

The approved extension adds a transparent six-scene watercolor atlas, semantic outlined icons, contextual Bo/Truc/But header companions, topic covers and illustrated empty states. The administration quick word preview is compact, and preview illustrations retain square proportions. Administration interface text, status labels, dialogs, errors, document controls and local question previews are Vietnamese; API enums/payloads and authored curriculum/source content are preserved.

## Final evidence

- `student/verification.json`: 44 captures at 1440/1024/768/390; fixture APIs only; no progress advancement.
- `admin/verification.json`: 40 captures, real read APIs with a default write barrier and explicit isolated save/delete fixtures. Covers cards/table, draft preservation, failed save/retry, preview, seven question types, mutation exclusion, empty/error/long/read-only and zoom reflow.
- `admin-extras/verification.json`: 6 captures for statistics, lesson creation and AI generation at desktop/mobile; Vietnamese control-copy checks.
- All capture reports have zero JavaScript errors; no real mutations. Student resource/unknown-route checks are empty.
- `tmp/academy-visual-ship-tests.json`: 402 passed, zero failed, including archived lesson read-only behavior after translating status labels.
- Production build passed. Lint passed with existing effect/fast-refresh and script warnings; existing bundle-size warning remains.
- Independent review and correction disposition: `finish-review.md`.

A final read-only comparison against `backend/content/hsk1/lesson-01.json` confirms the original 12 vocabulary records and all 20 question definitions/options. Lesson and exercise remain DRAFT with an 80% pass threshold. No backend or learner progress change was required.

## Assets

Built-in imagegen produced `frontend/public/academy/learning-scenes-v1.png`; exact prompt and provenance are beside it. The delivered `learning-scenes-v1.webp` is a lossless derivative with identical RGBA pixels and transparency, reducing the source from 2,830,277 to 2,029,116 bytes. SVG icons extend the existing icon set. Existing mascot and word-art assets are reused.
