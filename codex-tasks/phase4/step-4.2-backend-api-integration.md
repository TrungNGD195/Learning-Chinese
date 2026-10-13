# Codex Execution Task — Step 4.2: Backend API Integration

## Execution Gate

This is the **single current Codex execution task** for:

**Step 4.2 — Backend API Integration**

Owner: **App Engineering Specialist**

Implement Step 4.2 only.

Do **not** begin Step 4.3 or any later Phase-4 feature/session/UI work.

Before editing, inspect the actual repository and the canonical PM Decision Log. The expected accepted state is:

- backend complete through Step 3.6;
- frontend complete through Step 4.1;
- no existing frontend API client or generated OpenAPI TypeScript contracts;
- backend currently has no Uvicorn dependency before this Step;
- D-030, D-031 and D-032 are DECIDED and authoritative.

If the execution checkout materially differs, if actual backend routes contradict the endpoint inventory in this task, or if the Decision Log conflicts with this task, stop and report `BLOCKED` instead of inventing a new contract.

The only permitted backend change in this Step is the D-032 development-tooling change to:

```text
backend/pyproject.toml
backend/uv.lock
```

Do not modify backend Python application code unless a separately discovered genuine backend defect is reported and approved through the normal PM process.

---

# 1. Objective

Create the frontend HTTP integration foundation connecting the accepted React application to the accepted FastAPI backend.

Establish:

- one central native-`fetch` API client;
- `VITE_API_BASE_URL` configuration;
- cookie-authenticated requests using `credentials: "include"`;
- one canonical frontend `ApiError` transport/application error shape;
- FastAPI OpenAPI → `openapi-typescript` generated TypeScript contracts;
- a committed `src/types/api.generated.ts` generated artifact;
- reproducible `api:generate` and `api:check` workflows;
- handwritten feature API modules covering all accepted Phase-3 endpoints required by Phase 4;
- focused unit tests using the existing Vitest/jsdom setup;
- the Step 4.2 documentation note.

Mental model:

```text
Page / feature logic
→ feature API function
→ apiClient
→ fetch
→ HTTP/JSON + HttpOnly cookies
→ FastAPI
```

The backend remains authoritative for business rules, identity, authorization, progress, grading, curriculum access, Conversation state and AI behavior.

---

# 2. Source of Truth

## Primary authoritative Step

Use:

```text
Spec-CURRENT/Phase4/Step 4.2 — Backend API Integration.md
```

If the execution checkout uses the bundled source-pack form, use the Step-4.2 section in:

```text
02_APP_ENGINEERING_SPECS_PHASE3-4.md
```

## Required control sources

Read before editing:

```text
Spec-CURRENT/PROJECT_CONTEXT.md
Spec-CURRENT/PM-Control/04-Decision-Log-and-Open-Gates.md
Spec-CURRENT/PM-Control/05-Codex-Execution-Protocol.md
```

The canonical Decision Log must contain and control this task through at least:

```text
D-027 — Phase 4 Frontend Runtime and Package Workflow
D-028 — Phase 4 Client-Side Routing Baseline
D-029 — Phase 4 Frontend Unit / Component Testing Baseline
D-030 — Step 4.2 OpenAPI Generation Workflow and Generated Contract Ownership
D-031 — Step 4.2 Central API Client and Technical Error Contract
D-032 — Local ASGI Runner for Development and OpenAPI Contract Sync
```

Also preserve applicable accepted backend decisions, especially:

```text
D-014 — HttpOnly browser cookie model
D-015/D-016 — auth HTTP/error contracts
D-019/D-020/D-025 — Conversation/Message public contracts
```

## Precedence

If sources differ:

1. canonical PM Decision Log;
2. authoritative Step 4.2 specification;
3. later accepted refinement intentionally changing an earlier contract;
4. accepted backend/frontend implementation and its OpenAPI contract;
5. earlier project/context notes;
6. this reviewed execution packet.

Do not silently resolve a material conflict.

---

# 3. Current Accepted Repository State

## Backend

The accepted backend is complete through Step 3.6 and conceptually contains:

```text
backend/
├── app/
│   ├── auth/
│   ├── curriculum/
│   ├── progress/
│   ├── exercise/
│   ├── conversation/
│   ├── admin/
│   └── main.py
├── pyproject.toml
└── uv.lock
```

Before Step 4.2, backend `pyproject.toml` has the accepted runtime dependencies and a `dev` dependency group containing pytest/httpx, but does not yet contain Uvicorn.

Do not alter backend routes, schemas, database models/migrations, authentication or business services.

## Frontend

The accepted Step-4.1 frontend already contains:

```text
frontend/
├── package.json
├── package-lock.json
├── vite.config.ts
├── src/
│   ├── app/
│   ├── features/
│   ├── test/
│   └── main.tsx
└── ...
```

It already uses:

```text
React
TypeScript
Vite
react-router Data Mode
Vitest
jsdom
React Testing Library
npm + package-lock.json
Node >=22.12
```

It intentionally has no API client, OpenAPI generated types, TanStack Query or session layer yet.

Preserve the accepted Step-4.1 routing/layout/page structure. Step 4.2 does not need to wire real API calls into those pages merely to prove the HTTP layer exists.

