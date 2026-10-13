# Ownership and Execution Waves

## Specialist Roles

### PM & Project Control

Owns roadmap, architecture consistency, scope, decision log, implementation gate, cross-chat conflict resolution, and final acceptance of each Step.

### Data Engineering Specialist

Primary ownership:

```text
Phase 2 data model review/support
Phase 5 ingestion/transformation/chunking/versioning
Data-side support for vector readiness and migrations
```

### AI Engineering Specialist

Primary ownership:

```text
Phase 6 embedding/retrieval/reranking/prompt/LLM/RAG
free-form grading
AI assessment generation
AI-side support for Phase 7 evaluation
```

### App Engineering Specialist

Primary ownership:

```text
Phase 3 backend/business/auth/conversation APIs
Phase 4 frontend
App-side admin/document/AI UI integration
```

### DevOps & QA Specialist

Primary ownership:

```text
Phase 7 evaluation orchestration/regression quality gates
Phase 8 E2E/CI/deployment/security/backup/observability/release
```

## Rule for Consulted Roles

Only one specialist chat owns a Step. A consulted specialist may review interfaces or risks but must not independently redesign the Step.

## Execution Waves

### Wave 0 — PM Freeze

Inputs:

- reviewed spec set;
- PM decision log;
- current repository state.

Outputs:

- selected first executable Step;
- Codex task packet;
- no unresolved blocker for that Step.

### Wave 1 — Application Foundation

Suggested order:

```text
3.1 Backend Skeleton
→ 3.2 Configuration
→ 3.3 Database Access/Migrations
→ 3.4 Business APIs
→ 3.5 Authentication/User Context
→ 3.6 Conversation API
```

Owner: App Engineering, with Data review for schema/migration implications.

PM must verify schema implementation against Phase 2 before accepting 3.3/3.4.

### Wave 2 — Frontend Core

```text
4.1 Frontend Structure
→ 4.2 API Integration
→ 4.5 State/Error foundation
→ 4.6 Auth/Profile
→ 4.3 Learning UI
→ 4.4 AI Chat shell/integration boundary
→ 4.7 Admin Core UI
```

Owner: App Engineering.

Where backend AI is not implemented yet, UI may use only the mocks/contracts explicitly allowed by the Step; do not fake production behavior silently.

### Wave 3 — Data Ingestion

```text
5.1 Sources
→ 5.2 Raw ingestion
→ 5.3 Parsing/Cleaning
→ 5.4 Transformation
→ 5.5 Chunking
→ 5.6 Pipeline orchestration
→ 5.7 Incremental/Reprocessing
→ 5.8 Document Admin UI
```

Owner: Data Engineering; Step 5.8 owned by App Engineering with Data consulted.

The synchronous-vs-worker gate is re-evaluated after representative file profiling, not before evidence exists.

### Wave 4 — AI/RAG + Evidence Calibration Checkpoint

```text
6.1 Embeddings
→ 6.2 Vector Storage + knowledge-build activation
→ 6.3 Retrieval
→ 6.4 Filtering
→ 6.5 Reranking/evidence score
→ 6.6 Prompt/context
→ 6.7 LLM generation
→ 6.9 Conversation memory
→ 6.10 Citations
→ 6.8-A Internal End-to-End RAG bootstrap / score collection
→ 7.1 Evaluation dimensions
→ 7.2 Evaluation dataset
→ 7.3 Retrieval evaluation + calibrate RAG_MIN_RERANK_SCORE
→ PM records calibrated runtime threshold
→ close 6.8-A normal-runtime evidence gate
→ 6.8-B Trusted external fallback (only after provider/allowlist decision)
→ 6.11 Free-form AI grading
→ 6.12 Admin AI assessment generation
→ 6.13 AI feature UI integration
```

Owner: AI Engineering for Phase 6; DevOps & QA owns Steps 7.1–7.3 with AI consulted; Step 6.13 is App Engineering.

The calibration checkpoint is intentional: Codex must not invent `RAG_MIN_RERANK_SCORE`. Concrete LLM provider/model must be resolved before Step 6.7; external provider/domain allowlist only before 6.8-B.

### Wave 5 — Remaining Evaluation & Regression

After the calibration checkpoint above:

```text
7.4 Generation eval
→ 7.5 End-to-End RAG eval
→ 7.7 Grading/generation eval
→ 7.6 Regression gate
```

Owner: DevOps & QA, AI Engineering consulted.

Minimum official dataset gate is 60 approved cases; 120 is the portfolio target.

### Wave 6 — Production Readiness

```text
8.1 Product QA/E2E
→ 8.2 Containerized dev/CI
→ 8.3 Production deployment/adapters
→ 8.4 Security/backup/observability/release
```

Owner: DevOps & QA with PM/provider decisions.

## Parallelism Policy

Safe parallelism is allowed only when contracts are already frozen. Examples:

```text
Frontend screen implementation ↔ backend implementation
only after the OpenAPI contract is frozen.

AI evaluator scaffolding ↔ RAG implementation
only after trace/result schemas are frozen.
```

Do not parallelize two tasks that both modify the same schema, lifecycle, or public API contract without PM coordination.
