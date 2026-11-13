# Hanfolio

A Vietnamese-first Chinese learning web app with pronunciation, structured lessons and practice. The backend is a modular monolith; the frontend is a separate React client. Document AI is disabled in the deployed learning-only configuration.

## Project map

| Path | Purpose |
| --- | --- |
| `backend/` | FastAPI application, database migrations, tests, and AI integrations |
| `frontend/` | React, TypeScript, Vite client and browser tests |
| `evaluation/` | Versioned evaluation cases, fixtures, validators, and evaluation assets |
| `docs/` | Current operational guides, learning policies, sources and attribution; see [the index](docs/README.md) |
| `Spec-CURRENT/` | Current product specifications, PM decisions, and execution protocol |
| `infra/` | Local PostgreSQL initialization assets |
| `compose.yaml` | Local pgvector PostgreSQL service |
| `compose.app.yaml` | Development containers for the backend and frontend |
| `DESIGN.md`, `PRODUCT.md` | Approved visual system and product direction |

The approved academy interface is implemented in the application. The superseded
`/design-lab` and `/journey-test.html` prototypes have been removed.

## Local development

Requirements: Python 3.12, `uv`, Node.js 22.12 or newer, npm, and PostgreSQL with pgvector. Docker Compose can start a local PostgreSQL instance; its default credentials are for local development only.

Start the local database from the repository root:

```powershell
docker compose up -d db
```

PostgreSQL is available on `127.0.0.1:5433` by default. Set `POSTGRES_PORT`
to override the host port and use the same port in both backend database URLs.
CI explicitly uses port `5432` for its temporary database.

### Backend

```powershell
cd backend
uv sync
Copy-Item .env.example .env
# Edit .env for your local PostgreSQL and any provider credentials you choose to use.
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Run backend tests with:

```powershell
cd backend
uv run pytest -q
```

### Frontend

```powershell
cd frontend
npm ci
npm run dev
```

The frontend expects the backend API at the base URL configured by the frontend environment. See the current frontend and backend configuration for local values.

For local Vite development, use `VITE_API_BASE_URL=/api/v1` as shown in
`frontend/.env.example`. Vite proxies requests to `http://127.0.0.1:8000`;
set the shell variable `API_PROXY_TARGET` if your backend uses another port.
The app Compose configuration sets the internal backend target automatically.
This keeps session cookies on the frontend hostname whether you open
`localhost:5173` or `127.0.0.1:5173`.

## Verification

From `frontend/`, run `npm run lint`, `npm run test -- --run`, and `npm run build`.
With the test API running at port 8000, run `npm run api:check`.
`npm run test:e2e` starts its servers and resets/seeds only the dedicated
`chinese_learning_test` database. Never point it at learner or production data.
The authoritative CI sequence is [.github/workflows/ci.yml](.github/workflows/ci.yml).

## Current pause point

Step 8.3 Stage B T4 validation is paused. Modal required a payment method to continue, and adding one or incurring paid usage is outside the approved cost boundary. No model cache was populated, no validation runtime was deployed, no T4 was allocated, and no production GPU profile or production re-embedding was performed. See [Project status and resume notes](docs/PROJECT_STATUS.md) and the current [PM Decision Log](Spec-CURRENT/PM-Control/04-Decision-Log-and-Open-Gates.md) before resuming work.

## Safety and local-only files

Do not commit `.env` files, credentials, PostgreSQL data, uploaded documents, model weights, Python/Node environments, caches, or test-generated files. These are excluded by `.gitignore`. Keep `Spec-CURRENT/` and `docs/` as the in-repository project context. Codex execution task packets are maintained outside this checkout.

Installed agent skills (`.agents/`), machine-specific hooks (`.codex/`), generated
design previews, screenshots, and local textbook PDFs also stay outside Git.
The textbook filenames and checksums are recorded in [the source inventory](docs/learning-sources.md).
Retired journey prototypes, voice auditions and generated review outputs are
removed. Active pronunciation recordings retain their originals, processing
scripts, hashes and attribution; see [Mandarin audio](docs/mandarin-audio.md).
Run the verification scripts in `frontend/scripts/` to regenerate checks.
