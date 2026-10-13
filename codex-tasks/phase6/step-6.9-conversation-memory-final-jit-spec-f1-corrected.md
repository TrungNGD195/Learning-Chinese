# Step 6.9 — Conversation Memory
## Final JIT Task / Specification for PM Review

**Status:** READY_FOR_PM_TASK_REVIEW  
**Correction:** F1 — D-084 transient-retry/preflight semantics  
**Owner:** AI Engineering Specialist  
**Implementation authorization:** NOT YET — PM final task review required before Codex / production implementation  
**Production code changes during JIT review:** NO  
**Codex run:** NO  
**Step 6.10 started:** NO  
**Step 6.8-A started:** NO  

---

# 0. Frozen State

## Canonical decisions preserved

D-070 through D-085 remain authoritative.

Most directly relevant:

- **D-079–D-083** — Step 6.7 provider/model, OpenAI SDK, hybrid token accounting, stateless Responses, completed-only success.
- **D-084** — Memory-Specific Exact-Preflight Fail-Soft Fallback.
- **D-085** — Conversation Memory Turn Cap and Config Disable Policy.

Do not reopen them unless actual repository evidence proves a material contradiction.

---

# 1. Objective

Add bounded, Conversation-local short-term memory to Lesson Chat while preserving the current RAG authority model.

Memory exists only to improve conversational continuity.

It must NOT:

- become retrieved evidence;
- enter the vector retrieval query;
- displace current evidence;
- become a citation source;
- become long-term user memory;
- create a memory persistence subsystem;
- trigger summarization;
- trigger vectorized history retrieval;
- pull Step 6.8-A or Step 6.10 orchestration forward.

---

# 2. Problem

Without memory, a learner follow-up such as:

```text
User: Cách dùng 了?
Assistant: ...
User: Còn phủ định thì sao?
```

reaches generation with only the current query and current evidence.

The model loses conversational continuity even though the Conversation database already contains the prior successful turn.

The solution is a small recent-turn window added to generation context.

The key safety constraint is:

```text
current mandatory request
+
current retrieved evidence
>
conversation memory
```

Memory is optional context, never authoritative evidence.

---

# 3. Mental Model

```text
Conversation DB
↓
bounded prior complete-turn query
↓
ConversationMemoryBuilder
↓
recent eligible turns
↓
local residual token budget
↓
whole-turn packing
↓
ConversationMemory
↓
PromptPackage.conversation_memory
↓
LLMRequestSerializer
↓
historical user / assistant roles
↓
current user payload last
↓
provider exact token preflight
↓
generation
```

Authority:

```text
System instructions
>
Current retrieved evidence
>
Prior Assistant response
```

Previous USER content is conversational/user-provided context, not automatically factual truth.

---

# 4. Scope

## In Scope

- same-Conversation recent memory;
- complete prior USER + COMPLETED Assistant turns;
- failed/PENDING retry exclusion;
- bounded repository lookup;
- current-message exclusion;
- whole-turn token counting and selection;
- D-084 exact-preflight memory fallback;
- D-085 `RAG_MEMORY_MAX_TURNS`;
- PromptPackage memory extension;
- Step-6.7 historical role serialization support;
- historical Assistant citation-marker sanitation;
- memory authority system instruction;
- safe observability;
- typed technical memory failures;
- deterministic focused/regression tests;
- Step Note.

## Out of Scope

Do NOT implement:

```text
cross-conversation memory
cross-lesson memory
global user memory
long-term profile memory
conversation summarization
summary persistence
vector memory
semantic history search
LLM query rewrite
previous-query concatenation
memory embeddings
citation validation
citation persistence
CitationValidator
Step 6.8-A RagRunResult
Step 6.8 tier orchestration
external retrieval
new memory database tables
new memory snapshot persistence
streaming
background workers
```

---

# 5. Current Execution-Order Constraint

Current PM execution order is:

```text
6.7 CLOSED
→ 6.9 Conversation Memory
→ 6.10 Citations
→ 6.8-A Internal E2E RAG
```

Therefore Step 6.9 must be independently implementable and testable before `RagRunResult` exists.

Do NOT create placeholder Step-6.8 orchestration solely to satisfy old baseline wording.

Step 6.9 must expose a clean seam that 6.8-A can later call.

---

# 6. Memory Scope

Memory is strictly local to the current Conversation.

Required filter:

```text
conversation_id = current Conversation
```

Never load:

- another Conversation for the same Lesson;
- another Lesson;
- another User's Conversation;
- global User history.

Because V0 Conversations are Lesson-scoped, same-Conversation memory naturally remains same-Lesson.

---

# 7. Canonical Memory Unit

One eligible memory unit is one complete turn:

```text
USER Message
+
the single COMPLETED Assistant Message
whose reply_to_message_id = USER.id
```

Required USER state:

```text
role = USER
status = COMPLETED
sequence_number < current_user_sequence_number
```

Required Assistant state:

```text
role = ASSISTANT
status = COMPLETED
reply_to_message_id = USER.id
same conversation
sequence_number < current_user_sequence_number
```

Exclude:

```text
Assistant PENDING
Assistant FAILED
current USER Message
incomplete processing attempts
another Conversation
```

---

# 8. Retry / Turn Invariant

Accepted Step-3.6 workflow guarantees for one USER:

```text
zero or more FAILED Assistant attempts
+
at most one final COMPLETED Assistant
```

Valid example:

```text
USER
→ ASSISTANT FAILED
→ ASSISTANT FAILED
→ ASSISTANT COMPLETED
```

The final successful Assistant is the only eligible Assistant for memory.

Do NOT implement:

```text
latest COMPLETED wins
earliest COMPLETED wins
MAX(sequence_number) silent repair
```

More than one COMPLETED Assistant for the same original USER is a persistence invariant violation.

---

# 9. Current USER Exclusion

The current learner message is already represented by:

```text
PromptPackage.user_query
```

Memory lookup must use:

```text
prior USER.sequence_number < current USER.sequence_number
```

The current user query must appear exactly once in the final provider request.

---

# 10. `RAG_MEMORY_MAX_TURNS` — D-085

Add backend configuration:

```text
RAG_MEMORY_MAX_TURNS
```

Exact contract:

```text
type: int
default: 3
valid: 0..3 inclusive
bool: invalid
```

