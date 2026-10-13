# Step 4.2 — Backend API Integration

## Objective

Connect frontend feature modules to the accepted FastAPI HTTP API through one cookie-aware native-fetch client, generated OpenAPI contracts, typed handwritten feature wrappers, and a shared error shape.

## Why

Keeping HTTP configuration and parsing in one client prevents pages from building backend URLs or inventing transport behavior. Generating DTO contracts from FastAPI keeps the backend schema authoritative while feature wrappers make each operation explicit.

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

- An API client owns HTTP method, URL joining, scalar query serialization, JSON serialization/parsing, cookie credentials, and technical error normalization.
- `VITE_API_BASE_URL` is validated when the client is used, so structural pages render without backend configuration or availability.
- `credentials: 'include'` lets the browser send HttpOnly cookies. Frontend code does not read cookie values or handle raw access/refresh tokens.
- OpenAPI generated types define request and response DTOs; feature modules derive aliases from `paths` and do not copy backend object structures.
- Empty successful bodies return `undefined`; malformed success JSON becomes `INVALID_RESPONSE`; normalized backend errors retain their machine code; malformed HTTP errors use a safe `HTTP_ERROR`; pre-response fetch failures use `NETWORK_ERROR`.
- `api:check` fetches current OpenAPI, generates a temporary TypeScript artifact, compares it byte-for-byte with the committed contract, and removes its temporary directory without relying on Git.

## Data Flow

Future login UI values flow through `authApi.login` and `apiClient` to `POST /auth/login`. FastAPI sets HttpOnly cookies and returns its typed safe user profile.

When an accepted backend contract changes:

```text
FastAPI /openapi.json
→ npm run api:generate
→ updated src/types/api.generated.ts
→ TypeScript compiler surfaces wrapper mismatches
```

Normal `npm ci`, build, and tests use the committed generated contract and do not contact FastAPI or PostgreSQL.

## Key Design Decisions

- D-030: generate TypeScript contracts from the running accepted FastAPI `/openapi.json`; commit generated types but not `openapi.json`.
- D-031: one native-fetch JSON client uses `VITE_API_BASE_URL`, cookie credentials, scalar query parameters, and the canonical `ApiError` shape.
- D-032: Uvicorn is a backend development dependency used for local OpenAPI synchronization, not a production deployment choice.
- Feature API modules are handwritten and derive their request/response types from generated OpenAPI contracts.
- Runtime feature paths are relative to the API root, which already includes `/api/v1`.

## Reusable Approach

Add an operation to the owning feature’s API module, reference its generated OpenAPI path/method for request and response types, and delegate to `apiClient`. Keep page components independent of HTTP setup and leave business decisions with FastAPI.

## Common Mistakes

- Adding `/api/v1` to a runtime feature path and duplicating the prefix.
- Calling `fetch` from a component or feature API module.
- Reading, decoding, or storing JWTs in browser storage.
- Parsing JSON from an empty response body.
- Maintaining copied DTO interfaces instead of generated aliases.
- Forgetting to regenerate/check after an OpenAPI contract change.
- Moving progress, authorization, grading, curriculum, or Conversation rules into wrappers.

## Definition of Done

The live accepted FastAPI schema generates the checked-in TypeScript contract; `api:check` detects and verifies drift; all accepted Auth, learner, Conversation, and Admin operations have generated-type-backed wrappers; client and wrapper tests pass; clean npm install/build/tests pass without backend services.

## Concepts Actually Used

| Concept | Category | Step | Role |
|---|---|---|---|
| HTTP API client | SYSTEM | 4.2 | Centralizes frontend HTTP transport. |
| API contract | SYSTEM | 4.2 | Defines the frontend/backend interface. |
| OpenAPI | SYSTEM | 4.2 | Supplies the canonical machine-readable backend contract. |
| Type generation | SYSTEM | 4.2 | Creates TypeScript contracts from OpenAPI. |
| Generated-code ownership | SYSTEM | 4.2 | Keeps DTO authority with the backend schema. |
| Serialization / deserialization | SYSTEM | 4.2 | Converts request values and JSON responses. |
| Cookie-authenticated request | SYSTEM | 4.2 | Sends HttpOnly credentials without frontend token access. |
| Error normalization | SYSTEM | 4.2 | Provides a consistent transport/application error shape. |
| Feature API module | SYSTEM | 4.2 | Groups HTTP operations by feature ownership. |
| Environment configuration | SYSTEM | 4.2 | Separates API root from source code. |
| Contract drift checking | SYSTEM | 4.2 | Detects stale generated types against live OpenAPI. |

## Tools Actually Used

| Tool | Category | Step | Role |
|---|---|---|---|
| Node.js | SYSTEM | 4.2 | Frontend runtime and tooling. |
| npm | SYSTEM | 4.2 | Frontend dependency and script workflow. |
| TypeScript | SYSTEM | 4.2 | Typed API layer and generated contracts. |
| Vite | SYSTEM | 4.2 | Frontend environment and production build. |
| Native `fetch` | SYSTEM | 4.2 | Browser HTTP transport. |
| openapi-typescript | SYSTEM | 4.2 | Generates TypeScript contracts from OpenAPI. |
| Vitest | SYSTEM | 4.2 | API-layer and architecture tests. |
| uv | SYSTEM | 4.2 | Backend development dependency workflow. |
| Uvicorn | SYSTEM | 4.2 | Local FastAPI runner for contract synchronization. |
| FastAPI OpenAPI | SYSTEM | 4.2 | Canonical API contract source. |
