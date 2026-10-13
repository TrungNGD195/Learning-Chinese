# Step 3.2 — Configuration & Environment

## Objective

Add centralized, typed settings for development, test, and production, and make the current FastAPI application consume its relevant settings.

## Why

Environment-specific values should be validated at startup and accessed consistently. This keeps configuration out of domain modules and makes test and production behavior explicit without implementing database access or authentication.

## Mental Model

```text
Environment / backend/.env
→ typed Settings
→ FastAPI application setup
```

Configuration describes how the application should run. It is not mutable user, lesson, progress, conversation, or assessment state.

## Core Knowledge

- `pydantic-settings` loads environment variables and an optional local `.env` file into typed fields.
- A cached settings accessor avoids parsing configuration again for each request.
- Environment and log-level literals reject unknown values during startup.
- `CORS_ORIGINS` accepts comma-separated values and normalizes whitespace and empty entries.
- `DATABASE_URL`, `TEST_DATABASE_URL`, and `SECRET_KEY` are configuration contracts only in this Step. They do not create a database connection or implement authentication.

## Data Flow

The process environment takes precedence over the optional `backend/.env` file. Settings validates the values once when the application is created. FastAPI uses the configured app name and debug flag, stores the future API prefix for router registration, and configures CORS from the normalized origins.

Tests select `APP_ENV=test` and a distinct `TEST_DATABASE_URL`; they validate configuration without connecting to it.

## Key Design Decisions

- Preserve the accepted Step 3.1 default API title, `Trung Chinese Learning API`.
- Keep database and secret settings optional until their consumer Steps require them. Secret values use `SecretStr` and have no default.
- Require a dedicated test database URL in test mode and reject an exact match with `DATABASE_URL`.
- Reject debug mode and wildcard CORS origins in production. The default CORS list is empty; local origins are shown only as development examples.
- Apply `LOG_LEVEL` to the application logger using the standard library.
- Keep `/health` unchanged and do not create a placeholder business router for `/api/v1`.
- Treat internal/database timestamps as UTC; presentation code may convert them for display. No timestamp subsystem is needed yet.

## Approach Reusable in Another Project

Define one settings model in the application-wide infrastructure area, keep its fields typed and validated, load it once, and inject or pass it into application construction. Test the model with environment values while preventing settings cache leakage. Keep integration credentials as inert configuration until the relevant integration step exists.

## Common Mistakes

- Scattering `os.getenv()` calls across routes and domain modules.
- Rebuilding settings for every request.
- Giving production a real-looking secret default or unrestricted CORS origin.
- Treating a configured database URL as permission to create a connection early.
- Sharing the regular database URL with test configuration.
- Putting mutable domain state into application settings.

## Definition of Done

- Settings support validated development, test, and production environments.
- `.env` is ignored and `.env.example` contains placeholders only.
- FastAPI consumes configured name, debug, API prefix, CORS, and logging values.
- Tests use a dedicated test database URL without connecting to a database.
- Existing health, OpenAPI, and application-error behavior remains intact.
- No Step 3.3 or later implementation is present.