Semantics:

```text
3
→ normal V0 maximum

1..2
→ reduced-memory mode

0
→ memory disabled
→ no history lookup where possible
→ ConversationMemory.turns = ()
→ selected_turn_count = 0
→ memory_applied = false
→ generation continues normally
```

Invalid:

```text
< 0
> 3
non-integer semantic value
bool-as-int
```

Invalid configuration must fail normal Settings validation.

Do NOT:

```text
clamp
silently replace with 3
silently disable
choose another fallback
```

Do NOT add:

```text
RAG_MEMORY_MAX_TOKENS
```

---

# 11. Index / Migration Result

No Step-6.9 migration is required.

Reuse existing persistence support:

```text
UNIQUE(conversation_id, sequence_number)
```

and the existing reply relationship/index direction for:

```text
reply_to_message_id
```

Do NOT add duplicate/speculative indexes.

**Schema changes:** NO  
**Migration:** NO  
**Expected Alembic head:** `0012_vector_storage_readiness`

If actual repository inspection during implementation proves these indexes are missing contrary to the reconciled state, Codex must stop and report the conflict rather than silently add a migration.

---

# 12. Bounded Repository Query

Do not load the full Conversation history.

Add one memory-specific repository method to the **existing Conversation/Message repository module**. Do not create a duplicate persistence abstraction.

Equivalent interface:

```python
async def list_recent_completed_turn_pairs_for_memory(
    *,
    conversation_id: UUID,
    before_sequence_number: int,
    limit: int,
) -> Sequence[MemoryTurnRow]:
    ...
```

For `RAG_MEMORY_MAX_TURNS = 0`, caller skips this query.

## SQL semantics

Use USER and ASSISTANT aliases joined by the persisted reply relationship.

Equivalent predicates:

```text
USER.conversation_id = :conversation_id
USER.role = USER
USER.status = COMPLETED
USER.sequence_number < :before_sequence_number

ASSISTANT.conversation_id = :conversation_id
ASSISTANT.role = ASSISTANT
ASSISTANT.status = COMPLETED
ASSISTANT.reply_to_message_id = USER.id
ASSISTANT.sequence_number < :before_sequence_number
```

Ordering:

```text
USER.sequence_number DESC
ASSISTANT.sequence_number DESC
```

Limit:

```text
max_turns + 1
```

Since V0 max is 3, repository returns at most 4 joined rows.

Purpose of `+1`:

- keep access bounded;
- allow detection of a duplicate COMPLETED Assistant inside the recent candidate boundary;
- allow the builder to cap the recent eligible window deterministically.

Do NOT query FAILED/PENDING attempts for memory content. They are excluded by the SQL status predicate.

Do NOT infer pairings by timestamp or sequence adjacency.

## Repository result

Return a project-owned lightweight row/DTO, not ORM objects across the AI boundary.

Equivalent fields:

```text
user_message_id
assistant_message_id
user_text
assistant_text
user_sequence_number
assistant_sequence_number
conversation_id
```

---

# 13. Bounded Query Integrity Validation

The memory builder must validate returned rows.

For every returned pair:

```text
same conversation
user role/status contract already enforced
assistant reply points to user
user_sequence < assistant_sequence
assistant_sequence < current_user_sequence
nonblank user content
nonblank assistant content
```

If two returned rows have the same `user_message_id` with different COMPLETED Assistants:

```text
→ persistence invariant violation
→ technical failure
```

Do NOT silently deduplicate.

The memory query is not a full historical integrity audit. It validates the bounded recent memory candidate set that would affect the current generation.

---

# 14. `MemoryTurn` Contract

Add a provider-independent immutable runtime DTO equivalent to:

```text
MemoryTurn
├── user_text: str
├── assistant_text: str
├── user_message_id: UUID
├── assistant_message_id: UUID
├── user_sequence_number: int
└── assistant_sequence_number: int
```

LLM-visible:

```text
user_text
assistant_text
```

Internal only:

```text
message IDs
sequence metadata
```

Never expose to the model:

```text
status
error code
provider request ID
token usage
retrieval score
rerank score
timestamps
database metadata
```

No ORM object is stored in `MemoryTurn`.

---

# 15. `ConversationMemory` Contract

Add an immutable runtime DTO equivalent to:

```text
ConversationMemory
├── turns: tuple[MemoryTurn, ...]
├── selected_turn_count: int
├── omitted_turn_count: int
├── token_count: int
└── status: APPLIED | EMPTY
```

Semantics:

```text
APPLIED
→ turns is non-empty

EMPTY
→ turns == ()
→ token_count == 0
→ selected_turn_count == 0
```

`omitted_turn_count` means:

```text
number of turns inside the recent max_turns candidate window
that were dropped by local memory token packing
```

It does NOT attempt to count every older eligible turn beyond the configured recent window.

This keeps database access bounded.

---

# 16. Valid Empty Memory

All of these are valid non-error outcomes:

```text
RAG_MEMORY_MAX_TURNS = 0
no prior eligible complete turn
local_memory_budget <= 0
no whole MemoryTurn fits
D-084 exact-provider overflow drops memory and zero-memory request fits
historical assistant text becomes unusable after required citation-marker sanitation
```

Result:

```text
ConversationMemory(
    turns=(),
    selected_turn_count=0,
    token_count=0,
    status="EMPTY",
)
```

Generation continues when the mandatory current request remains valid.

Do NOT return:

```text
CONTEXT_BUDGET_EXHAUSTED
LLM_CONTEXT_LIMIT_EXCEEDED
```

merely because optional memory is empty.

---

# 17. Technical Failure Semantics

Valid absence of memory is NOT the same as inability to build memory.

Technical failures include:

```text
repository / DB read failure
TokenCounter failure
malformed persisted pair
multiple COMPLETED Assistants for one USER
cross-Conversation pair discovered
impossible sequence relationship
invalid runtime DTO relationship
```

Do NOT silently convert these to empty memory.

Add internal Step-6.9 errors equivalent to:

```text
MEMORY_REPOSITORY_FAILED
MEMORY_TOKEN_COUNT_FAILED
MEMORY_PERSISTENCE_INTEGRITY_FAILED
MEMORY_BUILD_FAILED
```

These remain internal normalized AI/application errors.

The Conversation/application boundary continues using the existing generic AI failure behavior:

```text
technical memory failure
→ AI processing fails
→ Assistant FAILED
→ existing public AI_RESPONSE_FAILED / equivalent
```

Do NOT introduce a new learner-facing memory-specific API error in Step 6.9.

Do NOT expose:

```text
raw SQL exception
raw ORM object
historical message content
internal stack trace
```

---

# 18. Historical Citation-Marker Isolation

Step 6.10 source labels are message-local.

Historical Assistant text may contain:

```text
[S1]
[S2]
[S12]
```

Those labels must not enter a later prompt because they can collide with current source labels.

## Required Step-6.9 behavior

During memory construction/serialization only:

```text
historical Assistant content
→ strip exact supported historical citation markers
→ LLM-visible assistant_text
```

Supported marker syntax to strip:

```regex
\[S[1-9][0-9]*\]
```

Example:

```text
stored:
"了 thường ... [S1]"

LLM-visible memory:
"了 thường ..."
```

Rules:

- do NOT modify the persisted Message;
- do NOT sanitize USER text;
- do NOT parse provenance;
- do NOT validate current citations;
- do NOT create `CitationValidator`;
- do NOT persist citations;
- do NOT repair malformed citation syntax.

If stripping exact historical markers makes an Assistant memory message blank/whitespace-only:

```text
drop that whole MemoryTurn as unusable optional memory
```

This is a valid memory omission, not a persistence failure.

Do not truncate the remaining prose.

---

# 19. Conversation Memory Authority Prompt

Extend the stable system instructions narrowly with meaning equivalent to:

```text
Prior assistant messages are conversational context, not authoritative reference sources.
Previous user messages may contain user claims and are not automatically factual truth.
When prior conversation conflicts with current retrieved evidence, follow the current retrieved evidence.
```

Do not otherwise rewrite the accepted Step-6.6 / 6.7 prompt policy.

Memory remains:

```text
conversation context
!=
grounding evidence
```

---

# 20. Retrieval Isolation

Retrieval stays unchanged.

Exact V0 rule:

```text
retrieval query
=
current normalized user query only
```

Conversation memory must never enter:

```text
query preprocessing
query embedding
semantic retrieval query
retrieval filter
reranker query
evidence selection
```

Do NOT add:

```text
LLM query rewrite
previous-turn concatenation
contextual embedding
memory retrieval
```

---

# 21. Local Memory Budget — D-084

The current Step-6.6 package remains authoritative for mandatory current prompt/evidence cost.

Compute:

```text
current_prompt_estimated_input_tokens
=
PromptPackage.budget_usage.estimated_input_tokens
```

Then:

```text
local_memory_budget
=
PromptPackage.budget_usage.model_input_limit
- PromptPackage.budget_usage.reserved_output_tokens
- PromptPackage.budget_usage.estimated_input_tokens
```

For V0:

```text
local_memory_budget
=
400000
- 800
- current_prompt_estimated_input_tokens
```

If:

```text
local_memory_budget <= 0
```

return valid EMPTY memory.

Do not alter current evidence.

Do not reopen Step-6.6 evidence packing.

---

# 22. Local Whole-Turn Token Cost

Reuse the frozen synchronous model-aware `TokenCounter`.

For one sanitized turn:

```text
turn_token_count
=
TokenCounter.count(user_text)
+
TokenCounter.count(sanitized_assistant_text)
```

Do NOT invent a numeric provider-role-overhead constant.

Reason:

```text
local tokenizer
= deterministic memory packing estimate

provider exact token preflight
= provider structural safety gate
```

This preserves D-081 and D-084.

TokenCounter exception / invalid return:

```text
→ MEMORY_TOKEN_COUNT_FAILED
→ technical failure
```

---

# 23. Memory Selection Algorithm

Input:

```text
bounded recent eligible complete-turn rows
max_turns
local_memory_budget
TokenCounter
```

Algorithm:

1. If `max_turns == 0`, return EMPTY without history query where possible.
2. Query recent complete pairs in descending USER sequence order.
3. Validate persistence invariants.
4. Strip exact historical citation markers from Assistant memory text.
5. Drop a turn only if its sanitized Assistant text becomes blank.
6. Keep the most recent `max_turns` eligible usable turns.
7. Convert them to chronological order.
8. Count each whole turn.
9. Sum token costs.
10. If total exceeds `local_memory_budget`, drop the oldest selected turn.
11. Repeat until fit or empty.
12. Never truncate a USER or Assistant message.

Example:

```text
recent window:
T3 = 700
T4 = 200
T5 = 200

budget = 500

→ drop T3
→ keep T4,T5
→ serialize T4,T5 chronologically
```

---

# 24. PromptPackage Backward-Compatible Extension

Current Step-6.6 `PromptPackage` is immutable.

Add the smallest backward-compatible field:

```python
conversation_memory: ConversationMemory | None = None
```

Place it so existing Step-6.6 construction remains valid.

Meaning:

```text
None
→ Step-6.9 memory has not been attached on this call path

ConversationMemory(status=EMPTY)
→ Step-6.9 was applied but selected no memory

ConversationMemory(status=APPLIED)
→ memory turns are present
```

Memory remains structurally separate from:

```text
context_blocks
source_map
selected_chunk_ids
omitted_chunk_ids
```

Do NOT assign S-labels to memory.

Do NOT modify Step-6.6 budget metadata to pretend memory was evidence.

Use `dataclasses.replace(...)` or an equivalent helper to attach memory without rebuilding evidence.

---

# 25. Step-6.7 Project-Owned Historical Role DTO

Add an immutable provider-independent DTO equivalent to:

```text
LLMRoleMessage
├── role: user | assistant
└── content: str
```

No OpenAI SDK type escapes the adapter.

Historical messages are created from `ConversationMemory.turns`:

```text
turn 1 USER
turn 1 ASSISTANT
turn 2 USER
turn 2 ASSISTANT
...
```

No system role is allowed inside historical messages.

---

# 26. `LLMGenerationRequest` Backward-Compatible Extension

Preserve current request structure and add historical messages.

Equivalent:

```text
LLMGenerationRequest
├── system_content: str
├── historical_messages: tuple[LLMRoleMessage, ...]
├── user_content: str
├── model
├── temperature
├── max_output_tokens
├── reasoning_effort
├── model_input_limit
├── estimated_input_tokens
└── memory_input_tokens
```

