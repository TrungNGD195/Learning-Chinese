# Codex Execution Task — Step 3.5: Authentication & User Context

## Status / Execution Gate

This is the **single current Codex execution task** for:

**Step 3.5 — Authentication & User Context**

Owner: **App Engineering Specialist**

Do not implement Step 3.6 or any later Step.

Before editing:

1. inspect the actual accepted repository after Step 3.4;
2. read the authoritative Step 3.5 specification;
3. read the canonical PM Decision Log through D-018;
4. preserve accepted Steps 3.1–3.4 behavior unless Step 3.5 explicitly replaces an integration seam.

If the repository materially differs from the accepted state described here, or if a current source conflicts with D-012 through D-018, stop and report `BLOCKED` rather than inventing a security contract.

Do not run destructive tests against any non-test database.

---

# 1. Objective

Implement the MVP authentication and authorization foundation for the FastAPI backend:

- public learner registration;
- email normalization;
- Argon2id password hashing;
- JWT Access Tokens;
- opaque server-revocable rotating Refresh Tokens;
- HttpOnly browser cookies;
- authoritative current-user resolution from PostgreSQL;
- disabled-user enforcement;
- reusable Admin authorization;
- logout / logout-all;
- authenticated change-password;
- password-reset request/confirm;
- provider-neutral `EmailService` boundary;
- explicit one-time production Admin bootstrap command;
- forward Alembic migration `0002_auth_token_tables`.

Step 3.5 also replaces the temporary Step-3.4 current-user seam with real authentication **without redesigning Step 3.4 business APIs or moving resource ownership out of domain services**.

---

# 2. Source of Truth

## Primary

- `Spec-CURRENT/Phase3/Step 3.5 — Authentication & User Context.md`

## Required dependencies

- `Spec-CURRENT/PROJECT_CONTEXT.md`
- current `PM-Control/04-Decision-Log-and-Open-Gates.md`
- accepted Step 3.4 repository state
- accepted Step 3.3 database/session/migration foundation
- relevant Phase 1 Auth/component ownership specifications
- relevant Phase 2 `users` / migration / Admin-bootstrap constraints
- `PM-Control/05-Codex-Execution-Protocol.md`

## Precedence

If documents differ:

1. latest PM Decision Log;
2. authoritative Step 3.5;
3. intentionally later refinements;
4. earlier Phase specifications;
5. notes/examples/plans.

Do not silently resolve a real security conflict.

---

# 3. Frozen Decisions

The following contracts are mandatory. Do not substitute library defaults or alternative security designs.

## D-001 — Same-Site V0 topology

The browser experiences frontend + API as one logical same-site application.

Do not redesign Step 3.5 for cross-site auth cookies.

## D-008 / D-011 — Replace temporary current-user seam

Step 3.4's temporary injectable `get_current_user()` is replaced by the real authenticated dependency.

Preserve existing learner `/me/...` APIs and existing normalized missing-auth contract:

```text
HTTP 401
AUTHENTICATION_REQUIRED
```

Do not reintroduce client-controlled learner `user_id`.

## D-012 — JWT signing and password cryptography

Access Token:

```text
algorithm = HS256
library   = PyJWT
```

Use existing protected `SECRET_KEY`.

Step 3.5 requirements:

```text
SECRET_KEY required in every environment
production SECRET_KEY length >= 32 characters
```

Do not add asymmetric signing, key rotation infrastructure, or external key management.

Password policy:

```text
minimum = 8 characters
maximum = 128 characters
no mandatory composition rules
```

Hash using:

```text
Argon2id
argon2-cffi PasswordHasher defaults
```

Reuse the same password policy for:

- registration;
- reset;
- change password.

Never persist or log plaintext passwords.

## D-013 — Opaque Refresh / Reset tokens

Refresh Tokens and reset tokens are **not JWTs**.

Generate:

```text
32 cryptographically-random bytes
→ URL-safe encoding
```

Persist only:

```text
SHA-256(raw_token)
→ lowercase hex token_hash
```

Do not use Argon2 for opaque token lookup hashes.

Raw Refresh/Reset tokens must never be persisted.

### `refresh_tokens`

```text
id UUID PK
user_id UUID NOT NULL FK → users.id ON DELETE CASCADE
token_hash TEXT NOT NULL UNIQUE
expires_at TIMESTAMPTZ NOT NULL
revoked_at TIMESTAMPTZ NULL
created_at TIMESTAMPTZ NOT NULL
index(user_id)
index(expires_at)
```

### `password_reset_tokens`

```text
id UUID PK
user_id UUID NOT NULL FK → users.id ON DELETE CASCADE
token_hash TEXT NOT NULL UNIQUE
expires_at TIMESTAMPTZ NOT NULL
used_at TIMESTAMPTZ NULL
created_at TIMESTAMPTZ NOT NULL
index(user_id)
index(expires_at)
```

No `family_id`, `session_id`, refresh-family table or compromise-detection subsystem.

Refresh rotation:

```text
A valid active Refresh Token
→ revoke old row
→ generate replacement Refresh Token
→ insert replacement hash
→ issue replacement Access Token
```

Reusing an already revoked/rotated Refresh Token:

```text
HTTP 401
INVALID_REFRESH_TOKEN
clear caller auth cookies
do not revoke unrelated User sessions
```

All-session revocation is explicit through logout-all, reset and change-password.

## D-014 — Browser cookie contract

### Access cookie

```text
name     = access_token
HttpOnly = true
Secure   = COOKIE_SECURE
SameSite = COOKIE_SAMESITE
Path     = /
Max-Age  = Access Token lifetime
Domain   = omitted / host-only
```

### Refresh cookie

```text
name     = refresh_token
HttpOnly = true
Secure   = COOKIE_SECURE
SameSite = COOKIE_SAMESITE
Path     = /api/v1/auth
Max-Age  = Refresh Token lifetime
Domain   = omitted / host-only
```

Development/test default:

```text
COOKIE_SECURE=false
```

Production:

```text
COOKIE_SECURE=true required
```

SameSite:

```text
default = lax
allowed = lax | strict
```

Do not enable `None` or cross-site cookies.

Cookie deletion must use the same **name + path** as cookie creation.

