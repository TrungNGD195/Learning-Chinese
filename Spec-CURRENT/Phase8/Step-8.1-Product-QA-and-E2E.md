# Step 8.1 — Product QA & End-to-End Verification

## Context
All MVP application/data/AI capabilities should now exist. Before deployment work, verify the product journeys and cross-component invariants as one system.

## Objective
Build/execute an end-to-end QA suite and release checklist covering critical learner/admin flows and failure semantics.

## Current State
Phases 3–7 are feature-complete; official evaluation gates are available.

## In Scope
Learner auth/pronunciation/progression/lesson/assessment/history/profile; Lesson RAG chat; Admin content/document/generation/stats; authorization; critical failure states; browser/API integration.

## Out of Scope
Production vendor setup, load testing at massive scale, mobile native apps.

## Functional Requirements
Define critical E2E paths and launch-blocking invariants. Include at least: new learner → pronunciation → Lesson → theory → exercise → unlock; periodic-test gate; AI chat normal/refusal/failure; Admin content lifecycle; document approval path; AI-generated draft review; learner/admin isolation.

## Technical Requirements
Prefer deterministic seeded data and mock only true external boundaries where required. E2E tests must not depend on random production Internet content.

## Inputs / Outputs
Input: built app + test DB/fixtures. Output: pass/fail report mapped to critical product criteria.

## Data Flow
Browser → Frontend → API → DB/AI test boundaries → asserted persisted/business state.

## Interfaces / API / Schema
No new product API solely for tests.

## Files / Components
E2E test directory following selected test framework/repo conventions; release checklist under docs/qa.

## Config / Env
Isolated test environment/database; test secrets only through environment/CI secret store.

## Error Handling
Test expected negative paths explicitly; a technical failure must not be asserted as successful no-evidence behavior.

## Testing
This Step is itself the system test. Preserve smaller unit/integration suites.

## Acceptance Criteria
- [x] Critical learner journey passes.
- [x] Critical Admin journey passes.
- [x] Authorization boundaries pass.
- [x] RAG/grading/generation failure semantics pass.
- [x] Document and AI-generated content never bypass approval.
- [x] Launch-blocking failures have reproducible evidence.

## Constraints / Non-goals
Do not rewrite application architecture to fit E2E tooling.

## Open Questions
None blocking Step 8.1.

## PM Reconciliation — Final Step 8.1 Gate (2026-10-13)

Status: **DONE — DETERMINISTIC PRODUCT QA PASSED**

Step 8.1 QA harness/evidence implementation is PM accepted.

Previously identified launch blockers are resolved:

- B1 Pronunciation completion journey: PASS.
- B4 Admin curriculum-membership workflow: PASS.
- Step 7.7 PostgreSQL regression exposed during full regression: fixed and PM accepted.

Final deterministic verification evidence includes:

- critical learner journey: PASS;
- critical Admin journey: PASS;
- authorization boundaries: PASS;
- RAG / grading / generation failure semantics: PASS;
- document and AI-generated content approval boundaries: PASS;
- B1/B4 Playwright reruns: PASS;
- full backend/frontend regression evidence: PASS with documented independent-review environment limitations;
- build / lint / `api:check`: PASS according to accepted implementation evidence.

No API, schema, migration, progression-semantic, AI/RAG, or architecture redesign was required.

Step 7.4 official runtime/human evaluation, Step 7.5 official E2E AI evaluation,
Step 7.7 official grading/generation evaluation, and Step 7.6 official regression
comparison remain `DEFERRED_EVALUATION_GATE`.

Important boundary:

**Step 8.1 DONE ≠ PRODUCT RELEASE READY.**

Deferred official Phase-7 runtime/human evaluation gates must not be represented as passed.

Next roadmap Step after PM reconciliation:

**Step 8.2 — Containerized Development & CI**