Rules:

```text
system_content
→ trusted stable system instructions only

historical_messages
→ prior user/assistant roles only

user_content
→ current LearningContext + current References + current Question
```

`estimated_input_tokens` becomes the local estimate for the full effective request:

```text
current PromptPackage estimated_input_tokens
+
selected ConversationMemory.token_count
```

`memory_input_tokens`:

```text
0 when no memory
ConversationMemory.token_count when memory exists
```

Existing no-memory request behavior remains equivalent.

---

# 27. Step-6.7 Serializer

`LLMRequestSerializer` must:

1. keep `system_content = package.system_instructions`;
2. serialize `package.conversation_memory.turns` into project-owned historical role messages;
3. serialize the existing current learner-side payload exactly as before;
4. keep current `user_content` as the final user message;
5. never place current evidence in a historical message;
6. never place historical messages in current `source_map`;
7. never duplicate the current query.

No memory:

```text
historical_messages = ()
```

Current learner payload remains:

```text
[Learning context] optional
[References] optional
[Question] current query
```

---

# 28. OpenAI Responses Input Representation

The OpenAI adapter converts the project-owned request into one role-aware provider input list.

Equivalent semantic structure:

```text
[
  {"role": "user",      "content": prior_user_1},
  {"role": "assistant", "content": prior_assistant_1},
  {"role": "user",      "content": prior_user_2},
  {"role": "assistant", "content": prior_assistant_2},
  ...
  {"role": "user",      "content": current_user_content},
]
```

System instructions remain separate in:

```text
instructions=request.system_content
```

Do NOT put system instructions into the input message list.

The current learner payload is always the final `user` item.

---

# 29. Same Input Structure for Preflight and Generation

Create the provider input structure once per effective request.

Use the same semantic input-bearing structure for:

```text
responses.input_tokens.count(...)
```

and:

```text
responses.create(...)
```

Do not independently reconstruct different message meanings for preflight and generation.

Provider-specific dict/SDK shapes stay inside `OpenAILLMProvider`.

---

# 30. D-084 Exact-Preflight Behavior

## Normal memory path

```text
selected memory
↓
role-aware input
↓
exact provider preflight
```

If:

```text
provider_input_tokens + 800 <= 400000
```

generate normally with memory.

Provider preflight count:

```text
1
```

## Memory exact-overflow path

If exact count overflows and historical memory is non-empty:

```text
do NOT fail yet
```

Remove:

```text
historical_messages only
```

Preserve unchanged:

```text
system instructions
current LearningContext
current References
current Question
source_map
generation config
```

Rebuild provider input as:

```text
[
  {"role": "user", "content": current_user_content}
]
```

Perform one final exact preflight.

If second preflight fits:

```text
generate without memory
```

If second still overflows:

```text
LLM_CONTEXT_LIMIT_EXCEEDED
no generation
no retry
no evidence removal
no prompt truncation
no output-reserve reduction
no model fallback
```

Maximum exact-preflight calls for the memory-overflow decision in one provider attempt:

```text
2
```

Do NOT iteratively drop one memory turn and re-preflight.

A provider-count **technical** failure is NOT an overflow signal and must NOT silently remove memory.

---

# 31. Transient Retry Interaction

Step-6.7 transient retry policy remains unchanged.

Accepted transient failures:

```text
timeout
connection failure
429
accepted 5xx
```

SDK retries remain:

```text
0
```

Application transient retries remain:

```text
max 1
```

Therefore one `LLMGenerationService.generate(...)` operation has at most:

```text
2 logical generation attempts
```

D-084 exact-preflight fallback is scoped **per logical attempt**.

Within one logical attempt:

```text
memory-bearing exact preflight
→ if it fits, generate with memory

memory-bearing exact preflight
→ if it overflows
→ drop all memory
→ one final zero-memory exact preflight
→ if it fits, generate without memory
```

Once memory is dropped because of exact overflow inside that logical attempt:

```text
do NOT reintroduce memory again inside that same logical attempt
```

However, if an accepted transient technical failure causes the application to start a **new logical attempt**:

```text
START FRESH
↓
reconstruct the normal memory-aware provider request
↓
run the memory-bearing exact preflight again
```

Memory is therefore eligible to be included again on the new logical attempt.

If that new attempt's memory-bearing exact preflight overflows:

```text
D-084 applies again
→ drop all memory for that logical attempt
→ perform one final zero-memory exact preflight
```

The D-084 second preflight:

```text
does NOT consume the transient retry budget
does NOT increment logical attempt_count
```

Every logical attempt independently evaluates provider-exact fit.

Maximum exact-provider preflight calls:

```text
per logical attempt:
  normal fit        → 1
  memory overflow   → 2

maximum logical attempts:
  2

maximum provider exact-preflight calls
across one complete generate(...) operation:
  4
```

Do NOT encode:

```text
provider_preflight_count <= 2
```

as a whole-operation invariant.

---

# 32. `LLMGenerationResult` Observability Extension

Preserve existing result fields and add:

```text
provider_preflight_count: int
memory_dropped_after_exact_preflight: bool
```

## `provider_preflight_count`

Exact meaning:

```text
total number of exact provider input-token preflight calls
performed across the complete
LLMGenerationService.generate(...) operation
```

It is NOT capped at 2 for the whole operation.

Examples:

```text
attempt 1 memory fits
→ success
→ provider_preflight_count = 1
```

```text
attempt 1 memory fits
→ transient generation failure
attempt 2 memory fits
→ success
→ provider_preflight_count = 2
```

```text
attempt 1:
  memory overflow
  zero-memory preflight fits
  generation transiently fails

attempt 2:
  memory overflow
  zero-memory preflight fits
  generation succeeds

→ provider_preflight_count = 4
```

The D-084 maximum of 2 applies only to one logical attempt.

## `provider_preflight_input_tokens`

Existing:

```text
provider_preflight_input_tokens
```

means:

```text
the final successful preflight token count
for the request actually sent to responses.create()
on the logical attempt that produced the returned successful result
```

## `memory_dropped_after_exact_preflight`

Meaning:

```text
true
→ D-084 dropped memory in at least one logical attempt
   during this complete generate(...) operation

false
→ no logical attempt required memory removal
   because of exact provider overflow
```

This is operation-level observability.