CORS must remain explicit-origin and become credentials-compatible. Do not weaken Step 3.2 origin validation.

No tokens in localStorage/sessionStorage.

## D-015 — Authentication HTTP/session contract

### Register

```http
POST /api/v1/auth/register
```

Success:

```text
201
create LEARNER
create Access + Refresh
persist Refresh hash
set both cookies
return safe User profile
```

Registration creates an authenticated browser session.

### Login

```http
POST /api/v1/auth/login
```

Success:

```text
200
issue Access + Refresh
persist Refresh hash
set both cookies
return safe User profile
```

### Current User

```http
GET /api/v1/auth/me
```

Success:

```text
200
safe User profile
```

Use exactly learner/admin-safe identity fields unless the authoritative spec requires more:

```text
id
email
full_name
role
```

### Refresh

```http
POST /api/v1/auth/refresh
```

Success:

```text
204
validate old Refresh
revoke old Refresh
issue replacement Access + Refresh
persist replacement Refresh hash
replace both cookies
```

### Logout

```http
POST /api/v1/auth/logout
```

Idempotent:

```text
revoke current Refresh Token when identifiable
always clear both local cookies
204
```

Do not require a valid Access Token for ordinary logout.

### Logout all

```http
POST /api/v1/auth/logout-all
```

Requires authenticated User:

```text
revoke every active Refresh Token for User
clear local auth cookies
204
```

### Reset request

```http
POST /api/v1/auth/password-reset/request
```

Public success:

```text
202
```

Use no account-existence-specific response body. An empty 202 response is acceptable and preferred over inventing a message contract.

### Reset confirm

```http
POST /api/v1/auth/password-reset/confirm
```

Success:

```text
update password
consume Reset Token
revoke all Refresh Tokens
clear browser auth cookies
204
User must log in again
```

### Change password

```http
POST /api/v1/auth/change-password
```

Authenticated success:

```text
verify current password
update password
revoke all Refresh Tokens
clear browser auth cookies
204
User must log in again
```

Access Tokens remain stateless. Do **not** add:

- access-token blacklist;
- `auth_version`;
- server-side access-token table.

A copied Access Token may remain cryptographically valid until normal expiration. Browser security after logout/password change/reset comes from Refresh revocation + cookie clearing.

## D-016 — Normalized auth errors

All errors use the existing project error envelope.

```text
missing/invalid/expired Access Token
→ 401 AUTHENTICATION_REQUIRED

authenticated non-Admin
→ 403 ADMIN_REQUIRED

missing/invalid/expired/revoked Refresh Token
→ 401 INVALID_REFRESH_TOKEN

wrong current password
→ 400 INVALID_CURRENT_PASSWORD

password policy failure
→ 422 INVALID_PASSWORD

invalid/expired/used Reset Token
→ 400 INVALID_RESET_TOKEN
```

Do not distinguish reset not-found vs expired vs used publicly.

Do not expose Refresh/Reset record existence.

Preserve:

```text
EMAIL_ALREADY_REGISTERED
INVALID_CREDENTIALS
ACCOUNT_DISABLED
```

Disabled User behavior:

- login → `403 ACCOUNT_DISABLED`;
- valid Access Token resolving to disabled DB User → `403 ACCOUNT_DISABLED`;
- Refresh Token belonging to disabled DB User → `403 ACCOUNT_DISABLED` and clear local cookies.

Do not leak hashes, token values, SQL/driver errors or auth internals.

## D-017 — Password reset lifecycle / Email boundary

For an existing **active** User:

```text
new reset request
→ invalidate earlier unused Reset Tokens
→ create one new Reset Token
→ persist only its hash
→ pass raw token transiently to EmailService
```

Because D-013 intentionally has no separate reset-revocation timestamp, use `used_at` as the terminal invalidation timestamp for superseded/consumed reset credentials. Do not add another schema column.

Successful reset:

```text
validate submitted token
→ mark submitted token used
→ invalidate other outstanding unused tokens
→ update password hash
→ revoke all Refresh Tokens
→ commit atomically
```

Nonexistent or disabled account reset request:

```text
same public 202
no usable Reset Token issued
```

Email boundary:

```text
EmailService.send_password_reset(...)
```

Test:

```text
FakeEmailService may capture raw Reset Token in process memory
```

Development:

- provider-neutral stub/logging implementation;
- may record that a reset request occurred;
- must **not** log the raw reset token or any password/hash/JWT secret/Refresh Token.

Production email-provider selection is out of scope and deferred. Do not add a vendor SDK.

Keep `EmailService` injectable so Phase 8 can supply the production adapter. Until then, the application may use a non-delivering provider-neutral stub; document that production email delivery is a deployment dependency, not implemented in Step 3.5.

If a delivery adapter raises after a Reset Token has been committed, invalidate that newly-created reset token in a short compensating transaction and preserve the generic public 202 response so provider failure does not become account-enumeration information.

Raw reset token exists only transiently in memory while being passed to the adapter/test fake.

## D-018 — Production Admin bootstrap

Provide explicit one-time CLI behavior equivalent to:

```bash
uv run python -m app.auth.bootstrap_admin
```

Input comes from environment values equivalent to:

```text
ADMIN_EMAIL
ADMIN_PASSWORD
ADMIN_FULL_NAME
```

Flow:

```text
normalize email
validate password policy
Argon2id hash
create User role=ADMIN
```

Must:

- require explicit operator invocation;
- create no default credentials;
- log no credentials;
- hard-code no credentials;
- refuse to overwrite existing account;
- refuse to silently promote an existing LEARNER;
- never run automatically at application startup.

Public registration remains LEARNER-only.

---

# 4. Accepted Repository State

Steps 3.1–3.4 are accepted and closed.

Current relevant structure:

```text
backend/
├── pyproject.toml
├── uv.lock
├── alembic.ini
├── migrations/
│   ├── env.py
│   └── versions/
│       └── 0001_initial_schema.py
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   └── errors.py
│   ├── database/
│   │   ├── engine.py
│   │   ├── session.py
│   │   └── models/
│   │       └── user.py
│   ├── auth/
│   │   ├── __init__.py
│   │   └── current_user.py
│   ├── curriculum/
│   ├── exercise/
│   ├── progress/
│   └── admin/
└── tests/
```

