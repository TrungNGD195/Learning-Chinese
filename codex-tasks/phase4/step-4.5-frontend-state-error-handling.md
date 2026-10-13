# Codex Execution Task — Step 4.5: Frontend State & Error Handling

## Execution Gate

This is the **single current Codex execution task** for:

**Step 4.5 — Frontend State & Error Handling**

Owner: **App Engineering Specialist**

Implement Step 4.5 only.

Do **not** begin Step 4.6 Auth/Profile forms, Step 4.7 Admin feature UI, Phase 5 ingestion, or Phase 6 AI/RAG.

Before editing, inspect the actual checkout and the latest canonical PM Decision Log. Expected accepted state:

- backend complete through Step 3.6;
- frontend PM-accepted through Step 4.4;
- current app root is `StrictMode -> RouterProvider` with no Query provider yet;
- learner/admin route groups exist but have no session guards yet;
- Step-4.2 `apiClient`, `ApiError`, generated OpenAPI, and feature API wrappers remain canonical;
- Step-4.3 learner behavior is accepted and must not regress;
- Step-4.4 Conversation/Message behavior is accepted and must not regress;
- `@tanstack/react-query` is not installed yet;
- D-039 through D-042 are DECIDED and authoritative.

If the execution checkout materially differs, if correct implementation requires a backend/API/OpenAPI change, another runtime dependency, token storage/decoding, or a new material session/state convention not frozen here, stop and report `BLOCKED` with evidence instead of inventing architecture.

---

# 1. Objective

Complete the frontend foundation for:

```text
server state
session bootstrap
protected routing
bounded read retry
central 401 Refresh/replay
single-flight Refresh
query invalidation
loading/error states
mutation pending state
rendering failure boundary
```

Required mental model:

```text
FastAPI / PostgreSQL
→ authoritative persistent business state

feature API wrapper
→ central apiClient
→ HTTP/cookie auth recovery

TanStack Query
→ in-memory cache of backend server state

React local state
→ UI-only interaction state

React form/temporary state
→ unsaved learner input
```

TanStack Query must **not** become a second business authority.

---

# 2. Source of Truth and Precedence

Read the latest canonical PM Decision Log before editing.

Required decisions include at least:

```text
D-014 — HttpOnly browser authentication cookies
D-015 — authentication/session HTTP contract
D-016 — normalized auth/security errors
D-019→D-026 — accepted Conversation/Message behavior
D-027→D-031 — frontend/runtime/apiClient boundaries
D-033→D-036 — accepted Learning UI behavior
D-037→D-038 — accepted Chat UI behavior
D-039 — global Query read retry / mutation retry policy
D-040 — central 401 recovery, single-flight Refresh, session invalidation
D-041 — authenticated non-admin Admin-route Forbidden UX
D-042 — ambiguous Chat Send technical-failure recovery
```

Precedence:

1. latest canonical PM Decision Log;
2. authoritative Step 4.5 specification;
3. later accepted Step refinements;
4. actual accepted backend/OpenAPI/frontend implementation;
5. earlier examples/notes;
6. this execution packet.

Do not silently reinterpret an earlier Step in a way that contradicts a later frozen decision.

---

# 3. Current Accepted Frontend State

Actual accepted root is equivalent to:

```text
StrictMode
→ RouterProvider
```

There is currently no:

```text
QueryClientProvider
session hook/infrastructure
ProtectedRoute
AdminRoute
TanStack Query cache
root route error boundary
```

Existing server reads are primarily local `useEffect -> feature API -> useState` flows in:

```text
DashboardPage
HskCurriculumPage
LessonPage
AssessmentPage
AssessmentResultPage
ProgressPage
ChatPanel
```

Structural/unimplemented pages such as current Pronunciation, History, and Admin content must not receive fake queries just to demonstrate Query usage.

Current local/form state that must remain local includes at least:

```text
Lesson expanded Vocabulary/Grammar cards
Assessment current question index
Assessment unsubmitted answer drafts
Assessment active Attempt ID
Chat panel open
selected Conversation ID
Chat composer draft
rename draft
delete confirmation
scroll state
blocked Chat action
D-042 uncertain-send recovery state
```

---

# 4. Dependency Scope

Add exactly the focused runtime dependency:

```text
@tanstack/react-query
```

Update:

```text
frontend/package.json
frontend/package-lock.json
```

Do not manually freeze a patch version; npm/package-lock owns the resolved version.

Do **not** add:

```text
Redux
Zustand
TanStack Query Devtools
query persistence plugin
toast library
Error Boundary package
another HTTP client
another state/cache library
```

No backend dependency change is expected.

---

# 5. Suggested Application Structure

Use small existing-convention-aligned modules. Equivalent structure is acceptable:

