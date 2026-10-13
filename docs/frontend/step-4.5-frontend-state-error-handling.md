# Step 4.5 — Frontend State & Error Handling

## Objective and mental model

Use TanStack Query for backend-owned state, React component state for transient UI choices, and local form state for unsaved answers and drafts. PostgreSQL/API responses remain authoritative; Query caches responses in memory and refreshes them after mutations. The cache is not persisted to browser storage.

```text
API response → Query cache → view
local UI choice → component state
unsaved input → form state
```

Current-user identity comes only from `GET /auth/me`. The frontend does not decode JWTs or read authentication cookies. Backend-managed HttpOnly cookies stay outside JavaScript.

## Query behavior

The application owns one `QueryClient` and one `QueryClientProvider`. Query keys are feature-oriented: `auth.me`, `dashboard`, `curriculum.levels` / `curriculum.hsk(id)`, `lesson.detail(id)` / `lesson.progress(id)`, `assessment.detail(id)`, `attempt.detail(id)`, `progress.overview` / `progress.hsk(id)`, and conversations/messages by Lesson or Conversation.

Reads retry at most twice only when the final canonical `ApiError` is `NETWORK_ERROR` or has HTTP status 500 or higher. This includes technical errors returned after an Auth recovery attempt; each Query retry starts a new `apiClient` invocation with its own bounded Refresh/replay. Other `ApiError` values and unexpected failures do not retry. Mutations default to `retry: false`. Query data is memory-only and uses normal TanStack freshness defaults.

Lesson detail must resolve before the first Lesson Progress read because the backend Lesson GET converges Lesson start state. Vocabulary/Grammar views invalidate backend progress and affected overview/curriculum resources; they do not calculate completion locally. Assessment submission invalidates only the attempt, dashboard, progress and curriculum resources that may have changed.

## Session and HTTP recovery

`apiClient` owns the single low-level request/parser path. On an eligible 401 it sends one low-level `POST /auth/refresh`; simultaneous 401s await the same Promise. On success, each original JSON request is rebuilt from its typed options and replayed once. Refresh and replay do not recurse. Login, registration, reset, refresh and logout paths are excluded from automatic refresh.

`auth.me` has three effective states: UNKNOWN while pending or after a technical verification failure, AUTHENTICATED when `/auth/me` returns a User, and UNAUTHENTICATED after definitive session rejection. A network/5xx refresh failure leaves a cached User intact and never fakes logout. `ACCOUNT_DISABLED` invalidates the session; ordinary authorization/business 403 responses do not. Session invalidation sets `auth.me` to null and removes user-specific Query entries so data from the prior session cannot reappear.

Learner and Admin routes wait while the session is UNKNOWN, redirect unauthenticated users to `/login`, and render protected content only after `/auth/me` succeeds. Authenticated non-admin users see a small Access denied page with a Dashboard link. Backend authorization remains authoritative. Unexpected render failures reach the React Router root boundary; ordinary API/query failures stay in their feature’s loading/error UI.

## Assessment drafts and navigation

Assessment details and results are Queries. The active Attempt ID, current question, answers and submission-navigation allowance remain local. The explicit Start action and submission are non-retried mutations. A dirty active Attempt blocks in-app navigation and sets `beforeunload`; Stay resets the blocker and Leave proceeds. Successful GRADED and accepted `AI_GRADING_UNAVAILABLE` terminal navigation bypasses the warning. No autosave or browser persistence is used.

## Conversation behavior

Conversation and Message pages use `useInfiniteQuery` only for the existing manual Load more / Load older buttons. Pages are flattened in backend order, Conversations deduplicated by ID, and Messages deduplicated then sorted by `sequence_number`. Selection, Composer/rename drafts, blocked actions and scroll restoration remain local. Send/retry cache updates use only backend-returned records; no fake Message IDs, polling or streaming is introduced.

`AI_RESPONSE_FAILED` means the backend persisted the USER Message and failed Assistant, so the UI refetches history and never resends that USER Message. An ambiguous technical Send failure preserves the exact draft, automatically refetches history, and gates another Send behind Edit draft or Send again. Send again is an explicit user action that submits the preserved text once. An ambiguous Assistant Retry refetches history and never automatically retries the Assistant.

## Common mistakes

- Treating every 403 as a logout or redirect.
- Letting a technical Refresh failure erase a cached User.
- Retrying mutations or re-sending an ambiguous Chat request automatically.
- Duplicating Query server data in long-lived component state.
- Calculating progression/completion from UI events instead of refetching backend truth.
- Persisting Query/session/business data in localStorage or sessionStorage.
- Replacing bounded Chat pagination with automatic scrolling, polling or streaming.

## Definition of Done

- One Query provider, exact bounded read retry and mutation retry policies.
- Central single-flight Refresh/replay and `/auth/me` session authority.
- Protected/Admin route behavior, local feature errors and a root route error boundary.
- Actual server reads moved to Query with bounded, feature-scoped invalidation.
- Assessment leave warning and D-042 uncertain-send recovery covered by tests.
- Existing Step 4.3/4.4 UI behavior and generated API contract remain intact.
- Build, frontend tests and lint pass; no browser-persisted Query cache or tokens.

## Concepts and tools used

| Concept | Category | Use |
|---|---|---|
| Server state | SYSTEM | Backend-originated resources managed through Query |
| Local UI state | SYSTEM | Transient selection, expansion and interaction state |
| Form / temporary state | SYSTEM | Unsaved answers and Chat drafts |
| Query cache | SYSTEM | In-memory cache of backend responses |
| Query invalidation | SYSTEM | Refresh affected backend truth after mutations |
| Session bootstrap | SYSTEM | `/auth/me` resolves the current browser session |
| Authentication vs authorization | SYSTEM | Distinguish session rejection from ordinary 403 |
| Single-flight | SYSTEM | Share one Refresh between concurrent requests |
| Bounded retry | SYSTEM | Retry transient reads no more than twice |
| Mutation retry safety | SYSTEM | Prevent duplicate side effects |
| Error classification | SYSTEM | Separate business, technical and rendering failures |
| Error Boundary | SYSTEM | Recover from unexpected render/route failures |
| Backend-authoritative state | SYSTEM | Query refreshes truth; UI does not compute business outcomes |

| Tool | Category | Use |
|---|---|---|
| `@tanstack/react-query` | SYSTEM | Server-state cache, queries and mutations |
| React | SYSTEM | Local and form state |
| React Router | SYSTEM | Route guards, leave blocking and error boundary |
| TypeScript | SYSTEM | Typed query/session boundaries |
| Step-4.2 `apiClient` / `ApiError` | SYSTEM | HTTP, auth recovery and error classification |
| Vitest | SYSTEM | Retry, transport and state tests |
| React Testing Library | SYSTEM | Route and UI behavior tests |
