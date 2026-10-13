# Step 4.2 — Backend API Integration

## Goal

Implement the frontend HTTP integration layer that connects the React application to the existing FastAPI backend.

This step must establish:

- central API client;
- environment-based backend URL;
- cookie-authenticated requests;
- feature-specific API functions;
- OpenAPI-generated TypeScript contracts;
- normalized backend errors.

Do not implement detailed loading/error/retry/session UX yet.

---

# Architecture

Preserve:

```text
React Feature
→ Feature API Function
→ Central API Client
→ HTTP/JSON
→ FastAPI
```

The frontend must never access PostgreSQL, vector storage or LLM providers directly.

---

# HTTP Client

Use native browser `fetch`.

Do not add Axios unless a later requirement clearly justifies it.

---

# API Base URL

Read backend base URL from:

```text
VITE_API_BASE_URL
```

Example development value:

```text
http://localhost:8000/api/v1
```

Do not hard-code backend URLs inside feature components or API modules.

Add an appropriate placeholder to frontend `.env.example`.

Do not expose backend secrets in frontend environment variables.

---

# Central API Client

Create a reusable API-client abstraction under an equivalent location:

```text
src/lib/api/client.ts
```

It should handle common concerns such as:

- base URL resolution;
- HTTP method;
- JSON request serialization;
- common headers;
- `credentials: "include"`;
- response parsing;
- empty response handling;
- normalized API errors.

Do not place product business rules inside the central API client.

---

# Authentication Cookies

Backend authentication uses HttpOnly cookies.

All appropriate API requests must support:

```ts
credentials: "include"
```

Frontend must not:

- read the JWT;
- store Access/Refresh Tokens in localStorage;
- decode JWT as authoritative User state;
- manually attach Bearer tokens.

Backend remains responsible for issuing, rotating and clearing authentication cookies.

---

# Current User

Provide an API function equivalent to:

```text
authApi.getMe()
```

calling:

```http
GET /api/v1/auth/me
```

Do not implement full session restoration/navigation behavior in this step.

That belongs to Step 4.5.

---

# Feature API Modules

Keep HTTP operations close to the feature that owns them.

Equivalent structure:

```text
features/auth/api.ts
features/curriculum/api.ts
features/lesson/api.ts
features/assessment/api.ts
features/progress/api.ts
features/conversation/api.ts
features/admin/api.ts
```

Do not create one application-wide API file containing all endpoints.

---

# Component Boundary

React components/pages must not construct raw backend URLs or duplicate fetch configuration.

Preferred:

```text
LessonPage
→ lessonApi.getLesson()
→ apiClient
```

Not:

```text
LessonPage
→ raw fetch backend URL
```

---

# OpenAPI Contracts

Use FastAPI's OpenAPI schema as the source for frontend request/response types.

Use:

```text
openapi-typescript
```

or an equivalent lightweight tool to generate TypeScript contracts.

Target generated file may be:

```text
src/types/api.generated.ts
```

Do not manually edit generated API type files.

If a generated contract is wrong:

```text
fix backend Pydantic/OpenAPI schema
→ regenerate
```

---

# Code Generation Scope

Generate types/contracts only.

Do not generate a full opaque frontend SDK.

Feature API functions should remain handwritten so application request flows stay explicit and understandable.

---

# Error Normalization

Backend error shape:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": null
  }
}
```

Normalize failed API calls into an application error object equivalent to:

```text
ApiError

status
code
message
details
```

Preserve backend machine-readable error codes.

Do not decide full UI error presentation in this step.

---

# Empty Responses

Do not assume all successful responses contain JSON.

Support success responses such as:

```text
204 No Content
```

without producing JSON parsing errors.

---

# Auth API

Provide functions corresponding to existing backend contracts:

```text
register
login
refresh
logout
logoutAll
getMe
requestPasswordReset
confirmPasswordReset
```

The API layer should expose application-friendly return types while preserving backend semantics.

---

# Learner APIs

Implement wrappers for existing backend operations.

## Curriculum

```text
getHskLevels
getCurriculum
```

## Dashboard

```text
getDashboard
```

## Pronunciation

```text
getSections
completeSection
```

## Lesson

```text
getLesson
markVocabularyViewed
markGrammarViewed
```

## Assessment

```text
getAssessment
startAttempt
submitAttempt
getAttempts
getAttempt
```

## Progress

Implement wrappers for the approved `/me/progress` endpoints.

## Conversation

Implement wrappers for the Conversation API approved in Step 3.6.

Do not implement UI behavior here.

---

# Admin APIs

Implement frontend wrappers only for Admin backend contracts that already exist.

At minimum this includes Lesson and Assessment management operations.

Do not invent backend APIs for future functionality.

---

# Document Screen

The frontend may already contain:

```text
/admin/documents
```

as a structural placeholder.

Do not implement fake Document upload/review endpoints during Step 4.2.

Document/Ingestion APIs belong to Phase 5.

---

# Business Logic Boundary

API modules may:

- send requests;
- map API parameters;
- return typed backend data.

They must not decide:

- lesson unlock;
- progress completion;
- assessment pass/fail;
- grading;
- HSK progression.

Use backend-returned authoritative state.

---

# Expected Structure

Equivalent target:

```text
src/
├── lib/
│   └── api/
│       ├── client.ts
│       └── errors.ts
│
├── types/
│   └── api.generated.ts
│
└── features/
    ├── auth/
    │   └── api.ts
    ├── curriculum/
    │   └── api.ts
    ├── lesson/
    │   └── api.ts
    ├── assessment/
    │   └── api.ts
    ├── progress/
    │   └── api.ts
    ├── conversation/
    │   └── api.ts
    └── admin/
        └── api.ts
```

Do not create unused boilerplate only to reproduce this tree exactly.

---

# Tests

Add focused tests for the integration layer where practical:

- base URL construction;
- credentials included;
- JSON response parsing;
- 204 response handling;
- backend error normalization;
- typed representative feature request;
- frontend API functions do not require raw auth token handling.

Mock HTTP responses.

Do not require real backend availability for every frontend unit test.

---

# Out of Scope

Do not implement yet:

- global server-state framework;
- session restoration;
- automatic navigation on 401;
- token-refresh retry orchestration;
- loading skeleton strategy;
- UI retry controls;
- detailed lesson UI;
- AI Chat interface behavior;
- streaming;
- Document ingestion API.

---

# Acceptance Criteria

- [ ] Frontend backend URL comes from `VITE_API_BASE_URL`.
- [ ] HTTP access uses a centralized client.
- [ ] Authenticated calls include cookies.
- [ ] Frontend does not read/store raw auth tokens.
- [ ] API calls are organized by feature.
- [ ] Components do not duplicate raw HTTP setup.
- [ ] FastAPI OpenAPI can generate TypeScript contracts.
- [ ] Generated API types are not manually maintained.
- [ ] Full SDK generation is not required.
- [ ] Backend error contract is normalized consistently.
- [ ] 204/empty responses are supported.
- [ ] Learner/Admin wrappers match existing backend API contracts.
- [ ] No nonexistent future APIs are invented.
- [ ] Business authority remains in FastAPI.

# Expected Deliverable

Frontend API integration foundation plus:

```text
docs/frontend/
└── step-4.2-backend-api-integration.md
```

Next Step:

**Step 4.3 — Learning UI**