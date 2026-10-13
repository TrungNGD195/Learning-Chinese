# Codex Execution Task — Step 4.6: Auth & Profile UI

## Execution Gate

This is the **single current Codex execution task** for:

**Step 4.6 — Auth & Profile UI**

Owner: **App Engineering Specialist**

Implement Step 4.6 only.

Do **not** begin Step 4.7 Admin CRUD, Phase 5 ingestion, or Phase 6 AI/RAG.

Before editing, inspect the actual checkout and the latest canonical PM Decision Log. Expected accepted state:

- backend complete through Step 3.6;
- Step-3.5 Auth backend/contracts accepted;
- frontend PM-accepted through Step 4.5;
- `@tanstack/react-query` server-state/session infrastructure is accepted;
- `/auth/me` Query is canonical current-User/session state;
- D-039 bounded read retry is accepted;
- D-040 central 401 Refresh/replay + single-flight behavior is accepted;
- D-041 Admin Forbidden behavior is accepted;
- D-042 Chat uncertain-send behavior is accepted;
- D-043 through D-045 are DECIDED and authoritative;
- current `/login`, `/register`, `/forgot-password`, `/reset-password`, and `/profile` screens are structural placeholders;
- Step 4.7 Admin CRUD has not started.

If the checkout materially differs, or correct implementation requires a backend/API/OpenAPI change, another runtime dependency, token/JWT storage or decoding, a new session store, or another material Auth/security/UX convention not frozen here, stop and report `BLOCKED` with evidence instead of inventing behavior.

---

# 1. Objective

Implement usable learner Auth/Profile UI for:

```text
/login
/register
/forgot-password
/reset-password?token=<opaque-token>
logout
/profile
change password
```

Required architecture:

```text
Auth/Profile UI
→ existing feature API wrapper
→ central apiClient
→ FastAPI
→ HttpOnly cookie authentication
→ authoritative /auth/me Query
→ session-derived frontend UX
```

Frontend must **not** become authentication authority.

Do not:

```text
decode JWT
read cookie contents
store Access Token
store Refresh Token
construct Authorization: Bearer
create a second current-User store
```

---

# 2. Source of Truth and Precedence

Read the latest canonical PM Decision Log before editing.

Required decisions/contracts include at least:

```text
D-012 — password policy / Argon2id contract
D-014 — HttpOnly browser cookie contract
D-015 — Auth HTTP/session lifecycle
D-016 — normalized Auth errors
D-017 — password-reset lifecycle
D-027→D-031 — frontend/apiClient boundaries
D-039 — Query read retry / mutation retry policy
D-040 — central 401 recovery + single-flight + session invalidation
D-041 — authenticated non-admin Admin-route Forbidden UX
D-043 — Login/Register post-auth destination
D-044 — authenticated User behavior on public Auth routes
D-045 — reset-token URL + post-reset UX
```

Precedence:

1. latest canonical PM Decision Log;
2. authoritative Step 4.6 specification;
3. later accepted Step refinements;
4. actual accepted backend/OpenAPI/frontend implementation;
5. earlier notes/examples;
6. this execution packet.

Do not silently reinterpret an earlier example against a later frozen decision.

---

# 3. Actual Accepted Contracts

## 3.1 Login

Runtime endpoint:

```text
POST /auth/login
```

Generated request:

```json
{
  "email": "...",
  "password": "..."
}
```

Success:

```text
HTTP 200
→ UserProfileResponse
→ backend sets Access cookie
→ backend sets Refresh cookie
```

Stable relevant errors:

```text
INVALID_CREDENTIALS
ACCOUNT_DISABLED
```

Login response User is **not** the permanent frontend session authority.

Required success sequence is D-043:

```text
login mutation succeeds
→ cookies have been set by backend
→ clear stale previous-user authenticated server cache as needed
→ authoritative /auth/me fetch/refetch
→ /auth/me returns current User
→ session = AUTHENTICATED
→ navigate /dashboard
```

Do not implement role-sensitive post-login routing.

Do not implement return-to-origin.

## 3.2 Register

