# Codex Execution Task — Step 3.6: Conversation API

## Execution Gate

This is the **single current Codex execution task** for:

**Step 3.6 — Conversation API**

Owner: **App Engineering Specialist**

Implement Step 3.6 only. Do not begin Phase 4 or any later AI/RAG Step.

Before editing, inspect the actual repository. If it materially differs from the accepted Step 3.1–3.5 state described here, or if the canonical PM Decision Log conflicts with this task, stop and report `BLOCKED` rather than redesigning the system.

Do not run destructive tests against a non-test database.

---

# 1. Objective

Implement persistent, authenticated, Lesson-scoped Conversation and Message APIs on top of the accepted Step 3.5 backend.

Step 3.6 must establish:

- learner-owned Lesson Conversations;
- Conversation list/detail/rename/soft-delete;
- persistent USER and ASSISTANT Messages;
- deterministic per-Conversation message ordering;
- explicit Assistant processing state;
- USER-message durability across AI failures;
- retry as a new Assistant processing attempt, not a new USER Message;
- Periodic-Test chat blocking at the frozen validation-time boundary;
- a provider-independent `AIChatService` boundary using only a deterministic Phase-3 stub;
- forward migration `0003_conversation_message_flow`.

Do not integrate real AI/RAG behavior.

---

# 2. Source of Truth

## Primary authoritative Step

Use:

```text
Spec-CURRENT/Phase3/Step 3.6 — Conversation API.md
```

If the local execution checkout uses the bundled source-pack form instead, consult the Step-3.6 section in:

```text
02_APP_ENGINEERING_SPECS_PHASE3-4.md
```

## Required control/dependency sources

Read before editing:

```text
Spec-CURRENT/PROJECT_CONTEXT.md
Spec-CURRENT/PM-Control/04-Decision-Log-and-Open-Gates.md
Spec-CURRENT/PM-Control/05-Codex-Execution-Protocol.md
```

Also inspect only the relevant accepted implementation/specification context for:

- Step 3.3 database/session/Alembic conventions;
- Step 3.4 lesson access, progression, Assessment/Attempt rules;
- Step 3.5 `get_current_user()` integration;
- Phase-2 Conversation/Message persistence.

The canonical Decision Log used for this task must contain D-019 through D-026.

## Precedence

If sources differ, use:

1. canonical PM Decision Log;
2. authoritative Step 3.6 specification;
3. later specification intentionally refining an earlier contract;
4. earlier Phase specifications;
5. notes/examples/plans;
6. this task only as the reviewed execution packet implementing the sources above.

Do not invent a resolution to a real conflict.

---

# 3. Mandatory PM Decisions

The implementation must follow D-001 through D-026 where applicable. The Step-3.6-specific hard contracts are D-019 through D-026.

## D-019 — Conversation public API, privacy and soft deletion

V0 scope is **LESSON only**.

Do not persist a Conversation `scope` column.

### Create

```http
POST /api/v1/conversations
```

Strict request body:

```json
{
  "lesson_id": "<uuid>"
}
```

Reject extra fields such as:

```text
scope
user_id
owner
```

Success:

```text
HTTP 201
→ ConversationResponse
```

`ConversationResponse` exposes exactly the learner-facing Conversation fields:

```text
id
scope = LESSON          # derived API value only
lesson_id
title
created_at
updated_at
```

Do not expose `user_id`.

### Rename

```http
PATCH /api/v1/conversations/{conversation_id}
```

Strict body:

```json
{
  "title": "..." | null
}
```

`title` is the only mutable field.

Rules:

```text
null
→ clear title

non-null
→ trim
→ length 1..200

whitespace-only
→ 422
```

An empty PATCH body is invalid; the `title` field must be present and may explicitly be `null`.

Success:

```text
HTTP 200
→ ConversationResponse
```

### Delete

```http
DELETE /api/v1/conversations/{conversation_id}
```

Soft-delete using `deleted_at`.

Success:

```text
HTTP 204
```

Repeated deletion by the same owner is idempotent and also returns 204.

Do not physically delete Conversations or Messages.

### Privacy

For:

```text
unknown Conversation
OR Conversation belonging to another User
```

return:

```text
HTTP 404
CONVERSATION_NOT_FOUND
```

Do not expose cross-user resource existence.

For an **owned soft-deleted Conversation**, these operations return:

```text
HTTP 410
CONVERSATION_DELETED
```

Operations:

```text
GET Conversation detail
PATCH Conversation
GET Message history
POST Message
Retry Assistant Message
```

Soft-deleted Conversations are excluded from normal list queries.

### Conversation list

```http
GET /api/v1/me/conversations
```

Pagination:

```text
page      default 1
page_size default 20
page_size max 100
```

Stable ordering:

```text
updated_at DESC
id DESC
```

Optional whitelisted filters:

```text
lesson_id
scope = LESSON only
```

`scope` is API-only. `scope=LESSON` is accepted; other values fail request validation. Do not query a persistent scope column.

Response:

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0
}
```

### Message input

Learner Message content:

```text
trim leading/trailing whitespace
length 1..4000 characters after trim
```

Persist the trimmed value.

Client Message creation must not accept:

```text
role
lesson_id
user_id
conversation owner
assistant content
```

Lesson context is always derived from:

```text
conversation.lesson_id
```

## D-020 — Newest-window Message pagination

Message history endpoint:

```http
GET /api/v1/conversations/{conversation_id}/messages
```

Pagination:

```text
page      default 1
page_size default 50
page_size max 100
```

Page semantics:

```text
page 1
→ newest N Messages

