# Step 3.6 — Conversation API

## Goal

Implement persistent Conversation and Message APIs for the Chinese-learning application.

V0 supports Lesson-scoped AI chat only. Standalone/global chat is outside MVP and must not be exposed through Phase 3 APIs.

Do not integrate a real LLM or RAG pipeline yet.

Use a deterministic fake/stub AIChatService for Phase 3 tests.

---

# Conversation Scope

V0 supports one conversation scope:

```text
LESSON
→ lesson_id must be non-null
```

Do not expose or persist `GLOBAL` conversations in V0. A later product decision may add them through a forward API/schema change.

---

# Conversation Ownership

Every Conversation belongs to one User.

User identity must come from:

```text
get_current_user()
```

Never accept arbitrary `user_id` from the conversation request.

Every read/write operation must verify ownership.

For resources belonging to another User, prefer a not-found response rather than exposing that the resource exists.

---

# Multiple Conversations

Allow multiple Conversations for the same:

```text
User + Lesson
```

Do not impose a unique User/Lesson Conversation constraint.

This allows learners to start a new chat without deleting historical conversations.

---

# Conversation Creation

Implement:

```http
POST /api/v1/conversations
```

Request shape:

```json
{
  "lesson_id": "<uuid>"
}
```

The client does not need to send a scope field because V0 has only Lesson conversations. If an implementation keeps an internal scope enum for compatibility, the public API must still accept only `LESSON`.

For the selected Lesson:

1. Load the Lesson.
2. Verify learner access.
3. Reject locked lessons.
4. Persist Conversation associated with current User.

Allowed lesson states:

```text
AVAILABLE
COMPLETED
```

Blocked:

```text
LOCKED
→ LESSON_LOCKED
```

---

# Conversation Title

Conversation title may be nullable.

Do not require AI-generated titles.

Provide:

```http
PATCH /api/v1/conversations/{conversation_id}
```

for simple title updates.

Only mutable learner-facing fields explicitly allowed by the API may be updated.

---

# Conversation List

Implement:

```http
GET /api/v1/me/conversations
```

Support whitelisted optional filters:

```text
scope
lesson_id
```

Default ordering:

```text
updated_at DESC
```

Exclude soft-deleted conversations.

Use bounded pagination.

---

# Conversation Detail

Implement:

```http
GET /api/v1/conversations/{conversation_id}
```

Verify:

```text
conversation.user_id == current_user.id
```

Do not include full unbounded message history in the main Conversation representation.

---

# Conversation Deletion

Implement:

```http
DELETE /api/v1/conversations/{conversation_id}
```

Use soft deletion:

```text
deleted_at
```

After deletion:

- hide Conversation from normal queries;
- reject new messages;
- reject normal history access;
- treat it as unavailable to the learner.

Do not provide individual-message deletion in MVP.

Do not physically purge retrieval/citation data in this step.

---

# Message History

Implement:

```http
GET /api/v1/conversations/{conversation_id}/messages
```

Use bounded page-based pagination for MVP.

Suggested default:

```text
page_size = 50
```

Return messages in correct chronological order within the requested result.

Cursor pagination is deferred.

---

# Message Creation

Implement:

```http
POST /api/v1/conversations/{conversation_id}/messages
```

Input:

```json
{
  "content": "<learner text>"
}
```

The client must not provide:

```text
user_id
role
lesson_id
conversation owner
assistant content
```

Backend creates the submitted message as:

```text
role = USER
status = COMPLETED
```

Validate non-empty content and reasonable input limits.

---

# Lesson Context

For LESSON conversations, always derive context from:

```text
conversation.lesson_id
```

Do not accept `lesson_id` again when submitting each Message.

This Conversation state is the authoritative lesson scope for AI processing.

---

# Message Sequence

Add:

```text
sequence_number
```

to Messages.

Within each Conversation:

```text
UNIQUE(conversation_id, sequence_number)
```

Use sequence number as the deterministic message-order field.

Do not rely exclusively on timestamp precision for chronology.

Ensure concurrent creation cannot silently assign duplicate sequence numbers.