```text
frontend/src/
  app/
    providers/
      QueryProvider.tsx
    router/
      ProtectedRoute.tsx
      AdminRoute.tsx
      AppRouteErrorBoundary.tsx
      routes.tsx
      routes.test.tsx

  lib/
    query/
      queryClient.ts
      queryKeys.ts
      errors.ts
    api/
      client.ts                 # extend existing client; do not replace boundary
      sessionInvalidation.ts    # small transport→session notification bridge

  features/
    auth/
      session.ts                # auth/me Query + derived session model
```

Feature-specific `queries.ts`/hooks may be introduced only where they reduce duplication. Do not build a generic repository/state framework.

Exact filenames may differ while preserving these responsibilities.

---

# 6. QueryClient Provider and Defaults

Root ownership must become equivalent to:

```text
StrictMode
→ QueryClientProvider
  → RouterProvider
```

Use one application-owned `QueryClient`.

## 6.1 Read retry — D-039

Global read/query retry predicate:

```text
NETWORK_ERROR
OR HTTP status >= 500
→ maximum 2 retries
```

Meaning:

```text
1 initial Query attempt
+ at most 2 Query retries
= at most 3 Query attempts
```

Do not generically Query-retry:

```text
400
401
403
404
409
422
```

Other unexpected/non-ApiError failures are not automatically retried.

Use canonical `ApiError`, conceptually:

```ts
error instanceof ApiError &&
(
  error.code === 'NETWORK_ERROR' ||
  (error.status !== null && error.status >= 500)
)
```

with TanStack's `failureCount < 2` semantics.

Do not add a custom project-wide retry scheduler.

## 6.2 Mutation retry

Global mutation default:

```text
retry = false
```

This includes:

```text
Assessment start/submit
Vocabulary/Grammar viewed
Conversation create/rename/delete
Message send
Assistant retry
```

A central auth Refresh/replay under D-040 is transport recovery, not TanStack mutation retry.

## 6.3 Cache timing

Do not introduce a project-wide `staleTime` policy merely to tune caching.

Leave normal TanStack defaults unless a specific feature requires a narrow documented exception to preserve accepted UX.

Do not add persistent Query cache storage.

---

# 7. Query Key Convention

Create stable feature-oriented key factories equivalent to:

```text
auth.me
→ ["auth", "me"]

dashboard
→ ["dashboard"]

curriculum.levels
→ ["curriculum", "levels"]

curriculum.hsk(hskId)
→ ["curriculum", "hsk", hskId]

lesson.detail(lessonId)
→ ["lesson", lessonId]

lesson.progress(lessonId)
→ ["lesson", lessonId, "progress"]

assessment.detail(assessmentId)
→ ["assessment", assessmentId]

attempt.detail(attemptId)
→ ["assessment-attempt", attemptId]

progress.overview
→ ["progress", "overview"]

progress.hsk(hskId)
→ ["progress", "hsk", hskId]

conversations.byLesson(lessonId)
→ ["conversations", "lesson", lessonId]

messages.byConversation(conversationId)
→ ["messages", "conversation", conversationId]
```

May also define namespace/root helpers used by invalidation, for example:

```text
["curriculum", "hsk"]
["progress", "hsk"]
["assessment-attempt"]
```

Do not encode business calculations or mutable presentation state in query keys.

---

# 8. Server-State Migration Scope

Migrate the **actual existing** server reads to TanStack Query:

```text
/auth/me
Dashboard
HSK levels
HSK curriculum
Lesson detail
Lesson progress
Lesson HSK-label lookup
Assessment detail
Attempt/result detail
Result-page Dashboard Continue target
Progress overview
HSK progress
Conversation list
Message history
```

Do not create fake data loading for currently structural Pronunciation/History/Admin pages.

Do not rewrite accepted presentation components solely to make them look more "Query-like".

## 8.1 Normal resources

Use ordinary `useQuery` for normal single-resource/list reads.

## 8.2 Existing bounded paginated UX

Use `useInfiniteQuery` only for:

```text
Conversation list → Load more
Message history   → Load older
```

This is only an implementation mechanism. Preserve manual bounded buttons; do **not** implement automatic infinite scrolling.

Conversation flattening:

```text
pages
→ flatten in backend page order
→ dedupe by Conversation ID
→ preserve backend returned order
```

Message flattening:

```text
pages
→ flatten
→ dedupe by Message ID
→ sort globally by sequence_number ASC
```

Use backend `page`, `page_size`, and `total` to calculate the next page.

---

# 9. Central 401 Recovery — D-040

This is a central `apiClient` transport responsibility.

Required architecture:

```text
Feature API
→ public apiClient(options)
→ private requestOnce(options)
→ fetch
→ FastAPI
```

`requestOnce` owns exactly the existing Step-4.2 low-level behavior:

```text
URL building
credentials: include
Accept header
JSON Content-Type only with body
JSON serialization
empty success handling
JSON success parsing
ApiError normalization
```

Do not duplicate that parsing logic in another client.

## 9.1 Eligible 401 flow