Current temporary `app/auth/current_user.py` returns no runtime identity and raises D-011 401.

Current learner routers depend on it as an injected UUID and then pass that UUID to existing domain services.

Current Admin router has no real auth guard.

Current app CORS middleware does not yet set `allow_credentials=True`.

Current Settings has optional `SECRET_KEY` and no Step-3.5 auth lifetime/cookie settings.

Current migration chain contains only:

```text
0001_initial_schema
```

`users` already exists:

```text
id UUID PK
email NOT NULL UNIQUE
password_hash NOT NULL
full_name NOT NULL
role LEARNER|ADMIN
is_active NOT NULL
created_at
updated_at
```

Do not redesign the User table in Step 3.5.

---

# 5. Required Dependencies

Add only the security libraries frozen by D-012:

```text
PyJWT
argon2-cffi
```

Use the normal `uv` workflow and update `uv.lock`.

Do **not** add:

- Passlib;
- python-jose;
- Authlib;
- OAuth frameworks;
- auth SaaS SDKs;
- Redis/session stores;
- CSRF packages for a cross-site design;
- MFA packages.

Use Python standard library `secrets` and `hashlib` for opaque tokens.

---

# 6. Target Auth Architecture

Preserve the modular-monolith boundary:

```text
Auth Router
→ AuthService
→ AuthRepository
→ AsyncSession / ORM
```

Additional focused components are allowed:

```text
PasswordHasher / password policy
JWT AccessTokenService
OpaqueTokenService
Cookie helpers
EmailService boundary
get_current_user()
require_admin()
Admin bootstrap CLI
```

Do not create a generic auth framework.

### Router

Owns:

- HTTP request/response;
- dependencies;
- setting/clearing cookies;
- status codes;
- Pydantic schemas.

### AuthService

Owns:

- register/login flows;
- refresh rotation;
- password-reset lifecycle;
- change-password;
- logout/logout-all orchestration;
- transaction boundaries;
- stable auth errors.

### AuthRepository

Owns controlled queries/mutations for:

- User lookup/create/password update;
- Refresh Token rows;
- Reset Token rows.

Repository must **not** call `commit()`.

### Auth dependencies

`get_current_user()`:

- validates Access JWT;
- loads authoritative User from DB;
- enforces active state;
- returns the database User object.

`require_admin()`:

- depends on `get_current_user()`;
- checks **database User.role**, not JWT claim alone;
- returns the authoritative User if ADMIN.

---

# 7. Expected Files / Components

Inspect current structure first. Prefer these locations or nearby repository conventions:

```text
backend/app/auth/
├── __init__.py
├── router.py
├── schemas.py
├── service.py
├── repository.py
├── security.py
├── cookies.py
├── email.py
├── current_user.py      # replace temporary implementation
└── bootstrap_admin.py

backend/app/database/models/auth.py

backend/migrations/versions/0002_auth_token_tables.py
```

Expected modifications:

```text
backend/pyproject.toml
backend/uv.lock
backend/.env.example
backend/app/core/config.py
backend/app/main.py
backend/app/database/models/__init__.py
backend/app/curriculum/router.py
backend/app/exercise/router.py
backend/app/progress/router.py
backend/app/admin/router.py
backend/tests/conftest.py
```

Add focused auth/integration/migration tests.

Create:

```text
docs/backend/step-3.5-authentication-user-context.md
```

Do not modify `0001_initial_schema.py`.

---

# 8. Configuration

Extend Settings with exactly the Step-3.5-relevant configuration:

```text
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
PASSWORD_RESET_EXPIRE_MINUTES=30
COOKIE_SECURE=false
COOKIE_SAMESITE=lax
```

`SECRET_KEY` becomes required for Step 3.5.

Validation:

- access lifetime > 0;
- refresh lifetime > 0;
- reset lifetime > 0;
- `COOKIE_SAMESITE` only `lax | strict`;
- production: `DEBUG=false` remains required;
- production: `COOKIE_SECURE=true` required;
- production: `SECRET_KEY` length >= 32 characters;
- explicit CORS origins only once cookie credentials are enabled; reject wildcard `*` in every Step-3.5 environment rather than combining wildcard origin with credentials.

Do not log `SECRET_KEY`.

Update `.env.example` with safe placeholders and no real secret.

Use a sufficiently long dummy placeholder description/value, but never a real deployment secret.

Do not put Admin bootstrap password in committed `.env.example`; D-018 credentials should be operator-provided for the one-time CLI invocation.

---

# 9. CORS Integration

Update `CORSMiddleware` for browser cookies:

```text
allow_credentials=True
```

Preserve:

- explicit allowed origins;
- current methods/headers behavior;
- same-site logical topology.

Do not use `allow_origins=["*"]` with credentialed requests.

Add a focused CORS/config test.

---

# 10. Password Policy / Hashing

Provide one reusable password-policy function used by register/reset/change-password.

Rules:

```text
8 <= len(password) <= 128
```

No uppercase/number/symbol composition rules.

Failure:

```text
422 INVALID_PASSWORD
```

Hash/verify using `argon2.PasswordHasher` defaults, which produce Argon2id hashes.

Never compare passwords manually.

Never log:

- plaintext password;
- password hash.

Tests must verify:

- stored password differs from plaintext;
- hash identifies Argon2id;
- correct password verifies;
- wrong password fails;
- bounds 7/8/128/129.

For login user-enumeration resistance, unknown-email and wrong-password paths must return the same public `INVALID_CREDENTIALS`. Use a safe dummy Argon2 verification path when the User does not exist so the implementation does not intentionally create a trivially different password-hash work path.

Do not expose whether a dummy hash was used.

---

# 11. Email Normalization

Use one helper:

```text
trim whitespace
→ lowercase
```

Apply before:

- registration persistence/lookup;
- login lookup;
- reset-request lookup;
- Admin bootstrap lookup/persistence.

Reject an empty normalized email through normal request validation.

Do not add an email-provider or email-verification subsystem.

Do not introduce a new case-insensitive email database type/index in this Step; normal application creation paths must persist normalized emails.