Runtime endpoint:

```text
POST /auth/register
```

Generated request:

```json
{
  "email": "...",
  "password": "...",
  "full_name": "..."
}
```

Do not send:

```text
role
confirm_password
```

Success:

```text
HTTP 201
→ LEARNER User
→ Access cookie
→ Refresh cookie
→ immediate authenticated browser session
```

Stable relevant errors:

```text
EMAIL_ALREADY_REGISTERED
INVALID_PASSWORD
```

Required D-043 sequence:

```text
register succeeds
→ authoritative /auth/me fetch/refetch
→ AUTHENTICATED
→ /dashboard
```

No second Login is required.

## 3.3 Current User

Canonical source:

```text
GET /auth/me
```

Public User fields currently supported:

```text
id
email
full_name
role
```

Current User remains TanStack Query data under the existing `auth.me` key/session infrastructure.

## 3.4 Forgot Password

Runtime endpoint:

```text
POST /auth/password-reset/request
```

Request:

```json
{
  "email": "..."
}
```

Success:

```text
HTTP 202
```

Public behavior is deliberately enumeration-safe for:

```text
existing account
missing account
disabled account
```

The UI must not claim whether an account exists.

## 3.5 Reset Password

Runtime endpoint:

```text
POST /auth/password-reset/confirm
```

Generated request:

```json
{
  "token": "<opaque reset token>",
  "new_password": "..."
}
```

Success:

```text
HTTP 204
→ password changed
→ reset credential consumed
→ all Refresh Tokens revoked
→ Access + Refresh cookies cleared
```

Stable error:

```text
INVALID_RESET_TOKEN
```

Do not distinguish:

```text
invalid
expired
already used
```

unless a future backend contract exposes that distinction.

## 3.6 Logout

Runtime endpoint:

```text
POST /auth/logout
```

Success:

```text
HTTP 204
→ current Refresh Token revoked when identifiable
→ auth cookies cleared
```

Logout is idempotent.

## 3.7 Change Password

Runtime endpoint:

```text
POST /auth/change-password
```

Request:

```json
{
  "current_password": "...",
  "new_password": "..."
}
```

Success:

```text
HTTP 204
→ password changed
→ all Refresh Tokens revoked
→ Access + Refresh cookies cleared
```

Therefore success **forces re-login**.

Relevant stable errors:

```text
INVALID_CURRENT_PASSWORD
INVALID_PASSWORD
```

---

# 4. Dependency Scope

Expected new runtime dependency:

```text
none
```

Continue using:

```text
React
TypeScript
React Router
@tanstack/react-query
existing apiClient / ApiError
existing generated OpenAPI types
Vitest
React Testing Library
```

Do **not** add:

```text
form library
validation library
auth library
state-management library
toast library
new HTTP client
Query persistence plugin
```

Do not modify `api.generated.ts`.

If generated contracts appear insufficient, stop instead of adding handwritten duplicate DTOs or changing backend contract silently.

---

# 5. Session Integration — Reuse Step 4.5

Do not create another bootstrap/session store.

Existing authority remains:

```text
/auth/me Query
→ UNKNOWN / AUTHENTICATED / UNAUTHENTICATED
```

Existing D-040 remains responsible for:

```text
eligible 401
→ one shared Refresh
→ one replay
```

Auth pages must not implement page-local Refresh orchestration.

## 5.1 Shared authenticated-session cleanup

Factor/reuse **one narrow cleanup operation** for these committed-success flows:

```text
Logout success
Reset Password success
Change Password success
```

Its effect must be equivalent to the accepted Step-4.5 definitive session cleanup:

```text
cancel authenticated/user-specific Queries
→ remove authenticated/user-specific Queries
→ auth.me = null / UNAUTHENTICATED
```

Do not duplicate slightly different cleanup logic across three pages.

Do not create another User store.

The existing definitive session-invalidation notification path may reuse this same underlying cache-cleanup helper.

Exact helper/file name is implementation detail.

## 5.2 Login/Register session restoration

After successful Login/Register:

```text
backend cookies are now current
→ ensure stale previous-user non-auth Query data cannot leak
→ fetch/refetch authoritative /auth/me
→ require successful User result
→ navigate /dashboard
```

Do not navigate first and hope a later bootstrap catches up.

Do not use Login/Register response as a second session store.

Prefer sharing the same auth.me query definition/query options between `useSession()` and imperative post-auth restoration so the repository does not duplicate the `/auth/me` Query contract.

---

# 6. D-043 — Post Login/Register Destination

Frozen behavior:

```text
Login success
→ auth.me authoritative success
→ /dashboard

Register success
→ auth.me authoritative success
→ /dashboard
```

Use `/dashboard` for both:

```text
LEARNER
ADMIN
```

Do not implement:

```text
ADMIN → /admin
return-to-origin
```

in Step 4.6.

---

# 7. D-044 — Public Auth Route Behavior

Create a small session-aware public-auth route boundary/wrapper consistent with the existing `ProtectedRoute` / `AdminRoute` architecture.

Do not build a new Auth router framework.

Required behavior:

## 7.1 `/login`, `/register`, `/forgot-password`

```text
session UNKNOWN + pending
→ session-checking UI
→ no redirect

session UNKNOWN + technical verification error
→ recoverable session-verification UI + Retry
→ no redirect

session UNAUTHENTICATED
→ render requested public Auth page

session AUTHENTICATED
→ redirect /dashboard
```

## 7.2 `/reset-password`

Frozen exception:

```text
session UNKNOWN
→ wait / verification UI as above

session UNAUTHENTICATED
→ render Reset Password

session AUTHENTICATED
→ ALSO render Reset Password
```

Reason: the Reset credential is an independent recovery credential and successful reset revokes the current browser session anyway.

Do not create account-switch behavior.

Do not weaken existing `ProtectedRoute` / `AdminRoute` behavior.

---

# 8. Login UI

Replace structural Login placeholder with a usable form.

Fields:

```text
Email
Password
```

Form state stays local React state.

Minimal client validation:

```text
email required
password required
```

Do not attempt to verify credential correctness locally.

Submit via existing `authApi.login` / generated contract.

Pending:

```text
mutation.isPending
→ disable duplicate submit
→ action label/state such as Signing in…
```

## 8.1 Error mapping

`INVALID_CREDENTIALS`:

```text
form-level credential error
```

Do not reveal whether the email or password specifically was wrong.

`ACCOUNT_DISABLED`:

```text
explicit disabled-account error
```

`NETWORK_ERROR` / 5xx:

```text
recoverable technical error
→ preserve safe email field
→ preserve password unless the component intentionally clears it for security UX; do not persist it anywhere
→ no automatic mutation retry
```

Normal unexpected errors:

```text
safe local form error
```

Behavior must use `ApiError.status/code`, not human-readable message parsing.

## 8.2 Navigation links

Provide lightweight links as appropriate:

```text
Create an account
Forgot password
```

Do not add social login.

---

# 9. Register UI

Fields:

```text
Full name
Email
Password
Confirm password
```

`Confirm password` is frontend-only.

Exact request body:

```json
{
  "full_name": "...",
  "email": "...",
  "password": "..."
}
```

Do not send `confirm_password` or `role`.

Client validation may include:

```text
trimmed Full name required
Email required
Password required
Confirm password required
Password == Confirm password
new password length 8..128 (mirrors frozen backend policy for UX only)
```

Backend remains authority and `INVALID_PASSWORD` must still be handled.

`EMAIL_ALREADY_REGISTERED`:

```text
email-specific registration feedback
```

Successful Register follows D-043 and does not require Login.

Provide link back to Login.

---

# 10. Forgot Password UI

Fields:

```text
Email
```

Submit exact request to existing `requestPasswordReset` wrapper.

On HTTP 202 show enumeration-safe acknowledgement equivalent to:

```text
If an eligible account exists for that email,
password-reset instructions will be sent.
```

Do not show different success states based on:

```text
account exists
account missing
account disabled
```

Frontend has no email-provider responsibility.