For one eligible original request:

```text
requestOnce(original)
→ 401
→ participate in shared Refresh
→ Refresh succeeds
→ requestOnce(original) exactly once more
→ return replay result
```

The replay must rebuild the current JSON-focused request from the same typed options/body. Do not introduce generic Request/stream replay machinery.

The replay may not trigger another Refresh loop.

## 9.2 Single-flight Refresh

Use one internal shared Promise equivalent to:

```ts
let refreshPromise: Promise<void> | null = null
```

Lifecycle:

```text
first eligible 401
→ create refreshPromise

concurrent eligible 401s
→ await same Promise

Refresh settles
→ all waiters reuse outcome

finally
→ refreshPromise = null
```

No Refresh storm.

## 9.3 Refresh recursion bypass

The central Refresh request must use the private low-level path directly, equivalent to:

```text
requestOnce({ method: POST, path: "/auth/refresh" })
```

with no authentication-recovery recursion.

Do **not** implement central Refresh by calling the public `authApi.refresh()` wrapper.

The existing public `authApi.refresh()` may remain for API-surface compatibility, but the central recovery mechanism must not call it.

Do not expose a generic feature-facing `skipAuthRefresh` option.

## 9.4 Public-auth endpoints excluded from automatic Refresh

Do not trigger central Refresh for equivalent exact paths:

```text
/auth/refresh
/auth/login
/auth/register
/auth/password-reset/request
/auth/password-reset/confirm
/auth/logout
```

Protected/session-sensitive endpoints remain eligible, including:

```text
/auth/me
/auth/logout-all
/auth/change-password
learner APIs
admin APIs
```

Use current accepted runtime feature paths, not `/api/v1/...` duplicated paths.

## 9.5 One replay only

Each original request may:

```text
participate in at most one Refresh
be replayed at most once
```

If replay still returns 401:

```text
no second Refresh
→ definitive session invalidation
→ throw final ApiError
```

---

# 10. Definitive vs Technical Session Failure

Use canonical `ApiError.status` / `code`.

## 10.1 Definitive session rejection

Treat accepted equivalents such as:

```text
401 INVALID_REFRESH_TOKEN
403 ACCOUNT_DISABLED
final 401 after successful Refresh/replay
```

as definitive session invalidation.

Important actual-backend detail:

```text
/auth/me and other protected APIs may directly return
403 ACCOUNT_DISABLED
```

`ACCOUNT_DISABLED` is a specific definitive auth condition and must invalidate the frontend session.

This does **not** mean generic 403 causes logout.

## 10.2 Ordinary 403

Examples such as:

```text
ADMIN_REQUIRED
LESSON_LOCKED
other authorization/business 403
```

must not:

```text
Refresh
clear current User
logout
globally redirect to /login
```

## 10.3 Technical Refresh failure

Examples:

```text
NETWORK_ERROR
HTTP 5xx
backend unavailable
```

must:

```text
not mark UNAUTHENTICATED
not fake logout
propagate a recoverable technical error
```

During initial session bootstrap:

```text
no cached User
+ technical verification failure
→ remain conceptually UNKNOWN
→ show technical session-verification error + Retry
→ no /login redirect
```

If cached User data already exists:

```text
technical refetch/Refresh failure
→ do not erase cached User identity
→ do not redirect as if backend rejected the session
```

---

# 11. Transport → Session Invalidation Bridge

Do not create a second independent User/session store.

Use a tiny internal notification bridge equivalent to:

```text
apiClient
→ notify definitive session invalidation

TanStack Query/session infrastructure
→ update auth.me Query state
```

Exact function names are implementation details.

A minimal module-scoped callback/subscription is sufficient. Do not add an event/state library.

On definitive invalidation:

1. make `auth.me` Query data represent UNAUTHENTICATED (`null` is acceptable);
2. remove/cancel cached authenticated/user-specific server queries so stale data from a previous session cannot later flash after account/session changes;
3. do not persist any of this to browser storage.

This session-boundary cleanup is distinct from normal mutation invalidation. Do not call `queryClient.clear()` after ordinary feature mutations.

The `apiClient` must not import/own a second User object.

---

# 12. Session Bootstrap

Create one TanStack Query-backed session abstraction around:

```text
GET /auth/me
```

The backend User response is the only current-User source.

Use a conceptual model equivalent to:

```text
auth.me pending / no data
→ UNKNOWN

auth.me returns User
→ AUTHENTICATED

auth.me definitive auth failure / invalidation
→ UNAUTHENTICATED

auth.me technical failure with no cached User
→ UNKNOWN + verification error
```

Do not create a fourth persistent business authentication state for network failure.

If `/auth/me` unexpectedly succeeds with an empty body, treat that as a technical/invalid response, not UNAUTHENTICATED.

Session abstraction may expose:

```text
status
user
verificationError
retryVerification()
```

but the User itself must remain Query data.

Do not:

```text
decode JWT
read cookie contents
store Access Token
store Refresh Token
persist User in localStorage/sessionStorage
```

---

# 13. Protected and Admin Routes

Preserve React Router Data Mode.

## 13.1 Learner route group

Wrap the accepted `LearnerLayout` route group with a small `ProtectedRoute`/equivalent.

Behavior:

```text
UNKNOWN + pending
→ session loading UI
→ no redirect

UNKNOWN + technical verification error
→ session verification error + explicit Retry
→ no redirect

UNAUTHENTICATED
→ Navigate /login (replace)

AUTHENTICATED
→ render LearnerLayout / learner route
```

Do not implement return-to-original-route/login form behavior in Step 4.5.

## 13.2 Admin route group — D-041

Use an `AdminRoute`/equivalent:

```text
UNKNOWN
→ loading / technical verification handling

UNAUTHENTICATED
→ /login

AUTHENTICATED role != ADMIN
→ lightweight Forbidden state

AUTHENTICATED role == ADMIN
→ AdminLayout / route allowed
```

Forbidden state equivalent to:

```text
Access denied
This area requires an Admin account.
[Back to Dashboard]
```

No `/forbidden` route.

Do not render normal Admin content/layout behind the Forbidden state.

Frontend guard is UX only; backend authorization remains authoritative.

## 13.3 Public auth routes

Do not implement Step-4.6 forms or authenticated-user redirects for:

```text
/login
/register
/forgot-password
/reset-password
```

Keep their current structural content.

---

# 14. Root Rendering Error Boundary

Use React Router Data Mode root/pathless route error handling.

Equivalent structure:

```text
root/pathless route
→ errorElement / route ErrorBoundary
→ existing root redirect
→ Public route branch
→ protected Learner branch
→ protected Admin branch
→ NotFound
```

No Error Boundary package.

The route boundary handles unexpected route/render failures only.

It must **not** replace normal handling for:

```text
ApiError
Query error
mutation error
validation error
business error
```

Provide a lightweight recovery/fallback UI, for example Reload/Back to Dashboard where appropriate.

---

# 15. Error Classification

Keep helpers narrow and consumer-driven.

Equivalent reusable predicates may include:

```text
isRetryableReadError(error)
isTechnicalApiError(error)
isDefinitiveAuthError(error)
```

Use canonical:

```text
ApiError.status
ApiError.code
```

Do not parse message strings for behavior.

Feature-specific codes remain feature-specific, including:

```text
AI_CHAT_DISABLED_DURING_TEST
AI_RESPONSE_FAILED
AI_GRADING_UNAVAILABLE
INVALID_MESSAGE_RETRY
LESSON_LOCKED
ADMIN_REQUIRED
```

Do not introduce one generic toast policy/dependency.

---

# 16. Loading-State Model

Map Query/Mutation state to three distinct concepts.

## Page loading

```text
primary required data unavailable
+ query isPending
→ full/primary page loading UI
```

## Background/section refresh

```text
existing data present
+ query isFetching
→ keep existing content visible
→ optional small Refreshing status
```

Do not blank the whole page during background refetch.

## Action loading

```text
mutation.isPending
→ disable duplicate action
→ show context-appropriate action progress
```

Preserve meaningful accepted labels such as:

```text
AI is thinking…
Submitting…
Starting…
```

---

# 17. Lesson Migration and Ordering

Preserve the accepted Step-4.3 initial ordering:

```text
lesson detail Query
→ success
→ lesson-progress Query becomes enabled
```

Do **not** start Lesson detail and Lesson Progress initial reads concurrently.

Reason: accepted backend Lesson GET performs Lesson-start convergence before Progress should be read.

HSK level lookup may be a separate Query after/alongside Lesson detail as appropriate; failure to resolve the optional HSK display label must not make Lesson content unusable.

Vocabulary/Grammar mutation behavior remains:

```text
explicit expansion of unviewed item
→ mutation
→ backend success
→ refetch/invalidate authoritative Lesson Progress
```

Do not locally set authoritative:

```text
theory_completed_at
completed_at
```

from counts or mutation assumptions.

---

# 18. Assessment State and Unsaved Answers

Assessment detail is server state and migrates to Query.

Keep local/form state local:

```text
activeAttemptId
current question index
unsubmitted answers
submission navigation allowance
```

Start Attempt remains an explicit mutation.

Starting an Attempt does not broadly invalidate progression.

All mutations retain `retry = false`.

## 18.1 Unsaved-answer warning

Use current React Router Data Mode facilities:

```text
useBlocker
→ in-app navigation

useBeforeUnload
→ browser refresh/tab close
```

Enable warning only while:

```text
active Attempt exists
AND at least one draft answer exists
AND terminal submission navigation has not been allowed
```

In-app UX equivalent:

```text
You have unsaved assessment answers.
[Stay]
[Leave]
```

`Stay` resets the blocker.

