# Step 8.3 — Production Deployment & Provider Adapters

## Context
Production vendors were intentionally deferred. Architecture is same-site logically, PostgreSQL/pgvector-based, provider-neutral for storage/email/LLM boundaries, with local AI inference retained only if profiling supports it.

## Objective
Select/configure the minimum production services and deploy a production-shaped environment without changing application semantics.

## Current State
D-001 same-site is decided. D-002 concrete LLM provider/model is already selected by Phase 6. D-004/D-005 profiling evidence exists. D-006 vendor choices are now due.

## In Scope
Hosting topology, managed PostgreSQL+pgvector, persistent object storage adapter, email adapter, HTTPS/domain/routing, environment secrets, migration execution, AI runtime placement decision from benchmark evidence, external retrieval provider only if 6.8-B was approved/enabled.

## Out of Scope
Kubernetes, multi-region HA, microservices, autoscaling platform engineering beyond measured MVP need.

## Functional Requirements
Browser experiences one logical same-site frontend/API topology. Production data/storage survive app redeploy. Database migrations run safely. Password-reset email works through selected adapter. LLM/storage/email/external-provider keys are server-side only.

## Technical Requirements
Before implementation PM records chosen vendors, budget constraints and D-004 evidence outcome. Keep vendor-specific code behind existing adapters/config. Use HTTPS and secure-cookie production settings.

## Inputs / Outputs
Build artifacts + env/secrets + managed services → reachable production environment.

## Data Flow
Client → same-site web routing → frontend/API → managed DB/storage/provider boundaries.

## Interfaces / API / Schema
No public API redesign for vendor choice.

## Files / Components
Deployment manifests/config, provider adapters only where existing abstraction requires them, deployment docs/runbook.

## Config / Env
Production secret inventory documented; values stored in platform secret manager, never Git.

## Error Handling
Deployment/migration failure must not silently leave partially upgraded production. Provider configuration failures should surface via health/readiness/operator diagnostics without leaking secrets.

## Testing
Smoke test auth, DB, upload/storage, email reset, AI call, migrations and key product flows in production-shaped staging/preview before release.

## Acceptance Criteria
- [ ] Concrete production vendors/LLM/runtime decisions are recorded by PM.
- [ ] Same-site logical topology is preserved.
- [ ] Managed persistence survives redeploy.
- [ ] Migrations and secret handling are safe/reproducible.
- [ ] D-004 local-vs-hosted AI choice is evidence-based.
- [ ] No unnecessary service is added.

## Constraints / Non-goals
Vendor convenience must not override documented app/data/security invariants.

## Open Questions
Provider selection is a timed PM decision at this Step, not something Codex may invent.
