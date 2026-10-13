# Step 3.5 — Authentication & User Context

## Goal

Implement secure MVP authentication and authorization for the FastAPI backend.

Required capabilities:

- learner registration;
- login;
- JWT access token;
- refresh-token rotation;
- logout;
- logout all devices;
- authenticated user resolution;
- Admin role protection;
- resource ownership checks;
- password reset.

Do not implement social login or mandatory email verification.

---

# Authentication Model

Use:

```text
short-lived JWT Access Token
+
server-revocable Refresh Token
```

Default lifetimes:

```text
Access Token  = 30 minutes
Refresh Token = 7 days
```

Store both credentials in HttpOnly cookies for browser usage.

Production cookie requirements:

```text
HttpOnly = true
Secure = true
SameSite = Lax
```

Do not use browser localStorage as the approved access-token storage mechanism.

---

# Access Token

JWT payload should contain only minimal identity claims:

```text
sub
role
iat
exp
```

`sub` represents User ID.

Do not embed mutable application state such as:

- HSK progress;
- lesson state;
- full user profile;
- assessment permissions.

Do not persist Access Tokens in the database.

---

# Refresh Tokens

Persist server-side Refresh Token state using a new table equivalent to:

```text
refresh_tokens

id UUID PK
user_id UUID NOT NULL FK → users.id
token_hash TEXT NOT NULL
expires_at TIMESTAMPTZ NOT NULL
revoked_at TIMESTAMPTZ NULL
created_at TIMESTAMPTZ NOT NULL
```

Never store raw Refresh Tokens in the database.

Refresh token validation must consider:

- token integrity;
- matching stored hash;
- expiry;
- revocation;
- associated active User.

---

# Refresh Rotation

Implement:

```text
Refresh Token A
→ validate
→ revoke A
→ generate Access Token B
→ generate Refresh Token B
→ persist hash of B
```

A revoked/rotated Refresh Token must not be usable again.

---

# Registration

Implement:

```http
POST /api/v1/auth/register
```

Input:

```text
email
password
full_name
```

Normalize email before persistence/lookup:

```text
trim
lowercase
```

Public registration must always create:

```text
role = LEARNER
```

Do not accept Admin role selection from the request.

Duplicate email:

```text
HTTP 409
EMAIL_ALREADY_REGISTERED
```

Email verification is not required for MVP.

---

# Password Storage

Never persist plaintext passwords.

Use Argon2id password hashing.

Persist only:

```text
password_hash
```

Minimum MVP password length:

```text
8 characters
```

Avoid unnecessarily complex mandatory composition rules.

---

# Login

Implement:

```http
POST /api/v1/auth/login
```

Input:

```text
email
password
```

Flow:

```text
normalize email
→ lookup User
→ verify password hash
→ verify is_active
→ issue Access Token
→ issue Refresh Token
→ persist Refresh Token hash
→ set cookies
```

Invalid email/password:

```text
HTTP 401
INVALID_CREDENTIALS
```

Do not reveal whether the email exists.

Disabled account:

```text
HTTP 403
ACCOUNT_DISABLED
```

---

# Current User

Implement a reusable FastAPI dependency equivalent to:

```text
get_current_user()
```

Flow:

```text
read Access Token
→ verify JWT signature/expiry
→ extract sub
→ load User from database
→ verify User exists
→ verify is_active
→ return User
```

JWT role may be used as a claim, but database User state remains authoritative.

---

# Current User Endpoint

Implement:

```http
GET /api/v1/auth/me
```

Return learner/admin-safe profile fields such as:

```text
id
email
full_name
role
```

Never expose:

```text
password_hash
refresh token hash
authentication secrets
```

---

# Change Password

Implement:

```http
POST /api/v1/auth/change-password
```

Authenticated request input:

```text
current_password
new_password
```

Required behavior:

```text
verify current password
→ validate new password policy
→ hash new password with Argon2id
→ update password hash
→ revoke all existing refresh-token families/sessions
→ require login again (or return a clearly documented equivalent secure session policy)
```

Do not accept a user ID from the client. Do not log either password. Reuse password-strength/validation rules from registration/reset.

Return stable errors for invalid current password and invalid new-password policy without leaking hashes or auth internals.

---

# Admin Authorization

Provide a reusable dependency equivalent to:

```text
require_admin()
```

It must depend on authenticated current-user resolution and verify the current role from authoritative User state.

Apply it to Admin router operations under:

```text
/api/v1/admin/...
```

Do not duplicate role-check code manually across every Admin endpoint.

---

# Resource Authorization

Role checks alone are insufficient.

Services must validate resource ownership where required.

Example:

```text
current_user requests AssessmentAttempt X

→ verify AssessmentAttempt.user_id
   == current_user.id
```

A learner must never gain access to another learner's:

- assessment attempts;
- progress;
- conversations;
- profile data.

---

# Logout

Implement:

```http
POST /api/v1/auth/logout
```

Behavior:

```text
identify current Refresh Token
→ revoke stored record
→ clear authentication cookies
```

Short-lived Access Token may remain cryptographically valid until expiration.

---

# Logout All

Implement:

```http
POST /api/v1/auth/logout-all
```

Require authentication.

Revoke all active Refresh Tokens associated with current User.

---

# Refresh Endpoint

Implement:

```http
POST /api/v1/auth/refresh
```

Required flow:

```text
read Refresh Token cookie
→ validate token
→ verify matching DB record
→ verify not expired/revoked
→ verify User active
→ rotate Refresh Token
→ issue new Access Token
→ update cookies
```

Do not reuse the same Refresh Token throughout its entire lifetime.

---

# Password Reset Request

Implement:

```http
POST /api/v1/auth/password-reset/request
```

Input:

```text
email
```

Normalize email.

Regardless of whether the account exists, return the same generic response.

Do not reveal registered-email existence.

---

# Password Reset Tokens

Add a persistent table equivalent to:

```text
password_reset_tokens

id UUID PK
user_id UUID NOT NULL FK → users.id
token_hash TEXT NOT NULL
expires_at TIMESTAMPTZ NOT NULL
used_at TIMESTAMPTZ NULL
created_at TIMESTAMPTZ NOT NULL
```

Reset tokens must be:

- cryptographically random;
- high entropy;
- stored only as hashes;
- single-use;
- expired after 30 minutes.

---

# Password Reset Confirm

Implement:

```http
POST /api/v1/auth/password-reset/confirm
POST /api/v1/auth/change-password
```

Input:

```text
token
new_password
```

Required flow:

```text
hash submitted token
→ locate valid token record
→ verify not expired
→ verify not already used
→ validate new password
→ generate new Argon2id password hash
→ update User
→ mark reset token used
→ revoke all active Refresh Tokens
```

Perform the database state changes atomically where practical.

---

# Email Boundary

Define an EmailService abstraction with capability equivalent to:

```text
send_password_reset(...)
```

Do not couple Auth business logic directly to one email provider.

For Development/Test, use an appropriate fake/stub/logging implementation.

A production email provider does not need to be selected in this step.

---

# Auth Configuration

Extend Step 3.2 Settings with configuration equivalent to:

```text
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
PASSWORD_RESET_EXPIRE_MINUTES=30

COOKIE_SECURE
COOKIE_SAMESITE
```

Use the existing protected SECRET_KEY as the initial JWT signing secret.

Do not commit signing secrets.

Do not introduce a complex key-rotation architecture in this MVP step.

---

# Cookie Security

Browser authentication cookies must be HttpOnly.

Production must use Secure cookies.

Default:

```text
SameSite=Lax
```

Keep frontend/backend deployment compatible with this strategy.

If later deployment requires cross-site authentication cookies, explicitly redesign CSRF protection rather than silently changing SameSite behavior.

---