`Leave` proceeds.

Before successful normal GRADED result navigation or D-036 `AI_GRADING_UNAVAILABLE -> GRADING_FAILED result` navigation:

```text
mark terminal submission navigation allowed
→ navigate Result
```

so the application does not block its own committed terminal flow.

No autosave.
No localStorage/sessionStorage.
No backend draft endpoint.
No additional routing/form dependency.

---

# 19. Assessment Submit Invalidation

## 19.1 Normal GRADED submit

After successful submit, refresh backend truth only.

Invalidate equivalent affected resources:

```text
attempt.detail(attemptId)
assessment-attempt/history namespace if present

dashboard
progress.overview
curriculum.levels
curriculum.hsk namespace / relevant loaded HSK queries
progress.hsk namespace / relevant loaded HSK queries

Lesson Progress queries when LESSON_EXERCISE progression may have changed
```

Then navigate Result.

Do not calculate score/pass/unlock/progression in cache.

### Public-contract ID limitation

Current public `AssessmentResponse` does not expose a reliable `lessonId` or `hskId` for every direct Assessment route.

Therefore:

- when a reliable identifier already exists from accepted backend-returned/cache context, targeted invalidation is fine;
- otherwise use **bounded feature-scoped invalidation** (for example all cached `progress.hsk`, all cached `curriculum.hsk`, or a predicate covering cached Lesson Progress queries);
- do **not** invent relation heuristics;
- do **not** add a backend/OpenAPI field;
- do **not** invalidate the entire QueryClient/application.

## 19.2 D-036 AI_GRADING_UNAVAILABLE

Preserve exact semantics:

```text
submission already persisted
Attempt = GRADING_FAILED
```

On this error:

```text
invalidate attempt.detail(attemptId)
invalidate attempt/history namespace if present
allow terminal navigation
navigate same Attempt result
```

Do not retry the mutation.

Do not invent progression invalidations for a GRADING_FAILED Attempt because backend does not progress the learner for that outcome.

## 19.3 Other submit failures

Remain on Assessment page.

Preserve draft answers.

No automatic retry.

---

# 20. Other Query Invalidation Matrix

Do not invalidate the entire application after every mutation.

## Vocabulary / Grammar viewed

Success:

```text
refetch/invalidate lesson.progress(lessonId)

dashboard
progress.overview
curriculum.levels
relevant/bounded curriculum.hsk queries
relevant/bounded progress.hsk queries
```

Use `lesson.hsk_level_id` when available for targeted HSK invalidation.

Do not rebuild progression in frontend cache.

## Conversation create

```text
invalidate conversations.byLesson(lessonId)
select backend-returned Conversation ID locally
```

## Conversation rename

```text
invalidate conversations.byLesson(lessonId)
```

Backend remains authoritative for `updated_at` ordering.

## Conversation delete

```text
invalidate conversations.byLesson(lessonId)
remove messages.byConversation(deletedConversationId) Query cache
```

Preserve accepted selection behavior after list refresh.

## Message send success

Backend returns persisted:

```text
USER Message
ASSISTANT Message
```

Update Message Query cache using only those backend-returned objects.

Do not create optimistic/fake backend Message IDs.

Then:

```text
invalidate conversations.byLesson(lessonId)
```

for backend activity ordering.

## Assistant retry success

Merge backend-returned Assistant into Message Query cache.

Invalidate Conversation list for activity ordering.

## AI_RESPONSE_FAILED

Backend has already persisted relevant USER/FAILED Assistant state.

Refetch authoritative Message history.

Do not resend USER Message.

---

# 21. Chat Query Migration

Preserve all Step-4.4 local semantics while moving only server resources to Query.

Local state remains:

```text
panel open
selected Conversation ID
Composer draft
rename draft
delete confirmation
scroll refs/state
blocked action
D-042 uncertain-send state
```

Server state moves to Query:

```text
Conversation pages
Message pages
```

Do not move selected Conversation ID or Composer into Query cache.

Preserve:

```text
D-037 explicit Conversation creation
sequence_number Message order
page-based Load more / Load older
blocked-action exclusivity
request-scoped scroll restoration
PENDING / COMPLETED / FAILED rendering
Assistant Retry semantics
no polling
no fake Message IDs
D-038 safe Markdown
```

Default Query refetch behavior must not be allowed to break accepted scroll behavior. If a narrow Chat query option is required to preserve accepted interaction, document it in code/tests; do not introduce a project-wide cache policy.

---

# 22. D-042 Ambiguous Chat Send Technical Failure

This intentionally refines Step 4.4.

Distinguish:

```text
AI_RESPONSE_FAILED
→ known persisted USER + FAILED Assistant

ambiguous technical Send failure
→ persistence unknown
```

Ambiguous technical failure includes cases where the transport cannot prove whether the request committed, such as:

```text
NETWORK_ERROR
unexpected technical HTTP failure where persistence is uncertain
successful-but-invalid response parsing where request persistence cannot be proven
```

Do not classify the known `AI_RESPONSE_FAILED` path as ambiguous.

## 22.1 Required flow

```text
sendMessage(...)
→ ambiguous technical failure
→ preserve exact Composer draft
→ automatically refetch authoritative Message history
→ display refreshed history
→ enter local uncertain-send state
→ gate normal resend of preserved draft
```

Show feedback equivalent to:

```text
We couldn't confirm whether this message was saved.
The conversation has been refreshed.
Review it before sending again.
```

Expose:

```text
[Edit draft]
[Send again]
```

### Edit draft

```text
→ clear/transition uncertain-send gate
→ Composer remains populated/editable
→ no Message sent
```

### Send again

```text
→ explicit new learner intent
→ submit preserved text exactly once
```

No automatic resend.

No content/timestamp/sequence heuristic.

No fake Message/persistence ID.

The learner may deliberately create a duplicate after reviewing server history; that is accepted D-042 behavior.

## 22.2 Assistant Retry technical failure

```text
retryAssistantMessage(...)
→ ambiguous technical failure
→ automatically refetch authoritative newest Message history
→ do not automatically retry old failed Assistant
```

A later normal Retry remains explicit and backend-authoritative.

## 22.3 Interaction with blocked action

`AI_CHAT_DISABLED_DURING_TEST` remains the accepted Step-4.4 action-scoped blocked state.

Do not convert uncertain-send into:

```text
Periodic-Test availability state
Message backend status
Query business truth
```

Changing Conversation / abandoning the relevant Composer lifecycle may clear uncertain-send state consistently with accepted Chat behavior.

---

# 23. Periodic-Test / Chat Boundary

Preserve:

```text
AI_CHAT_DISABLED_DURING_TEST
→ local blocked action
→ normal Send/Retry disabled
→ exact Try again operation
→ backend re-checks availability
```

Do not create:

```text
chatAvailability Query
Periodic-Test polling
frontend Chat availability calculation
```

401/Refresh infrastructure and TanStack Query must not alter this business rule.

---

# 24. Empty vs Error States

For every migrated Query, distinguish:

```text
pending
successful empty
error
background refetch
```

Example:

```text
Conversation Query success with []
→ Empty State

Conversation Query error
→ Error State + explicit Retry
```

Do not use `!data` alone to conflate these states.

Preserve existing user-facing empty states where already accepted.

---

# 25. Browser Persistence Boundary

Do not persist to `localStorage` or `sessionStorage`:

```text
Access Token
Refresh Token
current User session truth
Lesson business state
Progress
Assessment Attempts/results
Assessment drafts
Conversation history
Messages
```

TanStack Query cache remains memory-only in Step 4.5.

Do not decode JWTs.
Do not inspect HttpOnly cookie contents.

---

# 26. Expected Files / Components to Change

At minimum expect changes/additions around:

```text
frontend/package.json
frontend/package-lock.json

frontend/src/main.tsx
frontend/src/app/router/routes.tsx
frontend/src/app/router/routes.test.tsx

frontend/src/lib/api/client.ts
frontend/src/lib/api/client.test.ts

frontend/src/lib/query/*
frontend/src/features/auth/session* / route-guard support

frontend/src/features/dashboard/DashboardPage.tsx
frontend/src/features/curriculum/HskCurriculumPage.tsx
frontend/src/features/lesson/LessonPage.tsx
frontend/src/features/assessment/AssessmentPage.tsx
frontend/src/features/assessment/AssessmentResultPage.tsx
frontend/src/features/progress/ProgressPage.tsx
frontend/src/features/conversation/ChatPanel.tsx

frontend/src/test/api-boundary.test.ts
frontend/src/index.css                    # only small loading/error/Forbidden styles if needed
```

May create focused query/hook/test files under the relevant features.

Do not modify backend files or `api.generated.ts` unless execution discovers a genuine contract contradiction and stops `BLOCKED`; no backend/OpenAPI change is expected.

Do not implement Step-4.6 form/Profile behavior in existing auth/profile pages.

---

# 27. Testing Requirements

Use existing Vitest/jsdom/React Testing Library.

Normal tests must not require FastAPI/PostgreSQL.

Use mocked feature API/fetch behavior as appropriate.

## 27.1 QueryClient policy

Test:

```text
NETWORK_ERROR
→ exactly maximum 2 Query retries

5xx
→ exactly maximum 2 Query retries

400 / 401 / 403 / 404 / 409 / 422
→ no Query retry

mutation default
→ retry false
```

Prove 401 Refresh/replay does not multiply with Query retry.

## 27.2 Central 401 recovery

Test at least:

```text
eligible 401
→ exactly one Refresh
→ original request replay exactly once

replayed request 401
→ no second Refresh

/auth/refresh
→ never recursively Refresh

login/register/reset/logout excluded from automatic Refresh

concurrent eligible 401s
→ exactly one Refresh HTTP call
→ all waiters resume on success

shared Refresh definitive failure
→ all waiters fail consistently
→ session invalidated

technical Refresh failure
→ no fake logout
```

Also test a JSON POST/body request replay to prove current body is safely reproduced exactly once.

Test direct `ACCOUNT_DISABLED` from `/auth/me`/protected request as definitive session invalidation while ordinary `ADMIN_REQUIRED` 403 does not invalidate session.

## 27.3 Session

Test:

```text
UNKNOWN → AUTHENTICATED
UNKNOWN → UNAUTHENTICATED

/auth/me Access 401
→ Refresh success
→ replay /auth/me
→ AUTHENTICATED

initial technical failure after bounded retries
→ UNKNOWN technical error
→ no /login redirect
→ Retry works

cached User + technical refetch/Refresh failure
→ User not erased as fake logout

no JWT decode
no token/browser storage
```

## 27.4 Routes

Test:

```text
UNKNOWN learner route
→ loading

UNAUTHENTICATED learner route
→ /login

AUTHENTICATED learner
→ learner route renders

AUTHENTICATED non-admin /admin
→ D-041 Forbidden state
→ Dashboard link

ADMIN /admin
→ Admin content allowed

ordinary backend 403
→ no generic logout
```

Preserve all existing approved route tests including no standalone `/chat`.

## 27.5 Server-state migration

For each migrated page, verify user-visible behavior rather than implementation snapshots:

```text
page pending state
successful data render
error + Retry where appropriate
background refetch keeps existing content
```

Assert server data is no longer duplicated as independent long-lived `useState` snapshots in migrated pages.

## 27.6 Lesson

Test:

```text
Lesson query resolves before initial Lesson Progress request starts

Vocabulary viewed
→ mutation pending disables duplicate
→ authoritative Lesson Progress Query refetch/invalidation
→ no local completion calculation

Grammar viewed
→ same
```

Preserve Step-4.3 explicit-expansion semantics.

## 27.7 Assessment

Test:

```text
Start Attempt is explicit
mutation not auto-retried

draft answers remain local
ordinary submit failure preserves drafts

GRADED submit
→ required bounded invalidations
→ Result navigation

AI_GRADING_UNAVAILABLE
→ no mutation retry
→ Attempt detail/history invalidation
→ same Attempt Result navigation
→ no progression calculation
```

## 27.8 Assessment leave warning

Test:

```text
no Attempt / clean form
→ no blocker

dirty active Attempt
→ in-app navigation blocked

Stay
→ remains Assessment

Leave
→ proceeds

beforeunload handler active while dirty

successful GRADED navigation
→ not blocked

D-036 terminal GRADING_FAILED navigation
→ not blocked
```

## 27.9 Chat Query migration

Preserve/re-run Step-4.4 tests and add/update tests proving:

```text
Conversation list Load more still bounded
Message Load older still bounded
sequence_number order preserved
request-scoped scroll restoration preserved
blocked-action exclusivity preserved
D-037 explicit create preserved
D-038 Markdown security preserved
no polling
```

## 27.10 D-042 Chat technical failure

Test:

```text
ambiguous Send technical failure
→ draft preserved
→ Message Query automatically refetched
→ no persistence heuristic
→ normal resend gated
→ Edit draft sends nothing
→ Send again sends exact preserved content once
→ no automatic resend

AI_RESPONSE_FAILED
→ remains known-persisted path
→ authoritative history refetch
→ no USER resend

Assistant Retry technical failure
→ history refetch
→ no automatic retry
```

## 27.11 Error Boundary

Test:

```text
unexpected route/component render exception
→ root route fallback

normal Query/API error
→ feature error state
→ does not rely on root render boundary
```

## 27.12 Boundary scan/tests

Assert no:

```text
Redux
Zustand
Query Devtools
localStorage/sessionStorage token/business-state persistence
JWT decoding
second current-User store
Step-4.6 auth forms
AI/RAG/provider calls
SSE/WebSocket/polling introduced by this Step
```

---

# 28. Verification Commands

From `frontend/`:

```text
node --version
npm --version
npm ci
npm run build
npm run test -- --run
npm run lint
```

Expected Node remains compatible with:

```text
>= 22.12
```

No backend should be required for normal frontend build/tests.

Because no API/OpenAPI contract change is expected, `api.generated.ts` should remain unchanged. If it changes unexpectedly, stop and investigate rather than accepting a generated diff casually.

---

# 29. Step Note

Create/update:

```text
docs/frontend/step-4.5-frontend-state-error-handling.md
```

Include concise reusable knowledge:

```text
Objective
Why
Mental Model
Server vs Local vs Form state
Query cache role
Query keys
Read vs mutation retry
401 Refresh/single-flight flow
Session bootstrap
Authentication vs authorization
Query invalidation
Assessment drafts/leave warning
D-042 uncertain Send recovery
Loading/error distinctions
Error Boundary
Browser persistence boundary
Common mistakes
Definition of Done
```

