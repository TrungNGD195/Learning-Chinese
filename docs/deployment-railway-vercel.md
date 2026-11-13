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