---

# 4. Mandatory Decision D-032 — Local Uvicorn Runner

Add exactly one backend development dependency:

```text
uvicorn
```

Update only:

```text
backend/pyproject.toml
backend/uv.lock
```

Add Uvicorn to the existing backend `dev` dependency group. Do not add `fastapi[standard]`, `fastapi-cli`, another server framework, or transient `uv run --with uvicorn` tooling.

Do not manually PM-freeze a Uvicorn patch version. The resolved lockfile is the reproducible version.

Canonical local command:

```text
cd backend
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Purpose only:

```text
local backend development
+
D-030 OpenAPI generation/check
```

This is not a production deployment decision.

Do not modify backend Python application code to support this runner.

---

# 5. Mandatory Decision D-030 — OpenAPI Type Generation

Canonical contract synchronization flow:

```text
running accepted FastAPI app
→ http://localhost:8000/openapi.json
→ openapi-typescript
→ frontend/src/types/api.generated.ts
```

FastAPI OpenAPI is the single API-contract authority.

## Frontend dependency

Add:

```text
openapi-typescript
```

as a frontend development/code-generation dependency.

Do not add a full SDK generator.

## Generated artifact ownership

Commit:

```text
frontend/src/types/api.generated.ts
```

Do not commit:

```text
openapi.json
```

`api.generated.ts` is generated code:

- never manually edit it;
- never patch incorrect DTOs locally;
- if it is wrong, fix the backend contract through the normal backend process and regenerate.

Feature API modules remain handwritten.

## Required package scripts

Add to `frontend/package.json`:

```text
api:generate
api:check
```

### `npm run api:generate`

Must obtain the current schema from:

```text
http://localhost:8000/openapi.json
```

and regenerate:

```text
src/types/api.generated.ts
```

using `openapi-typescript`.

Do not call `app.openapi()` or add a backend schema export script.

### `npm run api:check`

Must:

```text
GET http://localhost:8000/openapi.json
→ generate a temporary TypeScript output using openapi-typescript
→ compare file contents with committed src/types/api.generated.ts
→ exit non-zero if different
→ clean temporary output
```

Requirements:

- no Git command dependency;
- use portable Node/built-in filesystem comparison if a helper script is needed;
- do not rely on `.git` existing;
- do not rewrite the committed generated file during a successful check;
- temporary artifacts must not remain after normal completion.

A small frontend script such as:

```text
frontend/scripts/check-api-contract.mjs
```

is allowed if needed. Keep it narrowly focused on D-030.

## Normal frontend workflow independence

These must work using the committed generated file without a running FastAPI backend:

```text
npm ci
npm run build
npm run test -- --run
```

Only these explicit synchronization commands intentionally need the backend running:

```text
npm run api:generate
npm run api:check
```

---

# 6. Generated Type Usage Rules

Use `frontend/src/types/api.generated.ts` as the source for frontend request/response contract types.

Do not manually re-declare backend DTO object shapes that already exist in generated OpenAPI contracts.

Allowed examples:

```ts
import type { components, paths } from '../../types/api.generated'

type LoginRequest = components['schemas']['LoginRequest']
type UserProfile = components['schemas']['UserProfileResponse']
```

or operation/path-derived equivalents.

The exact aliasing style may stay local to each feature API module, but aliases must reference generated types rather than copying fields into new manual interfaces.

It is acceptable to define frontend-only transport helper types that are not backend DTOs, for example:

```text
ApiError
ApiRequestOptions
QueryValue
```

Do not use the generated OpenAPI default `HTTPValidationError` shape as the authoritative runtime application-error model. Runtime backend errors continue to use the accepted normalized error envelope and must flow through `ApiError` per D-031.

---

# 7. Mandatory Decision D-031 — Central API Client

Create an equivalent structure:

```text
frontend/src/lib/api/
├── client.ts
└── errors.ts
```

One narrow JSON-oriented central client owns common transport behavior.

Feature modules must not call `fetch` directly.

## 7.1 VITE_API_BASE_URL

Read the API root only from:

```text
VITE_API_BASE_URL
```

Create:

```text
frontend/.env.example
```

containing:

```text
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

No backend secret may appear in frontend env.

Normalize the configured value by:

```text
trim whitespace
→ remove trailing slash(es)
```

Accepted forms:

```text
absolute http(s) API root
example: http://localhost:8000/api/v1

same-origin root-relative API root
example: /api/v1
```

The configured V0 API root must include the accepted `/api/v1` API prefix.

Reject clearly rather than fallback when configuration is missing or invalid.

Do not provide a hidden localhost fallback in application code.

The client may validate lazily when first used or through a pure helper suitable for tests; either way, normal Step-4.1 page rendering should not require a backend server.

## 7.2 Runtime relative paths

Feature modules pass paths relative to the API root, for example:

```text
/auth/login
/me/dashboard
/conversations
/admin/lessons
```

They must not pass:

```text
/api/v1/auth/login
```

because `VITE_API_BASE_URL` already contains `/api/v1`.

Generated OpenAPI type lookup still uses full canonical OpenAPI paths such as:

```text
/api/v1/auth/login
```

Keep this distinction explicit.

