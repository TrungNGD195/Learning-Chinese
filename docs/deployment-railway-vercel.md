# Railway backend and Vercel frontend

Deployed 2026-11-07 from the authorized local workspace. This release provides
the learning application with document processing/retrieval AI disabled.

## Live services

- Primary web (Hanfolio release): https://hanfolio-mcbo1.vercel.app
- Legacy web alias: https://learn-chinese-mcbo1.vercel.app
- Additional production alias: https://learn-chinese-pied-three.vercel.app
- Backend: https://backend-production-bc51b.up.railway.app
- Readiness: `/ready`; process health: `/health`.
- Railway project: `learn-chinese`, ID `f928bd3a-c3ea-479e-a156-9111e1207b1b`.
- Vercel project: `mcbo1/hanfolio` (renamed from `learn-chinese`, same project ID).

The frontend uses `VITE_API_BASE_URL=/api/v1`. Its external Vercel rewrite proxies
the API to Railway without changing the browser origin. Cookies remain Secure,
HttpOnly, session-scoped and SameSite=Lax; the refresh-cookie path is unchanged.
SPA routes fall back to `index.html`. API rewrites precede that fallback.

## Backend and database

Deploy the `backend` directory as the upload root. `Dockerfile` installs the
locked runtime without the `dev` and `local-ai` dependency groups. Local Docker
development continues to use `Dockerfile.dev` and the default local-ai group.
Uvicorn is a runtime dependency. The server listens on Railway's `$PORT`.
Startup runs `alembic upgrade head`; a failed migration prevents startup.
The Railway configuration also specifies migrations and `/ready` checks.

The `postgres` service uses `pgvector/pgvector:0.8.6-pg17` and a persistent
volume at `/var/lib/postgresql/data`. Backend database access uses Railway's
private network. A temporary public TCP proxy was used for initial migration
and removed afterwards. The backend has a persistent `/data` volume with
`DOCUMENT_STORAGE_ROOT=/data/documents`.

Required environment configuration includes `APP_ENV=production`, `DEBUG=false`,
`COOKIE_SECURE=true`, `COOKIE_SAMESITE=lax`, `LOG_LEVEL=INFO`, a generated
production signing key, private `DATABASE_URL`, explicit frontend CORS origins,
and `KNOWLEDGE_AI_ENABLED=false`. Secret values are not stored in this document
or committed. Deployment-only backup/transfer files remain ignored in `tmp/`.

## Learning-only mode

`KNOWLEDGE_AI_ENABLED` defaults to true to preserve development behavior.
When false, production does not require Modal credentials. Conversations are
not mounted; document process/approve/knowledge-retry operations and embedding /
reranking providers return a controlled `KNOWLEDGE_AI_DISABLED` error before
processing or mutations. Lesson publication remains available and skips the
post-publication knowledge build. Normal lessons, pronunciation, objective
practice, scores and administration continue to operate.

Document AI is not silently redirected to local model execution. To enable it
later, deploy and validate Modal, supply its credentials/configuration, then
enable the flag. Production still requires Modal when knowledge AI is enabled.
No Modal GPU was deployed or invoked for this release.

The separate OpenAI key for AI exercise generation/written-answer grading was
not copied to cloud in this learning-only release. The existing 150 objective
questions do not require it. Password-reset email delivery remains the existing
non-delivering placeholder; requesting a reset does not send an email yet.

## Initial data migration and verification

A complete local PostgreSQL backup was made before transfer. Imported source
IDs, password hashes, publication state and learner progress were preserved.
Refresh/password-reset token data was intentionally excluded, so existing users
sign in again with their current credentials. Fresh migration-generated lookup
rows were replaced only after verifying that cloud application tables were empty.
Data restore used a single transaction. Three stored lesson-processing artifacts
were copied into the backend's persistent volume.

Verified cloud counts after removing the temporary smoke account:

| Content | Count |
|---|---:|
| Accounts | 2: one admin, one learner |
| HSK levels | 3 |
| Lessons | 5: lesson 1 published; lessons 2–5 draft |
| Vocabulary | 127 |
| Grammar | 16 |
| Readings | 14 |
| Lesson exercises | 5, with 30 questions each and 80% pass threshold |
| Questions | 150 |
| Learner lesson progress | 1 |
| Viewed vocabulary records | 3 |

HSK2/3 have no authored lessons and remain independently selectable.

Validation: 83 backend checks passed, covering configuration, feature gating,
publication, architecture boundaries, business flows and progression gates.
Live browser smoke passed registration, secure cookies on the web domain,
refresh-cookie routing, authenticated SPA deep links/reload, published/draft
visibility, HSK2/3 access and logout. Its temporary account was removed.

## Subsequent releases

### Flashcard release — 2026-11-23

Vocabulary review supports two-sided cards with the same lesson
illustrations, account-scoped tracking preferences, KNOWN/LEARNING self-ratings,
undo and whole-deck shuffle. Migration `0019_vocabulary_review_progress` adds only
`vocabulary_review_preferences` and `vocabulary_review_states`; it does not rewrite
lesson completion, grades or accounts. The new `/me/vocabulary-review/progress`,
`/preferences` and `/cards/{card_id}` endpoints require a learner. Each write
rechecks eligible published/completed content (or the configured test learner).

Ratings use the existing canonical spelling/pronunciation/meaning card ID. Undo
restores the prior status with a monotonically increasing version; a stale write
returns 409 rather than overwriting another tab. Unseen status retains its
revision. Disabling tracking preserves existing ratings and blocks new rating
writes. Preferences and ratings survive reload; the undo stack and shuffle mode
belong to the current study session. Filter or shuffle changes clear undo history,
while paging preserves it. One shuffle seed orders the entire filtered deck, so
page changes cannot duplicate or omit cards. Counts cover that entire selection.

Review opens on a selection screen; cards and their progress controls mount only
after the learner confirms the HSK/lesson selection. In-session filters are
replaced by "Đổi bài ôn". Up/down flips the card; left/right records
LEARNING/KNOWN and advances after the write succeeds. The 150ms diagonal toss starts
immediately alongside the write: KNOWN goes up/right; LEARNING goes down/left.
A failed save returns the same card to its original position. Successful write
receipts update the local counts directly; other progress views are marked stale
without an extra GET in the card transition. An exit/entry card animation
and the write share a lock, so holding or rapidly repeating keys cannot rate the
next card accidentally. With tracking disabled, left/right browses without writes.
Touch gestures and labeled buttons provide alternatives. Data pages join
automatically, with the next page prefetched near the boundary. The final card
opens a round-end view that supports undo or restarting; restarting preserves
saved ratings. Reduced-motion mode uses short fades instead of spatial movement.

Release order: deploy the backend/migration before the frontend; keep the existing
production database and storage volumes. Verify a database backup and unchanged
account/content/history fingerprints around migration. No AI provider or paid
service is added.

### Account-scoped learning tests

`LEARNING_TEST_USER_IDS` is an optional comma-separated list of immutable learner
UUIDs configured on the backend only. It defaults to empty. The owner-designated
student456 account is configured separately in local and Railway environments;
account identities and credentials are not stored in this document.

Only an existing active LEARNER whose ID is listed can bypass pronunciation
ordering, the HSK1 pronunciation gate, ordered lesson/periodic-test access,
theory-before-practice, completed-lessons-before-HSK-exam and completed-lessons
before vocabulary review. Lesson progress and pronunciation state expose a
read-only `prerequisites_bypassed` capability for consistent frontend controls.
Do not infer this capability from names, email prefixes, local storage or URL
parameters. Renaming another account never grants access.

This grants no admin permissions, draft/archived content access, access to other
learners' attempts, answer-key access before exam submission, or changes to
grading thresholds and server exam timers. Real progress, grades and completion
timestamps remain real; unlocking does not mark content as completed. Explicit
pronunciation section completion remains available without prior sections.
Remove the UUID and restart the backend to restore prerequisites without
deleting the account or its history. No database migration is needed. Deploy
the backend and configure the capability before deploying the frontend.

