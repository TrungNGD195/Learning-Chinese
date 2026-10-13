# Step 6.9 — Conversation Memory

## Goal

Add bounded, conversation-local short-term memory to the Lesson Chat RAG flow without turning prior assistant messages into trusted evidence, without polluting retrieval queries, and without allowing memory to displace current grounded evidence.

Core flow:

```text
Current User Message
↓
RAG Evidence Selection
↓
ConversationMemoryBuilder
├── same Conversation only
├── COMPLETED turns only
├── recent max 3
├── budget-aware
└── no truncation
↓
PromptPackage
├── System Instructions
├── Previous User/Assistant Turns
├── Current Retrieved Evidence
└── Current Question
↓
LLM Generation
```

Step 6.9 does not implement cross-conversation memory, long-term user memory, conversation summarization, vectorized memory search, contextual query rewriting, or citation handling.

---

# Memory Scope

Conversation memory is short-term and local to one `Conversation`.

Do not read memory from:

```text
other conversations
other lessons
global user history
long-term user profile
```

For one Lesson Conversation:

```text
Conversation A
→ only prior messages from Conversation A
```

Do not merge another Conversation even if both belong to the same Lesson.

---

# Memory Unit

Use a complete conversational turn:

```text
ConversationTurn
├── user_message
└── assistant_message status=COMPLETED
```

A turn is eligible only when the assistant response completed successfully.

Do not use:

```text
assistant PENDING
assistant FAILED
soft-deleted messages
```

as conversation memory.

If a user message has a failed assistant attempt and later a successful retry, use only the successful completed pair.

---

# Current User Message Exclusion

The current user message is already represented by:

```text
PromptPackage.user_query
```

Do not load it again as prior memory.

Memory query must only consider messages/turns strictly before the current user message sequence.

---

# Bounded Memory

Do not include the full Conversation history.

V0 default:

```text
RAG_MEMORY_MAX_TURNS=3
```

This value is configurable.

The selected turns are the most recent complete turns.

Example:

```text
T1
T2
T3
T4
T5

max=3
→ select T3,T4,T5
```

Serialize selected turns chronologically:

```text
T3
→ T4
→ T5
→ Current Question
```

Do not serialize newest-first.

---

# Token-budget-aware Selection

Turn count alone is not sufficient because an assistant response may be large.

Memory must satisfy both:

```text
RAG_MEMORY_MAX_TURNS
+
available memory token budget
```

`ConversationMemoryBuilder` should receive a model-aware:

```text
memory_token_budget
```

Do not hard-code a model-independent memory token cap.

---

# Budget Priority

Prompt budget priority:

```text
System / current request requirements
↓
Current Retrieved Evidence
↓
Conversation Memory
```

Conversation memory is optional continuity context.

It must never displace current grounded evidence.

Do not remove trusted evidence merely to keep old chat history.

---

# Memory Packing

Recommended algorithm:

1. Load recent eligible complete turns.
2. Cap by `RAG_MEMORY_MAX_TURNS`.
3. Preserve newest relevant window.
4. Count whole-turn token cost.
5. If over budget, remove the oldest selected turn.
6. Repeat until the selected memory fits.
7. Serialize remaining turns chronologically.

Example:

```text
selected:
T3 = 700 tokens
T4 = 200
T5 = 200

memory budget = 500
```

Result:

```text
drop T3
keep T4 + T5
```

---

# Atomic Turn Policy

A `MemoryTurn` is atomic.

Do not truncate:

```text
user message
assistant response
```

mid-turn.

Use:

```text
include whole turn
or
drop whole turn
```

Do not use arbitrary character/token slicing of prior messages in V0.

If no turn fits:

```text
ConversationMemory.turns = []
```

This is valid and must not fail the RAG request.

---

# ConversationMemoryBuilder

Create a dedicated application component equivalent to:

```text
ConversationMemoryBuilder
```

Input:

```text
conversation_id
current_message_sequence
memory_token_budget
max_turns
```