page 2
→ next older N Messages
```

The database may select:

```text
sequence_number DESC
OFFSET / LIMIT
```

but the `items` returned **inside each page** must be sorted:

```text
sequence_number ASC
```

Response:

```json
{
  "items": [],
  "page": 1,
  "page_size": 50,
  "total": 0
}
```

Do not add cursor pagination.

## D-021 — Sequence allocation and Conversation activity

Serialize Message creation per Conversation by locking the Conversation row.

Do not add `next_sequence_number`.

Database safety:

```text
UNIQUE(conversation_id, sequence_number)
```

### Normal send — Transaction A

```text
SELECT Conversation ... FOR UPDATE

→ validate owner/state
→ evaluate chat availability
→ next = MAX(sequence_number) + 1

→ create USER:
   sequence_number = next
   role = USER
   status = COMPLETED
   content = trimmed learner content

→ create ASSISTANT:
   sequence_number = next + 1
   role = ASSISTANT
   status = PENDING
   content = null
   reply_to_message_id = USER.id

→ update Conversation.updated_at
→ COMMIT
```

If no prior Message exists, the first USER Message uses `sequence_number = 1`.

Transaction A must commit before the AI boundary is called.

### Retry attempt creation

```text
lock Conversation FOR UPDATE
→ validate retry using D-022
→ next = MAX(sequence_number) + 1
→ create one new ASSISTANT PENDING
→ reply_to_message_id = original USER Message
→ update Conversation.updated_at
→ COMMIT
```

`Conversation.updated_at` changes on:

```text
Conversation rename
new USER turn creation
new retry attempt creation
```

AI completion/failure in Transaction B does not require another `updated_at` bump.

Concurrency is serialized only within the same Conversation. Do not globally serialize different Conversations.

## D-022 — Retry eligibility and concurrency

Retry endpoint:

```http
POST /api/v1/messages/{assistant_message_id}/retry
```

A retry target is valid only when:

```text
target.role = ASSISTANT
target.status = FAILED
target belongs to the current User through its Conversation
Conversation is not deleted
target.reply_to_message_id identifies the original USER Message
the original USER Message exists in the same Conversation and is role USER
target is the latest Assistant processing attempt for that USER Message
```

The retry relationship is grouped by:

```text
reply_to_message_id = original USER Message id
```

A valid retry creates exactly one new Assistant PENDING attempt.

If a later Assistant attempt already exists for the original USER Message:

```text
HTTP 409
INVALID_MESSAGE_RETRY
```

Concurrent retries serialize on the Conversation row:

```text
first retry
→ new PENDING attempt

second concurrent retry
→ sees newer attempt
→ 409 INVALID_MESSAGE_RETRY
```

If the new attempt fails, the learner may retry using **that new failed Assistant ID**.

If the latest attempt succeeds, no further retry is allowed for that USER Message.

Retry must re-evaluate the active Periodic-Test rule before creating a new Assistant attempt.

## D-023 — AIChatService boundary and AI failure HTTP contract

Application boundary:

```text
ConversationService
→ AIChatService.generate_reply(ChatRequest)
```

`ChatRequest` contains backend-owned scalar/value data only:

```text
user_id
conversation_id
lesson_id
user_message_id
content
```

Do not pass:

```text
AsyncSession
ORM objects
provider credentials
retrieval objects
```

Successful AI result is a non-empty Assistant content string.

Technical processing failure is represented internally by a typed error equivalent to:

```text
AIChatProcessingError
```

Do not expose internal exception/provider text.

### Phase-3 implementation

Use only a deterministic fake/stub `AIChatService`.

The default Phase-3 implementation may return one deterministic non-empty stub response. The exact wording is **not** a public product contract.

Tests must be able to inject deterministic success and deterministic failure implementations.

Do not add an AI/provider SDK.

### Send success

```http
POST /api/v1/conversations/{conversation_id}/messages
```

Success:

```text
HTTP 201
```

Response:

```json
{
  "user_message": { "...": "MessageResponse" },
  "assistant_message": { "...": "MessageResponse" }
}
```

Returned Assistant status is `COMPLETED`.

### Send AI failure

First persist Transaction B:

```text
Assistant PENDING
→ status = FAILED
→ content = null
→ COMMIT
```

Then return:

```text
HTTP 502
AI_RESPONSE_FAILED
```

Safe error `details` may contain only:

```json
{
  "user_message_id": "<uuid>",
  "assistant_message_id": "<uuid>"
}
```

The USER Message must remain persisted.

### Retry success

```text
HTTP 201
→ MessageResponse for the newly-created Assistant attempt
```

### Retry AI failure

Persist the new Assistant attempt as `FAILED`, then return:

```text
HTTP 502
AI_RESPONSE_FAILED
```

Safe `details` contains only:

```text
assistant_message_id
```

## D-024 — Migration 0003

Migration chain must become:

```text
0001_initial_schema
→ 0002_auth_token_tables
→ 0003_conversation_message_flow
```

Do not modify `0001` or `0002`.

### Conversation change

Add:

```text
deleted_at TIMESTAMPTZ NULL
```

### Message changes

Migration sequence:

1. Add nullable columns:

```text
sequence_number INTEGER NULL
reply_to_message_id UUID NULL
```

2. Backfill `sequence_number` deterministically:

```sql
ROW_NUMBER()
OVER (
  PARTITION BY conversation_id
  ORDER BY created_at ASC, id ASC
)
```

3. Alter:

```text
sequence_number → NOT NULL
```

4. Add:

```text
UNIQUE(conversation_id, sequence_number)
```

5. Add self-referencing FK:

```text
reply_to_message_id → messages.id
ON DELETE RESTRICT / NO ACTION
```

Do not cascade-delete reply history.

6. Add index:

```text
messages(reply_to_message_id)
```

Do not destructively rewrite existing Conversation/Message indexes merely for this Step.

Historical rows:

```text
sequence_number
→ deterministic backfill