It does NOT mean the final successful generation necessarily ran without memory.

Example:

```text
attempt 1:
  memory overflow
  → memory dropped
  → zero-memory generation gets transient 503

attempt 2:
  memory-bearing preflight fits
  → generation succeeds WITH memory

result:
  memory_dropped_after_exact_preflight = true
```

No database persistence is introduced for these fields.

---

# 33. Memory Authority / Citation Separation

Conversation memory never receives:

```text
S1
S2
...
```

labels.

Conversation memory never enters:

```text
PromptPackage.source_map
```

Historical `[S<number>]` markers are stripped from Assistant memory text solely to prevent message-local labels from colliding with current source labels.

Step 6.10 still owns:

```text
citation prompt requirement
CitationValidator
current-answer parsing
citation validation
citation persistence
MessageCitation
```

---

# 34. `ConversationMemoryBuilder`

Create a dedicated component equivalent to:

```python
class ConversationMemoryBuilder:
    async def build(
        self,
        *,
        conversation_id: UUID,
        current_user_sequence_number: int,
        memory_token_budget: int,
        max_turns: int,
    ) -> ConversationMemory:
        ...
```

Dependencies are injected:

```text
existing Conversation/Message repository boundary
TokenCounter
```

Builder owns:

```text
bounded eligible history loading
pair validation
citation-marker sanitation
recent-window selection
whole-turn token counting
oldest-first dropping
ConversationMemory metadata
safe logging
```

Builder does NOT own:

```text
retrieval
reranking
LLM provider calls
provider exact preflight
DB writes
Conversation ownership authorization
Step 6.8 orchestration
```

---

# 35. Local Budget Helper / Future 6.8-A Seam

Add a pure helper equivalent to:

```python
def derive_memory_token_budget(package: PromptPackage) -> int:
    return max(
        0,
        package.budget_usage.model_input_limit
        - package.budget_usage.reserved_output_tokens
        - package.budget_usage.estimated_input_tokens,
    )
```

Future Step 6.8-A orchestration seam:

```text
current Conversation validated
+
current USER Message sequence known
+
current evidence PromptPackage built
↓
derive_memory_token_budget(package)
↓
ConversationMemoryBuilder.build(...)
↓
attach ConversationMemory to PromptPackage
↓
LLMGenerationService.generate(...)
```

Step 6.9 tests this seam through focused composition tests.

Do NOT implement RagRunResult or retrieval-tier sequencing now.

---

# 36. Memory Attachment Helper

Provide a small provider-independent helper equivalent to:

```python
def with_conversation_memory(
    package: PromptPackage,
    memory: ConversationMemory,
) -> PromptPackage:
    return dataclasses.replace(
        package,
        conversation_memory=memory,
    )
```

It must not mutate:

```text
context_blocks
source_map
selected/omitted chunk IDs
budget_usage
user_query
learning_context
```

---

# 37. Logging / Observability

Memory builder safe log fields may include:

```text
conversation_id
eligible_memory_turns
selected_memory_turns
omitted_memory_turns
memory_token_count
memory_build_duration_ms
memory_applied
memory_disabled_by_config
status
error_code
```

Provider/generation logs additionally may include:

```text
memory_dropped_after_exact_preflight
provider_preflight_count
```

Do NOT log:

```text
historical USER text
historical ASSISTANT text
current full query
current evidence content
full provider input
full generated answer
API credentials
```

Do not persist a full memory snapshot.

---

# 38. Exact Empty vs Failure Contract

## Semantic EMPTY

```text
status = EMPTY
turns = ()
normal generation may continue
```

Examples:

```text
config 0
no eligible history
budget 0
no whole turn fits
sanitized candidate becomes unusable
D-084 memory drop
```

## Technical failure

Raise typed internal error.

Examples:

```text
repository unavailable
SQL execution failure
tokenizer/count failure
duplicate COMPLETED persisted state
cross-conversation relation
impossible sequence relation
malformed returned row
```

Higher application/orchestration layer maps technical memory failure to the existing generic AI processing failure semantics.

Do not convert technical failure to EMPTY.

---

# 39. Dependencies

No new dependency is required.

Reuse:

```text
Python
SQLAlchemy / existing repository stack
existing TiktokenTokenCounter
existing OpenAI Step-6.7 provider
pytest
uv
```

Do NOT add:

```text
LangChain
LlamaIndex
Redis
Celery
new tokenizer
new retry framework
```

**Dependency change:** NO

---

# 40. Expected Files / Components

Follow actual repository structure and modify existing modules rather than creating duplicate abstractions.

Expected equivalent components:

```text
backend/app/ai/memory/
├── __init__.py
├── schemas.py
├── errors.py
├── sanitizer.py
└── builder.py

existing Conversation / Message repository module
└── add bounded memory turn-pair query

backend/app/ai/prompting/
├── schemas.py
└── instructions.py

backend/app/ai/llm/
├── schemas.py
├── serializer.py
└── openai_provider.py

backend/app/core/
└── config.py

backend/.env.example

backend/tests/
├── test_step69_memory_builder.py
├── test_step69_memory_repository.py
├── test_step69_memory_serialization.py
├── test_step69_memory_provider.py
└── existing config / Step-6.6 / Step-6.7 regression tests

docs/ai/
└── step-6.9-conversation-memory.md
```

If the repository already has a Conversation memory-appropriate module location, use the existing module convention rather than creating parallel ownership.

Do not create a new persistence repository solely for memory if the existing Message repository is the canonical read boundary.

---

# 41. Test Matrix

## A. Config — D-085

Test:

```text
default = 3
0 accepted and disables memory
1 accepted
2 accepted
3 accepted
-1 invalid
4 invalid
bool invalid
invalid value does not clamp
```

When disabled:

```text
no history lookup where possible
ConversationMemory EMPTY
generation-compatible path remains valid
```

No `RAG_MEMORY_MAX_TOKENS`.

---

## B. Memory Scope

Test:

```text
same Conversation
→ eligible

another Conversation, same Lesson
→ excluded

another Conversation
→ excluded
```

---

## C. Current Message Exclusion

Only:

```text
USER.sequence_number < current USER.sequence_number
```

Current USER appears exactly once in final provider input.

---

## D. Eligibility / Retry

Test:

```text
USER + COMPLETED Assistant
→ eligible

USER + FAILED only
→ not eligible

USER + PENDING only
→ not eligible

USER
→ FAILED
→ FAILED
→ COMPLETED
→ exactly one eligible turn
```

More than one COMPLETED for same USER:

```text
→ MEMORY_PERSISTENCE_INTEGRITY_FAILED
→ no silent winner
```

---

## E. Bounded Query

Prove:

```text
query uses conversation_id
query uses current sequence upper bound
query filters USER COMPLETED
query joins ASSISTANT COMPLETED by reply_to_message_id
query orders deterministic sequence DESC
query LIMIT = max_turns + 1
full Conversation is not loaded
```

Verify existing indexes are reused.

---

## F. Recent Window

Given valid turns:

```text
T1 T2 T3 T4 T5
max_turns=3
```

candidate window:

```text
T3 T4 T5
```

serialize chronologically:

```text
T3
T4
T5
current request
```

---

## G. Citation-Marker Sanitation

Historical Assistant:

```text
"... [S1] ... [S12]"
```

LLM-visible memory:

```text
"...  ... "
```

Stored DB content remains unchanged.

USER text containing `[S1]` is NOT stripped.

Malformed/non-supported citation-like text is not parsed/repaired by Step 6.9.

No CitationValidator exists.

---

## H. Whole-Turn Token Packing

Example:

```text
T3 = 700
T4 = 200
T5 = 200
budget = 500
```

Expected:

```text
drop T3
keep T4,T5
```

Never truncate a message.

Zero budget:

```text
→ EMPTY
```

No whole turn fits:

```text
→ EMPTY
```

Evidence remains unchanged.

---

## I. Token Counting Failure

TokenCounter raises or returns invalid count:

```text
→ MEMORY_TOKEN_COUNT_FAILED
→ technical failure
→ not EMPTY
```

---

## J. Repository Failure

DB/repository exception:

```text
→ MEMORY_REPOSITORY_FAILED
→ technical failure
→ not EMPTY
```

No raw SQL error leaked.

---

## K. Persistence Integrity

Cover:

```text
duplicate COMPLETED Assistants for one USER
cross-Conversation pair
assistant before/equal user sequence
assistant >= current user sequence
invalid/nonblank content relationship
```

Expected:

```text
MEMORY_PERSISTENCE_INTEGRITY_FAILED
```

No silent repair.

---

## L. PromptPackage Extension

Verify:

```text
memory separate from context_blocks
memory absent from source_map
memory absent from selected_chunk_ids
memory absent from omitted_chunk_ids
budget_usage unchanged
```

No-memory Step-6.6 construction still passes.

---

## M. Historical Role Serialization

Verify exact order:

```text
historical USER
historical ASSISTANT
historical USER
historical ASSISTANT
...
current USER payload
```

System instructions remain separate.

Current References remain only in the final user payload.

Internal IDs/sequence never reach provider input.

---

## N. Memory Authority Prompt

System prompt includes equivalent policy:

```text
prior Assistant is context, not authoritative evidence
prior USER claims are not automatic truth
current retrieved evidence wins on conflict
```

No broad accepted-prompt rewrite.

---

## O. Retrieval Isolation

Verify memory is never passed to:

```text
QueryPreprocessor
embed_query
retrieval filters
reranker query
evidence selection
```

Retrieval query remains the current normalized query only.

---

## P. D-084 Provider Preflight

All provider-preflight limits in this subsection are **per logical attempt**.

### Normal

Memory request fits:

```text
one provider exact preflight
generation includes history
```

### Exact overflow with memory

First count overflows:

```text
drop all historical messages
preserve current request/evidence
second exact preflight
```

Second fits:

```text
generation without memory
provider_preflight_count = 2
memory_dropped_after_exact_preflight = true
```

Second still overflows:

```text
LLM_CONTEXT_LIMIT_EXCEEDED
responses.create not called
no transient retry
no evidence removal
```

Technical preflight error:

```text
does NOT trigger memory removal
normal Step-6.7 error/retry semantics apply
```

---

## Q. Transient Retry after Memory Fallback

Canonical D-084 retry behavior must be tested across fresh logical attempts.

### Case A — attempt 2 memory now fits

Attempt 1:

```text
memory-bearing exact preflight
→ overflow

zero-memory exact preflight
→ fits

responses.create()
→ transient 503
```

Attempt 2 starts fresh:

```text
recompose normal memory-aware request
↓
memory-bearing exact preflight
→ fits
↓
responses.create() WITH memory
→ success
```

Verify:

```text
attempt_count = 2
provider_preflight_count = 3
memory is eligible again on attempt 2
SDK retries = 0
no third logical attempt
```

### Case B — attempt 2 memory overflows again

Attempt 1:

```text
memory-bearing exact preflight
→ overflow

zero-memory exact preflight
→ fits

responses.create()
→ transient 503
```

Attempt 2 starts fresh:

```text
memory-bearing exact preflight
→ overflow

drop memory for attempt 2

zero-memory exact preflight
→ fits

responses.create() WITHOUT memory
→ success
```

Verify:

```text
attempt_count = 2
provider_preflight_count = 4
D-084 second preflight does not increment attempt_count
D-084 second preflight does not consume transient retry budget
SDK retries = 0
no third logical attempt
```

Also verify there is no whole-operation invariant:

```text
provider_preflight_count <= 2
```

---

## R. `LLMGenerationResult`

Verify:

```text
provider_preflight_count
memory_dropped_after_exact_preflight
```

alongside existing metadata.

No persistence change.

---

## S. Safe Logging

Capture logs.

Safe:

```text
counts
status
conversation_id
token counts
memory flags
preflight count
normalized error
```

Absent:

```text
historical content
query
evidence
full provider input
answer
credentials
```

---

## T. Boundaries

Assert no:

```text
memory table
memory summary
vector memory
query rewriting
citation parser
citation validation
citation persistence
RagRunResult
Step-6.8 tier logic
external retrieval
streaming
background worker
```

---

# 42. Normal Test Isolation

Normal tests require:

```text
NO internet
NO real OpenAI API key
NO paid provider request
```

Use:

```text
fake repository
fake TokenCounter where useful
fake AsyncOpenAI client / existing Step-6.7 fixtures
```

Provider-memory tests must not contact OpenAI.

---

# 43. Verification Commands