A defensive central-client check rejecting an accidental runtime path beginning with `/api/v1` is allowed and encouraged, but do not invent another runtime prefix system.

## 7.3 Narrow request interface

The central client should expose only current needs, equivalent to:

```text
method
relative path
optional scalar query parameters
optional JSON body
```

Current query values need only support:

```text
string
number
boolean
null / undefined (omitted)
```

Do not add generic nested/array query serialization when accepted APIs do not need it.

Do not expose a generic `RequestInit` pass-through.

Do not add AbortSignal yet.

## 7.4 URL joining and query serialization

Join exactly once:

```text
normalized VITE_API_BASE_URL
+
relative feature path
```

Example:

```text
http://localhost:8000/api/v1
+
/auth/login
=
http://localhost:8000/api/v1/auth/login
```

Use standard URL/query encoding. Omit `null`/`undefined` query values.

Do not create double prefixes such as:

```text
/api/v1/api/v1/...
```

## 7.5 Request headers and authentication

Every `apiClient` request uses:

```ts
credentials: 'include'
```

This includes public-looking auth calls such as register/login because successful responses issue HttpOnly cookies.

Default header:

```text
Accept: application/json
```

Add:

```text
Content-Type: application/json
```

only when a JSON body is actually supplied.

Centralize JSON serialization in `apiClient`.

Feature modules must not:

- set `credentials` themselves;
- attach Bearer tokens;
- read cookies;
- parse/decode JWTs;
- store Access/Refresh Tokens.

## 7.6 Response body handling

Read the response body in a way that can distinguish zero-length bodies from non-empty malformed JSON.

### Successful empty response

Any successful HTTP response with a genuinely empty body returns:

```text
undefined
```

Feature wrappers for accepted empty-success endpoints expose:

```text
Promise<void>
```

This includes HTTP 204 and accepted empty HTTP 202 behavior.

### Successful JSON response

For a successful response with a non-empty body:

```text
parse JSON
→ return typed result
```

If the HTTP response is successful but the non-empty body cannot be parsed as JSON:

```text
throw ApiError
status  = actual success HTTP status
code    = INVALID_RESPONSE
message = safe generic invalid-response message
details = null
```

Do not expose raw malformed content.

Whitespace-only non-zero-length content should be treated as a non-empty malformed JSON response rather than silently converted to an empty response.

### HTTP error with accepted normalized envelope

When the parsed response matches:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": null
  }
}
```

throw canonical `ApiError` preserving:

```text
status  = actual HTTP status
code    = backend error.code
message = backend error.message
details = backend error.details
```

The envelope guard should require at least a usable string `code` and `message`; otherwise treat the HTTP failure as malformed/non-normalized.

### Malformed/non-JSON HTTP error

For an HTTP failure whose body is non-JSON or does not match the normalized backend error envelope:

```text
ApiError
status  = actual HTTP status
code    = HTTP_ERROR
message = safe generic HTTP failure message
details = null
```

Never expose raw HTML proxy content, stack traces or server exception text.

### Network failure

If `fetch` rejects before an HTTP response exists:

```text
ApiError
status  = null
code    = NETWORK_ERROR
message = "Network request failed"
details = null
```

Do not accidentally catch an `ApiError` created after an HTTP response and remap it to `NETWORK_ERROR`.

If response-body reading/parsing fails after a `Response` exists, map according to HTTP success/error semantics above, not as a pre-response network failure.

---

# 8. Canonical ApiError

Implement in an equivalent location:

```text
frontend/src/lib/api/errors.ts
```

Canonical shape:

```ts
ApiError {
  status: number | null
  code: string
  message: string
  details: unknown
}
```

It may extend JavaScript `Error`.

Required technical codes from D-031:

```text
NETWORK_ERROR
HTTP_ERROR
INVALID_RESPONSE
```

Backend machine-readable codes are preserved unchanged when the backend supplies a valid normalized application error.

This is not a UI presentation policy.

Do not add toast/message mapping, route navigation or retry decisions here.

Later frontend behavior must rely on `status` and `code`, not parse human-readable `message` text.

---

# 9. Feature API Module Boundary

Keep endpoint operations close to the owning feature.

Create only modules with actual Step-4.2 operations. Equivalent target:

```text
frontend/src/features/auth/api.ts
frontend/src/features/curriculum/api.ts
frontend/src/features/dashboard/api.ts
frontend/src/features/pronunciation/api.ts
frontend/src/features/lesson/api.ts
frontend/src/features/assessment/api.ts
frontend/src/features/progress/api.ts
frontend/src/features/conversation/api.ts
frontend/src/features/admin/api.ts
```

A slightly different grouping is acceptable only when it follows existing Step-4.1 feature ownership and still prevents one giant application-wide API file.

Do not create empty future API modules.

Each feature API module:

- accepts application parameters;
- maps path/query/body parameters;
- calls `apiClient`;
- returns generated-contract typed backend data;
- contains no business-rule decisions.

Components/pages do not need to call these modules yet.

---

# 10. Auth API Scope — All Accepted Step-3.5 Operations

Implement all nine accepted operations.

Runtime paths are relative to API root.

## 10.1 register

```text
POST /auth/register
```

Request/response types must come from generated contracts for canonical OpenAPI path:

```text
/api/v1/auth/register
```

Return safe User profile data.

## 10.2 login

```text
POST /auth/login
```

Return safe User profile data.

## 10.3 getMe

```text
GET /auth/me
```

Return safe User profile data.

Do not implement session restoration behavior here.

## 10.4 refresh

```text
POST /auth/refresh
→ Promise<void>
```

Do not implement automatic use of this endpoint.

## 10.5 logout

```text
POST /auth/logout
→ Promise<void>
```

## 10.6 logoutAll

```text
POST /auth/logout-all
→ Promise<void>
```

## 10.7 changePassword

```text
POST /auth/change-password
→ Promise<void>
```

This operation is required even though an earlier short Step-4.2 list omitted it. The accepted Step-3.5 backend exposes it and Step 4.6 depends on it.

## 10.8 requestPasswordReset

```text
POST /auth/password-reset/request
→ accepted empty HTTP 202
→ Promise<void>
```

## 10.9 confirmPasswordReset

```text
POST /auth/password-reset/confirm
→ Promise<void>
```

No Auth wrapper accepts or exposes raw Access/Refresh Token values.

---

# 11. Learner API Scope — Accepted Step-3.4 Operations

## 11.1 Curriculum

Equivalent functions:

```text
getHskLevels()
GET /hsk-levels