reply_to_message_id
→ NULL
```

Do not infer historical Assistant→USER links from timestamp/sequence proximity.

Do not modify citation/retrieval persistence.

## D-025 — Canonical MessageResponse and Message errors

Use exactly one public Message representation:

```text
MessageResponse
- id
- conversation_id
- sequence_number
- role
- content
- status
- reply_to_message_id
- created_at
```

Types:

```text
role = USER | ASSISTANT
status = PENDING | COMPLETED | FAILED
content = string | null
reply_to_message_id = UUID | null
```

Do not expose:

```text
User identity
AI/provider internals
retrieval state
citations
provider metadata
```

Use `MessageResponse` in:

```text
Message history page items
send-message user_message
send-message assistant_message
retry success response
```

Unknown Message or a Message belonging through another User's Conversation:

```text
HTTP 404
CONVERSATION_NOT_FOUND
```

Do not expose Message/Conversation existence.

Owned invalid retry because of wrong role, non-FAILED status, not-latest attempt, or invalid/missing original USER relationship:

```text
HTTP 409
INVALID_MESSAGE_RETRY
```

Active Periodic Test blocks a new send/retry:

```text
HTTP 409
AI_CHAT_DISABLED_DURING_TEST
```

The blocked operation creates **no new Message**.

All errors use the existing project error envelope.

## D-026 — Periodic-Test/chat validation-time snapshot semantics

Do **not** add cross-domain global User locks or modify Step-3.4 assessment-start lock ordering solely for chat.

For a new send or retry, inside Transaction A:

```text
lock Conversation as required
→ evaluate active Periodic Test from committed database state
```

If at that validation point:

```text
Assessment.type = PERIODIC_TEST
AND
AssessmentAttempt.status = IN_PROGRESS
```

then:

```text
409 AI_CHAT_DISABLED_DURING_TEST
→ no new USER Message
→ no new Assistant attempt
```

If no active Periodic Test exists at validation time, Transaction A may create/commit the turn.

After Transaction A commits, the turn is considered started.

If a Periodic Test begins later:

```text
do not cancel the turn
do not roll back USER/PENDING Assistant
allow Transaction B to finalize
```

The same non-retroactive rule applies if the Conversation is soft-deleted after Transaction A commits:

```text
Conversation becomes unavailable to new learner operations
but already-started Assistant processing may finalize in Transaction B
```

Do not add:

```text
global User serialization
cross-domain User lock coupling
new Step-3.4 lock ordering
AI cancellation infrastructure
background cancellation
```

---

# 4. Accepted Current Repository State

Steps 3.1–3.5 are accepted and closed.

Relevant actual backend state before Step 3.6:

```text
backend/app/
├── auth/                 # real Step-3.5 authentication
├── admin/
├── curriculum/
├── exercise/
├── progress/
├── ai/__init__.py
├── database/
│   ├── session.py
│   └── models/
│       └── conversation.py
└── main.py
```

No `app/conversation/` application module exists yet.

Current persistence model from accepted Phase 2:

```text
conversations
- id UUID PK
- user_id UUID NOT NULL FK users.id
- lesson_id UUID NOT NULL FK lessons.id
- title TEXT NULL
- created_at
- updated_at
- index(user_id, updated_at)

messages
- id UUID PK
- conversation_id UUID NOT NULL FK conversations.id
- role USER | ASSISTANT
- content TEXT NULL
- status PENDING | COMPLETED | FAILED
- created_at
- index(conversation_id, created_at)
```

Existing Message checks already permit nullable content for PENDING/FAILED Assistant rows and require non-empty content for COMPLETED rows.

Current migrations:

```text
0001_initial_schema.py
0002_auth_token_tables.py
```

Step 3.3 session convention remains:

```text
request-scoped AsyncSession
repository → no commit
service/application → commit/rollback ownership
```

Step 3.5 `get_current_user()` resolves the authoritative database User.

Step 3.4 already provides authoritative lesson access through Progress domain behavior equivalent to:

```text
ProgressService.require_lesson_access(session, user_id, lesson_id)
```

Accepted behavior includes:

```text
AVAILABLE lesson → accessible
COMPLETED lesson → accessible
LOCKED lesson → LESSON_LOCKED
```

Exercise currently owns Assessment/Attempt persistence. Add only a focused Exercise-domain read use case for the active Periodic-Test check; do not move Assessment rules into Conversation.

---

# 5. Required Architecture

Preserve:

```text
Conversation Router
→ ConversationService
→ ConversationRepository
→ AsyncSession / ORM
```

Cross-domain calls:

```text
ConversationService
→ ProgressService         # lesson access at Conversation creation
→ ExerciseService         # active Periodic-Test read check for send/retry
→ AIChatService           # processing boundary
```

## Router responsibilities

- HTTP request/response;
- `get_current_user()` dependency;
- Pydantic validation;
- pagination query validation;
- inject `AIChatService`;
- call ConversationService;
- no ownership, sequence, retry or transaction rules.

## ConversationService responsibilities

- ownership/privacy semantics;
- soft-delete semantics;
- Step-3.4 lesson-access orchestration;
- active Periodic-Test orchestration;
- send/retry state machines;
- sequence allocation orchestration;
- transaction boundaries;
- AI boundary invocation outside transactions;
- stable application errors.

## ConversationRepository responsibilities

Own SQL/ORM operations for:

- Conversation lookup/list/create/update/soft-delete;
- row locking;
- Message lookup/list/create/finalize;
- sequence queries;
- latest Assistant attempt lookup;
- persistence `flush()` when needed.

Repository must **not** call `commit()` or `rollback()`.

Do not make one generic repository for unrelated domains.

## Exercise domain addition

Add a focused application use case equivalent to:

```text
ExerciseService.has_active_periodic_test(session, user_id) -> bool
```

The SQL belongs in `exercise.repository`.

The query is conceptually:

```text
AssessmentAttempt
JOIN Assessment
WHERE user_id = current user
  AND AssessmentAttempt.status = IN_PROGRESS
  AND Assessment.type = PERIODIC_TEST