Use appropriate transaction/locking/retry logic when allocating the next sequence.

---

# Reply Relationship

Add nullable:

```text
reply_to_message_id
```

as a self-referencing Message foreign key.

Normal AI turn:

```text
USER message
↑
ASSISTANT.reply_to_message_id
```

An Assistant Message must reference the User Message it is answering when applicable.

This relationship must be preserved across retries.

---

# Message Status

Support:

```text
PENDING
COMPLETED
FAILED
```

Expected user message:

```text
role = USER
status = COMPLETED
```

Expected AI response lifecycle:

```text
ASSISTANT PENDING
→ COMPLETED

or

ASSISTANT PENDING
→ FAILED
```

---

# Send Message Workflow

Use the following persistence pattern.

## Transaction A

```text
validate Conversation ownership/state
validate chat availability

create USER message COMPLETED
create ASSISTANT message PENDING
link Assistant to User using reply_to_message_id

COMMIT
```

Do not keep this transaction open during external AI processing.

## AI Processing

Invoke:

```text
AIChatService
```

In Phase 3 this must use a deterministic fake/stub implementation.

## Transaction B

On success:

```text
ASSISTANT status = COMPLETED
ASSISTANT content = generated result
```

On failure:

```text
ASSISTANT status = FAILED
```

Commit final Message state.

The USER Message must remain persisted even if AI processing fails.

---

# AI Boundary

ConversationService must not directly implement:

- RAG retrieval;
- embedding search;
- Knowledge Index access;
- prompt construction;
- LLM provider calls;
- external web retrieval.

Use:

```text
ConversationService
→ AIChatService
```

Future Phase 6 structure may become:

```text
AIChatService
├── DomainGuard
├── Retrieval
├── Prompting
└── LLM Provider
```

Preserve this separation.

---

# Phase 3 AI Stub

Provide a deterministic fake or stub `AIChatService`.

It should allow tests to explicitly simulate:

```text
successful response
failed response
```

Do not add real LLM credentials or providers.

---

# Synchronous API V0

For the initial implementation:

```text
POST Message
→ save Message state
→ call AIChatService
→ save Assistant result
→ return result
```

Do not implement:

- background queue;
- worker;
- WebSocket;
- SSE;
- token streaming.

Streaming architecture is deferred until the actual LLM integration in Phase 6.

---

# AI Chat During Tests

Chat must be unavailable while the learner has an active Periodic Test attempt.

Blocked condition:

```text
Assessment.type = PERIODIC_TEST
AND
AssessmentAttempt.status = IN_PROGRESS
```

When this condition is true, message submission must fail with a stable business error such as:

```text
AI_CHAT_DISABLED_DURING_TEST
```

Normal lesson exercises must not trigger this restriction.

This rule applies to all V0 Lesson conversations.

---

# Deferred Global Chat

Standalone/global chat is out of scope for V0. Do not expose a global-conversation creation path, do not create null-Lesson conversations, and do not add global RAG behavior.

If product scope later adds this capability, PM must first update product scope, persistence constraints and retrieval policy.

---

# Domain Guard

Define an abstraction/boundary for future domain validation if useful:

```text
DomainGuard
```

Do not implement LLM-based classification in Phase 3.

Future allowed domain includes:

- Chinese-language learning;
- pronunciation;
- vocabulary;
- grammar;
- relevant cultural context.

Unrelated-domain refusal belongs to Phase 6 AI behavior.

---

# Failed Response Retry

Implement:

```http
POST /api/v1/messages/{assistant_message_id}/retry
```

Requirements:

- Message must belong to current User through its Conversation.
- Target must be an ASSISTANT Message.
- Target status must be FAILED.
- The original USER Message must still exist.
- Do not duplicate the USER Message.

Retry creates a new Assistant Message:

```text
role = ASSISTANT
status = PENDING
reply_to_message_id = original USER Message
```

Then run AIChatService again.

On success:

```text
new Assistant → COMPLETED
```

On failure:

```text
new Assistant → FAILED
```

Do not overwrite the original failed Assistant Message.

