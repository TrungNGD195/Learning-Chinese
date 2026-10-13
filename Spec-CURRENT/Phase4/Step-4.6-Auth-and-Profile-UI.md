# Step 4.6 — Auth & Profile UI

## Context
Backend authentication from Step 3.5 provides registration, login, refresh/logout, password reset, current-user lookup, and authenticated password change. Phase 4 already has route/layout and API-client foundations.

## Objective
Implement usable learner authentication/session UI and the basic Profile screen without moving authorization or token logic into the browser.

## Current State
Expected dependencies: Steps 4.1, 4.2 and 4.5 complete; Step 3.5 API contracts available and generated into frontend types.

## In Scope
- `/login`, `/register`, `/forgot-password`, `/reset-password`.
- session restoration through `GET /auth/me`.
- logout.
- protected Learner/Admin route behavior using backend current-user state.
- `/profile` showing name, email, current HSK/progress summary where available.
- change-password form using `/auth/change-password`.

## Out of Scope
Social login, avatar/profile ecosystem, standalone account settings platform, frontend JWT parsing, role decisions based only on client state.

## Functional Requirements
- Public auth forms validate required client fields but backend remains authoritative.
- Successful login/register restores current-user state and navigates to the appropriate product entry.
- Anonymous access to protected routes redirects to login.
- Logged-in learner cannot enter Admin UI solely by manipulating client state; backend 403/404 remains authoritative.
- Password-reset screens support request and confirm flows.
- Password change requires current password + new password and handles forced re-login/session revocation cleanly.
- Profile displays server-provided identity; current HSK/progress comes from canonical progress/dashboard API rather than frontend recomputation.

## Technical Requirements
Use the existing central `fetch` client, `credentials: "include"`, generated OpenAPI types and TanStack Query/session primitives from Steps 4.2/4.5. Never store access/refresh tokens in localStorage/sessionStorage.

## Inputs / Outputs
Inputs: form values, URL reset token where contract requires it, current-user/progress API responses. Outputs: authenticated navigation state, safe field errors, profile/password-change UI states.

## Data Flow
```text
Auth form → feature API → FastAPI → HttpOnly cookies
                           ↓
                    GET /auth/me
                           ↓
                  frontend session state
```

## Interfaces / API
Use the exact Step 3.5 OpenAPI contracts for register/login/logout/password-reset/current-user/change-password. Do not duplicate request/response interfaces manually.

## Files / Components
Expected areas: `features/auth`, `features/profile`, public pages/routes, route guards/layout integration, focused tests. Follow repository conventions established in 4.1–4.5.

## Config / Env
Only existing `VITE_API_BASE_URL`. No auth secrets in frontend env.

## Error Handling
Map stable backend codes to actionable form/page states. Authentication failure must not crash the app or loop refresh indefinitely. Network/5xx remains distinguishable from invalid credentials/validation.

## Testing
Cover login success/failure, anonymous protected-route redirect, session restore, logout, reset request/confirm, profile rendering, password-change success/failure, and Admin route denial for learner state.

## Acceptance Criteria
- [ ] Public auth flows are usable end-to-end against backend contracts.
- [ ] HttpOnly-cookie model is preserved; frontend never stores JWTs.
- [ ] Current-user session restoration works.
- [ ] Protected-route UX works without replacing backend authorization.
- [ ] Profile shows basic identity and canonical progress summary.
- [ ] Password change works and handles session revocation/re-login.
- [ ] Error/loading states are explicit and tested.

## Constraints / Non-goals
Do not redesign auth architecture or add a new state-management library.

## Open Questions
None that block this Step.