Duplicate-registration handling must be race-safe: application pre-check is allowed, but the database UNIQUE constraint remains authoritative and a uniqueness failure must normalize to:

```text
409 EMAIL_ALREADY_REGISTERED
```

without leaking SQL details.

---

# 12. Access JWT

Implement using PyJWT and HS256 only.

Claims:

```text
sub  = User UUID string
role = current DB User role at issue time
iat  = UTC NumericDate
exp  = UTC NumericDate
```

Do not add mutable progress/profile/authz state.

JWT creation uses `Settings.secret_key.get_secret_value()`.

JWT decode must:

- specify `algorithms=["HS256"]`;
- verify signature;
- verify expiry;
- require `sub`, `role`, `iat`, `exp`;
- reject malformed UUID `sub`;
- map invalid/expired/missing Access credentials to D-016 `AUTHENTICATION_REQUIRED`.

Never log the Access Token.

Do not persist Access Tokens.

---

# 13. Opaque Token Service

Use Python standard library only.

Equivalent implementation:

```text
raw = secrets.token_urlsafe(32)
hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
```

The random source must correspond to 32 random bytes.

Provide helper(s) shared by Refresh and Reset flows.

Never log raw values.

Do not compare raw credentials against database values because raw values are never stored.

---

# 14. Persistence Models and Migration 0002

Create mappings for:

```text
RefreshToken
PasswordResetToken
```

Use application-side UUID v4 defaults consistent with existing entity mappings.

Use UTC-aware timestamps.

Create forward migration:

```text
revision      = 0002_auth_token_tables
down_revision = 0001_initial_schema
```

Migration must create exactly the D-013 persistence structures.

### Refresh token table

Required:

- PK UUID;
- user FK CASCADE;
- token hash UNIQUE;
- expires_at timezone-aware;
- revoked_at nullable timezone-aware;
- created_at timezone-aware server default/current UTC;
- explicit user index;
- explicit expires index.

### Reset token table

Required:

- PK UUID;
- user FK CASCADE;
- token hash UNIQUE;
- expires_at timezone-aware;
- used_at nullable timezone-aware;
- created_at timezone-aware;
- explicit user index;
- explicit expires index.

Do not add:

- raw token columns;
- token family/session columns;
- access token table;
- auth_version;
- email verification table;
- MFA/OAuth tables.

Update `app.database.models.__init__` so Alembic metadata sees the new mappings.

Do not rewrite `0001`.

Manually review autogenerate if used.

---

# 15. AuthRepository

Provide focused repository operations, for example:

### Users

- get user by normalized email;
- get user by id;
- add learner/admin User supplied by AuthService/bootstrap;
- update password hash.

### Refresh Tokens

- insert token hash;
- lookup token by hash;
- lookup token by hash **FOR UPDATE** for rotation;
- revoke token;
- revoke all active tokens for user.

### Reset Tokens

- insert token hash;
- lookup token by hash **FOR UPDATE** for consume;
- invalidate all unused tokens for user;
- mark token used/invalidated.

Repository does not commit.

Do not hide transaction ownership inside repository helpers.

---

# 16. Register

Endpoint:

```http
POST /api/v1/auth/register
```

Request model:

```text
email
password
full_name
```

Use Pydantic with `extra="forbid"` so public callers cannot send `role` or hidden identity fields.

Validation:

- normalize email;
- non-empty `full_name` after trim;
- password D-012 policy.

Flow:

```text
validate/hash password before write transaction
→ short DB transaction
→ create User role=LEARNER, is_active=true
→ create Refresh Token row
→ commit
→ create Access JWT / return raw Refresh to router
→ set both cookies
→ return profile
```

It is also acceptable to create the Access JWT before commit as long as cookies/body are not returned until commit succeeds.

Do not set cookies if DB commit fails.

Handle duplicate normalized email as exact:

```text
409 EMAIL_ALREADY_REGISTERED
```

Response profile:

```text
id
email
full_name
role
```

No password/token hashes in API output.

---

# 17. Login

Endpoint:

```http
POST /api/v1/auth/login
```

Request:

```text
email
password
```

Flow:

```text
normalize email
→ lookup User
→ Argon2 verify (or dummy verify if unknown)
→ generic invalid-credentials handling
→ verify User active
→ generate Access + raw Refresh
→ short transaction persists Refresh hash
→ commit
→ set cookies
→ return safe profile
```

Do not hold a deliberate DB write transaction around Argon2 verification.

Unknown email and wrong password both:

```text
401 INVALID_CREDENTIALS
```

Disabled account with correct credentials:

```text
403 ACCOUNT_DISABLED
```

Do not return tokens in JSON.

---

# 18. Cookie Helpers

Centralize cookie set/clear behavior so register/login/refresh/logout/reset/change-password cannot drift.

Functions should use D-014 exact names/paths/options.

Max-Age:

```text
Access = ACCESS_TOKEN_EXPIRE_MINUTES * 60
Refresh = REFRESH_TOKEN_EXPIRE_DAYS * 86400
```

Cookie values:

- access cookie = raw JWT string;
- refresh cookie = raw opaque Refresh Token.

No Domain attribute.

Cookie clear must exactly match:

```text
access_token path=/
refresh_token path=/api/v1/auth
```

Add tests inspecting `Set-Cookie` headers for:

- HttpOnly;
- Secure based on config;
- SameSite;
- Path;
- Max-Age;
- correct clearing paths.

---

# 19. `get_current_user()`

Replace the temporary Step-3.4 implementation in place so imports remain stable.

Signature may receive:

- Access cookie;
- request-scoped AsyncSession;
- Settings/token service as dependencies/helpers.

Flow:

```text
read access_token cookie
→ missing = AUTHENTICATION_REQUIRED
→ decode JWT HS256
→ parse sub UUID
→ load User by id from PostgreSQL
→ missing User = AUTHENTICATION_REQUIRED
→ disabled User = ACCOUNT_DISABLED
→ return authoritative User ORM object
```

JWT role is **not authoritative**.

Do not authorize Admin from JWT role without DB lookup.

Auth dependency must not commit.

Do not change business ownership/access logic inside Step-3.4 services.

---