From the repository root after validation:

```powershell
railway up backend --path-as-root --service backend --detach
vercel deploy --prod --yes --cwd frontend
```

Confirm Railway logs/readiness, Vercel deployment status and the real browser
login flow before reporting success. The initial release was deployed directly;
automatic deployments from GitHub are not configured.

## Hanfolio release — 2026-11-11

The user authorized committing and pushing the complete current local version,
then deploying it to the existing Railway production backend and renamed Vercel
project. The public UI name and document title are Hanfolio. The intended primary
address is `hanfolio-mcbo1.vercel.app`, selected by the user because
`hanfolio.vercel.app` is already in use; no paid domain was purchased or registered.
Legacy production origins remain allowed and the new origin is added explicitly.
Deployment uses the existing database and migrations; local database records are
not restored over production. AI document processing remains disabled.

## Pronunciation and workspace release — 2026-11-13

The release retains the current curriculum, learner pronunciation navigation,
shared browser Mandarin player and selected fixed recordings. Source originals,
hashes, notices and owner-attested distribution authorization are retained.
See `docs/mandarin-audio.md` and the audio distribution-rights manifest.

Retired 2D/3D journey implementations, image prototypes, voice auditions and
unused TTS endpoint experiments are removed. Lesson cloud transitions remain.
The frontend no longer depends on Three.js. Build/test outputs and temporary
review files stay excluded from Git; database backups are preserved outside
the checkout. No lesson data, user records, migrations or API DTOs change.

Only the Vercel frontend requires a new production build. Railway application
source matches its deployed runtime; retain the existing backend/database and
verify readiness rather than restarting them for a frontend-only release.

## Read-only account directory — 2026-11-14

Admin navigation adds `/admin/users` and `/admin/users/:userId`. The backend
provides admin-only GET list/detail endpoints with bounded pagination, literal
case-insensitive name/email search, role filtering and newest-first ordering.
Explicit response projections exclude password hashes and session versions.
Details include existing lesson activity, pronunciation completion and graded
attempt summaries. Account status is the stored active flag, not online status.

This release has no database migration, account mutation endpoint or seed/data
transfer operation. Deploy the backend first, confirm readiness and protection,
then deploy the frontend. Preserve existing database/storage volumes. Directory
requests execute only SELECT queries; do not invoke learner progress endpoints
to derive admin activity, since those can materialize progress records.

## Curriculum and cover release — 2026-11-21

The reviewed collection contains 40 lessons: HSK1 1–15, HSK2 1–10 and HSK3
1–15. HSK3 comes from the supplied DOCX; its source audit records merged lesson
3 parts, contextual pronunciation corrections and exact duplicate omissions.
Each lesson has 30 objective questions, explanations and an 80% pass threshold.
The frontend has a distinct subject cover for every lesson in both roles, an
admin library with 10 lessons per page, and completed-lesson vocabulary cards.

This release requires the new backend route before the frontend. It introduces
no schema migration or AI-provider change. Production Docker includes only the
reviewed curriculum manifests and explicitly named release/import scripts.

Database content is updated separately from the application deployment; never
restore a local database into production. Before the explicit content release,
make a PostgreSQL custom-format dump, verify its table of contents, download it
to ignored operational storage and compare SHA-256. Keep the dump and its
receipt outside Git. The production release command is
`python -m scripts.release_curriculum --inspect`, followed by `--apply` with the
returned `--expected-fingerprint`, a `--backup-receipt` path and matching
`--backup-sha256`. This command only permits the existing named Railway project,
its production environment and learning-only mode. Import/publication share an
outer transaction; a failure rolls back the whole batch. Account, pronunciation
and learner-history fingerprints must remain identical before/after. Existing
assessment attempts and old questions remain attached to archived assessments.

After release, verify 15/10/15 published lessons, 40 published lesson exercises,
1,200 active practice questions, 1,097 attached vocabulary senses, 119 grammar
points and 144 readings. Confirm protected account/history counts and real
student/admin access, vocabulary review, cover assets and deep-link reload.