Output:

```text
ConversationMemory
```

The builder owns:

```text
eligible-history loading
turn reconstruction
recent-window selection
token budgeting
memory metadata
```

Do not make `LLMProvider` query the Conversation database.

---

# ConversationMemory Contract

Logical runtime structure:

```text
ConversationMemory
├── turns[]
├── selected_turn_count
├── omitted_turn_count
├── token_count
└── status
```

Each turn:

```text
MemoryTurn
├── user_text
├── assistant_text
├── user_message_id internal
├── assistant_message_id internal
└── sequence metadata internal
```

Internal IDs/sequence are useful for tracing but must not be exposed to the LLM prompt.

---

# PromptPackage Extension

Extend the provider-independent prompt contract:

```text
PromptPackage
├── system_instructions
├── conversation_memory[]
├── learning_context?
├── context_blocks[]
├── user_query
└── source_map
```

Conversation memory remains separate from retrieved context.

Do not merge memory into `context_blocks`.

---

# Provider Serialization

For providers supporting role-based messages, preserve historical roles.

Logical serialization:

```text
system:
  stable system instructions

user:
  prior user message

assistant:
  prior completed assistant reply

user:
  prior user message

assistant:
  prior completed assistant reply

...

user:
  LearningContext
  References
  Current Question
```

Do not flatten memory into one opaque string like:

```text
Conversation history: user said ..., assistant said ...
```

unless required by a provider that lacks role support.

---

# Retrieved Evidence Placement

Retrieved evidence belongs to the current request.

Do not pretend current retrieved references were part of historical turns.

Logical order:

```text
system
↓
historical user/assistant turns
↓
current user payload
    ├── LearningContext
    ├── References
    └── Current Question
```

---

# Memory Authority

Conversation memory is conversational context, not authoritative knowledge.

Critical rule:

```text
Conversation Memory
!=
Retrieved Evidence
```

Previous assistant messages may contain mistakes.

System instructions should encode an equivalent rule:

```text
Prior assistant messages are conversational context, not authoritative reference sources.
When prior conversation conflicts with current retrieved evidence, follow the current retrieved evidence.
```

---

# Previous User Messages

Previous user messages represent:

```text
user intent
conversation context
user-provided claims
```

They are not automatically factual truth.

Do not allow them to override current trusted evidence.

---

# Evidence Priority

When memory conflicts with current retrieved knowledge:

```text
Current Retrieved Evidence
>
Previous Assistant Response
```

This is a hard conceptual rule for generation.

---

# Memory Is Not a Citation Source

Do not assign source labels:

```text
S1
S2
...
```

to conversation memory.

Source labels belong only to actual evidence sources.

Conversation memory must not appear in Step 6.10 as a citation source.

---

# Retrieval Query Remains Current-query-only

Do not concatenate conversation history into the vector retrieval query in V0.

Keep:

```text
retrieval query
=
current normalized user query
```

Do not use:

```text
last 3 turns + current query
→ one embedding
```

because previous topics can contaminate semantic retrieval.

---

# Follow-up Query Limitation

This causes an accepted V0 limitation.

Example:

```text
User: Cách dùng 了?
Assistant: ...

User: Còn phủ định thì sao?
```

The retrieval query sees only:

```text
"Còn phủ định thì sao?"
```

Lesson scope helps narrow the corpus, but referent resolution may still be imperfect.

Accept this limitation in V0.

Phase 7 should evaluate follow-up retrieval quality before adding contextual query rewriting.

---

# No LLM Query Rewrite

Do not implement:

```text
conversation memory
↓
LLM standalone-question rewrite
↓
retrieval
```

in Step 6.9.

Reasons:

```text
extra latency
extra cost
extra failure point
possible intent distortion
```

Do not add a separate LLM call merely to rewrite retrieval queries in V0.

---

# No Deterministic Previous-query Concatenation

Do not automatically prepend the previous user question to the current query.

This can cause:

```text
topic contamination
incorrect semantic retrieval
```