# 20. Step 3.4 Learner Integration

Current Step-3.4 routers currently expect:

```text
user_id: UUID = Depends(get_current_user)
```

Update them to use the authoritative User:

```text
current_user: User = Depends(get_current_user)
→ service(..., current_user.id)
```

Apply to all learner/current-user routes in:

- Curriculum router;
- Progress router;
- Exercise/attempt/history router.

Do not add User IDs to request bodies/query params.

Do not remove existing resource ownership checks from services.

Update old Step-3.4 tests that override `get_current_user()` so overrides return an actual persisted User object when they are intentionally testing business behavior rather than authentication.

Add true Step-3.5 integration tests using cookies/no dependency override.

---

# 21. `require_admin()` and Admin integration

Implement reusable:

```text
require_admin()
```

Flow:

```text
get_current_user()
→ authoritative DB User
→ role == ADMIN ? return User : 403 ADMIN_REQUIRED
```

Protect **every** `/api/v1/admin/...` endpoint through a reusable router-level dependency or an equivalent single reusable integration point.

Do not manually repeat role checks inside each Admin service method.

Do not move Admin authorization into Curriculum/Exercise/Progress business services.

Tests must prove:

- anonymous Admin request → 401 AUTHENTICATION_REQUIRED;
- authenticated LEARNER → 403 ADMIN_REQUIRED;
- authenticated ADMIN → reaches existing Admin business behavior;
- changing an issued token's User role in DB changes authorization immediately because DB state is authoritative.

---

# 22. Refresh Rotation

Endpoint:

```http
POST /api/v1/auth/refresh
```

Uses only Refresh cookie; a valid Access Token is not required.

Flow:

```text
read refresh_token cookie
→ missing = INVALID_REFRESH_TOKEN + clear cookies
→ SHA-256 hash
→ short transaction
→ SELECT matching Refresh row FOR UPDATE
→ validate exists / not expired / not revoked
→ load User
→ verify active
→ revoke old row
→ generate replacement raw Refresh + hash
→ insert replacement row
→ commit
→ issue new Access JWT
→ replace both cookies
→ 204
```

Generate replacement values before/inside the short transaction as convenient, but do not publish cookies until the transaction commits.

Use row locking so concurrent use of one Refresh Token cannot both rotate successfully.

If a second/concurrent/reused request observes the old row revoked:

```text
401 INVALID_REFRESH_TOKEN
clear caller cookies
do not revoke unrelated sessions
```

Expired/missing/unknown/revoked all share the same public error.

Disabled User:

```text
403 ACCOUNT_DISABLED
clear local cookies
```

Never expose token-record existence.

---

# 23. Logout

Endpoint:

```http
POST /api/v1/auth/logout
```

No Access Token required.

Behavior:

```text
if refresh cookie maps to a stored active row:
    revoke it in a short transaction
else:
    no error
always clear both cookies
return 204
```

If the Refresh Token is malformed/unknown/expired/revoked, logout remains idempotent 204.

Do not create or rotate a token during logout.

---

# 24. Logout All

Endpoint:

```http
POST /api/v1/auth/logout-all
```

Requires `get_current_user()`.

Short transaction:

```text
revoke all rows for current_user.id where revoked_at IS NULL
→ commit
```

Then clear both cookies and return 204.

Do not delete refresh-token history merely to implement logout-all.

---

# 25. Change Password

Endpoint:

```http
POST /api/v1/auth/change-password
```

Authenticated request:

```text
current_password
new_password
```

Rules:

- no client User ID;
- both passwords never logged;
- new password uses D-012 shared policy;
- verify current password against current DB hash;
- wrong current password → `400 INVALID_CURRENT_PASSWORD`;
- do not add a requirement that the new password differ from the old one because that is not frozen.

Preferred flow:

```text
read/snapshot current password hash
→ verify current password outside deliberate write transaction
→ validate/hash new password
→ short transaction
→ update User.password_hash
→ revoke all active Refresh Tokens for User
→ commit
→ clear both cookies
→ 204
```

Do not create a replacement session.

Copied Access Tokens remain valid only until their normal JWT expiration according to D-015.

---

# 26. Password Reset Request

Endpoint:

```http
POST /api/v1/auth/password-reset/request
```

Request:

```text
email
```

Always return public 202 for:

- nonexistent account;
- disabled account;
- existing active account;
- provider-neutral email adapter delivery failure.

For nonexistent/disabled User:

- create no usable Reset Token;
- invoke no delivery containing a credential.

For active User:

```text
normalize email
→ generate raw Reset Token + hash
→ short transaction
→ invalidate prior unused Reset Tokens using used_at=now
→ insert new hash, expiry now+configured minutes
→ commit
→ call EmailService outside DB transaction
```

Never hold DB transaction open around future email network I/O.

If EmailService raises after commit:

```text
short compensating transaction
→ mark newly-created Reset Token used/invalidated
→ commit
→ still return same public 202
```

Never log the raw token.

Tests needing the token inject `FakeEmailService`, which may capture it only in memory.

---

# 27. Password Reset Confirm

Endpoint:

```http
POST /api/v1/auth/password-reset/confirm
```

Request:

```text
token
new_password
```

Validate/hash new password before the DB state-change transaction.

Flow:

```text
SHA-256 submitted raw token
→ short transaction
→ SELECT Reset Token FOR UPDATE
→ invalid/missing/expired/used = INVALID_RESET_TOKEN
→ load User
→ if User missing/disabled = INVALID_RESET_TOKEN
→ update User.password_hash
→ mark submitted reset token used_at=now
→ mark any other unused reset tokens for User used_at=now
→ revoke all active Refresh Tokens for User
→ commit atomically
→ clear cookies
→ 204
```

Do not reveal which reset validation failed.

Do not automatically reactivate a disabled account.

---

# 28. EmailService

Define a small provider-neutral interface/Protocol equivalent to:

```text
send_password_reset(email, raw_token, ...)
```

Do not couple AuthService to a vendor SDK.

Development adapter:

- non-delivering is acceptable at this phase;
- may log only that a reset email/request was requested;
- must not log raw token or secrets.

Test fake:

- deterministic/in-memory;
- may capture the raw Reset Token for assertions;
- never writes it to persistent storage.

