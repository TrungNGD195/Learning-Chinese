# Browser tab login lifetime

The web initializes its session before rendering either authenticated routes or
login/register forms. A new tab with no initialization marker first completes
the existing `/auth/logout` operation, clearing shared auth cookies and revoking
the refresh token through the backend's established logout flow. Only then can
the router content render.

A non-sensitive `bo.tab-initialized.v1=ready` marker lives in `sessionStorage`.
It contains no identity, password, access token or refresh token. The same tab
retains the marker across reload and navigation, so those actions do not invoke
logout. A newly opened tab after the previous tab is closed has fresh tab
storage and cannot silently reuse its cookies. There are no unload/beacon
logout handlers that could mistake reload for closing the tab.

Initialization is single flight under React StrictMode. Failed logout or blocked
storage keeps forms and private content hidden and offers retry. A failed logout
does not write the marker. Explicit login/logout and cookie refresh otherwise
keep their existing behavior.

This policy applies to both learner and administrator web routes. Cookies are
shared across tabs: initializing a new tab clears the browser's current shared
login, so other tabs will also need authentication when they next check it.
This is an entry-time policy, not a promise of a reliable server request at the
instant a tab or browser process closes. Browser restoration/duplication may
restore tab storage; such restored tabs follow the browser's retained tab
session rather than a fresh-tab startup.

The source-level storage audit restricts auth initialization storage to this
exact marker. Named journey view modules may also keep non-secret `bo-` visual
position/arrival keys in tab storage; those do not retain credentials or update
learning progress. The audit continues to forbid credentials in browser storage.
No backend schema or learner progress data changes are required.

Validation: focused auth/security tests cover initialization ordering, concurrent
startup, reload, fresh-tab logout, failure/retry and blocked storage. Guarded
real-backend browser tests cover both roles, internal navigation, reload,
cookie refresh, closing/opening a new tab and removal of auth cookies.

## Local API transport

Local Docker frontend requests use `/api/v1` through Vite's development proxy
to `http://backend:8000`. Direct Vite defaults to `http://127.0.0.1:8000`, with
`API_PROXY_TARGET` available as a shell override. The API address seen by the
browser stays on the frontend origin. This avoids a successful login followed
by rejected SameSite=Lax cookies when frontend `127.0.0.1` calls API `localhost`.
HttpOnly cookie protections and production deployment configuration are unchanged.

`frontend/scripts/verify-local-auth-transport.mjs` verifies real learner login,
reload, refresh-cookie recovery and fresh-tab logout on both local hostnames.
It creates an isolated temporary learner and removes only that exact generated
UUID/email after the check; it never changes an existing account's password.
