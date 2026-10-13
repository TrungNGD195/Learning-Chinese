# Step 3.1 — Backend Skeleton

## Objective

Create a small FastAPI application that starts without external services, reports process liveness, and establishes the backend's module ownership boundaries.

## Why

The first implementation step needs a runnable foundation while keeping database, configuration, authentication, AI, ingestion processing, and deployment work in their later approved steps.

## Mental Model

The backend is one modular monolith. Domain packages own their future responsibilities. HTTP routes adapt requests and responses; future business logic will follow `Router → Service → Repository → Database`.

## Core Knowledge

- FastAPI creates the ASGI application and exposes development OpenAPI documentation by default.
- `GET /health` is a process-liveness check and must not depend on downstream services.
- A reusable application exception and registered handler can normalize expected application failures without catching programming errors globally.
- `uv` manages the Python project and its development/test dependencies.

## Data Flow

For the current health endpoint, an HTTP request reaches the FastAPI application, the health handler returns `{"status": "ok"}`, and FastAPI serializes it as JSON with HTTP 200. No database or provider is consulted.

For an expected application failure, the exception handler returns the standard `error` object containing `code`, `message`, and `details`.

## Key Design Decisions

- Target Python `>=3.12,<3.13` and manage dependencies with `uv`.
- Keep only FastAPI as a runtime dependency; keep pytest and HTTPX in the development group.
- Keep `/health` outside the reserved future `/api/v1` business API prefix.
- Add package markers to make approved domain and AI submodule boundaries recognizable, without fake implementations or empty future layers.
- Do not add a root endpoint, server dependency, environment settings, or external-service integration.

## Approach Reusable in Another Project

Start with a runtime constraint and only current-step dependencies. Add one application entry point, one dependency-free liveness route, package markers for approved ownership boundaries, and focused tests. Add framework-wide error handling only for deliberate application errors and leave unexpected failures visible during development.

## Common Mistakes

- Making health checks depend on a database or provider that is not needed to verify process liveness.
- Adding future database, auth, AI, or deployment dependencies to an initial skeleton.
- Creating unused router/service/repository files across every domain.
- Catching all exceptions and converting bugs into ordinary client errors.
- Wrapping successful responses in a generic `data` envelope.

## Definition of Done

- The project targets Python `>=3.12,<3.13` and uses `uv`.
- The FastAPI app imports without secrets or external services.
- `GET /health` returns HTTP 200 and exactly `{"status": "ok"}`.
- Development OpenAPI is available.
- A focused test verifies the normalized application-error response.
- Approved backend module boundaries are recognizable without implementing future features.
- No Step 3.2 or later implementation is present.