Production provider:

- not selected in Step 3.5;
- do not add SendGrid/SES/Mailgun/etc.;
- keep dependency injection point ready for Phase 8;
- document production delivery as deferred deployment wiring.

---

# 29. Auth HTTP Schemas / OpenAPI

Use explicit Pydantic request/response models so Phase 4 `openapi-typescript` receives stable contracts.

Minimum models:

```text
RegisterRequest
LoginRequest
UserProfileResponse
ChangePasswordRequest
PasswordResetRequest
PasswordResetConfirmRequest
```

Use `extra="forbid"` on credential/request models so callers cannot smuggle role/user/token-state fields.

Response contracts:

- register/login/me → typed `UserProfileResponse`;
- refresh/logout/logout-all/reset-confirm/change-password → 204, no JSON body;
- reset-request → 202, no account-specific JSON body.

Do not return tokens in JSON.

Ensure OpenAPI documents cookie-auth endpoints without manually exposing secret schema fields.

---

# 30. Auth Error Handling

Use `ApplicationError` and existing normalized error envelope.

Do not add another error envelope.

Exact auth codes:

```text
EMAIL_ALREADY_REGISTERED
INVALID_CREDENTIALS
ACCOUNT_DISABLED
AUTHENTICATION_REQUIRED
ADMIN_REQUIRED
INVALID_REFRESH_TOKEN
INVALID_CURRENT_PASSWORD
INVALID_PASSWORD
INVALID_RESET_TOKEN
```

Expected status:

```text
409 EMAIL_ALREADY_REGISTERED
401 INVALID_CREDENTIALS
403 ACCOUNT_DISABLED
401 AUTHENTICATION_REQUIRED
403 ADMIN_REQUIRED
401 INVALID_REFRESH_TOKEN
400 INVALID_CURRENT_PASSWORD
422 INVALID_PASSWORD
400 INVALID_RESET_TOKEN
```

Pydantic shape/type failures remain the existing normalized `422 INVALID_REQUEST`.

Password-policy failures intentionally use `INVALID_PASSWORD` rather than generic `INVALID_REQUEST`.

Never expose JWT/Argon2/SQL exception text.

---

# 31. Admin Bootstrap CLI

Create explicit module entry point equivalent to:

```bash
uv run python -m app.auth.bootstrap_admin
```

Read operator-provided:

```text
ADMIN_EMAIL
ADMIN_PASSWORD
ADMIN_FULL_NAME
```

Do not place default Admin credentials in source or required seed.

Flow:

```text
validate all required env inputs
→ normalize email
→ shared password policy
→ Argon2 hash
→ short DB transaction
→ if email already exists: fail explicitly / no mutation
→ create ADMIN
→ commit
```

Rules:

- do not promote LEARNER;
- do not overwrite ADMIN;
- do not run during normal FastAPI startup;
- do not print password/hash/SECRET_KEY/token;
- a safe success message may identify that bootstrap completed without echoing credentials.

Tests should invoke bootstrap logic through a testable function rather than shelling to production DB.

---

# 32. Transaction Ownership

Preserve Step 3.3 principle:

```text
AuthService / bootstrap application operation
→ owns commit / rollback

AuthRepository
→ never commits
```

Do not hold transactions across:

- email delivery;
- slow external work.

Argon2 hashing/verifying is CPU work, not DB work. Avoid intentionally wrapping it in a write transaction.

Refresh rotation and reset-token consumption require short row-lock transactions to preserve one-time/rotation semantics.

If commit fails:

- do not set success cookies;
- do not report success;
- rollback via service/application boundary;
- expose only normalized safe application/technical behavior, never raw DB exception.

---

# 33. Security-Sensitive Logging

Never log or include in exception details:

- plaintext password;
- password hash;
- Access Token;
- raw Refresh Token;
- Refresh token hash where unnecessary;
- raw Reset Token;
- Reset token hash where unnecessary;
- JWT `SECRET_KEY`;
- cookie header contents;
- DSNs/credentials.

Development EmailService may log only non-secret event metadata.

Tests should include a targeted log-capture assertion for password-reset and login failures to make sure raw credentials are absent.

---

# 34. Integration with Existing Step 3.4 Ownership

Authentication answers:

```text
Who is the User?
What role does the User currently have?
```

Business services continue answering:

```text
Can this User access this Lesson?
Does this Attempt belong to this User?
Is this curriculum unit unlocked?
Can this content transition?
```

Do not remove or weaken Step-3.4 resource ownership/business-access checks merely because authentication now exists.

At least one integration test must show:

```text
User A authenticated
→ cannot read User B attempt
```

with real auth cookies rather than only dependency override.

---

# 35. Test Database / Migration Safety

Continue using Step-3.3 dedicated PostgreSQL test configuration.

Never destructive-test production/runtime DB.

Tests must not use SQLite fallback.

Update migration/schema tests from the old Step-3.4 assumption so they verify:

- every accepted Phase-2 table remains;
- `refresh_tokens` exists after 0002;
- `password_reset_tokens` exists after 0002;
- exact FK delete actions / uniqueness / indexes;
- Alembic head is 0002;
- `alembic check` has no pending operations.

Test forward migration against an existing `0001` database containing at least representative User / Step-3.4 application data, and verify that data survives the `0001 → 0002` upgrade.

Do not edit 0001 to make tests pass.

---

# 36. Required Tests

Add/extend tests covering at least all items below.

## Settings / configuration

- `SECRET_KEY` required;
- production secret <32 rejected;
- production `COOKIE_SECURE=false` rejected;
- SameSite accepts lax/strict only;
- auth lifetimes positive;
- wildcard CORS rejected for credentialed Step 3.5;
- CORS response supports credentials for explicit allowed origin.

## Password security

- Argon2id stored hash;
- no plaintext persistence;
- correct/incorrect verify;
- 8 and 128 accepted;
- 7 and 129 rejected with `INVALID_PASSWORD`;
- no credential in logs.

## Registration

- successful 201;
- role forced LEARNER;
- request cannot set role;
- email trim/lower persistence;
- safe profile only;
- cookies exact D-014;
- duplicate email exact 409;
- duplicate race/unique failure normalized safely.