Do not turn the note into a library syntax tutorial.

---

# 30. Concepts Actually Expected

Document only concepts actually implemented:

| Concept | Category | Role |
|---|---|---|
| Server state | SYSTEM | Backend-originated state managed through Query |
| Local UI state | SYSTEM | UI-only transient interaction |
| Form / temporary state | SYSTEM | Unsaved learner input |
| Query cache | SYSTEM | In-memory backend-state cache |
| Query invalidation | SYSTEM | Refresh affected backend truth |
| Session bootstrap | SYSTEM | `/auth/me` resolves current browser session |
| Authentication vs authorization | SYSTEM | 401 vs 403 semantics |
| Single-flight | SYSTEM | One Refresh shared by concurrent 401s |
| Bounded retry | SYSTEM | Limited transient read recovery |
| Mutation retry safety | SYSTEM | Prevent duplicate side effects |
| Error classification | SYSTEM | Business vs technical vs rendering |
| Error Boundary | SYSTEM | Unexpected render/route failure |
| Backend-authoritative state | SYSTEM | Query cache never owns business rules |

No new DE or AI core concept is implemented in this Step.

---

# 31. Tools Actually Expected

| Tool | Category | Role |
|---|---|---|
| `@tanstack/react-query` | SYSTEM | Server-state cache, queries, mutations |
| React | SYSTEM | Local/form state |
| React Router | SYSTEM | Guards, leave blocking, root route error boundary |
| TypeScript | SYSTEM | Typed state/session/query boundaries |
| Step-4.2 `apiClient` / `ApiError` | SYSTEM | HTTP/auth recovery/error boundary |
| Vitest | SYSTEM | Unit/state/retry tests |
| React Testing Library | SYSTEM | Route/UI behavior tests |

Do not list Redux/Zustand/Query Devtools as used.

---

# 32. Scope / Non-Goals

Do not implement:

```text
Step-4.6 Login/Register/Forgot/Reset/Change-Password/Profile UI
Step-4.7 Admin CRUD UI
backend/API/schema changes
JWT decode/token state
browser-persisted Query cache
Redux/Zustand
Query Devtools
toast system
new HTTP client
optimistic fake Message IDs
frontend grading/progression rules
Chat availability polling
SSE/WebSocket/streaming
real LLM/RAG/provider logic
```

Do not convert every form/UI value into Query data.

Do not add a second current-User store.

---

# 33. Acceptance Criteria

Step 4.5 is complete only when all are true:

1. `@tanstack/react-query` is the only new runtime dependency.
2. App has one QueryClientProvider.
3. Actual existing server reads listed in this task are migrated to Query.
4. Genuine UI/form state remains local.
5. D-039 retry policy is exact.
6. All mutations default to `retry=false`.
7. `apiClient` implements central eligible-401 Refresh/replay.
8. Concurrent 401s share one Refresh.
9. Refresh bypasses recursion and original request replays at most once.
10. Definitive auth failure invalidates session; technical Refresh failure does not fake logout.
11. `/auth/me` is current-User/session authority.
12. Protected routes wait during UNKNOWN and redirect only after UNAUTHENTICATED.
13. Non-admin Admin access renders D-041 Forbidden state.
14. Ordinary 403 does not logout.
15. Lesson initial Query ordering preserves Step-4.3 start/progress behavior.
16. Query invalidation refreshes backend truth without frontend progression calculation.
17. Assessment drafts remain local and get the required leave warning.
18. D-036 assessment semantics remain intact.
19. Step-4.4 Chat semantics remain intact after Query migration.
20. D-042 ambiguous Send automatically refetches history and requires explicit Edit/Send-again choice.
21. Root rendering failures have a Router error boundary.
22. Empty/error/background-loading states are distinct.
23. No token/JWT/business-state browser persistence is introduced.
24. No backend/OpenAPI changes are made.
25. Existing and new frontend build/tests/lint pass.
26. Step Note reflects the actual implementation.

---

# 34. Codex Completion Report Required

Return a concise handoff with:

```text
Step
Status (DONE implementation handoff; not PM acceptance)
Implementation plan executed
Files created
Files modified
Dependencies added/removed
QueryClient defaults
Query keys
Server-state migration completed
Session bootstrap behavior
401 Refresh/single-flight behavior
Definitive-vs-technical Refresh behavior
Protected/Admin route behavior
Error/loading behavior
Invalidation behavior
Assessment leave-warning behavior
D-042 Chat behavior
Tests added
Exact verification commands/results
Acceptance-criteria status
Step Note path
Concepts actually used
Tools actually used
Deviations
Problems/risks
Decisions needed
Recommended next action
Handoff ZIP path
```

Do not claim PM acceptance.