Run from `backend/`.

## Focused Step 6.9

```bash
uv run pytest -q \
  tests/test_step69_memory_builder.py \
  tests/test_step69_memory_repository.py \
  tests/test_step69_memory_serialization.py \
  tests/test_step69_memory_provider.py
```

## Step-3.6 Conversation / retry regression

Because exact legacy filename is repository-owned, use the actual existing Conversation API test file(s) discovered during repository inspection.

At minimum run an executable selector equivalent to:

```bash
uv run pytest -q tests -k "conversation or message_retry"
```

and report the exact collected test files/count in the Codex handoff.

Codex must not invent a new Step-3.6 test module merely to avoid running existing tests.

## Step 6.6 regression

```bash
uv run pytest -q \
  tests/test_step66_prompt_schemas.py \
  tests/test_step66_prompt_formatter.py \
  tests/test_step66_prompt_builder.py
```

## Step 6.7 regression

```bash
uv run pytest -q \
  tests/test_step67_tiktoken_counter.py \
  tests/test_step67_llm_serializer.py \
  tests/test_step67_llm_provider.py \
  tests/test_step67_llm_service.py
```

## Earlier relevant Phase-6 regression

Run the accepted Step 6.5 focused suite and any retrieval suite touched indirectly by current-query-isolation tests.

## Full backend

```bash
uv run pytest -q
```

## Compile/import

```bash
uv run python -m compileall -q app tests
```

## Dependency lock

No dependency change is expected.

Run:

```bash
uv lock --check
```

Do not run `uv sync` solely for Step 6.9 unless the actual implementation unexpectedly changes dependencies.

## Alembic

```bash
uv run alembic current
uv run alembic check
```

Expected:

```text
0012_vector_storage_readiness (head)
no new upgrade operations
```

---

# 44. Acceptance Criteria

Step 6.9 implementation passes only when all are true:

```text
[ ] D-070..D-085 preserved.
[ ] Same-Conversation-only memory.
[ ] Current USER excluded.
[ ] Complete USER + final COMPLETED Assistant only.
[ ] FAILED/PENDING attempts excluded.
[ ] Multiple COMPLETED is technical integrity failure.
[ ] RAG_MEMORY_MAX_TURNS default 3.
[ ] Valid range exactly 0..3.
[ ] 0 disables memory.
[ ] No fixed memory-token-cap config.
[ ] Bounded recent-turn repository query exists.
[ ] Full Conversation history is not loaded.
[ ] Existing indexes reused.
[ ] No migration.
[ ] MemoryTurn DTO contains only required runtime fields.
[ ] ConversationMemory DTO exists.
[ ] Whole-turn atomic packing.
[ ] Oldest selected turn dropped first.
[ ] Evidence never removed for memory.
[ ] Memory may be empty without failure.
[ ] Technical DB/token/integrity failures do not become EMPTY.
[ ] Historical Assistant exact citation markers stripped in memory serialization.
[ ] Stored historical Message remains unchanged.
[ ] USER citation-like text is not stripped.
[ ] Memory has no S-labels.
[ ] Memory absent from source_map.
[ ] PromptPackage memory extension is backward-compatible.
[ ] Historical user/assistant roles preserved.
[ ] Current learner payload is final user message.
[ ] System instructions remain separate.
[ ] Same provider input semantics used for preflight and generation.
[ ] D-084 one-to-two exact-preflight fallback implemented per logical attempt.
[ ] Maximum exact preflights per logical attempt is 2.
[ ] Maximum logical generation attempts is 2.
[ ] New transient-retry logical attempt starts fresh from the normal memory-aware request.
[ ] Memory may be reintroduced on a new logical attempt after an earlier attempt dropped it.
[ ] Whole-operation provider_preflight_count is total exact-preflight calls and may reach 4.
[ ] D-084 second preflight does not increment attempt_count or consume transient retry budget.
[ ] Memory-only exact overflow can drop all memory within that logical attempt.
[ ] Zero-memory overflow still fails normally.
[ ] Technical provider-count failure does not silently drop memory.
[ ] Retrieval query remains current-query-only.
[ ] Memory authority prompt addition is narrow.
[ ] No new public memory-specific API error.
[ ] Safe logging contains metadata only.
[ ] No memory persistence subsystem.
[ ] No Step 6.8-A implementation.
[ ] No Step 6.10 citation implementation.
[ ] No new dependency.
[ ] Focused tests pass.
[ ] Conversation/retry regression passes.
[ ] Step 6.6 regression passes.
[ ] Step 6.7 regression passes.
[ ] Relevant earlier Phase-6 regressions pass.
[ ] Full backend passes.
[ ] compileall passes.
[ ] uv lock --check passes.
[ ] Alembic current/check pass with unchanged head.
[ ] Step Note completed.
[ ] Concepts/Tools updated from actual implementation.
[ ] Specialist handoff returned to PM.
```

---

# 45. Required Step Note

After implementation create:

```text
docs/ai/step-6.9-conversation-memory.md
```

Required sections:

- Objective
- Why
- Mental Model
- Core Knowledge
- Data Flow
- Key Design Decisions
- Reusable Approach
- Common Mistakes
- Definition of Done

## MUST KNOW

- short-term conversation memory vs evidence;
- complete-turn memory unit;
- Conversation-local scope;
- current-message exclusion;
- bounded DB reads;
- whole-turn token packing;
- evidence > memory priority;
- D-084 exact-preflight fallback;
- role-preserving serialization;
- valid empty memory vs technical failure;
- message-local citation labels.

## SHOULD KNOW

- retry persistence model;
- local token estimate vs provider exact count;
- immutable runtime DTOs;
- process/provider observability;
- bounded history window trade-offs.

## AWARENESS ONLY

- summarization;
- vector memory;
- contextual query rewriting;
- long-term personalization;
- semantic memory retrieval.

---

# 46. Concepts Discovered

Add only if actually used.

Expected:

| Concept | Category | Step | Role / Why it matters |
|---|---|---|---|
| Conversation-local Short-term Memory | AI | 6.9 | Provides bounded conversational continuity |
| Atomic Conversation Turn | AI | 6.9 | Keeps prior USER/Assistant pair coherent |
| Memory vs Evidence Authority | AI | 6.9 | Prevents historical answers from becoming grounding truth |
| Bounded History Query | DE | 6.9 | Avoids full Conversation history reads |
| Reply Relationship Reconstruction | DE | 6.9 | Reconstructs successful turns from persisted message relations |
| Whole-turn Token Packing | AI | 6.9 | Fits optional history without truncating messages |
| Memory-specific Exact-preflight Fallback | AI | 6.9 | Removes optional memory before failing current grounded request |
| Role-preserving Historical Serialization | AI | 6.9 | Preserves user/assistant conversational structure |
| Message-local Citation Isolation | AI | 6.9 | Prevents historical `[S#]` labels from colliding with current evidence |
| Persistence Invariant Validation | SYSTEM | 6.9 | Fails closed on impossible stored relationships |
| Valid Empty vs Technical Memory Failure | BOTH | 6.9 | Distinguishes optional absence from runtime failure |

Do not classify Conversation persistence itself as BOTH merely because AI consumes it.

---

# 47. Tools Used

Expected if implementation matches this spec:

| Tool | Category | Step | Role / Why used |
|---|---|---|---|
| Python | SYSTEM | 6.9 | Runtime implementation |
| SQLAlchemy | DE | 6.9 | Bounded Conversation/Message lookup |
| PostgreSQL | DE | 6.9 | Existing Conversation/Message persistence |
| tiktoken | AI | 6.9 | Existing model-aware local token counting |
| OpenAI Python SDK | AI | 6.9 | Existing exact preflight and generation path |
| uv | SYSTEM | 6.9 | Lock verification |
| pytest | SYSTEM | 6.9 | Focused/regression verification |

Retain only tools actually used.

---

# 48. Codex Implementation Rules

Before editing:

1. Read Project Context.
2. Read PM Decision Log D-070..D-085.
3. Read this frozen task.
4. Inspect actual Step-3.6 Conversation/Message repository and tests.
5. Inspect actual Step-6.6 PromptPackage.
6. Inspect actual Step-6.7 request serializer/provider.
7. Reconcile only mechanical filename/module differences.

Stop and report to PM if actual repository materially contradicts:

```text
Step-3.6 final-success retry invariant
existing index state
PromptPackage shape
Step-6.7 provider input capability
D-084
D-085
```

Do NOT let Codex decide new architecture.

One Codex task handles this Step only.

---

# 49. Required Specialist Handoff After Implementation

Return:

```text
Step:
6.9 — Conversation Memory

Status:
READY_FOR_SPECIALIST_REVIEW / BLOCKED

What was done:
...

Canonical decisions preserved:
D-070 through D-085

Memory scope:
...

Eligible-turn invariant:
...

Current-message exclusion:
...

RAG_MEMORY_MAX_TURNS:
...

Bounded repository query:
...

Index/migration:
...

ConversationMemory:
...

MemoryTurn:
...

PromptPackage extension:
...

Historical-role serialization:
...

Citation-marker sanitation:
...

Local memory budget:
...

D-084 exact-overflow fallback:
...

Provider preflight count:
...

Technical failure semantics:
...

Logging:
...

6.8-A integration seam:
...

Schema changes:
NO

Migration:
NO

Dependencies changed:
NO

Alembic head:
...

Focused Step-6.9 tests:
...

Step-3.6 regressions:
...

Step-6.6 regressions:
...

Step-6.7 regressions:
...

Earlier Phase-6 regressions:
...

Full backend:
...

compileall:
...

uv lock --check:
...

Alembic check:
...

Concepts added:
...

Tools added:
...

Problems/risks:
...

Decisions needed:
NONE or exact blocker

Step 6.10 started:
NO

Step 6.8-A started:
NO

Recommended next action:
AI Engineering Specialist actual-code review
```

Do not claim PM acceptance.

Do not start Step 6.10 or Step 6.8-A.

---

# 50. Final JIT Freeze

```text
Step: 6.9 — Conversation Memory
Status: READY_FOR_PM_TASK_REVIEW

Repository state reconciled: YES
Canonical decisions preserved: D-070 through D-085

D-084: PRESERVED
D-085: PRESERVED

Memory scope:
same Conversation only

Eligible turn:
prior COMPLETED USER + single final COMPLETED Assistant via reply_to_message_id

Malformed state:
typed technical failure; no silent repair

Current-message exclusion:
USER.sequence_number < current USER sequence_number

RAG_MEMORY_MAX_TURNS:
0..3 inclusive; default 3

Bounded repository query:
completed USER↔Assistant pairs, sequence-bounded, ordered newest-first, LIMIT max_turns+1

Index/migration:
reuse existing indexes; NO migration

ConversationMemory:
immutable runtime DTO; APPLIED | EMPTY

MemoryTurn:
immutable runtime USER/Assistant pair with internal IDs/sequence metadata

PromptPackage extension:
optional provider-independent conversation_memory field

Historical-role request:
project-owned user/assistant messages; current user payload last

Step-6.7 change:
historical_messages + role-aware Responses input; same input semantics for preflight/create

Local memory budget:
model_limit - output_reserve - current_prompt_estimated_input_tokens

Exact-preflight fallback:
per logical attempt: memory exact overflow → drop all memory → one final zero-memory exact preflight

Transient retry interaction:
new logical attempt starts fresh from the normal memory-aware request; D-084 may apply again independently

Provider-preflight count:
total exact provider preflight calls across the full generate(...) operation;
1 or 2 per logical attempt;
maximum 4 across at most 2 logical attempts

Evidence priority:
current evidence > memory

Retrieval isolation:
current normalized query only

Memory authority prompt:
prior Assistant/user claims are contextual; current evidence wins

Citation isolation:
strip exact historical Assistant [S<number>] markers only during memory serialization

Valid empty memory:
normal non-error outcome

Technical failure:
fail closed; internal typed error; public flow remains existing AI_RESPONSE_FAILED / Assistant FAILED semantics

Config:
RAG_MEMORY_MAX_TURNS int 0..3 default 3

Logging:
metadata only; no historical content

6.8-A seam:
derive budget → build memory → attach to PromptPackage → generation

Schema changes:
NO

Migration:
NO

Dependencies:
NO CHANGE

Production code changed during JIT:
NO

Codex run:
NO

Step 6.10 started:
NO

Step 6.8-A started:
NO

Decisions needed:
NONE

Remaining blockers:
NONE
```
