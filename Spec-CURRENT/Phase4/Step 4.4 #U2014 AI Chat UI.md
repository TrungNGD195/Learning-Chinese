# Step 4.4 — AI Chat UI

## Goal

Implement the learner-facing AI Chat interface connected to the existing Conversation API.

The current MVP supports lesson-scoped chat only.

The frontend must render persistent Conversation/Message state from the backend and must not implement AI, RAG or grading logic itself.

---

# Placement

AI Chat belongs inside the Lesson experience.

Do not create a standalone `/chat` route for MVP.

Use an interaction pattern equivalent to:

```text
Desktop
→ side panel / drawer

Mobile
→ bottom sheet or full-screen overlay
```

Preserve access to the lesson while making chat usable.

---

# Conversation Model

Allow multiple Conversations for one Lesson.

Support learner UI for:

```text
current conversation
conversation history
new conversation
rename
delete
```

Do not assume User + Lesson has only one thread.

---

# Conversation Creation

Provide a New Chat action.

Call the existing Conversation API with:

```json
{
  "scope": "LESSON",
  "lesson_id": "<current lesson id>"
}
```

Do not send `user_id`.

User identity is derived by the backend from authentication.

---

# Empty State

Opening the chat panel must not automatically create a Conversation.

If no Conversation exists, show an empty state equivalent to:

```text
Ask AI about this lesson

[Start a conversation]
```

Only create a Conversation after explicit learner action or first-send behavior if implementation remains semantically explicit.

---

# Conversation List

Display appropriate metadata such as:

```text
title
last updated
```

Order by backend-supported recent activity:

```text
updated_at DESC
```

Load a Conversation when selected.

Do not preload every Conversation's complete Message history.

---

# Rename

Support:

```text
PATCH /api/v1/conversations/{conversation_id}
```

for title changes only.

Do not allow frontend to modify Conversation ownership or lesson scope.

---

# Delete

Support:

```text
DELETE /api/v1/conversations/{conversation_id}
```

Provide a lightweight confirmation before deletion.

After successful deletion:

- remove it from the normal Conversation list;
- close it if currently selected;
- select another valid Conversation or return to empty state.

Do not implement individual Message deletion.

---

# Message History

Load history using:

```text
GET /api/v1/conversations/{conversation_id}/messages
```

Render Messages using:

```text
sequence_number
```

as the deterministic ordering field.

Do not rely only on timestamp sorting.

---

# Message Roles

Render USER and ASSISTANT Messages differently.

Use simple learner-friendly components such as:

```text
UserMessage
AssistantMessage
```

Do not expose internal database fields in the UI.

Do not allow the frontend to create ASSISTANT Messages directly.

---

# Composer

Provide:

```text
textarea
Send button
```

Expected interaction:

```text
Enter
→ send

Shift+Enter
→ newline
```

Disable submission for empty/whitespace-only content.

Backend validation remains mandatory.

---

# Sending Messages

Use the existing Conversation API.

Do not call the LLM provider directly.

Flow:

```text
MessageComposer
→ conversationApi
→ FastAPI
→ AIChatService
→ persisted Message result
→ Chat UI
```

Do not expose AI provider credentials in frontend code.

---

# Optimistic Behavior

For the initial MVP, prefer backend-confirmed persisted Message state over complex optimistic Message creation.

Do not invent temporary backend Message IDs.

Keep implementation simple and consistent with the persistent Conversation model.

---

# Message Status

Support backend states:

```text
PENDING
COMPLETED
FAILED
```

## PENDING

Render a processing state such as:

```text
AI is thinking...
```

or a lightweight Assistant Message skeleton.

Do not generate placeholder answer content.

## COMPLETED

Render the returned Assistant content.

## FAILED

Keep the USER Message visible.

Render an Assistant failure state with a Retry action.

Do not silently remove failed responses.

---

# Retry

Retry only failed Assistant responses through:

```text
POST /api/v1/messages/{assistant_message_id}/retry
```

Do not resend the original USER content as a new USER Message.

The backend creates a new Assistant processing attempt.

Preserve the server-side relationship between retry responses and the original USER Message.

The learner-facing UI does not need a complex processing-attempt audit interface.

---

# Lesson Context

For lesson-scoped Conversations, display lightweight context such as:

```text
AI Tutor
HSK <level> • Lesson <number>
```

Do not provide a context selector that can change the Lesson of an existing LESSON Conversation.

Lesson scope is authoritative backend Conversation state.

---

# Chat Availability

If the backend returns:

```text
AI_CHAT_DISABLED_DURING_TEST
```

render a specific disabled state.

Disable the Message composer while this state applies.

Do not derive this restriction solely from frontend-local Assessment state.

Normal Lesson Exercises must not automatically disable chat.

---

# Message Pagination

Use the backend pagination contract.

For MVP, provide an explicit action equivalent to:

```text
Load older messages
```

Do not introduce complex infinite-scroll infrastructure unless already trivial to support.

---

# Auto Scroll

Auto-scroll to the newest Message when appropriate:

- Conversation first opens;
- learner sends a Message;
- new Assistant response appears.

Avoid forcing scroll if the learner intentionally moved upward to read older history.

---

# Content Rendering

Support safe basic Markdown in Assistant Messages when useful.

Expected content includes:

- paragraphs;
- bullet lists;
- bold text;
- Chinese examples.

Do not render raw HTML supplied by AI output.

Ensure typography renders Chinese characters, pinyin and Vietnamese text correctly.

---

# Citations

Do not fake source citations.

Real citation/source-grounding behavior belongs to Phase 6.

The UI may remain structurally extensible for future Message citation rendering, but no placeholder source data should be presented as genuine grounding.

---

# Streaming

Do not implement:

```text
SSE
WebSocket
token-by-token rendering
```

in this step.

Current MVP behavior remains:

```text
submit Message
→ wait for Conversation API result
→ render final response/state
```

Streaming will be revisited with the real LLM pipeline.

---

# Global Chat

Do not expose GLOBAL Chat UI in MVP.

Keep frontend component design reusable enough that a future standalone Global Chat experience can use the same Conversation/Message components.

---

# Suggested Structure

Equivalent structure:

```text
features/conversation/
├── ChatPanel
├── ConversationList
├── ConversationHeader
├── MessageList
├── UserMessage
├── AssistantMessage
├── MessageComposer
└── ConversationEmptyState
```

Do not create unnecessary empty files merely to match this tree.

---

# Tests

Add focused tests for:

- opening Lesson Chat;
- Conversation empty state;
- creating a Conversation;
- loading Conversation history;
- `sequence_number` ordering;
- USER/ASSISTANT rendering;
- whitespace Message submission blocked;
- successful Assistant response;
- PENDING rendering;
- FAILED rendering;
- Retry action calls retry endpoint;
- Retry does not create another USER Message;
- Conversation rename;
- Conversation deletion;
- periodic-test chat-blocking error;
- normal Lesson Exercise does not disable chat.

Use mocked Conversation API responses.

---

# Out of Scope

Do not implement:

- real LLM logic;
- RAG;
- retrieval;
- citation generation;
- external search;
- global Chat route;
- streaming;
- WebSocket;
- SSE;
- audio input/output;
- pronunciation scoring;
- advanced Conversation analytics.

---

# Acceptance Criteria

- [ ] AI Chat is embedded in Lesson flow.
- [ ] Multiple Conversations per Lesson are supported.
- [ ] Conversation history can be selected and loaded.
- [ ] New Conversation does not accept client-controlled User ID.
- [ ] Messages render in deterministic sequence order.
- [ ] USER and ASSISTANT roles are visually distinguishable.
- [ ] Composer rejects empty submission.
- [ ] PENDING/COMPLETED/FAILED states are represented.
- [ ] Failed AI responses remain visible and retryable.
- [ ] Retry does not duplicate the original USER Message.
- [ ] Lesson scope cannot be changed inside an existing LESSON Conversation.
- [ ] Periodic Test blocking is represented from backend error/state.
- [ ] Basic safe AI text formatting works.
- [ ] Fake citations are not shown.
- [ ] Streaming is not introduced prematurely.
- [ ] Frontend never contacts an LLM provider directly.

# Expected Deliverable

AI Chat UI foundation plus:

```text
docs/frontend/
└── step-4.4-ai-chat-ui.md
```

Next Step:

**Step 4.5 — Frontend State & Error Handling**