# Step 4.6 — Auth & Profile UI

## Objective and mental model

Provide the Login, Register, password-recovery, Logout, Profile, and Change Password flows on the existing React application. The backend owns credentials, cookies, identity, authorization, and progression. `GET /auth/me` is the sole current-User source; the existing `auth.me` TanStack Query is shared by route guards, Auth restoration, and Profile.

```text
temporary form values → Auth API wrapper → central apiClient → backend
backend HttpOnly cookies → GET /auth/me → auth.me Query → session UX
GET /me/progress → progressOverview Query → Profile summary
```

## Login and registration

Login submits only email and password. Register submits full name, email, and password; confirmation and role are never sent. Both successful mutations clear stale user-specific Query entries, fetch the canonical `auth.me` Query, and navigate to `/dashboard` only after a User is returned. Learners and Admins use the same destination; registration is already authenticated and does not call Login.

## Forgot and reset password

Forgot Password submits the email and gives the same enumeration-safe acknowledgement for HTTP 202. Reset reads the opaque token from `?token=` inside the Reset flow and submits it only with the new password. Missing or invalid tokens share one safe state. Successful reset clears local password fields and authenticated Query state, does not re-check `/auth/me`, then navigates to Login with a transient navigation-state notice.

## Session revocation and Logout

Logout, successful Reset, successful Change Password, and definitive session invalidation reuse `clearAuthenticatedSessionCache`. It sets `auth.me` to unauthenticated, cancels user Queries, then removes them after the protected view can unmount. After successful Login/Register, `prepareAuthenticatedSessionCache` clears user-specific business Queries and clears stale `auth.me` result/error state without asserting unauthenticated; `/auth/me` remains UNKNOWN until its verification returns. A technical verification error remains UNKNOWN even when `auth.me` data is null. Logout network/5xx failures preserve the current session and require an explicit retry. The browser never reads or edits cookie values.

## Public and protected routes

Login, Register, and Forgot Password wait for session verification; authenticated users go to `/dashboard`. Reset Password remains accessible with an authenticated session. Technical `/auth/me` errors keep the existing UNKNOWN verification state and Retry action. Protected and Admin guards keep their existing authentication and Forbidden behavior.

## Profile data sources

Identity (full name and email) comes from `auth.me`. Current HSK and overall percentage come from the existing `progressOverview` Query (`GET /me/progress`). Profile displays backend values without recomputing progression. Progress loads independently, can be retried independently, and retains cached values while refreshing.

## Server and form state

Current User and progress are server state in the existing Query cache. Email/password fields, confirmation fields, local field errors, and loading state stay in component state. Success notices use React Router navigation state and are copied into transient Login-page state before the history entry is cleared.

## Error handling

Stable `ApiError.code` values drive safe feedback: invalid credentials stay generic; disabled accounts are explicit; duplicate registration identifies the email; invalid current/new password errors are assigned to the relevant field; invalid reset credentials use the common invalid-link state. Network and server errors preserve safe form values and allow user-triggered retry. Auth mutations do not auto-retry.

## Security and browser-persistence boundary

Passwords and reset tokens remain temporary form/flow inputs and never enter Query data, global state, logs, localStorage, or sessionStorage. The reset token is not rendered. The UI does not decode JWTs, create Bearer headers, inspect cookies, or manage tokens. Backend HttpOnly cookies and `/auth/me` remain authoritative.

## Key design decisions

- Preserve D-039 bounded read retry and D-040 central single-flight Refresh/replay.
- Restore `/auth/me` before post-Login/Register navigation.
- Separate post-auth cache preparation from committed session termination.
- Use `/dashboard` for both roles and avoid return-to-origin or account-switch flows.
- Keep authenticated Reset Password accessible under D-044.
- Reuse the existing Profile progress Query key and one session/cache cleanup operation.
- Add Logout to the existing Learner and Admin shells without changing Admin page scope.

## Common mistakes

- Treating Login/Register response bodies as the current session source.
- Retrying Auth mutations automatically or repeating registration after session verification fails.
- Revealing account existence from password-reset requests.
- Sending confirmation fields or role to the backend.
- Putting credentials, reset tokens, or identity copies in Query or browser storage.
- Recomputing progress in the frontend or logging out after an ordinary 403.

## Definition of Done

- Auth and password forms match accepted request contracts and error semantics.
- Session-aware public routes, forced re-login, Logout, and Profile use existing session/API/query foundations.
- Previous-user Query data is removed on session cleanup and before post-auth restoration; preparation does not mark the new session unauthenticated.
- Step 4.3–4.5 behavior remains covered; no backend, generated contract, runtime dependency, or Step 4.7 work is added.

## Concepts and tools used

| Concept | Category | Role |
| --- | --- | --- |
| Authentication and authorization | SYSTEM | Keep identity separate from role/access decisions |
| Backend-authoritative session | SYSTEM | Current User comes from `/auth/me` |
| HttpOnly cookie authentication | SYSTEM | Browser-managed credentials |
| Credential form state | SYSTEM | Temporary local input and validation |
| Password reset and session revocation | SYSTEM | Recover credentials and force re-login |
| Query/session cache cleanup | SYSTEM | Prevent previous-user data from remaining available |

| Tool | Category | Role |
| --- | --- | --- |
| React and TypeScript | SYSTEM | UI, local state, generated contract types |
| React Router | SYSTEM | Route boundaries, reset query input, transient notice |
| TanStack Query | SYSTEM | Canonical session/progress reads and mutation lifecycle |
| Existing apiClient and ApiError | SYSTEM | Shared HTTP recovery and error classification |
| Vitest and React Testing Library | SYSTEM | User-visible behavior and route tests |
