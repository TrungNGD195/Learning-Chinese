# Trung Chinese Learning

A Vietnamese-first Chinese learning web app with a structured curriculum and a lesson-aware AI assistant. The backend is a modular monolith; the frontend is a separate React client. AI providers are called through backend interfaces.

## Project map

| Path | Purpose |
| --- | --- |
| `backend/` | FastAPI application, database migrations, tests, and AI integrations |
| `frontend/` | React, TypeScript, Vite client and browser tests |
| `evaluation/` | Versioned evaluation cases, fixtures, validators, and evaluation assets |
| `docs/` | Implementation notes, run reports, and learning/evaluation documentation |
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

## Current pause point

Step 8.3 Stage B T4 validation is paused. Modal required a payment method to continue, and adding one or incurring paid usage is outside the approved cost boundary. No model cache was populated, no validation runtime was deployed, no T4 was allocated, and no production GPU profile or production re-embedding was performed. See [Project status and resume notes](docs/PROJECT_STATUS.md) and the current [PM Decision Log](Spec-CURRENT/PM-Control/04-Decision-Log-and-Open-Gates.md) before resuming work.

## Safety and local-only files

Do not commit `.env` files, credentials, PostgreSQL data, uploaded documents, model weights, Python/Node environments, caches, or test-generated files. These are excluded by `.gitignore`. Keep `Spec-CURRENT/` and `docs/` as the in-repository project context. Codex execution task packets are maintained outside this checkout.

Installed agent skills (`.agents/`), machine-specific hooks (`.codex/`), generated
design previews, screenshots, and local textbook PDFs also stay outside Git.
The textbook filenames and checksums are recorded in [the source inventory](docs/learning-sources.md).
Committed design review notes describe past checks; regenerate their screenshots
with the verification scripts in `frontend/scripts/` when needed.