Technical/network failure:

```text
preserve email
→ recoverable local error
→ explicit learner Retry
```

Mutation retry remains false.

---

# 11. D-045 — Reset Password URL / Token Lifecycle

Canonical route remains:

```text
/reset-password?token=<opaque-token>
```

Use React Router URL/search-param facilities.

Read the `token` query parameter only inside the Reset flow.

Do not:

```text
render raw token
log token
put token in TanStack Query data
copy token to global application state
persist token in localStorage/sessionStorage
place password in URL
```

## 11.1 Missing token

For:

```text
/reset-password
```

without a non-empty token:

```text
show dedicated invalid/missing reset-link state
→ provide link/action to /forgot-password
→ do not call confirm endpoint
```

## 11.2 Reset form

Fields:

```text
New password
Confirm new password
```

Confirmation is local-only.

Client validation may include:

```text
required
matching confirmation
8..128 new password length
```

Backend remains authoritative.

Exact request:

```json
{
  "token": "<token from ?token=>",
  "new_password": "..."
}
```

## 11.3 Invalid reset credential

`INVALID_RESET_TOKEN`:

```text
show one safe invalid-reset-link state
→ link to /forgot-password
```

Do not differentiate invalid/expired/used.

## 11.4 Success

Backend deliberately revoked session credentials.

Required sequence:

```text
confirm reset 204
→ clear sensitive form state
→ shared authenticated-session/cache cleanup
→ DO NOT call /auth/me → Refresh
→ navigate /login
→ transient success notice
```

Notice equivalent to:

```text
Password reset successfully.
Please sign in with your new password.
```

Use lightweight React Router navigation state or equivalent in-memory route state.

Do not use:

```text
success-message query parameter
localStorage/sessionStorage
toast dependency
```

Consume/clear transient notice appropriately so it does not become persistent application state.

Mutation retry remains false.

---

# 12. Logout

Add an explicit Logout action to authenticated application shells where appropriate:

```text
LearnerLayout
AdminLayout
```

Do not implement Step-4.7 Admin CRUD while touching `AdminLayout`.

Submit existing `authApi.logout` mutation.

## 12.1 Success

```text
logout 204
→ shared authenticated-session/cache cleanup
→ navigate /login
```

Do not manually clear cookies.

## 12.2 Technical/network failure

Do not pretend logout succeeded.

```text
NETWORK_ERROR / 5xx
→ keep current session/cache
→ remain in authenticated UX
→ show recoverable Logout error
→ explicit Retry action
```

No automatic mutation retry.

Because backend Logout is idempotent, explicit learner Retry is acceptable.

If the first ambiguous response actually committed server logout, later backend/session recovery remains authoritative; do not invent client-side cookie truth.

---

# 13. Profile UI

Replace structural `/profile` placeholder with the smallest real Profile screen supported by existing APIs.

## 13.1 Identity

Source:

```text
auth.me Query / useSession
```

Display at minimum:

```text
Full name
Email
```

Role may be shown as simple account information.

Role display must not become authorization authority.

Do not invent:

```text
avatar
phone
bio
timezone
preferences
account settings platform
```

## 13.2 Progress summary

Canonical source:

```text
queryKeys.progressOverview
→ existing GET /me/progress
```

Reuse the same Query key/cache used by the Progress feature.

Do not create a duplicate Profile-specific server-state resource.

Display sufficient Step-4.6 summary:

```text
Current HSK
Overall progress %
```

The existing backend returns:

```text
current_hsk: number | null
progress_percentage: number
pronunciation_complete: boolean
hsk_levels: ...
```

Render backend values as presentation.

Do not calculate:

```text
current HSK
progress percentage
unlock state
completion
```

from Lessons/Attempts.

If `current_hsk` is null, show a neutral learner-facing equivalent such as `Not started yet` rather than manufacturing a level.

## 13.3 Profile loading/error behavior

Identity comes from the already-resolved protected session.

Progress section loads independently.