getCurriculum(hskId)
GET /hsk-levels/{hsk_id}/curriculum
```

## 11.2 Dashboard

```text
getDashboard()
GET /me/dashboard
```

## 11.3 Pronunciation

```text
getSections()
GET /pronunciation

completeSection(sectionId)
POST /pronunciation/{section_id}/complete
```

Use the actual generated response type. Do not invent a stronger response DTO than OpenAPI provides.

## 11.4 Lesson/theory

```text
getLesson(lessonId)
GET /lessons/{lesson_id}

markVocabularyViewed(lessonId, lessonVocabularyId)
POST /lessons/{lesson_id}/theory/vocabulary/{lesson_vocabulary_id}/view

markGrammarViewed(lessonId, lessonGrammarId)
POST /lessons/{lesson_id}/theory/grammar/{lesson_grammar_id}/view
```

Do not mark theory viewed automatically anywhere in Step 4.2; these are HTTP wrappers only.

## 11.5 Assessment / attempts / history

```text
getAssessment(assessmentId)
GET /assessments/{assessment_id}

startAttempt(assessmentId)
POST /assessments/{assessment_id}/attempts

submitAttempt(attemptId, body)
POST /assessment-attempts/{attempt_id}/submit

getAttempts(filters)
GET /me/assessment-attempts

getAttempt(attemptId)
GET /me/assessment-attempts/{attempt_id}
```

Supported `getAttempts` query parameters are exactly the accepted backend values:

```text
page
page_size
assessment_id
lesson_id
assessment_type
```

Do not add frontend grading or pass/fail logic.

## 11.6 Progress

```text
getProgressOverview()
GET /me/progress

getHskProgress(hskId)
GET /me/progress/hsk/{hsk_id}

getLessonProgress(lessonId)
GET /me/progress/lessons/{lesson_id}
```

Do not compute progress percentages or unlock state in API modules.

---

# 12. Conversation API Scope — Accepted Step-3.6 Operations

Implement every accepted public Conversation operation.

## Conversation lifecycle

```text
createConversation(body)
POST /conversations

listConversations(filters)
GET /me/conversations

getConversation(conversationId)
GET /conversations/{conversation_id}

renameConversation(conversationId, body)
PATCH /conversations/{conversation_id}

deleteConversation(conversationId)
DELETE /conversations/{conversation_id}
→ Promise<void>
```

`listConversations` supports only accepted filters:

```text
page
page_size
lesson_id
scope
```

`scope` remains only:

```text
LESSON
```

Do not create a GLOBAL-chat abstraction.

## Messages

```text
getMessages(conversationId, filters)
GET /conversations/{conversation_id}/messages

sendMessage(conversationId, body)
POST /conversations/{conversation_id}/messages

retryAssistantMessage(assistantMessageId)
POST /messages/{assistant_message_id}/retry
```

Message-history filters:

```text
page
page_size
```

Use generated canonical contracts for Conversation/Message responses. Do not create route-specific Message DTO copies.

Do not add streaming, SSE, WebSocket, cancellation or UI retry behavior.

---

# 13. Admin API Scope — Every Existing Step-3.4 Admin Endpoint

Use only accepted existing backend endpoints under `/admin`.

Do not implement any Document/Ingestion wrapper.

## 13.1 HSK management

```text
listHskLevels()
GET /admin/hsk-levels

updateHskLevel(hskId, body)
PATCH /admin/hsk-levels/{hsk_id}
```

## 13.2 Curriculum ordering

```text
getCurriculum(hskId)
GET /admin/hsk-levels/{hsk_id}/curriculum

replaceCurriculum(hskId, body)
PUT /admin/hsk-levels/{hsk_id}/curriculum
```

## 13.3 Lessons

```text
listLessons(filters)
GET /admin/lessons

createLesson(body)
POST /admin/lessons

updateLesson(lessonId, body)
PATCH /admin/lessons/{lesson_id}