Preserve processing attempt history.

---

# Conversation Schema Update

Add to `conversations`:

```text
deleted_at TIMESTAMPTZ NULL
```

---

# Message Schema Update

Add to `messages`:

```text
sequence_number NOT NULL
reply_to_message_id UUID NULL
```

Add FK:

```text
reply_to_message_id
→ messages.id
```

Add:

```text
UNIQUE(conversation_id, sequence_number)
```

Ensure reply targets belong to the expected Conversation/application flow.

---

# Migration

Create a new Alembic migration equivalent to:

```text
0003_conversation_message_flow
```

Do not rewrite already-applied migrations.

The migration must safely introduce:

- Conversation soft deletion;
- Message sequence;
- reply relationship;
- required indexes/constraints.

Review migration manually.

---

# API Surface

Implement:

```text
POST   /api/v1/conversations
GET    /api/v1/me/conversations

GET    /api/v1/conversations/{conversation_id}
PATCH  /api/v1/conversations/{conversation_id}
DELETE /api/v1/conversations/{conversation_id}

GET    /api/v1/conversations/{conversation_id}/messages
POST   /api/v1/conversations/{conversation_id}/messages

POST   /api/v1/messages/{assistant_message_id}/retry
```

All endpoints require authenticated current-user context.

---

# Error Codes

Support stable business errors where applicable, including:

```text
LESSON_LOCKED
CONVERSATION_NOT_FOUND
CONVERSATION_DELETED
AI_CHAT_DISABLED_DURING_TEST
INVALID_MESSAGE_RETRY
AI_RESPONSE_FAILED
```

Do not expose internal AI/provider exceptions directly to the client.

---

# Tests

Add tests covering at least:

- create Lesson Conversation;
- reject locked Lesson Conversation;
- completed Lesson remains chat-accessible;
- multiple Conversations allowed for same Lesson;
- Conversation ownership;
- another User cannot discover/read Conversation;
- Conversation list ordering/filtering;
- rename;
- soft delete;
- deleted Conversation excluded from normal queries;
- USER role cannot be spoofed;
- Lesson ID derived from Conversation;
- Message sequence ordering;
- Assistant reply relationship;
- successful fake AI turn;
- user Message remains after AI failure;
- FAILED Assistant state;
- retry creates new Assistant Message;
- retry does not duplicate USER Message;
- retry relation points to same USER Message;
- Periodic Test IN_PROGRESS disables AI chat;
- normal lesson exercise does not disable chat.

---

# Out of Scope

Do not implement:

- real LLM provider;
- embeddings;
- RAG retrieval;
- reranking;
- external trusted retrieval;
- citations generation;
- retrieval traces generation;
- AI domain classification;
- token streaming;
- SSE;
- WebSocket;
- background AI worker;
- global-chat API/frontend.

---

# Acceptance Criteria

- [ ] Conversations are owned by authenticated Users.
- [ ] V0 conversations are Lesson-scoped only and require a Lesson.
- [ ] Multiple Conversations per Lesson are supported.
- [ ] Locked Lesson conversations are rejected.
- [ ] Conversation history is persistent.
- [ ] Messages have deterministic sequence ordering.
- [ ] Assistant Messages reference their USER Message.
- [ ] USER Messages survive AI processing failures.
- [ ] AI processing state supports PENDING/COMPLETED/FAILED.
- [ ] Failed AI responses can be retried without duplicating the USER question.
- [ ] Soft-deleted Conversations disappear from normal learner flows.
- [ ] Client cannot create ASSISTANT Messages directly.
- [ ] Lesson context cannot be spoofed per Message.
- [ ] AI chat is disabled during active Periodic Tests.
- [ ] AI calls do not hold long-lived database transactions.
- [ ] Conversation persistence remains separated from AI implementation.
- [ ] Real LLM/RAG integration has not been introduced prematurely.

# Expected Deliverable

Conversation API foundation plus:

```text
docs/backend/
└── step-3.6-conversation-api.md
```

Next Phase:

**Phase 4 — Frontend Foundation**