If Phase 7 proves the follow-up problem significant, design a contextual query resolver then.

---

# No Conversation Summarization

Do not create:

```text
old messages
→ LLM summary
→ conversation memory summary
```

in V0.

Do not add:

```text
conversation_summary column
memory summary table
summary version lifecycle
```

Conversation Messages remain the canonical chat history.

---

# No Vectorized Conversation Memory

Do not:

```text
embed prior messages
create message vector store
semantic-search old conversation
```

in V0.

A bounded recent turn window is sufficient for the baseline.

---

# Memory Database Query

Use the existing canonical message ordering:

```text
Conversation
→ Message.sequence
```

Query only messages before the current message sequence.

Equivalent filters:

```text
conversation_id = current conversation
sequence < current user message sequence
not soft-deleted
```

Only reconstruct eligible complete turns.

---

# Bounded Database Access

Do not fetch the entire Conversation then slice in Python.

Use a bounded database query sufficient to reconstruct the recent complete turn window.

The exact query may retrieve a small multiple of the configured turn count to handle failed/deleted messages, but must remain bounded.

---

# Indexing

Inspect the existing schema/migrations first.

If an equivalent index already exists for:

```text
conversation_id + sequence
```

reuse it.

Only add:

```text
INDEX(conversation_id, sequence)
```

if the current schema lacks an efficient equivalent.

Do not create duplicate/speculative indexes.

---

# Retry / Failed Turn Semantics

Example:

```text
User M10
├── Assistant FAILED
└── Assistant COMPLETED retry
```

Memory turn:

```text
User M10
+
successful COMPLETED assistant response
```

Ignore the failed attempt.

If no successful completed assistant response exists yet, do not construct a complete memory turn from that user message.

---

# Lesson Boundary

Because memory is same-Conversation-only and Lesson Conversations are bound to:

```text
Conversation.lesson_id
```

memory naturally remains within the same Lesson context.

Do not import historical messages from another Lesson or another Conversation.

---

# Memory Must Never Cause RAG Failure

Conversation memory is optional.

If:

```text
memory does not fit
```

then:

```text
drop memory turns
```

Do not return:

```text
CONTEXT_BUDGET_EXHAUSTED
```

because of optional memory alone.

That error remains reserved for mandatory prompt/evidence configuration failures.

---

# Evidence Must Not Be Sacrificed for Memory

Do not omit evidence to preserve prior conversation turns.

Correct priority:

```text
current grounded evidence
>
old conversational continuity
```

If needed:

```text
selected memory → []
```

while keeping the current evidence context intact.

---

# LLM-visible Memory Fields

Only include:

```text
prior user text
prior completed assistant text
```

Do not include:

```text
message IDs
error codes
provider request IDs
retrieval scores
rerank scores
token usage
timestamps unless explicitly needed
internal status metadata
```

---

# Persistence

Step 6.9 requires no new memory table.

Reuse:

```text
Conversation
Message
sequence
status
soft-delete state
```

Do not create:

```text
conversation_memory
memory_items
memory_summary
```

tables in V0.

---

# RagRunResult Extension

Runtime metadata may include:

```text
memory_turn_count
memory_token_count
```

This is useful for logging/tests.

Do not persist a full memory snapshot merely for Step 6.9.

---

# Structured Logging

Log fields equivalent to:

```text
conversation_id
eligible_memory_turns
selected_memory_turns
omitted_memory_turns
memory_token_count
memory_build_duration_ms
memory_applied
status
error_code
```

Do not log full previous user/assistant message text by default.

---

# Tests

## Recent Window

Conversation has:

```text
T1
T2
T3
T4
T5
```

With:

```text
RAG_MEMORY_MAX_TURNS=3
```

Expected:

```text
select T3,T4,T5
serialize T3→T4→T5
```

## Token Budget

Selected initially:

```text
T3 = 700 tokens
T4 = 200
T5 = 200
```

Budget:

```text
500 tokens
```

Expected:

```text
drop T3
keep T4,T5
```

Do not truncate T3.

## Failed Assistant

```text
user
→ assistant FAILED
```

Expected:

```text
not eligible memory turn
```

After successful retry:

```text
user
→ assistant COMPLETED
```

Expected:

```text
eligible memory turn
```

## Current Message Exclusion

Verify the current user message appears only once in the final provider request.

## Authority

Given:

```text
old assistant answer conflicts with current retrieved evidence
```

verify prompt instructions establish:

```text
current retrieved evidence wins
```

## Memory Budget Zero

Expected:

```text
ConversationMemory.turns=[]
```

and RAG continues normally.

## Retrieval Query Isolation

Verify:

```text
semantic retrieval query
=
current normalized user message only
```

Conversation memory must not be concatenated into the vector query.

## Deleted Messages

Soft-deleted messages/turns must not appear in memory.

## Same-conversation Boundary

Messages from another Conversation, including another Conversation for the same Lesson, must never be loaded.

---

# Suggested Module Structure

Equivalent:

```text
conversation/
├── memory_builder.py
├── memory_schemas.py
└── repository.py
```

or:

```text
ai/
└── memory/
    ├── builder.py
    └── schemas.py
```

Follow the existing repository/module conventions.

Do not create a separate persistence subsystem for memory.

---

# Out of Scope

Do not implement in Step 6.9:

```text
cross-conversation memory
cross-lesson memory
long-term user memory
learner preference memory
conversation summarization
summary persistence
vectorized message memory
semantic history retrieval
LLM query rewriting
deterministic previous-query concatenation
citation parsing
citation validation
citation persistence
```

Step 6.10 owns citations.

---

# Acceptance Criteria

- [ ] Conversation memory is same-Conversation-only.
- [ ] No cross-conversation or long-term user memory exists.
- [ ] Memory unit is a complete user + COMPLETED assistant turn.
- [ ] PENDING/FAILED/soft-deleted messages are excluded.
- [ ] Current user message is not duplicated in history.
- [ ] `RAG_MEMORY_MAX_TURNS=3` is the configurable V0 default.
- [ ] Most recent complete turns are selected.
- [ ] Selected turns are serialized chronologically.
- [ ] Memory is model-budget-aware.
- [ ] Retrieved evidence has higher budget priority than memory.
- [ ] Oldest selected turns are dropped first when memory exceeds budget.
- [ ] Memory turns are never silently truncated.
- [ ] Empty memory is a valid outcome.
- [ ] `ConversationMemoryBuilder` is independent from `LLMProvider`.
- [ ] `PromptPackage` contains conversation memory separately from evidence.
- [ ] Historical roles are preserved in provider serialization.
- [ ] Retrieved references remain part of the current request.
- [ ] Previous assistant responses are not trusted evidence.
- [ ] Current retrieved evidence outranks previous assistant responses.
- [ ] Previous user claims do not automatically override evidence.
- [ ] Memory receives no `S1..Sn` citation labels.
- [ ] Retrieval query remains current-query-only.
- [ ] No LLM query rewrite is added.
- [ ] No deterministic previous-query concatenation is added.
- [ ] No conversation summarization is added.
- [ ] No vectorized conversation memory is added.
- [ ] History DB access is bounded.
- [ ] Existing `(conversation_id, sequence)` indexing is reused when available.
- [ ] Failed retry attempts are excluded; successful completion is canonical.
- [ ] Memory never causes the RAG request to fail merely because it does not fit.
- [ ] Evidence is never dropped to preserve memory.
- [ ] Internal metadata is not inserted into LLM-visible history.
- [ ] No new memory persistence table is introduced.
- [ ] Memory metadata is observable without logging full content.
- [ ] Step 6.10 can add citation handling without treating memory as a source.

# Expected Deliverable

Conversation-local short-term memory foundation plus documentation:

```text
docs/ai/
└── step-6.9-conversation-memory.md
```

Next Step:

**Step 6.10 — Citations**