# Migration

Do not rewrite the already-approved initial migration if it has been applied.

Create a new migration such as:

```text
0002_auth_token_tables
```

to add:

```text
refresh_tokens
password_reset_tokens
```

Include appropriate:

- foreign keys;
- timestamps;
- indexes for token/user lookup;
- uniqueness as required by the concrete token representation.

Use Alembic.

Review the migration manually.

---

# Public Admin Creation

Public registration must never create an Admin.

Production Admin creation must use the explicit bootstrap/setup mechanism defined in the database/bootstrap strategy.

Do not hard-code Admin credentials in source control.

---

# Auth API Surface

Implement:

```text
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
POST /api/v1/auth/logout-all

GET  /api/v1/auth/me

POST /api/v1/auth/password-reset/request
POST /api/v1/auth/password-reset/confirm
POST /api/v1/auth/change-password
```

Reusable dependencies:

```text
get_current_user()
require_admin()
```

---

# Integration with Step 3.4

Replace temporary unauthenticated/current-user assumptions in Business APIs.

Examples:

```text
/me/dashboard
/me/progress
/me/assessment-attempts
```

must use `get_current_user()`.

Admin APIs must use `require_admin()`.

Lesson/Assessment services must continue performing their own business-access checks after authentication.

---

# Rate Limiting

Login and password-reset request endpoints are expected to receive rate limiting before production launch.

Do not introduce unrelated distributed rate-limit infrastructure solely for this step if none exists yet.

Keep the API/service structure compatible with adding it later.

---

# Tests

Add tests covering at least:

- successful registration;
- forced LEARNER role;
- duplicate email;
- email normalization;
- password hashing;
- valid login;
- invalid credentials generic failure;
- disabled User login;
- Access Token validation;
- expired/invalid Access Token;
- `get_current_user`;
- Admin guard;
- learner blocked from Admin API;
- resource ownership enforcement;
- refresh success;
- refresh-token rotation;
- reuse of revoked Refresh Token rejected;
- logout;
- logout all;
- password-reset account enumeration protection;
- expired reset token;
- used reset token;
- successful password reset;
- refresh tokens revoked after password reset.

Tests must not depend on a real email provider.

---

# Out of Scope

Do not implement:

- Google/social login;
- mandatory email verification;
- OAuth provider integration;
- complex permission/RBAC system;
- MFA;
- production email-provider selection;
- distributed rate-limit infrastructure;
- LLM/API credentials;
- Conversation API.

---

# Acceptance Criteria

- [ ] Public registration can only create LEARNER.
- [ ] Passwords are never stored in plaintext.
- [ ] Argon2id is used for password hashing.
- [ ] Login does not expose user-enumeration information.
- [ ] Access Tokens are short-lived JWTs.
- [ ] Refresh Tokens are server-revocable.
- [ ] Raw Refresh Tokens are not persisted.
- [ ] Refresh rotation is implemented.
- [ ] Authentication cookies are HttpOnly.
- [ ] Production supports Secure cookies.
- [ ] `get_current_user()` resolves authoritative DB User state.
- [ ] Disabled users cannot continue normal authenticated access.
- [ ] Admin authorization is reusable.
- [ ] Resource ownership is enforced by service logic.
- [ ] Logout revokes the relevant Refresh Token.
- [ ] Logout-all revokes all User sessions.
- [ ] Password reset does not reveal whether email exists.
- [ ] Reset tokens are hashed, expiring and single-use.
- [ ] Password reset revokes existing sessions.
- [ ] Public API cannot create Admin accounts.
- [ ] Auth persistence changes are migration-driven.

- [ ] Authenticated learner/admin can change password using current password verification.
- [ ] Successful password change revokes existing refresh sessions according to the documented policy.

# Expected Deliverable

Authentication foundation plus:

```text
docs/backend/
└── step-3.5-authentication-user-context.md
```

Next Step:

**Step 3.6 — Conversation API**