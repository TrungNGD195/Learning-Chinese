# Step 3.2 — Configuration & Environment

## Goal

Implement the backend configuration foundation for Development, Test and Production.

Configuration must be centralized, typed, validated and environment-driven.

Do not implement database connections, authentication, LLM providers or external services yet.

---

# Environments

Support:

```text
development
test
production
```

Use one codebase for all environments.

Environment differences must be supplied through configuration rather than source-code branches.

---

# Configuration Source

Runtime configuration must come primarily from environment variables.

Local development may load variables from:

```text
backend/.env
```

`.env` must not be committed.

Commit:

```text
backend/.env.example
```

with placeholder/example values only.

---

# Settings Implementation

Use:

```text
pydantic-settings
```

and define centralized configuration under:

```text
app/core/config.py
```

All application modules should access configuration through the Settings abstraction.

Do not scatter direct `os.getenv()` calls throughout domain modules.

---

# Initial Settings

Support at least:

```text
APP_NAME
APP_ENV
DEBUG
API_V1_PREFIX
DATABASE_URL
SECRET_KEY
CORS_ORIGINS
LOG_LEVEL
```

Recommended defaults where safe:

```text
APP_NAME=Chinese Learning API
APP_ENV=development
DEBUG=true
API_V1_PREFIX=/api/v1
LOG_LEVEL=DEBUG
```

Do not provide insecure production secret defaults.

`DATABASE_URL` and `SECRET_KEY` should be treated as required where the application step requires them.

---

# Deferred Configuration

Do not add unused configuration for future integrations yet, including:

```text
LLM_PROVIDER
LLM_API_KEY
EMBEDDING_API_KEY
EXTERNAL_SEARCH_API_KEY
EMAIL_API_KEY
```

Add them when the corresponding feature is implemented.

---

# Settings Validation

Settings must use appropriate Python types.

Examples:

```text
DEBUG → bool
CORS_ORIGINS → list/string collection
DATABASE_URL → validated connection string representation where practical
```

If a required setting is missing or invalid:

```text
startup must fail
```

Do not silently substitute ambiguous production values.

---

# Settings Loading

Provide a reusable cached accessor such as:

```python
get_settings()
```

or an equivalent singleton/cached Settings instance.

Do not reconstruct Settings and reload `.env` for every request.

---

# Secret Rules

Never commit real values for:

```text
SECRET_KEY
database credentials
future authentication secrets
external API keys
provider credentials
```

`.env.example` must contain placeholders only.

---

# Debug Behavior

Expected policy:

```text
development
→ DEBUG enabled

test
→ controlled, normally disabled

production
→ DEBUG disabled
```

Do not expose internal stack traces or sensitive configuration details in production API responses.

---

# API Prefix

Use Settings as the source of truth for:

```text
API_V1_PREFIX=/api/v1
```

Application router registration should use this setting rather than repeating the string across modules.

---

# CORS

Configuration must support:

```text
CORS_ORIGINS
```

Development may allow known localhost frontend origins.

Do not configure unrestricted production wildcard origins by default.

Actual frontend production origins will be provided later through environment configuration.

---

# Logging

Support configurable:

```text
LOG_LEVEL
```

Typical policy:

```text
development → DEBUG
production  → INFO
```

Do not implement advanced observability/monitoring in this step.

---

# Time Convention

Application/database timestamps must use UTC internally.

Do not persist application timestamps as fixed Bangkok/local timezone values.

Frontend/presentation layer may convert UTC timestamps to the user-facing timezone.

---

# Test Configuration

Tests must run using:

```text
APP_ENV=test
```

and a dedicated test database configuration, such as:

```text
TEST_DATABASE_URL
```

or an equivalent explicitly test-scoped setting.

Test setup must not accidentally connect to or mutate a production database.

Implement a safety guard where practical so destructive test setup refuses unsafe database targets.

---

# Config vs Runtime State

Configuration may contain:

```text
environment
database connection
API prefix
secrets
CORS
logging
```

It must not contain mutable application state such as:

```text
current user
current lesson
learning progress
active conversation
assessment attempt
```

Those belong to domain/database state.

---

# Expected Files

Target:

```text
backend/
├── .env.example
│
└── app/
    └── core/
        └── config.py
```

Update:

```text
.gitignore
pyproject.toml
```

as required.

Local `.env` may exist but must remain untracked.

---

# `.env.example`

Include the currently required/configured variable names only.

Example shape:

```env
APP_NAME=Chinese Learning API
APP_ENV=development
DEBUG=true
API_V1_PREFIX=/api/v1

DATABASE_URL=postgresql://user:password@localhost:5432/chinese_learning

SECRET_KEY=replace-with-local-secret

CORS_ORIGINS=http://localhost:5173
LOG_LEVEL=DEBUG
```

Do not add real credentials.

---

# Application Integration

Update FastAPI startup/application setup so it can consume:

- app name;
- debug mode;
- API prefix;
- CORS settings;

from the centralized Settings object where applicable.

Do not open the PostgreSQL connection in this step.

---

# Out of Scope

Do not implement:

- SQLAlchemy/session management;
- PostgreSQL connection;
- migrations;
- authentication/JWT behavior;
- password hashing;
- LLM/provider configuration;
- email service configuration;
- external retrieval configuration;
- production secret-manager integration;
- Docker/deployment configuration.

---

# Acceptance Criteria

- [ ] Development/Test/Production environment values are supported.
- [ ] Configuration is centralized in `core/config.py`.
- [ ] `pydantic-settings` is used.
- [ ] `.env` is ignored by Git.
- [ ] `.env.example` contains no real secrets.
- [ ] Settings use typed values.
- [ ] Invalid required configuration fails early.
- [ ] Settings are not reparsed for every request.
- [ ] API prefix comes from configuration.
- [ ] CORS origins are configurable.
- [ ] Production debug behavior can be disabled.
- [ ] Logging level is configurable.
- [ ] Backend timestamps use UTC convention.
- [ ] Tests have dedicated database configuration/safety.
- [ ] No unused LLM/external-provider settings are introduced prematurely.

# Expected Deliverable

Runnable configuration foundation plus:

```text
docs/backend/
└── step-3.2-configuration-environment.md
```

Next Step:

**Step 3.3 — Database Access**