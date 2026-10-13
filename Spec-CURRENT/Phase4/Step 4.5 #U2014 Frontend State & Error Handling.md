# Step 4.5 — Frontend State & Error Handling

## Goal

Complete the frontend foundation by implementing predictable handling for:

- server state;
- local UI state;
- form/temporary state;
- authentication session bootstrap;
- route protection;
- loading;
- errors;
- retries;
- query invalidation;
- mutation pending states.

The frontend must not become authoritative for product business state.

---

# State Categories

Use three conceptual categories.

## Server State

Examples:

```text
current User
Dashboard
Curriculum
Lesson
Progress
Assessment
Assessment history
Conversation
Messages
```

These originate from FastAPI and must be treated as backend-owned state.

## Local UI State

Examples:

```text
drawer open
selected Conversation
expanded Vocabulary card
current UI selection
```

Use normal React state where sufficient.

## Form / Temporary State

Examples:

```text
login input
registration input
chat composer
unsubmitted Assessment answers
```

Do not persist these as backend business state unless a specific business action submits them.

---

# Server State Tool

Use TanStack Query for backend/server state.

Configure a QueryClient at application-provider level.

Do not add Redux or Zustand for MVP unless a later concrete requirement justifies them.

Do not duplicate TanStack Query data into another global store.

---

# Queries

Use TanStack Query for appropriate read operations including:

```text
/auth/me
/dashboard
curriculum
lesson
progress
assessment
assessment history
conversations
messages
```

Use stable, feature-oriented query keys.

Do not encode business calculations inside query keys/cache logic.

---

# Mutations

Use mutations for operations such as:

```text
complete Pronunciation section
mark Vocabulary viewed
mark Grammar viewed
start Assessment Attempt
submit Assessment
create/rename/delete Conversation
send Message
retry AI Message
Admin content actions
```

Mutation result handling must respect backend-authoritative state.

---

# Session Bootstrap

On application startup, determine session using:

```http
GET /api/v1/auth/me
```

Use frontend session states equivalent to:

```text
UNKNOWN
AUTHENTICATED
UNAUTHENTICATED
```

While session is UNKNOWN, do not prematurely redirect protected routes.

Provide a lightweight session-loading state.

Do not read/decode JWT as the authoritative session source.

---

# Current User

Store/currently expose authenticated User using the `/auth/me` server-state query or equivalent session abstraction.

Do not store:

```text
Access Token
Refresh Token
```

in application state or localStorage.

---

# Protected Routes

Learner protected routes require an authenticated User.

Admin routes additionally require:

```text
role == ADMIN
```

Frontend route guards are UX/navigation controls only.

Backend authentication, authorization and ownership validation remain mandatory.

---

# 401 Handling

Central API/session handling must support:

```text
request
→ HTTP 401
→ attempt token refresh once
→ retry original request once
```

If refresh succeeds:

```text
continue request
```

If refresh fails:

```text
session → UNAUTHENTICATED
redirect to /login
```

Do not implement recursive/infinite refresh loops.

---

# Concurrent Refresh

When multiple requests simultaneously receive 401:

```text
allow only one refresh request to be in flight
```

Other requests should wait for/reuse the same refresh outcome.

Do not independently call `/auth/refresh` for every failed request.

---

# 403 Handling

Do not automatically log the User out on every HTTP 403.

Treat:

```text
401
```

as an authentication/session problem.

Treat:

```text
403
```

as an authenticated-but-forbidden/business-access result.

Use backend error codes to determine appropriate UI behavior.

---

# Error Classification

Distinguish:

```text
Validation Error
Business Error
Technical/API Error
Rendering Error
```

Examples of Business Errors:

```text
LESSON_LOCKED
ATTEMPT_ALREADY_SUBMITTED
AI_CHAT_DISABLED_DURING_TEST
```

Examples of Technical Errors:

```text
network failure
timeout
HTTP 5xx
backend unavailable
```

Do not treat all errors as one generic toast.

---

# ApiError

Continue using the normalized API error representation from Step 4.2:

```text
status
code
message
details
```

Use `code` for behavior.

Do not parse human-readable `message` strings to determine application logic.

---

# Loading States

Support separate UI concepts for:

## Page Loading

Used when primary screen data is unavailable.

Prefer appropriate skeleton/content loading.

## Section / Refetch Loading

Used when existing data remains visible while background refresh occurs.

Do not blank an entire page unnecessarily.

## Action Loading

Used for mutations/buttons.

Disable duplicate submission while an action is pending.

---

# Read Retry Policy

For GET/read queries:

```text
network error
HTTP 5xx
```

may automatically retry a small bounded number of times.

MVP recommendation:

```text
maximum 2 retries
```

Do not automatically retry ordinary:

```text
400
401
403
404
409
422
```

as generic transient failures.

Authentication refresh is handled separately.

---

# Mutation Retry Policy

Do not automatically retry side-effectful mutations by default.

Examples:

```text
submit Assessment
publish content
delete Conversation
```

On failure:

```text
preserve user state
show recoverable error
allow explicit retry
```

Idempotent operations such as theory-view marking may use limited network retry if useful.

Never implement infinite mutation retry.

---

# Error Presentation

Use context-appropriate presentation.

## Field Errors

Display near the related form field.

## Page/Section Load Errors

Display dedicated error state with retry where appropriate.

