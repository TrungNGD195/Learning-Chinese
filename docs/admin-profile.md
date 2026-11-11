# Administrator profile

The administrator's last navigation item, Hồ sơ, opens `/admin/profile`. It
contains editable full name, read-only login email and administrator role,
password change and an account-wide logout action with confirmation.

`PATCH /api/v1/auth/me` accepts only `full_name`, trimmed to 1–120 characters.
The server chooses the authenticated user; callers cannot provide another user
ID, email, role or account state. Successful updates refresh the frontend auth
cache. There is no learner progress query on the admin profile page.

Password fields have independent show/hide controls, proper autocomplete,
inline field errors and a confirmation check. Passwords remain 8–128 characters;
the server additionally rejects reuse of the current password with
`PASSWORD_UNCHANGED`. Only the current/new pair is sent to the existing change
endpoint; confirmation is checked in the browser. Success clears sensitive form
state and redirects to login.

Migration `0017_account_session_version` adds a zero-default integer to users.
New access cookies include the current version. Existing valid version-zero
cookies continue to work until an account-wide revocation. Logout-all, password
change and reset confirmation advance the version and revoke refresh tokens in
the same locked-user transaction. Authentication compares versions against the
current user record, rejecting old access cookies as well as old refresh tokens.
Single-device logout retains its previous behavior. No account, password hash,
lesson or learning progress is replaced by the migration.

Deploy the backend migration before the frontend. Verify name persistence,
incorrect/current-equals-new password errors, return to login, and another
browser's access/refresh rejection after each security action. Use temporary
test accounts rather than changing the user's real password.

Evidence: backend profile/auth/database tests, frontend form/route tests,
`frontend/e2e/admin-profile.spec.ts` against the dedicated test database and
fixture screenshots in `.impeccable/review/admin-profile/`.
