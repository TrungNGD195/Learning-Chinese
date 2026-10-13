# Step 3.5 — Authentication & User Context

## Objective

Add a minimal, server-authoritative authentication boundary to the FastAPI modular monolith. Auth owns identity and browser sessions; existing business services continue to enforce lesson access, attempt ownership, and progression rules.

## Why

The application needs browser login, recoverable sessions, account recovery, and protected Admin operations without putting long-lived credentials in browser JavaScript or changing Step 3.4 business ownership.

## Mental Model

Treat credentials according to their purpose:

```text
Password
→ slow one-way Argon2id password hash

Opaque high-entropy bearer token
→ deterministic SHA-256 lookup hash

Access JWT
→ signed, short-lived, stateless credential

Refresh Token
→ opaque, stateful, server-revocable credential
```

Authentication answers who the User is. Business ownership authorization answers whether that User may access a particular resource. A JWT role claim is not authoritative: current role and active state come from PostgreSQL.

## Core Knowledge

- Normalize email once at every account lookup/write boundary.
- Give registration one role only: `LEARNER`.
- Use Argon2id defaults for passwords and keep the same 8–128 character policy across register, reset, and password change.
- Use HS256 through PyJWT for short-lived Access Tokens with only `sub`, `role`, `iat`, and `exp` claims.
- Generate Refresh and Reset credentials from 32 random bytes and persist only SHA-256 hex hashes.
- Rotate Refresh Tokens under a row lock; consume Reset Tokens under a row lock.
- Store browser credentials in host-only HttpOnly cookies with fixed paths and configured Secure/SameSite flags.
- Put database commits in AuthService/application operations. AuthRepository only queries and mutates ORM state.
- Use a reusable DB-backed `get_current_user()` and `require_admin()` boundary.
- Keep password-reset delivery behind an injectable EmailService. Production provider wiring remains a deployment dependency.
- Apply schema changes forward with Alembic and preserve existing application data.

## Data Flow

```text
Auth Router
→ AuthService
→ AuthRepository
→ AsyncSession / PostgreSQL
```

Registration/login hash or verify passwords outside the token-write transaction, persist a Refresh Token hash, then set cookies after commit. Refresh locks and revokes the old row before persisting a replacement. Reset request commits a one-time token hash before calling EmailService; provider failure invalidates that token in a compensating transaction. Reset confirmation updates the password, consumes reset credentials, and revokes refresh sessions atomically.

## Transaction and Lock Order

AuthService owns each use case and its commit/rollback boundary. AuthRepository owns ORM queries and mutations but never commits. Security-sensitive session operations use one lock order:

```text
identify User/token without a lock
-> lock authoritative User row FOR UPDATE
-> lock and revalidate the relevant token row FOR UPDATE
-> mutate credentials/sessions
-> commit
```

Reset issuance locks the User before invalidating earlier unused Reset Tokens and inserting one replacement. It commits before EmailService delivery; delivery failure invalidates only the just-issued credential in a compensating transaction. Refresh rotation uses the same User-before-Refresh-Token order, so logout-all, password change, or reset confirmation cannot leave its replacement session active. Password verification stays outside the write transaction; login and password change then lock and revalidate the current active User and password hash before persisting.

## Key Design Decisions

- Access Tokens are stateless and are not blacklisted. Browser logout and password changes clear cookies and revoke server-side Refresh Tokens.
- Refresh and Reset tokens are opaque, never JWTs, and raw values never reach persistent storage or logs.
- Disabled users cannot log in, refresh, or continue authenticated requests.
- Admin access is checked against the current database role on every request.
- Admin bootstrap is an explicit one-time CLI operation; application startup never creates privileged users.
- Migration `0002_auth_token_tables` adds only Refresh and Password Reset token persistence. Migration `0001` remains unchanged.
- Email delivery is intentionally non-delivering in this Step; production adapter selection is deferred to Phase 8.

## Reusable Approach for Other Projects

Keep HTTP concerns in routers, account/session workflows in an application service, and persistence operations in a repository. Store slow-to-crack password verifiers for human passwords, but use fast deterministic hashes for random high-entropy lookup tokens. Make one-time credentials single-use with database locks and transactions. Resolve mutable identity and role state from the database, then let each domain service retain ownership of resource authorization.

## Common Mistakes

- Returning tokens in JSON or storing them in localStorage.
- Persisting raw Refresh or Reset credentials.
- Using a JWT as a refresh credential.
- Trusting a role claim after the database role changes.
- Performing email I/O while a database transaction is open.
- Committing inside repository helpers.
- Clearing cookies with a path different from the original path.
- Revealing whether an email account or reset credential exists.
- Removing domain ownership checks after adding authentication.

## Definition of Done

- Registration, login, refresh rotation, logout, logout-all, change-password, reset request/confirm, and `/auth/me` follow D-012 through D-018.
- Every Admin endpoint uses reusable database-backed `require_admin()`.
- Existing learner resource ownership remains enforced by Step 3.4 services.
- Migration 0002 is synchronized with ORM metadata and preserves 0001 data.
- PostgreSQL integration tests and the Step 3.1–3.4 regression suite pass.
- No raw credentials are persisted or logged.

## Concepts Actually Used

| Concept | Category | Role |
|---|---|---|
| Authentication vs authorization | SYSTEM | Separates identity resolution from role/resource decisions. |
| Password hashing / Argon2id | SYSTEM | Persists password verifiers rather than passwords. |
| JWT Access Token | SYSTEM | Short-lived signed browser credential. |
| Opaque bearer token | SYSTEM | Random Refresh and Reset credential. |
| Credential hashing at rest | SYSTEM | Stores SHA-256 token lookup hashes. |
| Refresh-token rotation | SYSTEM | Replaces and revokes each used Refresh Token. |
| Session revocation | SYSTEM | Server-side Refresh Token state supports logout and password recovery. |
| Cookie security | SYSTEM | Controls browser transport with HttpOnly, Secure, SameSite, and path flags. |
| Dependency injection / current User | SYSTEM | Resolves an authoritative database User for routes. |
| Role authorization | SYSTEM | Protects Admin routes through a reusable guard. |
| Resource ownership authorization | SYSTEM | Leaves User-resource checks in domain services. |
| Password-reset lifecycle | SYSTEM | Uses expiring single-use recovery credentials without enumeration. |
| Row locking / one-time credential consumption | SYSTEM | Prevents concurrent refresh/reset reuse. |
| Database migration | DE | Adds token tables through a forward migration. |

## Tools Actually Used

| Tool | Category | Role |
|---|---|---|
| Python | SYSTEM | Backend authentication implementation. |
| uv | SYSTEM | Dependency and environment workflow. |
| FastAPI | SYSTEM | HTTP, cookie, and dependency boundary. |
| Pydantic | SYSTEM | Request and response contracts. |
| pydantic-settings | SYSTEM | Security and lifetime configuration. |
| PyJWT | SYSTEM | HS256 Access Token encoding/validation. |
| argon2-cffi | SYSTEM | Argon2id password hashing. |
| SQLAlchemy | SYSTEM | Async auth persistence and row locking. |
| psycopg 3 | SYSTEM | PostgreSQL driver. |
| PostgreSQL | DE | User/token persistence and transactional locking. |
| Alembic | DE | Forward migration 0002. |
| pytest | SYSTEM | Auth and regression tests. |