## Business Action Errors

Use inline feedback or toast based on context.

## Unexpected Rendering Failure

Use an application/layout-level React Error Boundary.

React Error Boundary does not replace HTTP/API error handling.

---

# Empty State vs Error State

Do not treat a successful empty result as an error.

Example:

```text
Conversation list = []
→ Conversation Empty State
```

versus:

```text
Conversation request failed
→ Error State
```

Use separate UI.

---

# Query Invalidation

After business mutations, invalidate only affected server-state queries.

Examples:

## Complete Pronunciation

Potentially invalidate:

```text
pronunciation
curriculum
dashboard
progress
```

## Mark Theory Viewed

Potentially invalidate:

```text
lesson
dashboard/progress when relevant
```

## Submit Assessment

Invalidate/refetch:

```text
assessment attempt/history
lesson
curriculum
dashboard
progress
```

Use actual dependencies rather than invalidating the entire application indiscriminately.

Do not manually reconstruct backend progression logic inside frontend cache updates.

---

# Assessment Submit

Expected UI flow:

```text
temporary answers
→ submit mutation
→ action pending
→ backend response
→ invalidate affected server state
→ navigate to Assessment Result
```

If submission fails:

```text
remain on current Assessment
preserve temporary answers
display error
```

Do not clear learner answers automatically.

---

# Unsaved Assessment State

Unsubmitted Assessment answers may remain frontend-only in V0.

Browser refresh may lose them.

Do not implement autosave/draft persistence in this step.

When learner navigates away with unsaved answers, provide a lightweight leave-warning where practical.

---

# Chat Technical Failure

If message submission returns an ambiguous technical/network failure:

```text
refetch Conversation/Message history
```

before assuming the USER Message was not persisted.

Do not automatically create another USER Message that may duplicate server state.

Render backend `FAILED` Assistant state when it exists.

---

# Browser Persistence

Do not persist the following to localStorage:

```text
authentication tokens
Lesson business state
Progress
Assessment score
Conversation history
Messages
```

Persistent product data must be recovered from FastAPI.

UI preferences may be persisted later if a concrete need appears.

---

# Page Reload

Expected reload flow:

```text
React application starts
→ session UNKNOWN
→ GET /auth/me
→ resolve User/session
→ queries refetch required server state
```

Persistent business state survives because it lives in the backend/database.

---

# Periodic Test / Chat Interaction

Do not rely solely on local frontend Assessment state to enforce AI Chat blocking.

Backend business errors remain authoritative.

When Periodic Test state changes, refresh/invalidate relevant Chat availability/server state as necessary.

---

# Suggested Structure

Equivalent organization:

```text
src/
├── app/
│   ├── providers/
│   │   └── QueryProvider
│   ├── router/
│   │   ├── ProtectedRoute
│   │   └── AdminRoute
│   └── error-boundary/
│
├── features/
│   └── auth/
│       └── session/
│
└── lib/
    └── api/
        └── client.ts
```

Exact filenames may differ.

Do not add unnecessary abstractions only to reproduce this tree.

---

# Tests

Add focused tests for at least:

- session UNKNOWN → AUTHENTICATED;
- session UNKNOWN → UNAUTHENTICATED;
- protected route behavior;
- Admin route behavior;
- initial loading state;
- query error state;
- GET retry behavior;
- GET non-retryable 4xx behavior;
- one refresh attempt on 401;
- original request retried once after successful refresh;
- failed refresh redirects to login;
- concurrent 401 requests share one refresh;
- 403 does not trigger generic logout;
- mutation action is disabled while pending;
- failed Assessment submission preserves temporary answers;
- successful Assessment submission invalidates relevant queries;
- empty Conversation state differs from loading failure;
- backend business error code drives correct UI state;
- Error Boundary renders fallback for rendering failures.

Mock backend/API behavior.

---

# Out of Scope

Do not implement:

- Redux;
- Zustand;
- offline-first application state;
- assessment autosave;
- browser-persisted business state;
- complex optimistic cache synchronization;
- distributed frontend event bus;
- advanced telemetry;
- production observability;
- AI/RAG implementation.

---

# Acceptance Criteria

- [ ] Server/local/form state are kept conceptually separate.
- [ ] TanStack Query manages server state.
- [ ] No unnecessary Redux/Zustand store exists.
- [ ] Session is reconstructed through `/auth/me`.
- [ ] Protected routes wait until session state is known.
- [ ] Auth tokens are not stored/read by frontend.
- [ ] 401 triggers at most one refresh and one request retry.
- [ ] Concurrent 401s do not create refresh storms.
- [ ] 403 does not automatically log out the User.
- [ ] Business and technical errors are differentiated.
- [ ] Loading states are scoped to page/section/action.
- [ ] Read retries are bounded.
- [ ] Side-effectful mutations do not automatically retry blindly.
- [ ] Query invalidation refreshes backend-authoritative state.
- [ ] Failed Assessment submission preserves temporary answers.
- [ ] Empty and error states are distinct.
- [ ] React rendering failures have an Error Boundary.
- [ ] Persistent product state remains backend-owned.

# Expected Deliverable

Frontend state/error foundation plus:

```text
docs/frontend/
└── step-4.5-frontend-state-error-handling.md
```

Next Phase:

**Phase 5 — Data Ingestion Pipeline**