```

This is a committed-state read. Do not add cross-domain locking.

---

# 6. Expected Files / Components

Inspect the repository first. Reconcile with existing conventions rather than duplicating equivalent code.

Expected new application files:

```text
backend/app/conversation/__init__.py
backend/app/conversation/router.py
backend/app/conversation/schemas.py
backend/app/conversation/service.py
backend/app/conversation/repository.py
backend/app/conversation/ai_chat.py
```

Expected modifications:

```text
backend/app/main.py
backend/app/database/models/conversation.py
backend/app/exercise/repository.py
backend/app/exercise/service.py
backend/app/database/models/__init__.py       # only if required by existing export convention
```

Migration:

```text
backend/migrations/versions/0003_conversation_message_flow.py
```

Tests: add focused Step-3.6 test files under:

```text
backend/tests/
```

Create Step Note:

```text
docs/backend/step-3.6-conversation-api.md
```

Do not change dependencies unless a real blocker is discovered. The accepted stack is sufficient.

If a new runtime dependency appears necessary, stop `BLOCKED`; do not add one autonomously.

---

# 7. API Schemas and OpenAPI Contract

Use Pydantic models with strict public request contracts (`extra="forbid"` or equivalent).

## ConversationCreateRequest

```text
lesson_id: UUID
```

No other public fields.

## ConversationPatchRequest

```text
title: str | null      # required field, explicit null allowed
```

Validation implements D-019 exactly.

## ConversationResponse

```text
id: UUID
scope: Literal["LESSON"]
lesson_id: UUID
title: str | null
created_at: datetime
updated_at: datetime
```

Do not expose `user_id` or `deleted_at`.

## ConversationPage

```text
items: list[ConversationResponse]
page: int
page_size: int
total: int
```

## MessageCreateRequest

```text
content: str
```

Trim + validate 1..4000 after trim.

No role/user/lesson/assistant fields.

## MessageResponse

Exactly D-025:

```text
id: UUID
conversation_id: UUID
sequence_number: int
role: Literal["USER", "ASSISTANT"]
content: str | null
status: Literal["PENDING", "COMPLETED", "FAILED"]
reply_to_message_id: UUID | null
created_at: datetime
```

## MessagePage

```text
items: list[MessageResponse]
page: int
page_size: int
total: int
```

## SendMessageResponse

```text
user_message: MessageResponse
assistant_message: MessageResponse
```

## Retry response

Return `MessageResponse` directly for the newly-created Assistant attempt.

OpenAPI must accurately expose:

- all Step-3.6 paths;
- status codes;
- strict request models;
- canonical Message shape;
- pagination defaults/bounds;
- no client-controlled identity/role/lesson context on Message creation.

---

# 8. Public API Surface

Implement exactly:

```http
POST   /api/v1/conversations
GET    /api/v1/me/conversations
GET    /api/v1/conversations/{conversation_id}
PATCH  /api/v1/conversations/{conversation_id}
DELETE /api/v1/conversations/{conversation_id}
GET    /api/v1/conversations/{conversation_id}/messages
POST   /api/v1/conversations/{conversation_id}/messages
POST   /api/v1/messages/{assistant_message_id}/retry
```

All endpoints require real Step-3.5 authentication.

Do not expose Admin Conversation APIs or GLOBAL Conversation APIs.

---

# 9. Conversation Use Cases

## Create Conversation

Flow:

```text
current User from get_current_user()
→ ProgressService.require_lesson_access(user.id, lesson_id)
→ create Conversation(user_id=user.id, lesson_id=lesson_id)
→ commit
→ 201 ConversationResponse
```

Multiple Conversations for the same User + Lesson are allowed.

Do not add a unique User/Lesson constraint.

Conversation creation itself is not blocked solely because a Periodic Test is active. The Periodic-Test rule is applied when starting an AI processing operation: send/retry.

## List

Only rows owned by the current User and `deleted_at IS NULL`.

Apply D-019 filters/pagination/order.

`scope=LESSON` is an accepted no-op semantic filter because all V0 Conversations are LESSON-scoped; no scope column exists.

## Detail

Lookup by:

```text
conversation_id + current_user.id
```

so cross-owner resources are indistinguishable from unknown resources.

If owned row exists but is soft-deleted:

```text
410 CONVERSATION_DELETED
```

Do not include unbounded Message history.

## Rename

Lock or otherwise safely load the owned Conversation for mutation.

If deleted → 410.

Set/clear title and update `updated_at`.

Commit.

## Delete

Use an ownership lookup that can see an already-deleted owned row.

Behavior:

```text
unknown/cross-owner → 404 CONVERSATION_NOT_FOUND
active owned row     → set deleted_at, commit, 204
already deleted row  → no-op, 204
```

Deletion must coordinate through Conversation-row locking so send/retry/delete on one Conversation serialize consistently.

Do not physically delete Messages/citations/retrieval history.

---

# 10. Message History

Validate owned Conversation first.

If deleted → 410.

Apply D-020 newest-window semantics.

Use `sequence_number` as the authoritative chronology field.

Do not rely on `created_at` for ordering once Step 3.6 is active.

Return canonical `MessageResponse` only.

Do not join/expose citations or retrieval state in Step 3.6.

---

# 11. Send Message — Exact Workflow

Endpoint:

```http
POST /api/v1/conversations/{conversation_id}/messages
```

## Request validation

Pydantic layer:

```text
content trimmed
1..4000 after trim
extra fields rejected
```

## Transaction A

Perform in one short service-owned transaction:

```text
1. Lock owned Conversation row FOR UPDATE.
2. If no owned row → 404 CONVERSATION_NOT_FOUND.
3. If deleted → 410 CONVERSATION_DELETED.
4. Query Exercise domain for active Periodic Test using committed DB state.
5. If active → 409 AI_CHAT_DISABLED_DURING_TEST; create nothing.
6. Allocate next sequence under the Conversation lock.
7. Persist USER COMPLETED.
8. Persist ASSISTANT PENDING linked to USER.
9. Touch Conversation.updated_at.
10. Commit.
```

Materialize the scalar `ChatRequest` values before leaving Transaction A.

## AI processing

After Transaction A has committed and the request-scoped `AsyncSession` has no intentionally open transaction:

```text
AIChatService.generate_reply(ChatRequest)
```

No DB session/ORM object is supplied to the AI boundary.

No network/provider call exists in Phase 3.

## Transaction B — success

In a new short transaction:

```text
1. Lock/reload the specific Assistant Message.
2. Confirm it is still the expected PENDING Assistant attempt.
3. Validate generated content is a non-empty string.
4. Set content.
5. Set status = COMPLETED.
6. Commit.
```

Do **not** re-check:

```text
Conversation deleted_at
active Periodic Test
lesson availability
```

in a way that cancels the already-started turn.

D-026 explicitly allows finalization after those later state changes.

Return HTTP 201 + `SendMessageResponse`.

## Transaction B — AI failure

For typed `AIChatProcessingError`:

```text
1. Begin new short transaction.
2. Lock/reload the specific PENDING Assistant.
3. Set status = FAILED.
4. Set content = null.
5. Commit.
6. Return normalized HTTP 502 AI_RESPONSE_FAILED.
```

Safe details:

```text
user_message_id
assistant_message_id
```

Never roll back/delete Transaction-A USER history because AI processing failed.

The Phase-3 `AIChatService` implementation should translate its deliberate failure mode into the typed application error. Do not expose raw implementation exceptions to the client.

---

# 12. Retry — Exact Workflow

Endpoint:

```http
POST /api/v1/messages/{assistant_message_id}/retry
```

## Privacy pre-resolution

Resolve the target Assistant through the current User's Conversation ownership without exposing cross-user existence.

Unknown/cross-owner target:

```text
404 CONVERSATION_NOT_FOUND
```

## Transaction A

Serialize on the target Conversation row:

```text
1. Lock Conversation FOR UPDATE.
2. Re-read/revalidate target Message while lock is held.
3. If owned Conversation deleted → 410 CONVERSATION_DELETED.
4. Validate target role/status/reply relation.
5. Load original USER Message and validate same Conversation + role USER.
6. Find latest Assistant attempt where reply_to_message_id = original USER id.
7. Target must be that latest attempt.
8. Query active Periodic Test from committed DB state.
9. If active → 409 AI_CHAT_DISABLED_DURING_TEST; create nothing.
10. Allocate max(sequence_number)+1.
11. Persist new ASSISTANT PENDING, content null, same reply_to_message_id.
12. Touch Conversation.updated_at.
13. Commit.
```

Owned invalid retry state returns:

```text
409 INVALID_MESSAGE_RETRY
```

Do not modify or delete the original failed Assistant.

## AI processing / Transaction B

Use the **original USER Message content and identity** to build the new `ChatRequest`.

Then apply the same D-023 processing/finalization rules as normal send.

On success:

```text
201 MessageResponse
```

On failure:

```text
new Assistant persists FAILED
502 AI_RESPONSE_FAILED
safe details: assistant_message_id only
```

A later retry, if needed, must target the newest failed Assistant ID.

---

# 13. Periodic-Test Chat Rule

Add a focused Exercise-domain read boundary rather than duplicating assessment SQL in Conversation.

Blocked only when:

```text
Assessment.type = PERIODIC_TEST
AND
AssessmentAttempt.user_id = current user
AND
AssessmentAttempt.status = IN_PROGRESS
```

Do not block for:

```text
LESSON_EXERCISE IN_PROGRESS
SUBMITTED/GRADED/GRADING_FAILED periodic attempts
```

D-026 semantics:

```text
state observed at Transaction-A validation point
→ authoritative for whether this operation may start
```

Do not cancel a turn after Transaction A commits if a Periodic Test begins later.

Do not modify accepted Step-3.4 attempt-start locking to create a User-wide mutex.

---

# 14. AIChatService Boundary

Create an application boundary equivalent to:

```text
ChatRequest
AIChatService
AIChatProcessingError
DeterministicStubAIChatService
get_ai_chat_service() / equivalent injectable dependency
```

`ChatRequest` contains only:

```text
user_id
conversation_id
lesson_id
user_message_id
content
```

Use plain dataclass/Pydantic/value types as appropriate. Do not pass ORM objects.

The default Phase-3 stub:

- is deterministic;
- returns one non-empty response;
- uses no network;
- has no provider credentials;
- has no RAG/retrieval behavior.

Tests must inject a failure-capable fake/stub without changing service business logic.

Do not implement a `DomainGuard` unless a tiny interface is genuinely required by current Step-3.6 code. Do not add LLM-based classification.

---

# 15. Persistence / ORM Changes

Update accepted ORM metadata to match D-024 exactly.

## Conversation

Add:

```text
deleted_at: timezone-aware datetime | null
```

Keep:

```text
user_id NOT NULL
lesson_id NOT NULL
```

Do not add a scope column.

## Message

Add:

```text
sequence_number INTEGER NOT NULL
reply_to_message_id UUID NULL FK messages.id ON DELETE RESTRICT/NO ACTION
```

Add:

```text
UNIQUE(conversation_id, sequence_number)
INDEX(reply_to_message_id)
```

Keep existing role/status/content checks.

Application writes must ensure a new Assistant `reply_to_message_id` points to the original USER Message in the same Conversation.

Do not attempt to encode same-Conversation reply integrity through an additional schema redesign in Step 3.6.

---

# 16. Migration 0003

Create only:

```text
0003_conversation_message_flow.py
```

Its `down_revision` must point to the accepted `0002_auth_token_tables` revision.

Do not modify 0001 or 0002.

Upgrade must perform D-024 in a safe order:

```text
1. add conversations.deleted_at nullable
2. add messages.sequence_number nullable
3. add messages.reply_to_message_id nullable
4. deterministically backfill sequence_number using ROW_NUMBER partitioned by conversation
5. alter sequence_number NOT NULL
6. add unique(conversation_id, sequence_number)
7. add self FK for reply_to_message_id with RESTRICT/NO ACTION semantics
8. add index on reply_to_message_id
```

Historical reply IDs remain null.

Do not infer reply relationships.

Downgrade must remove only the Step-3.6 additions in reverse-safe order.

No changes to:

```text
message_citations
message_retrievals
chunks
knowledge/RAG tables
```

---

# 17. Transaction Rules

Preserve Step-3.3 semantics:

```text
repository
→ no commit / rollback

