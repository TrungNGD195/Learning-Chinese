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
| `codex-tasks/` | Step-specific implementation tasks and review packets |
| `infra/` | Local PostgreSQL initialization assets |
| `compose.yaml` | Local pgvector PostgreSQL service |

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

Do not commit `.env` files, credentials, PostgreSQL data, uploaded documents, model weights, Python/Node environments, caches, or test-generated files. These are excluded by `.gitignore`. Keep PM specifications and step task files with the project so later work can resume against the current contracts.