```text
progress query primary pending
→ identity remains visible
→ progress section shows loading

progress query error without data
→ identity remains visible
→ progress section shows recoverable error + Retry

background refetch + existing data
→ keep old progress visible
→ optional subtle refreshing state
```

Do not blank the whole Profile during background Progress refetch.

---

# 14. Change Password UI

Implement Change Password as a Profile section/form.

Fields:

```text
Current password
New password
Confirm new password
```

Confirmation is frontend-only.

Client validation may include:

```text
all required
new password confirmation matches
new password length 8..128
```

Exact backend request:

```json
{
  "current_password": "...",
  "new_password": "..."
}
```

Relevant mapping:

```text
INVALID_CURRENT_PASSWORD
→ current-password field feedback

INVALID_PASSWORD
→ new-password policy feedback

NETWORK_ERROR / 5xx
→ recoverable technical error
→ no automatic retry
```

## 14.1 Success — forced re-login

Backend revokes all Refresh Tokens and clears cookies.

Required sequence:

```text
change-password 204
→ clear current/new/confirm fields
→ shared authenticated-session/cache cleanup
→ DO NOT call /auth/me → Refresh
→ navigate /login
→ transient success notice
```

Notice equivalent to:

```text
Password changed successfully.
Please sign in again.
```

Use the same transient in-memory navigation-notice convention as Reset success.

No toast dependency.

---

# 15. Auth Error Mapping

Use:

```text
ApiError.status
ApiError.code
ApiError.details
```

Do not parse human-readable `message` for behavior.

Required behavior map:

| Code / condition | Required UI behavior |
| --- | --- |
| `INVALID_CREDENTIALS` | Login credential error; do not identify email vs password |
| `EMAIL_ALREADY_REGISTERED` | Register email feedback |
| `ACCOUNT_DISABLED` | explicit disabled-account feedback; preserve D-040 definitive semantics where applicable |
| `INVALID_CURRENT_PASSWORD` | current-password field feedback |
| `INVALID_PASSWORD` | Register/new-password policy feedback |
| `INVALID_RESET_TOKEN` | safe invalid-reset-link state + Forgot Password action |
| `INVALID_REQUEST` / safe validation details | map only known safe form fields when practical |
| `NETWORK_ERROR` / 5xx | recoverable technical error, preserve safe form input |
| unexpected | safe local form/page error |

Do not build a generic global toast layer.

Do not parse backend prose to decide behavior.

---

# 16. Form / Sensitive State

Auth/password inputs remain local component state.

Do not put into TanStack Query cache:

```text
email input
password input
current password
new password
confirmation fields
reset token
field errors
success notice
```

Do not persist them to browser storage.

Clear password fields after committed success.

Do not log:

```text
passwords
reset token
Refresh Token
Access Token
```

Do not place passwords in URL/query parameters.

---

# 17. Loading / Pending

All Auth mutations use accepted Step-4.5 mutation behavior:

```text
retry = false
mutation.isPending
→ disable duplicate submit
→ show action loading
```

Do not add mutation auto retry for:

```text
Login
Register
Forgot Password
Reset Password
Logout
Change Password
```

Public-auth route session resolution preserves Step-4.5 UNKNOWN/error semantics.

Do not interpret one technical session-verification error as UNAUTHENTICATED.

---

# 18. Protected/Admin Regression Guardrails

Do not regress:

```text
UNKNOWN
→ session verification state
→ no premature redirect

UNAUTHENTICATED protected route
→ /login

AUTHENTICATED protected learner route
→ allowed

AUTHENTICATED non-admin + /admin
→ D-041 Forbidden

AUTHENTICATED ADMIN + /admin
→ allowed
```

Do not implement Step-4.7 Admin content/CRUD.

Ordinary backend 403 must not globally logout.

---

# 19. 401 / Refresh Preservation

Do not alter D-039/D-040 architecture unless actual runtime proves a contradiction and you stop for review.

Normal protected requests continue through:

```text
request
→ eligible 401
→ shared Refresh
→ one replay
```

Public endpoint exclusions remain accepted, including equivalents of:

```text
/auth/login
/auth/register
/auth/password-reset/request
/auth/password-reset/confirm
/auth/logout
/auth/refresh
```

Do not add page-level Refresh logic.

Do not expose a feature-level `skipAuthRefresh` control.

---

# 20. Suggested File/Component Scope

Exact organization may follow existing conventions, but expected modifications are approximately:

```text
frontend/src/features/auth/
  PublicPages.tsx               # replace placeholders or split into small page components
  session.ts                    # reuse/export auth.me Query definition if useful
  api.ts                        # likely no public contract changes
  new focused auth UI/tests     # acceptable

frontend/src/features/profile/
  ProfilePage.tsx
  focused profile/auth tests

frontend/src/app/router/
  RouteGuards.tsx               # add small public-auth route guard/boundary
  routes.tsx
  route/session tests

frontend/src/app/layouts/
  LearnerLayout.tsx             # Logout action
  AdminLayout.tsx               # Logout action only; no Admin CRUD

frontend/src/app/query/ or features/auth/
  one shared authenticated-session cache cleanup helper

frontend/src/index.css           # only styles required for current simple UI

docs/frontend/step-4.6-auth-profile-ui.md
```

Avoid large component frameworks or generic Auth abstractions.

---

# 21. Testing Requirements

Use existing:

```text
Vitest
jsdom
React Testing Library
```

Normal tests must not require FastAPI/PostgreSQL.

Mock feature API/query behavior at appropriate boundaries.

## 21.1 Login

Test:

```text
required fields
exact request { email, password }
no token/JWT behavior
duplicate submit disabled
INVALID_CREDENTIALS
ACCOUNT_DISABLED
NETWORK_ERROR / 5xx
auth.me authoritative refetch after success
D-043 → /dashboard
ADMIN also → /dashboard
```

Prove navigation occurs **after** authoritative `/auth/me` restoration, not merely after Login response.

## 21.2 Register

Test:

```text
exact payload { email, password, full_name }
no role field
confirm password frontend-only
required/matching confirmation
EMAIL_ALREADY_REGISTERED
INVALID_PASSWORD
immediate authenticated backend behavior
auth.me refetch
/dashboard
no second Login
```

## 21.3 Forgot Password

Test:

```text
exact request
HTTP 202 success acknowledgement
enumeration-safe copy
no account-existence leakage
technical failure preserves email
no auto retry
```

Do not write tests that depend on whether an account actually exists because the frontend contract intentionally cannot know that from success response.

## 21.4 Reset Password

Test:

```text
token read from ?token=
missing token → invalid-link state
missing token → no API request
exact { token, new_password } request
confirm password frontend-only
INVALID_RESET_TOKEN → one safe invalid-link state
success 204
shared session/authenticated Query cleanup
/login navigation
transient sign-in-again notice
no /auth/me Refresh after committed reset success
no token logging/storage/Query cache
no automatic mutation retry
```

Authenticated User must still be able to render `/reset-password?token=...` under D-044.

## 21.5 Logout

Test:

```text
Logout action present in authenticated learner shell
Logout action present in Admin shell where relevant
backend logout called once
success → shared cleanup
success → /login
technical failure → session/cache preserved
technical failure → recoverable Retry
no manual cookie manipulation
mutation no auto retry
```

## 21.6 Public Auth routes — D-044

Test:

```text
AUTHENTICATED + /login → /dashboard
AUTHENTICATED + /register → /dashboard
AUTHENTICATED + /forgot-password → /dashboard
AUTHENTICATED + /reset-password?token=... → Reset page remains accessible

UNKNOWN pending → no premature redirect
UNKNOWN technical verification error → recoverable verification state
UNAUTHENTICATED → requested public Auth page renders
```

Preserve no-redirect-loop behavior.

## 21.7 Profile

Test:

```text
identity from auth.me
full_name
email
role only as presentation if shown
progressOverview current_hsk
progress_percentage rendered from backend
no frontend recomputation
null current_hsk neutral state
progress loading does not hide identity
progress error + Retry
background refetch keeps existing progress visible
```

## 21.8 Change Password

Test:

```text
required current/new password
confirm password frontend-only
exact backend payload
INVALID_CURRENT_PASSWORD
INVALID_PASSWORD
NETWORK/5xx recoverable error
success 204
sensitive fields cleared
shared session/cache cleanup
/login
transient sign-in-again notice
no /auth/me Refresh after committed success
no automatic mutation retry
```

## 21.9 Session/cache isolation

Test shared cleanup and post-auth restoration explicitly:

```text
Logout/Reset/Change success
→ auth.me becomes unauthenticated
→ user-specific Query cache removed
→ previous-user server data cannot flash

Login/Register success
→ stale previous-user cache cleared as needed
→ authoritative auth.me repopulates User
```

Do not create or test a second User store.

## 21.10 Regression

Keep all existing Step-4.5 and earlier tests passing, including:

```text
D-039 bounded retry
D-040 one Refresh/replay
D-040 concurrent single-flight
D-041 Forbidden
ProtectedRoute UNKNOWN/UNAUTHENTICATED/AUTHENTICATED
Step-4.3 learner behavior
Step-4.4 Chat behavior
D-042 Chat uncertain Send
```

Boundary scan must continue to prove no:

```text
JWT decoding
Bearer construction
token localStorage/sessionStorage
cookie inspection
Redux
Zustand
new Auth state library
Step-4.7 Admin CRUD
```

---

# 22. Step Note

Create/update:

```text
docs/frontend/step-4.6-auth-profile-ui.md
```

Include concise reusable sections:

```text
Objective
Why
Mental Model
Backend-authoritative identity/session
Login lifecycle
Register lifecycle
Forgot/Reset lifecycle
Session revocation and forced re-login
Public vs protected route behavior
Profile data sources
Current User vs Profile presentation
Server vs form state
Error-code handling
Security/browser-persistence boundary
Key Design Decisions
Common Mistakes
Definition of Done
Concepts actually used
Tools actually used
```

Do not turn the note into a React/TanStack syntax tutorial.

---

# 23. Concepts Expected

Only list if actually used.

| Concept | Category | Role |
| --- | --- | --- |
| Authentication | SYSTEM | Establish backend-authenticated browser session |
| Authorization | SYSTEM | Preserve role/access distinction |
| Session | SYSTEM | `/auth/me`-derived browser identity |
| HttpOnly cookie authentication | SYSTEM | Browser-managed credentials |
| Credential form state | SYSTEM | Temporary sensitive input |
| Password reset lifecycle | SYSTEM | Recovery credential → password update |
| Session revocation | SYSTEM | Reset/change-password force re-login |
| Backend-authoritative identity | SYSTEM | Current User comes from `/auth/me` |
| Query/session cache cleanup | SYSTEM | Prevent previous-user data leakage |

No new DE/AI core concept belongs to this Step.

---

# 24. Tools Expected

No new tool should be introduced.

Actual tools may include:

| Tool | Category | Role |
| --- | --- | --- |
| React | SYSTEM | Auth/Profile UI and local form state |
| TypeScript | SYSTEM | Typed generated contracts |
| React Router | SYSTEM | Public/protected navigation and reset query parameter |
| TanStack Query | SYSTEM | Session/Profile server state and mutation lifecycle |
| Step-4.2 apiClient / ApiError | SYSTEM | Existing HTTP/error boundary |
| generated OpenAPI types | SYSTEM | Auth request/response source |
| Vitest | SYSTEM | Behavior tests |
| React Testing Library | SYSTEM | User interaction/routing tests |

Do not list libraries merely considered but not used.

---

# 25. Scope Guardrails

Implement Step 4.6 only.

Do **not** implement:

```text
return-to-origin
account switching UX
social login
avatar/profile ecosystem
phone/bio/preferences
generic account-settings platform
frontend JWT parsing
token storage
manual cookie management
Authorization Bearer
new Auth/session store
form/validation dependency
new HTTP client
toast system
backend/API/OpenAPI changes
Step-4.7 Admin CRUD
Phase-5 Data Engineering
Phase-6 AI/RAG
```