service/application
→ transaction owner
```

Use short transactions.

Do not intentionally hold a PostgreSQL transaction while invoking `AIChatService`.

Do not call AI from inside a repository.

Do not use background tasks/workers to avoid the synchronous contract.

For per-Conversation mutation:

```text
Conversation row lock
→ one Conversation only
```

Do not acquire a User-wide lock for Step 3.6.

Use the database unique constraint as the final sequence-allocation safety net.

---

# 18. Error Contract

Use the existing normalized project error envelope.

Required Step-3.6 business errors:

```text
LESSON_LOCKED
CONVERSATION_NOT_FOUND
CONVERSATION_DELETED
AI_CHAT_DISABLED_DURING_TEST
INVALID_MESSAGE_RETRY
AI_RESPONSE_FAILED
```

Required statuses:

```text
LESSON_LOCKED                    → existing Step-3.4 status (403)
CONVERSATION_NOT_FOUND           → 404
CONVERSATION_DELETED             → 410
AI_CHAT_DISABLED_DURING_TEST     → 409
INVALID_MESSAGE_RETRY            → 409
AI_RESPONSE_FAILED               → 502
AUTHENTICATION_REQUIRED          → existing Step-3.5 401
```

Use stable safe messages such as:

```text
CONVERSATION_NOT_FOUND       → "Conversation was not found"
CONVERSATION_DELETED         → "Conversation has been deleted"
AI_CHAT_DISABLED_DURING_TEST → "AI chat is disabled during an active periodic test"
INVALID_MESSAGE_RETRY        → "Message retry is not valid"
AI_RESPONSE_FAILED           → "AI response processing failed"
```

Do not expose SQL, provider, stack-trace or internal exception text.

Validation errors remain normalized according to the accepted project-wide request-validation handler.

---

# 19. Testing Requirements

Use the dedicated PostgreSQL test database. Do not substitute SQLite for DB/concurrency/migration behavior.

Add focused tests covering at least the following.

## Authentication / ownership

- all Step-3.6 endpoints require real authenticated current User;
- create request cannot choose `user_id`;
- no GLOBAL scope in create;
- cross-user Conversation detail → 404;
- cross-user message history → 404;
- cross-user retry target → 404 `CONVERSATION_NOT_FOUND`;
- response models never expose `user_id`.

## Conversation creation / lesson access

- AVAILABLE Lesson create → 201;
- COMPLETED Lesson create → 201;
- LOCKED Lesson → 403 `LESSON_LOCKED`;
- multiple Conversations for same User + Lesson succeed;
- no unique User/Lesson constraint introduced.

## Conversation title / detail / list

- detail response exact shape;
- title trimmed;
- title 200 chars accepted;
- title 201 chars rejected;
- whitespace-only title rejected;
- explicit null clears title;
- empty PATCH rejected;
- list excludes deleted;
- `lesson_id` filter;
- `scope=LESSON` accepted;
- invalid scope rejected;
- page/page_size defaults and max;
- stable `updated_at DESC, id DESC` ordering.

## Soft deletion

- first delete → 204;
- repeated same-owner delete → 204;
- unknown/cross-owner delete → 404;
- deleted detail → 410;
- deleted rename → 410;
- deleted history → 410;
- deleted send → 410;
- deleted retry → 410;
- physical Conversation/Message history remains in DB.

## Message input / OpenAPI

- whitespace-only content rejected;
- content is trimmed before persistence;
- 4000-char content accepted;
- 4001-char content rejected;
- extra `role`, `lesson_id`, `user_id`, `assistant content` fields rejected;
- exact D-025 `MessageResponse` OpenAPI schema;
- exact send response schema;
- exact retry response schema;
- canonical role/status enums;
- no citation/retrieval/provider fields.

## Pagination

Seed enough ordered Messages to prove D-020:

```text
page 1 = newest window
page 2 = older window
items inside each page = sequence ASC
```

Verify `total` and page-size bounds.

## Sequence allocation

- first USER/Assistant use sequence 1/2;
- later send continues sequence;
- retry consumes one new sequence;
- `UNIQUE(conversation_id, sequence_number)` exists;
- concurrent sends to the **same Conversation** using separate PostgreSQL sessions produce unique deterministic sequences and no lost turn;
- different Conversations are not globally serialized.

## Reply integrity

- normal Assistant points to its USER Message;
- retry Assistant points to the same original USER Message;
- retry does not create another USER Message;
- application rejects missing/invalid original USER relationship for retry;
- historical migrated rows may have null reply relation.

## AI success / failure

Success:

```text
Transaction A committed
AI called with ChatRequest scalars only
Assistant finalized COMPLETED
201
```

Failure:

```text
USER remains COMPLETED
Assistant remains persisted FAILED
content null
502 AI_RESPONSE_FAILED
safe details only
```

Verify no DB transaction is intentionally open when the fake AI service is invoked. A service-level test may inject a fake that observes the request session's transaction state through the test closure; the AI interface itself must not receive the session.

## Retry state machine

- retry of latest FAILED Assistant → 201 new Assistant;
- original failed Assistant unchanged;
- retry success → latest COMPLETED and no further retry;
- retry failure → new latest FAILED; retrying **that new ID** works;
- retrying older failed ID after later attempt exists → 409;
- wrong role/non-FAILED target → 409;
- two concurrent retries → exactly one creates a new PENDING attempt; other → 409;
- no duplicate USER Message.

## Periodic-Test rule

- active `PERIODIC_TEST` IN_PROGRESS blocks send with 409 and creates zero Messages;
- active `PERIODIC_TEST` IN_PROGRESS blocks retry with 409 and creates zero new attempt;
- active `LESSON_EXERCISE` IN_PROGRESS does **not** block;
- completed/terminal Periodic-Test attempt does not block.

## D-026 snapshot races

Use deterministic synchronization in integration tests where practical.

### Periodic Test begins after Transaction A

```text
send/retry Transaction A commits
→ fake AI pauses
→ another PostgreSQL session starts Periodic Test
→ fake AI resumes
→ Transaction B finalizes Assistant
```

Expected: already-started turn succeeds/fails according to AI result; it is not cancelled by the later test start.

### Soft delete after Transaction A

```text
send/retry Transaction A commits
→ fake AI pauses
→ Conversation soft-delete commits
→ fake AI resumes
→ Transaction B finalizes Assistant
```

Expected:

- processing finalizes persisted Assistant;
- Conversation remains deleted;
- future learner detail/history/send/retry follow 410 rules.

### Send/delete serialization before Transaction-A commit

Exercise both lock orders if practical:

```text
delete wins first
→ later send sees deleted and returns 410