## Login

- valid login 200 + cookies/profile;
- unknown email and wrong password both exact `INVALID_CREDENTIALS`;
- disabled User exact `ACCOUNT_DISABLED`;
- dummy verification path does not change public error;
- Refresh hash persisted, raw refresh absent from DB.

## Access JWT / current User

- valid JWT;
- tampered signature;
- expired JWT;
- missing claims;
- malformed UUID sub;
- missing cookie;
- DB User deleted/missing after token issue;
- User disabled after token issue;
- DB role is authoritative over role claim;
- `/auth/me` safe fields only.

## Admin authorization

- anonymous Admin request 401;
- LEARNER Admin request 403 ADMIN_REQUIRED;
- ADMIN can access Admin route;
- role change in DB is effective without reissuing Access Token;
- every Admin router is protected through reusable guard integration.

## Step-3.4 integration

- existing learner `/me`, curriculum, lesson, assessment/attempt flows work with real auth cookie;
- no client-controlled learner ID appears;
- User A cannot access User B attempt/progress owned resource;
- full Step-3.4 regression suite continues to pass.

## Refresh

- successful 204 rotation;
- old row revoked;
- new row inserted;
- old raw token reuse → 401 INVALID_REFRESH_TOKEN;
- reuse clears caller cookies;
- unrelated sessions survive reused old token;
- missing token → same invalid-refresh contract;
- expired token → same contract;
- unknown token → same contract;
- disabled User blocked;
- row-lock/concurrent reuse test proves at most one successful rotation;
- raw replacement token absent from DB.

## Logout

- active Refresh revoked;
- both cookies cleared with exact paths;
- missing/invalid/revoked Refresh still returns 204 and clears cookies;
- Access Token is not added to a blacklist.

## Logout all

- auth required;
- every active Refresh Token for User revoked;
- other Users' sessions untouched;
- local cookies cleared.

## Change password

- current password verified;
- wrong current password → exact error;
- shared password policy enforced;
- new Argon2 hash persisted;
- all User Refresh Tokens revoked;
- cookies cleared;
- must log in again for new browser session;
- no user_id accepted;
- copied old Access JWT behavior remains stateless/unblacklisted until expiry.

## Password reset request

- account enumeration protection: same 202 for existing/nonexistent/disabled;
- nonexistent/disabled create no usable Reset Token;
- active User receives one new Reset Token hash;
- previous unused token invalidated;
- FakeEmailService receives raw token in memory;
- raw reset token absent from DB/logs;
- email adapter failure invalidates newly-created token and still returns generic 202.

## Password reset confirm

- valid token success 204;
- expired token → `INVALID_RESET_TOKEN`;
- used token → same error;
- unknown token → same error;
- concurrent/double consumption yields one success at most;
- password updated;
- submitted + other outstanding reset tokens invalidated;
- every Refresh Token for User revoked;
- cookies cleared;
- disabled User credential cannot be used to reactivate/reset access;
- login with new password succeeds afterwards for active User.

## Migration 0002

- clean upgrade to head;
- `0001 → 0002` with existing User/business data;
- exact tables/columns/FKs/uniques/indexes;
- no raw-token columns;
- `alembic check` clean.

## Admin bootstrap

- requires explicit inputs;
- creates ADMIN with normalized email + Argon2id hash;
- no default credentials;
- existing LEARNER not promoted;
- existing ADMIN not overwritten;
- public registration still LEARNER;
- bootstrap not called during FastAPI startup;
- credentials absent from logs/output.

## Regression

Run all accepted Steps 3.1–3.4 tests after adapting test auth fixtures to the real current-user boundary.

---

# 37. OpenAPI / Public Contract Verification

Generate app OpenAPI and verify:

- all 9 auth routes exist;
- register/login return typed safe profile;
- `/auth/me` typed profile;
- change/reset credential request schemas exclude `user_id`, `role`, token hashes;
- Refresh/Logout use cookies and no token request body;
- 204 endpoints do not advertise a JSON credential body;
- Admin/learner business route shapes from Step 3.4 remain unchanged except authentication dependencies.

Do not return JWT/Refresh tokens in OpenAPI response schemas.

---

# 38. Verification Commands

At minimum:

```bash
cd backend
uv sync
uv run python -c "from app.main import app; assert app is not None"
uv run python -c "from app.main import app; schema=app.openapi(); assert '/api/v1/auth/login' in schema['paths']"
uv run alembic upgrade head
uv run alembic check
uv run pytest -q
```

Use the configured isolated PostgreSQL test database.

Also execute the Admin bootstrap tests without pointing the CLI at production/runtime DB.

If real PostgreSQL migration/auth integration verification cannot run, report `PARTIAL`/`BLOCKED`; do not substitute SQLite and claim DONE.

---

# 39. Acceptance Criteria

## Security architecture

- [ ] PyJWT HS256 only.
- [ ] Argon2id via argon2-cffi defaults.
- [ ] Password policy 8..128 shared across all password flows.
- [ ] Raw Refresh/Reset tokens never persisted/logged.
- [ ] Access Tokens never persisted.
- [ ] No access blacklist/auth_version/family subsystem.
- [ ] Cookie settings exactly D-014.

## Auth flow

- [ ] Public registration creates LEARNER only and authenticates browser session.
- [ ] Login does not reveal email existence.
- [ ] Access JWT + authoritative DB User resolution implemented.
- [ ] Disabled User enforcement implemented.
- [ ] Refresh rotation + revocation implemented.
- [ ] Revoked reuse follows D-013 exactly.
- [ ] Logout idempotent.
- [ ] Logout-all revokes all User Refresh Tokens.
- [ ] Reset enumeration protection preserved.
- [ ] Reset tokens expire and are single-use.
- [ ] Change/reset revoke Refresh sessions and force browser re-login.

## Authorization

- [ ] real `get_current_user()` replaces temporary seam.
- [ ] `require_admin()` reusable and applied to all Admin endpoints.
- [ ] DB role is authoritative.
- [ ] Step-3.4 resource ownership/business checks remain intact.

## Persistence / migration