publishLesson(lessonId)
POST /admin/lessons/{lesson_id}/publish

archiveLesson(lessonId)
POST /admin/lessons/{lesson_id}/archive
```

Accepted lesson-list query parameters:

```text
status
hsk_level_id
page
page_size
```

## 13.4 Lesson vocabulary

```text
listLessonVocabulary(lessonId)
GET /admin/lessons/{lesson_id}/vocabulary

attachLessonVocabulary(lessonId, body)
POST /admin/lessons/{lesson_id}/vocabulary

updateLessonVocabulary(lessonId, itemId, body)
PATCH /admin/lessons/{lesson_id}/vocabulary/{item_id}

detachLessonVocabulary(lessonId, itemId)
DELETE /admin/lessons/{lesson_id}/vocabulary/{item_id}
```

Return the actual generated endpoint response type. Do not assume DELETE means 204 when OpenAPI says otherwise.

## 13.5 Lesson grammar

```text
listLessonGrammar(lessonId)
GET /admin/lessons/{lesson_id}/grammar

attachLessonGrammar(lessonId, body)
POST /admin/lessons/{lesson_id}/grammar

updateLessonGrammar(lessonId, itemId, body)
PATCH /admin/lessons/{lesson_id}/grammar/{item_id}

detachLessonGrammar(lessonId, itemId)
DELETE /admin/lessons/{lesson_id}/grammar/{item_id}
```

## 13.6 Assessments

```text
listAssessments(filters)
GET /admin/assessments

createAssessment(body)
POST /admin/assessments

updateAssessment(assessmentId, body)
PATCH /admin/assessments/{assessment_id}
```

Accepted list filters:

```text
status
assessment_type
page
page_size
```

## 13.7 Questions

```text
listQuestions(assessmentId)
GET /admin/assessments/{assessment_id}/questions

createQuestion(assessmentId, body)
POST /admin/assessments/{assessment_id}/questions

updateQuestion(assessmentId, questionId, body)
PATCH /admin/assessments/{assessment_id}/questions/{question_id}

deleteQuestion(assessmentId, questionId)
DELETE /admin/assessments/{assessment_id}/questions/{question_id}
```

Use generated request/response semantics for DELETE.

## 13.8 Assessment lifecycle

```text
submitAssessmentReview(assessmentId)
POST /admin/assessments/{assessment_id}/submit-review

publishAssessment(assessmentId)
POST /admin/assessments/{assessment_id}/publish

archiveAssessment(assessmentId)
POST /admin/assessments/{assessment_id}/archive
```

## 13.9 Stats

```text
getStats()
GET /admin/stats
```

## Explicitly forbidden Admin wrappers

Do not create frontend APIs for:

```text
Documents
uploads
ingestion
chunks
embeddings
knowledge versions / activation
```

The existing `/admin/documents` Step-4.1 page remains structural only.

---

# 14. Component / API Boundary

Required direction:

```text
Page / feature logic
→ feature API function
→ apiClient
→ fetch
→ FastAPI
```

Components/pages must not:

- call `fetch` directly;
- read `VITE_API_BASE_URL` directly;
- construct backend URLs;
- set `credentials` independently;
- attach `Authorization: Bearer`;
- parse/decode JWTs;
- read authentication-cookie contents;
- store Access/Refresh Tokens in `localStorage` or `sessionStorage`;
- duplicate backend request/response DTOs;
- calculate lesson unlock, HSK progression, grading, progress completion or Conversation business state.

The feature API layer may map path/query parameters and return typed backend data. It must not become a business-service layer.

Do not add API calls to structural pages simply to exercise wrappers. Unit tests should exercise the integration layer directly.

---

# 15. Configuration / Environment

Create:

```text
frontend/.env.example
```

with exactly the public frontend configuration needed now, equivalent to:

```text
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

No frontend environment configuration may contain:

```text
SECRET_KEY
DATABASE_URL
JWT secret
Access Token
Refresh Token
LLM/provider key
backend credential
```

Do not commit an actual `.env` containing local secrets.

If useful, keep/extend the existing frontend `.gitignore` so local env files and temporary API-check output are not accidentally committed while `.env.example` remains trackable.

---

# 16. Testing Requirements

Use the accepted Step-4.1 test baseline:

```text
Vitest
jsdom
React Testing Library where UI rendering is relevant
```

For Step 4.2 HTTP-layer tests, no new HTTP mocking library is required. Prefer focused `fetch` stubs, for example:

```text
vi.stubGlobal('fetch', ...)
```

Reset global/env stubs between tests.

Frontend unit tests must not require FastAPI or PostgreSQL.

## 16.1 Central client tests

Cover at least:

1. absolute `VITE_API_BASE_URL` joining;
2. root-relative API root joining;
3. trailing-slash normalization;
4. missing config fails clearly;
5. invalid config fails clearly;
6. no double `/api/v1` runtime prefix;
7. every request has `credentials: "include"`;
8. every request has `Accept: application/json`;
9. `Content-Type: application/json` exists only with JSON body;
10. GET JSON success;
11. POST body JSON serialization;
12. scalar query serialization and omission of null/undefined;
13. 204 empty success returns `undefined`;
14. empty 202 success returns `undefined`;
15. another empty 2xx response returns `undefined`;
16. normalized backend error preserves status/code/message/details;
17. non-JSON HTTP error → `HTTP_ERROR`;
18. malformed JSON HTTP error → `HTTP_ERROR`;
19. JSON error with wrong envelope → `HTTP_ERROR`;
20. `fetch` rejection before response → `NETWORK_ERROR`, status null, exact network message;
21. non-empty malformed successful response → `INVALID_RESPONSE`;
22. raw malformed/error body is not exposed through `ApiError`.

Do not assert exact generic `HTTP_ERROR` / `INVALID_RESPONSE` human wording beyond being safe/stable unless the implementation intentionally publishes constants for them. The frozen exact network message is:

```text
Network request failed
```

## 16.2 Feature wrapper tests

Cover representative operations and the non-obvious required surface:

- `authApi.login` or equivalent sends correct relative path/body;
- `changePassword` exists and delegates centrally;
- one empty Auth wrapper returns void;
- one learner read wrapper;
- one learner mutation wrapper;
- assessment history maps `page`, `page_size`, `assessment_id`, `lesson_id`, `assessment_type` correctly;
- Conversation list maps `page`, `page_size`, `lesson_id`, `scope` correctly;
- Message history maps pagination correctly;
- one Conversation mutation;
- one Admin list wrapper with filters;
- one Admin mutation wrapper;
- one Admin lesson-content wrapper;
- no Document/Ingestion wrapper is present.

Do not duplicate central-client behavior tests exhaustively in every feature module.

## 16.3 Generated contract compile/type tests

Add a focused compile-time/Vitest type assertion or equivalent source-level check proving `api.generated.ts` exposes representative canonical OpenAPI paths from all major groups, including at least:

```text
/api/v1/auth/login
/api/v1/me/dashboard
/api/v1/assessments/{assessment_id}
/api/v1/conversations
/api/v1/conversations/{conversation_id}/messages
/api/v1/admin/lessons
/api/v1/admin/assessments/{assessment_id}/questions
```

Prefer TypeScript type references to generated `paths` rather than brittle large text snapshots.

## 16.4 Security/scope regression checks

Add focused checks or static assertions sufficient to catch accidental introduction of:

```text
Authorization: Bearer
localStorage token storage
sessionStorage token storage
manual JWT decode
raw fetch in feature modules/components
```

Do not build a complicated custom linter. A small architecture/static test is acceptable if it is simple and robust.

The central client itself is the only intended application source file calling browser `fetch` in Step 4.2. The D-030 generation/check script may perform its own contract-fetch/code-generation work as tooling and is outside the browser application transport boundary.

---

# 17. OpenAPI Contract Sync Verification

This is an explicit integration/tooling verification and intentionally requires the backend contract server.

Use the accepted backend environment conventions from Steps 3.2–3.6. Do not hard-code credentials or secrets into scripts.

## Terminal 1 — backend

```text
cd backend
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Confirm the accepted FastAPI application serves:

```text
http://localhost:8000/openapi.json
```

Do not use a substitute schema source.

## Terminal 2 — frontend

```text
cd frontend
npm ci
npm run api:generate
npm run api:check
npm run build
npm run test -- --run
```

Required behavior:

- `api:generate` succeeds against current accepted backend;
- generated artifact is committed output, not hand-authored;
- immediate `api:check` succeeds;
- normal build succeeds;
- normal tests succeed;
- build/tests do not make network calls to the backend;
- no `openapi.json` is committed.

If practical, verify `api:check` actually detects drift by temporarily changing/copying the generated file in a controlled test/manual check and restoring/regenerating it before handoff. Do not leave an intentionally stale file.

---

# 18. Expected Files / Components

Exact filenames may vary slightly to follow accepted Step-4.1 conventions, but the implementation should be equivalent to:

```text
backend/
├── pyproject.toml                 # add uvicorn dev dependency only
└── uv.lock                        # resolved lock update only

frontend/
├── .env.example
├── package.json                   # openapi-typescript + api scripts
├── package-lock.json
├── scripts/
│   └── check-api-contract.mjs     # if needed
└── src/
    ├── lib/
    │   └── api/
    │       ├── client.ts
    │       └── errors.ts
    ├── types/
    │   └── api.generated.ts
    └── features/
        ├── auth/api.ts
        ├── curriculum/api.ts
        ├── dashboard/api.ts
        ├── pronunciation/api.ts
        ├── lesson/api.ts
        ├── assessment/api.ts
        ├── progress/api.ts
        ├── conversation/api.ts
        └── admin/api.ts