Do not weaken existing backend authorization because frontend guards exist.

---

# 26. Acceptance Criteria

Step 4.6 implementation is acceptable only when all are true:

1. Login is usable and sends exact backend fields.
2. Successful Login restores authoritative `/auth/me` before `/dashboard` navigation.
3. Register sends exact backend fields, does not send role/confirmation, authenticates immediately, restores `/auth/me`, then goes `/dashboard`.
4. Forgot Password uses enumeration-safe acknowledgement.
5. Reset uses only `?token=`, never displays/logs/persists token, handles missing/invalid token safely, and forces re-login after success.
6. Logout uses backend endpoint, performs shared session/cache cleanup only on committed success, and handles technical failure recoverably.
7. Authenticated `/login`, `/register`, `/forgot-password` redirect `/dashboard`.
8. Authenticated `/reset-password` remains accessible.
9. Public Auth routes preserve UNKNOWN/session-verification behavior and do not fake logout.
10. Profile identity comes from `auth.me`.
11. Profile HSK/progress comes from existing `progressOverview` Query/cache.
12. Profile does not recompute backend progression.
13. Change Password sends exact backend payload and forces re-login after success.
14. Logout/Reset/Change reuse one authenticated-session/cache cleanup behavior.
15. Previous-user authenticated Query data cannot flash after cleanup/new authentication.
16. No JWT/token/cookie-content handling is introduced.
17. D-039/D-040/D-041 regressions remain passing.
18. No Step-4.7 work is introduced.
19. No new runtime dependency is introduced.
20. Step Note reflects actual implementation.

---

# 27. Verification

From `frontend/` run:

```text
node --version
npm --version
npm ci
npm run build
npm run test -- --run
npm run lint
```

Required:

```text
npm ci PASS
build PASS
full frontend tests PASS
focused Step-4.6 tests PASS
lint PASS except unchanged pre-existing warnings already accepted before this Step
```

Normal tests must not require a running FastAPI backend.

`api.generated.ts` should remain unchanged.

If it changes unexpectedly:

```text
STOP
→ investigate contract drift
```

No `api:generate` is expected because Step 4.6 requires no backend/OpenAPI change.

---

# 28. Stop Conditions

Stop and report `BLOCKED` with evidence if:

```text
actual Auth backend behavior materially contradicts D-043/D-044/D-045
Login/Register cannot restore authoritative auth.me without a new session architecture
correct reset-token handling requires a backend route/API contract change
correct Profile summary requires unsupported backend fields
correct session cleanup requires token/cookie inspection
another runtime dependency becomes necessary
api.generated.ts/backend contract must change
D-039/D-040 must be redesigned
correct implementation requires Step-4.7 Admin work
another material Auth/security/UX convention is required
```

Do not silently work around a stop condition.

---

# 29. Handoff Requirements

Return a completion handoff containing:

```text
Step
Status
What was implemented
Key decisions preserved
Files/components changed
Dependency changes
Login behavior
Register behavior
Forgot-password behavior
Reset-password behavior
Logout behavior
Public-auth route behavior
Profile identity/progress behavior
Change-password behavior
Session/cache cleanup behavior
Error-code behavior
Security/browser-persistence check
Concepts added
Tools added
Tests/verification results
Problems/risks
Deviations
Decisions needed
Recommended next action
```

Explicitly report:

```text
whether package.json/package-lock.json changed
whether any runtime dependency was added/removed
whether backend changed
whether api.generated.ts changed
whether JWT/token/browser-storage/cookie-inspection code was introduced
whether Step-4.7 Admin CRUD was touched
full test file/test totals
focused Step-4.6 test totals
lint result
all remaining warnings
```

Package a focused Step-4.6 handoff ZIP for independent App Engineering Specialist review.

Do not claim PM acceptance.

Required flow after implementation:

```text
Codex completion
→ completion report + focused ZIP
→ App Engineering Specialist independent actual-code review
→ PM acceptance only after PASS_FOR_PM_ACCEPTANCE
```

Do **not** begin Step 4.7.