send wins first
→ turn starts; later delete does not cancel Transaction B
```

Do not add User-wide locks merely to make tests deterministic.

## Migration 0003

PostgreSQL migration test must cover:

```text
existing DB at 0002
+ existing Conversation
+ multiple historical Messages
→ upgrade 0003
```

Verify:

- every Conversation/Message preserved;
- `deleted_at` added nullable;
- sequence backfill uses deterministic `created_at ASC, id ASC` per Conversation;
- sequences restart per Conversation;
- sequence values unique per Conversation;
- historical `reply_to_message_id` remains null;
- self FK exists with non-cascade semantics;
- reply index exists;
- 0001 and 0002 unchanged;
- citation/retrieval rows/schema unaffected where representative fixtures are feasible;
- `alembic check` passes after ORM updates.

## Architecture regression

Add a lightweight AST/source regression test equivalent to previous Steps:

- ConversationService does not call `session.execute/add/delete` directly for persistence;
- ConversationRepository contains no `commit/rollback`;
- Conversation router contains no core state-machine logic;
- AIChatService does not import/use AsyncSession or ORM model types;
- Conversation module contains no real LLM/RAG/provider SDK usage.

## Full regression

Run all accepted Steps 3.1–3.5 tests.

---

# 20. Verification Commands

At minimum:

```bash
cd backend
uv sync
uv run python -c "from app.main import app; assert app is not None"
uv run python -c "from app.main import app; s=app.openapi(); assert '/api/v1/conversations' in s['paths']; assert '/api/v1/messages/{assistant_message_id}/retry' in s['paths']"
uv run alembic upgrade head
uv run alembic check
uv run pytest -q
```

Use the configured dedicated PostgreSQL test environment.

If PostgreSQL/pgvector is unavailable, report required integration/concurrency/migration verification as `PARTIAL`/`BLOCKED`; do not claim full DONE using SQLite or mocks.

---

# 21. Acceptance Criteria

## Architecture

- [ ] Conversation Router → ConversationService → ConversationRepository → AsyncSession preserved.
- [ ] Repositories own SQL/ORM persistence and never commit.
- [ ] Service/application owns transactions.
- [ ] `ConversationService → AIChatService` boundary is explicit.
- [ ] `AIChatService` receives no session/ORM object.
- [ ] No DB transaction intentionally remains open during AI processing.

## Conversation

- [ ] LESSON-only public scope.
- [ ] No persistent scope column.
- [ ] Authenticated ownership only.
- [ ] Cross-owner privacy returns 404.
- [ ] Multiple Conversations per User + Lesson allowed.
- [ ] Locked Lesson rejected on Conversation creation.
- [ ] Completed Lesson remains allowed.
- [ ] Title contract exact.
- [ ] List pagination/filter/order exact.
- [ ] Soft delete exact and idempotent.
- [ ] Deleted Conversation normal operations return 410.

## Message

- [ ] Canonical D-025 MessageResponse used everywhere.
- [ ] Input trim/1..4000/strict extra-field behavior exact.
- [ ] Lesson/user/role cannot be spoofed.
- [ ] `sequence_number` is deterministic and unique per Conversation.
- [ ] Same-Conversation concurrent sends serialize correctly.
- [ ] Assistant reply relationship points to original USER.
- [ ] Message history uses D-020 newest-window pagination.

## AI processing

- [ ] Transaction A persists USER + PENDING Assistant before AI.
- [ ] USER survives AI failure.
- [ ] Success finalizes COMPLETED.
- [ ] Failure finalizes FAILED then returns 502.
- [ ] Phase-3 implementation is deterministic fake/stub only.
- [ ] No real provider/RAG/embedding/retrieval logic.

## Retry

- [ ] Only latest FAILED Assistant attempt is retryable.
- [ ] Retry creates a new Assistant attempt only.
- [ ] Original USER is not duplicated.
- [ ] Concurrent retry produces one new attempt.
- [ ] Older failed attempts become non-retryable after a later attempt exists.
- [ ] Sequential retries after repeated failures remain possible using latest failed ID.

## Periodic Test / concurrency

- [ ] Active Periodic Test blocks new send/retry at validation time.
- [ ] Lesson Exercise does not block chat.
- [ ] D-026 validation-time snapshot semantics are preserved.
- [ ] Later Periodic-Test start does not cancel an already-started AI turn.
- [ ] Later soft delete does not cancel an already-started AI turn.
- [ ] No cross-domain User-wide lock added.

## Migration

- [ ] Only forward `0003_conversation_message_flow` added.
- [ ] 0001/0002 unchanged.
- [ ] Historical sequence backfill deterministic.
- [ ] Historical reply relationships remain null.
- [ ] Unique sequence constraint/self-FK/index exact.
- [ ] No citation/RAG/global-chat schema change.
- [ ] ORM metadata and migration agree.

## Scope

- [ ] No GLOBAL chat.
- [ ] No real LLM/provider SDK.
- [ ] No RAG/embeddings/reranking/citation generation.
- [ ] No SSE/WebSocket/streaming.
- [ ] No background queue/worker.
- [ ] No frontend/Phase-4 work.
- [ ] No unnecessary dependency.
- [ ] Step Note created.
- [ ] Full relevant regression suite passes.

---

# 22. Step Note

Create:

```text
docs/backend/step-3.6-conversation-api.md
```

Include:

- Objective
- Why
- Mental Model
- Core Knowledge
- Data Flow
- Key Design Decisions
- Reusable approach for another project
- Common Mistakes
- Definition of Done
- Concepts Actually Used
- Tools Actually Used

The note must explicitly explain the two-transaction mental model:

```text
Persist intent/history
→ commit
→ external/AI processing
→ short finalization transaction
```

and why retry creates a new Assistant processing attempt rather than rewriting history.

---

# 23. Expected Concepts

Record only concepts actually implemented.

| Concept | Category | Role |
|---|---|---|
| Conversation ownership | SYSTEM | Keeps learner Conversation data private to authenticated Users. |
| Soft deletion | SYSTEM | Hides learner resources while preserving historical persistence. |
| Deterministic sequence allocation | SYSTEM | Gives Messages stable chronology independent of timestamp precision. |
| Row-level locking | SYSTEM | Serializes per-Conversation send/retry/delete mutation. |
| Message processing state machine | SYSTEM | Represents PENDING/COMPLETED/FAILED Assistant processing. |
| Reply relationship | SYSTEM | Links every Assistant processing attempt to the original USER Message. |
| Two-transaction external-call pattern | SYSTEM | Keeps long AI work outside database transactions while preserving history. |
| Retry processing semantics | SYSTEM | Preserves attempt history without duplicating learner input. |
| Validation-time snapshot semantics | SYSTEM | Defines cross-domain behavior without global locking. |
| Stable newest-window pagination | SYSTEM | Supports recent history and Load Older. |
| AIChatService application boundary | AI | Provides a replaceable future AI integration port without real AI in Phase 3. |
| Migration backfill | DE | Evolves existing Message rows safely and deterministically. |

Do not categorize generic HTTP/framework syntax as DE/AI unless it genuinely serves those domains.

---

# 24. Expected Tools

No new runtime tool/library is expected.

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

Do not add an LLM SDK or RAG framework.

---

# 25. Explicit Non-Goals

Do not implement:

```text
GLOBAL Conversation scope
standalone chat API
real LLM provider
provider credentials
prompt engineering pipeline
RAG retrieval
embeddings
reranking
external web retrieval
citation generation
retrieval traces
AI domain classification
SSE
WebSocket
streaming
background worker
background queue
AI task cancellation infrastructure
cross-domain global User locking
frontend code
Phase 4 work
Conversation analytics
individual Message deletion
```

Do not add placeholder implementations for these future features.

---

# 26. Required Completion Report

Return:

```text
Step: 3.6 — Conversation API
Status: DONE | PARTIAL | BLOCKED

