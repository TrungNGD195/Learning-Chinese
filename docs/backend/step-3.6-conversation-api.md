# Step 3.6 — Conversation API

## Objective

Provide authenticated, persistent Lesson-scoped Conversations and Messages with private ownership, deterministic ordering, retryable Assistant attempts, and a replaceable AI boundary.

## Why

The backend needs durable chat history before Phase 4 can build its interface. User input and Assistant processing attempts must remain auditable when AI work fails or is retried.

## Mental Model

```text
Conversation = private Lesson-scoped thread
USER Message = durable learner input
ASSISTANT Message = one processing attempt for that input
```

Each send or retry follows two transactions:

```text
persist intent/history
→ commit
→ AIChatService processing
→ short finalization transaction
```

The USER Message and PENDING Assistant attempt are committed before AI processing. A failure changes that attempt to FAILED without erasing the learner's input. Retry creates another Assistant attempt linked to the same USER Message; it never rewrites history or duplicates the question.

## Core Knowledge

- Scope is LESSON only. `scope=LESSON` is derived in API responses; no scope column is stored.
- The authenticated database User owns each Conversation. Cross-user lookups are indistinguishable from missing resources.
- Soft deletion hides a Conversation while preserving its Messages.
- Lock one Conversation row to allocate deterministic per-thread sequence numbers and serialize sends, retries, and deletion.
- The database enforces unique `(conversation_id, sequence_number)` values.
- Message history selects newest pages and returns each page in ascending sequence order.
- An Assistant attempt points to the original USER Message with `reply_to_message_id`.
- Active Periodic-Test state is checked when Transaction A validates a send or retry. Later state changes do not cancel an already-committed turn.
- The AI boundary receives scalar request data only, never a database session or ORM object.

## Data Flow

```text
Conversation Router
→ ConversationService
→ ConversationRepository
→ AsyncSession / PostgreSQL
```

Cross-domain decisions remain with their owners:

```text
ConversationService → ProgressService.require_lesson_access()
ConversationService → ExerciseService.has_active_periodic_test()
ConversationService → AIChatService.generate_reply()
```

Transaction A locks the owned Conversation, checks soft-delete and Periodic-Test state, assigns sequence numbers, persists USER COMPLETED plus ASSISTANT PENDING, updates Conversation activity, and commits. AIChatService runs after that commit. Transaction B locks the pending Assistant row and finalizes it as COMPLETED or FAILED.

## Key Design Decisions

- D-019: LESSON-only API, strict create/rename contracts, privacy-preserving 404, soft-delete and bounded Conversation list.
- D-020: newest-window Message pagination with chronological order within each page.
- D-021: Conversation-row locking for sequence allocation and activity timestamps.
- D-022: only the latest FAILED Assistant attempt may be retried; retries serialize per Conversation.
- D-023: deterministic Phase-3 AI stub, typed processing failure, and safe 502 response after persisting FAILED.
- D-024: forward migration 0003 adds deletion, sequence and reply fields; historical sequences use `created_at, id` order and historical replies remain null.
- D-025: one canonical MessageResponse shape across history, send, and retry.
- D-026: committed state at Transaction-A validation decides whether work may start; later Periodic-Test or soft-delete changes do not cancel it.
- No real LLM, provider SDK, RAG, streaming, queue, or cross-domain User lock is introduced.

## Reusable Approach for Another Project

When a request needs slow external processing, persist the intent and a pending attempt in a short transaction, commit, call the external boundary with value data, then finalize in another short transaction. Preserve failed attempts and make retry create a new attempt tied to the same original input. Use a narrow row lock for the aggregate whose ordering must be deterministic.

## Common Mistakes

- Holding a database transaction open during network or model work.
- Deleting user input when downstream processing fails.
- Rewriting an old Assistant response during retry.
- Trusting client-supplied user, role, or Lesson identifiers on Message creation.
- Returning another User's resource existence through a distinct error.
- Using timestamps alone to order messages.
- Cancelling a committed turn because a later assessment or deletion changed state.

## Definition of Done

- Conversation APIs use the authenticated Step-3.5 User and preserve Step-3.4 Lesson access rules.
- Soft deletion, ownership privacy, bounded pagination, message states, reply links, retries, and Periodic-Test behavior follow D-019 through D-026.
- AI runs outside intentional database transactions and USER history survives processing failure.
- Migration 0003 is synchronized with ORM metadata and deterministically backfills historical messages.
- PostgreSQL concurrency/migration tests and Steps 3.1–3.5 regression tests pass.
- No real AI/RAG/provider implementation or Phase 4 work is present.

## Concepts Actually Used

| Concept | Category | Role |
|---|---|---|
| Conversation ownership | SYSTEM | Keeps Lesson chat private to the authenticated User. |
| Soft deletion | SYSTEM | Hides learner resources while preserving history. |
| Deterministic sequence allocation | SYSTEM | Gives messages stable order per Conversation. |
| Row-level locking | SYSTEM | Serializes mutations within one Conversation. |
| Message processing state machine | SYSTEM | Persists PENDING, COMPLETED, and FAILED Assistant attempts. |
| Reply relationship | SYSTEM | Links Assistant attempts to original USER input. |
| Two-transaction external-call pattern | SYSTEM | Keeps AI work outside database transactions while preserving intent. |
| Retry processing semantics | SYSTEM | Preserves attempt history without duplicating learner input. |
| Validation-time snapshot semantics | SYSTEM | Defines chat availability without global locks. |
| Stable newest-window pagination | SYSTEM | Supports loading older messages in bounded pages. |
| AIChatService boundary | AI | Provides a provider-neutral replacement seam with a deterministic stub. |
| Migration backfill | DE | Evolves historical message ordering safely. |

## Tools Actually Used

| Tool | Category |
|---|---|
| Python | SYSTEM |
| uv | SYSTEM |
| FastAPI | SYSTEM |
| Pydantic | SYSTEM |
| SQLAlchemy | SYSTEM |
| psycopg 3 | SYSTEM |
| PostgreSQL | DE |
| Alembic | DE |
| pytest | SYSTEM |
