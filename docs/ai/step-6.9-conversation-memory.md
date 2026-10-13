# Step 6.9 — Conversation Memory

## Objective

Add bounded, short-term memory from completed turns in the current conversation. Memory improves continuity while current retrieved lesson evidence remains the authority for factual claims.

## Why

The learner should not need to repeat a recent question or preference. Historical answers are not retrieval evidence, and they must not displace current evidence or leak across conversations.

## Mental Model

```text
same Conversation
  → prior completed USER + its one completed ASSISTANT reply
  → bounded, whole-turn optional memory
  → current evidence and current question remain separate
```

Memory is context, not evidence. Only message text is sent to the model. IDs, sequences, and usage metadata stay in application code.

## Core Knowledge

- A memory unit is one completed USER message and the single completed ASSISTANT message linked by `reply_to_message_id`.
- Only messages in the same conversation and before the current USER sequence are eligible. Failed and pending attempts are excluded.
- The bounded query uses the existing `(conversation_id, sequence_number)` uniqueness and `reply_to_message_id` index. No schema or migration change is needed.
- `RAG_MEMORY_MAX_TURNS` defaults to 3, accepts only integer values 0 through 3, and 0 skips the history query.
- Historical assistant citation labels matching `[S1]`, `[S2]`, and so on are removed from memory text only. Persisted messages and user text are untouched.
- Local packing counts complete turns and drops the oldest selected turn until the budget fits. It never truncates a message.
- D-084 preserves the current system policy, lesson context, evidence, and query. If the exact provider count overflows with memory, the provider removes all memory and performs one final count before generation.
- Empty memory is a valid result. Database, integrity, or token-count failures remain technical failures and are not disguised as empty history.

## Data Flow

```text
current PromptPackage
  → derive remaining memory token budget
  → query at most max_turns + 1 completed pairs
  → validate and sanitize bounded rows
  → select recent whole turns and pack locally
  → attach immutable ConversationMemory
  → serialize historical USER/ASSISTANT roles
  → exact provider preflight
  → if needed, retry preflight with zero memory
  → generate with the same role-aware input that passed preflight
```

Retrieval continues to use only the current normalized query. Step 6.9 exposes the composition seam for a later caller; it does not add retrieval orchestration.

## Key Design Decisions

- Memory is conversation-local and bounded; no global history or cross-conversation lookup exists.
- The repository query joins by the persisted reply relationship, sorts by sequence descending, and applies `max_turns + 1` as its SQL limit.
- Duplicate completed replies and impossible sequence or conversation relationships fail closed.
- `PromptPackage` and memory DTOs are immutable. Memory does not enter evidence blocks, source labels, or the source map.
- The provider owns SDK-shaped messages and uses the same role-aware input for exact token preflight and generation.
- D-084 fallback is per logical generation attempt. A transient retry starts again with memory; one operation can make at most four exact preflight calls.
- Logs contain counts, safe IDs, state, and error codes, never message text, evidence, full provider input, or generated answers.

## Reusable Approach

For a future composition caller, derive the residual budget from the already-built package, invoke `ConversationMemoryBuilder` with the current conversation and USER sequence, and attach the result with `with_conversation_memory`. This keeps DB reads before provider calls and leaves the current evidence package unchanged.

## Common Mistakes

- Loading full message history or data from another conversation.
- Treating a failed retry as a completed turn, or selecting an arbitrary winner when duplicate completed replies exist.
- Including the current USER message a second time in historical roles.
- Turning `[S#]` markers in memory into current evidence citations.
- Truncating a long turn or sacrificing current evidence to preserve memory.
- Treating a failed repository/token operation as valid empty memory.
- Reusing a zero-memory fallback across a new transient attempt instead of starting fresh.

## Definition of Done

- Settings reject booleans and values outside 0–3 while allowing environment string integers.
- Bounded query and memory builder tests cover scope, current-message exclusion, completed-pair eligibility, retry relationships, sanitation, packing, and technical failures.
- Serialization preserves historical roles and keeps the current payload last and unchanged.
- Provider tests cover D-084 fallback, no-memory overflow, and fresh memory composition on transient retry.
- Step 3.6, Step 6.6, Step 6.7, relevant Phase 6, full backend, compile, lock, and Alembic verification pass.
- No schema, migration, dependency, Step 6.10, or Step 6.8-A implementation is introduced.

## Concepts Discovered

| Concept | Category | Step | Role / Why it matters |
|---|---|---|---|
| Conversation-local Short-term Memory | AI | 6.9 | Provides bounded conversational continuity |
| Atomic Conversation Turn | AI | 6.9 | Keeps prior USER/ASSISTANT pairs coherent |
| Memory vs Evidence Authority | AI | 6.9 | Prevents historical answers becoming grounding truth |
| Bounded History Query | DE | 6.9 | Avoids full Conversation history reads |
| Reply Relationship Reconstruction | DE | 6.9 | Reconstructs successful turns from persisted reply links |
| Whole-turn Token Packing | AI | 6.9 | Fits optional history without truncating messages |
| Memory-specific Exact-preflight Fallback | AI | 6.9 | Removes optional memory before failing current context |
| Role-preserving Historical Serialization | AI | 6.9 | Preserves USER/ASSISTANT conversation structure |
| Message-local Citation Isolation | AI | 6.9 | Prevents historical labels colliding with current sources |
| Persistence Invariant Validation | SYSTEM | 6.9 | Fails closed on impossible stored relationships |
| Valid Empty vs Technical Memory Failure | BOTH | 6.9 | Distinguishes optional absence from runtime failure |

## Tools Used

| Tool | Category | Step | Role / Why used |
|---|---|---|---|
| Python | SYSTEM | 6.9 | Runtime implementation |
| SQLAlchemy | DE | 6.9 | Bounded Conversation/Message lookup |
| PostgreSQL | DE | 6.9 | Existing Conversation/Message persistence |
| tiktoken | AI | 6.9 | Existing model-aware local token counting |
| OpenAI Python SDK | AI | 6.9 | Existing exact preflight and generation adapter |
| uv | SYSTEM | 6.9 | Dependency lock verification |
| pytest | SYSTEM | 6.9 | Focused and regression verification |