```

Add focused tests adjacent to or under the existing frontend test convention.

Do not create empty speculative layers such as:

```text
query/
store/
services/
session/
interceptors/
retry/
rag/
ai-provider/
```

---

# 19. Scope / Guardrails

## In scope

- native browser `fetch` API client;
- generated OpenAPI TypeScript contracts;
- feature-specific handwritten API wrappers;
- normalized transport/backend errors;
- HttpOnly-cookie request transport;
- env-based backend API root;
- empty-success support;
- contract sync scripts;
- Uvicorn as backend dev dependency only;
- focused integration-layer tests;
- Step Note.

## Explicitly out of scope

Do not implement:

```text
TanStack Query
server-state cache
session restoration
protected-route behavior
role-aware route guards
automatic 401 handling
automatic refresh-token orchestration
request replay
navigation redirects
AbortSignal / cancellation semantics
generic RequestInit pass-through
global loading/error UI
UI retry controls
detailed Lesson UI
assessment UI behavior
AI Chat interaction UI
streaming
SSE
WebSocket
Document/Ingestion API or UI
Axios
runtime schema-validation framework
backend route/schema/business changes
production ASGI/deployment architecture
```

Do not refactor Step-4.1 pages/layouts without a direct Step-4.2 need.

---

# 20. Acceptance Criteria

Step 4.2 is implementation-complete only when all are true:

## Backend tooling

- [ ] `uvicorn` is added to backend dev dependencies.
- [ ] `backend/uv.lock` is updated reproducibly.
- [ ] No backend Python application file was changed for the runner.
- [ ] No backend route/schema/database/business/auth/Conversation behavior changed.

## OpenAPI contracts

- [ ] `openapi-typescript` is added to frontend code-generation/dev dependencies.
- [ ] `npm run api:generate` reads `http://localhost:8000/openapi.json` from a running accepted FastAPI app.
- [ ] `frontend/src/types/api.generated.ts` is committed/generated.
- [ ] No `openapi.json` is committed.
- [ ] Generated type file is not manually maintained.
- [ ] `npm run api:check` generates temporary output, compares file contents without Git, and detects drift.
- [ ] Normal frontend build/tests do not require backend availability.

## Central client

- [ ] `VITE_API_BASE_URL` is the only frontend backend-root configuration.
- [ ] `.env.example` contains the development API root placeholder only.
- [ ] Missing/invalid API root fails clearly without hidden fallback.
- [ ] Runtime feature paths are relative to `/api/v1` root and are joined once.
- [ ] Every request uses `credentials: "include"`.
- [ ] `Accept: application/json` is centralized.
- [ ] `Content-Type: application/json` is sent only with a JSON body.
- [ ] JSON serialization is centralized.
- [ ] successful empty responses return `undefined`.
- [ ] successful non-empty responses parse JSON.
- [ ] malformed successful response becomes `INVALID_RESPONSE`.
- [ ] normalized backend errors preserve status/code/message/details.
- [ ] malformed/non-JSON HTTP failures become `HTTP_ERROR`.
- [ ] pre-response fetch failures become `NETWORK_ERROR` with status `null`.

## Feature APIs

- [ ] all nine accepted Auth operations exist, including `changePassword`.
- [ ] all required learner curriculum/dashboard/pronunciation/lesson/assessment/progress wrappers exist.
- [ ] all eight accepted Step-3.6 Conversation/Message operations exist.
- [ ] all existing Step-3.4 Admin HSK/curriculum/lesson/content/assessment/question/lifecycle/stats operations have wrappers.
- [ ] no Document/Ingestion wrapper exists.
- [ ] wrapper request/response contracts derive from generated OpenAPI types rather than duplicated DTO shapes.

## Boundaries

- [ ] feature modules delegate to the central `apiClient`.
- [ ] components/pages do not call `fetch` or construct backend URLs.
- [ ] frontend does not read/decode/store JWT Access/Refresh Tokens.
- [ ] no `Authorization: Bearer` logic exists.
- [ ] backend business rules are not duplicated in frontend.
- [ ] TanStack Query/session/route-guard behavior was not introduced.

## Verification

- [ ] backend `uv sync` succeeds.
- [ ] canonical Uvicorn command serves the accepted FastAPI app at port 8000.
- [ ] `npm ci` succeeds.
- [ ] `npm run api:generate` succeeds.
- [ ] `npm run api:check` succeeds immediately after generation.
- [ ] `npm run build` succeeds without requiring backend network access.
- [ ] `npm run test -- --run` succeeds without requiring backend/PostgreSQL.
- [ ] Step-4.1 routing/layout tests remain passing.

---

# 21. Required Step Note

Create/update:

```text
docs/frontend/step-4.2-backend-api-integration.md
```

Keep it concise and reusable.

Include:

## Objective

What HTTP integration foundation Step 4.2 establishes.

## Why

Why components should not call FastAPI directly and why generated contracts matter.

## Mental Model

```text
React Feature
→ Feature API Function
→ apiClient
→ HTTP/JSON + cookies
→ FastAPI
```

Contract synchronization:

```text
FastAPI OpenAPI
→ openapi-typescript
→ generated TypeScript contracts
→ handwritten feature API wrappers
```

## Core Knowledge

Explain at least:

- HTTP request/response;
- API client abstraction;
- serialization/deserialization;
- HttpOnly cookie authentication from the frontend perspective;
- OpenAPI contract/type generation;
- normalized technical/application errors;
- generated-code ownership;
- environment configuration;
- contract drift checking.

## Data Flow

Use representative flows such as:

```text
login form value (future UI)
→ authApi.login
→ apiClient
→ POST /auth/login
→ backend sets HttpOnly cookies
→ typed User profile response
```

and:

```text
backend contract changes
→ FastAPI /openapi.json
→ api:generate
→ updated api.generated.ts
→ TypeScript compiler exposes downstream mismatches
```

## Key Design Decisions

Record D-030/D-031/D-032 impacts without rewriting the full PM Decision Log.

## Reusable approach

Explain how a future feature should add one API wrapper without bypassing the central transport boundary or duplicating backend DTOs.

## Common Mistakes

Include:

```text
double /api/v1 prefix
raw fetch in components
manual JWT handling
JSON parsing on empty responses
manually maintained duplicate DTOs
stale generated types
putting business logic into API wrappers
```

## Definition of Done

Reflect actual implemented/verified state.

## Concepts Discovered

Use only concepts actually implemented, with category `SYSTEM` unless a genuinely different category is justified.

## Tools Used

Include only tools actually used.

---

# 22. Concepts Expected

Likely concepts actually used:

| Concept | Category | Role |
|---|---|---|
| HTTP API client | SYSTEM | Centralizes browser HTTP transport |
| API contract | SYSTEM | Defines frontend/backend interface |
| OpenAPI | SYSTEM | Backend machine-readable contract |
| Type generation | SYSTEM | Produces TypeScript contracts from OpenAPI |
| Generated-code ownership | SYSTEM | Keeps backend as DTO authority |
| Serialization / deserialization | SYSTEM | Converts JS values and HTTP JSON |
| Cookie-authenticated request | SYSTEM | Sends HttpOnly credentials without token access |
| Error normalization | SYSTEM | Converts transport/backend failures into one frontend error shape |
| Feature API module | SYSTEM | Organizes HTTP calls by product ownership |
| Environment configuration | SYSTEM | Separates API root from source code |
| Contract drift checking | SYSTEM | Detects stale generated contracts |

Do not add DE/AI concepts merely because backend endpoints represent learning/AI domains; Step 4.2 itself is a SYSTEM integration Step.

---

# 23. Tools Expected

Only tools actually used should be documented after implementation.

Expected:

| Tool | Category | Role |
|---|---|---|
| Node.js | SYSTEM | Frontend runtime/tooling |
| npm | SYSTEM | Frontend dependency/scripts workflow |
| TypeScript | SYSTEM | Typed API layer |
| Vite | SYSTEM | Frontend env/build |
| native fetch | SYSTEM | Browser HTTP transport |
| openapi-typescript | SYSTEM | OpenAPI → TypeScript generation |
| Vitest | SYSTEM | API-layer unit tests |
| uv | SYSTEM | Backend dev dependency workflow |
| Uvicorn | SYSTEM | Local FastAPI ASGI runner for contract sync |
| FastAPI OpenAPI | SYSTEM | Canonical HTTP contract source |

Do not list TanStack Query because it is not used in this Step.

---

# 24. Implementation Review Checklist Before Handoff

Before reporting DONE, inspect the implementation rather than relying only on passing tests.

Confirm:

1. no application `fetch` calls outside central client;
2. no Bearer/JWT/localStorage/sessionStorage auth handling;
3. no `/api/v1` duplicated inside runtime feature paths;
4. no manually copied request/response DTO structures when generated contracts exist;
5. no committed `openapi.json`;
6. generated file actually comes from current live accepted backend;
7. `api:check` is Git-independent;
8. normal frontend tests/build do not contact backend;
9. all wrapper groups are complete;
10. no Document/Ingestion API exists;
11. no TanStack Query/session/route guards were added;
12. backend diff is limited to Uvicorn dev dependency metadata.

If any required endpoint is absent from current OpenAPI although accepted backend code/spec says it should exist, stop and report a backend contract defect rather than inventing a frontend endpoint.

---

# 25. Completion Report Required From Codex

Return a structured handoff containing:

```text
Step
Status
Implementation plan executed
Files created
Files modified
Dependencies added/removed
Backend tooling change
OpenAPI generation/check implementation
Generated contract path
Central apiClient behavior
ApiError behavior
Auth wrappers implemented
Learner wrappers implemented
Conversation wrappers implemented
Admin wrappers implemented
Config/env changes
Tests added
Verification commands/results
Acceptance criteria
Step Note
Concepts actually used
Tools actually used
Deviations from specification
Problems / risks
Decisions needed
Recommended next action
```

Also report:

- exact `node --version` and `npm --version`;
- whether `backend/pyproject.toml` and `backend/uv.lock` were the only backend files changed;
- whether `api.generated.ts` changed only through generation;
- output of `npm run api:check`;
- total frontend test count;
- confirmation that no backend/PostgreSQL service was required for normal frontend build/unit tests;
- confirmation that Step 4.3+ work was not started.

Do not claim PM acceptance.

---

# 26. Final Non-Goals Reminder

Step 4.2 ends at the HTTP integration boundary.

Do not continue into:

```text
Step 4.3 learner UI data wiring
Step 4.4 Conversation interaction UI
Step 4.5 server-state/session infrastructure
Step 4.6 auth/profile UX
Step 4.7 Admin UI behavior
Phase 5 Documents/Ingestion
Phase 6 real AI/RAG
```

Expected next workflow after implementation:

```text
Codex implementation
→ App Engineering Specialist independent review
→ PM acceptance
→ next JIT Step review
```