Implementation plan executed:
- ...

Files created:
- ...

Files modified:
- ...

Dependencies added/removed:
- ...

Migration 0003:
- ...

Public Conversation APIs:
- ...

D-019 Conversation/privacy/soft-delete:
- ...

D-020 Message pagination:
- ...

D-021 sequence allocation:
- ...

D-022 retry semantics:
- ...

D-023 AIChatService/two-transaction behavior:
- ...

D-024 migration/backfill:
- ...

D-025 MessageResponse/error contract:
- ...

D-026 Periodic-Test/chat snapshot semantics:
- ...

Step-3.4 lesson/assessment integration:
- ...

Step-3.5 current-user integration:
- ...

Repository/service/transaction design:
- ...

Concurrency verification:
- ...

Tests / verification:
- command:
  result:

Acceptance criteria:
- [PASS/FAIL] ...

Step Note:
- path:

Concepts actually used:
- ...

Tools actually used:
- ...

Deviations from specification:
- none | ...

Problems / risks:
- ...

Decisions needed:
- none | ...

Recommended next action:
Return to App Engineering Specialist for independent review.
Do not begin Phase 4.
```

Do not claim `DONE` when:

- PostgreSQL concurrency/migration verification did not run;
- any D-019 through D-026 contract is not implemented exactly;
- 0001/0002 were modified;
- the implementation introduced real AI/RAG/provider dependencies;
- the required USER-history/failure/retry semantics are incomplete;
- Phase 4 work was started.