- [ ] `0001` unchanged.
- [ ] `0002_auth_token_tables` is the new migration.
- [ ] exact D-013 tables/indexes/FKs/uniques present.
- [ ] ORM metadata matches migration.
- [ ] clean and existing-data migration tests pass.

## Configuration / boundaries

- [ ] SECRET_KEY required and production length validated.
- [ ] Production secure-cookie rule validated.
- [ ] SameSite restricted to lax/strict.
- [ ] credentialed CORS remains explicit-origin.
- [ ] EmailService provider-neutral and raw-token safe.
- [ ] explicit Admin bootstrap exists and never runs automatically.

## Scope

- [ ] No Conversation API.
- [ ] No social/OAuth login.
- [ ] No MFA.
- [ ] No production email-provider SDK.
- [ ] No distributed rate-limit infrastructure.
- [ ] No new auth framework beyond PyJWT + argon2-cffi.
- [ ] Full Steps 3.1–3.4 regression suite passes.
- [ ] Step Note completed.

---

# 40. Step Note

Create:

```text
docs/backend/step-3.5-authentication-user-context.md
```

Include:

- Objective
- Why
- Mental Model
- Core Knowledge
- Data Flow
- Key Design Decisions
- Reusable approach for other projects
- Common Mistakes
- Definition of Done
- Concepts Actually Used
- Tools Actually Used

The note should explain the mental distinction:

```text
Password
→ slow one-way password hash

Opaque high-entropy bearer token
→ deterministic SHA-256 lookup hash

Access JWT
→ signed, short-lived, stateless credential

Refresh Token
→ opaque, stateful, server-revocable credential
```

Also explain:

```text
Authentication
!=
Business ownership authorization
```

Keep it reusable, not route-by-route narration.

---

# 41. Concepts Expected

Record only concepts actually used.

| Concept | Category | Role |
|---|---|---|
| Authentication vs authorization | SYSTEM | Separates identity resolution from role/resource decisions. |
| Password hashing / Argon2id | SYSTEM | Stores verifiers rather than passwords. |
| JWT Access Token | SYSTEM | Short-lived signed browser credential. |
| Opaque bearer token | SYSTEM | Random Refresh/Reset credential. |
| Credential hashing at rest | SYSTEM | Stores SHA-256 lookup representation instead of raw high-entropy token. |
| Refresh-token rotation | SYSTEM | Replaces each used Refresh Token and revokes the old credential. |
| Session revocation | SYSTEM | Server-side Refresh Token state enables logout-all/password-reset invalidation. |
| Cookie security | SYSTEM | HttpOnly/Secure/SameSite/path controls browser credential transport. |
| Dependency injection / current User | SYSTEM | Reusable authenticated DB User boundary. |
| Role authorization | SYSTEM | Reusable authoritative Admin guard. |
| Resource ownership authorization | SYSTEM | Existing business services continue protecting owned resources. |
| Password-reset lifecycle | SYSTEM | Single-use recovery credentials with enumeration protection. |
| Row locking / one-time credential consumption | SYSTEM | Prevents concurrent Refresh/Reset reuse. |
| Database migration | DE | Evolves persistence from 0001 to 0002 safely. |

---

# 42. Tools Expected

| Tool | Category | Role |
|---|---|---|
| Python | SYSTEM | Backend/auth implementation. |
| uv | SYSTEM | Dependency + command workflow. |
| FastAPI | SYSTEM | HTTP/dependency/cookie boundary. |
| Pydantic | SYSTEM | Stable auth request/response contracts. |
| pydantic-settings | SYSTEM | Auth/security configuration. |
| PyJWT | SYSTEM | HS256 Access JWT implementation. |
| argon2-cffi | SYSTEM | Argon2id password hashing. |
| SQLAlchemy | SYSTEM | Async auth persistence. |
| psycopg 3 | SYSTEM | PostgreSQL driver. |
| PostgreSQL | DE | User/token persistence and locking. |
| Alembic | DE | Forward migration 0002. |
| pytest | SYSTEM | Security/business regression tests. |

Do not record standard-library `hashlib`/`secrets` as project tools unless the project convention explicitly records standard-library modules.

---

# 43. Out of Scope

Do **not** implement:

- Conversation API / Step 3.6;
- Google/social login;
- OAuth/OIDC provider integration;
- MFA;
- mandatory email verification;
- complex RBAC/permission tables;
- Access Token blacklist;
- `auth_version`;
- refresh families/session family table;
- CSRF redesign for cross-site cookies;
- production email vendor;
- distributed rate-limiter/Redis;
- frontend changes;
- RAG/AI work;
- deployment infrastructure.

Do not opportunistically refactor Step-3.4 business APIs except the minimal authentication dependency integration required here.

---

# 44. Required Completion Report

Return enough evidence for independent specialist review:

```text
Step: 3.5 — Authentication & User Context
Status: DONE | PARTIAL | BLOCKED

Implementation plan executed:
- ...

Files created:
- ...

Files modified:
- ...

Dependencies added/removed:
- ...

Migration 0002:
- ...

D-012 JWT/password implementation:
- ...

D-013 opaque-token persistence/rotation:
- ...

D-014 cookie/CORS behavior:
- ...

D-015 HTTP/session behavior:
- ...

D-016 normalized errors:
- ...

D-017 reset/email behavior:
- ...

D-018 Admin bootstrap:
- ...

get_current_user / require_admin integration:
- ...

Step-3.4 ownership/business checks preserved:
- ...

Transaction design:
- ...

Security-sensitive logging review:
- ...

Tests / verification:
- command:
  result:

Acceptance criteria:
- [PASS/FAIL] ...

Step Note:
- path:

Concepts actually used:
- ...

Tools actually used:
- ...

Deviations from specification:
- none | ...

Problems / risks:
- ...

Decisions needed:
- none | ...

Recommended next action:
Return to App Engineering Specialist for independent review.
Do not begin Step 3.6.
```

Do not claim `DONE` if:

- PostgreSQL migration/integration tests did not run;
- 0001 was modified;
- D-012 through D-018 are not implemented exactly;
- any Admin API remains unprotected;
- raw Refresh/Reset token storage/logging exists;
- Step-3.4 ownership checks were removed;
- Step 3.6 or later scope was started.
