# Codex Execution Task — Step 4.4: AI Chat UI

## Execution Gate

This is the **single current Codex execution task** for:

**Step 4.4 — AI Chat UI**

Owner: **App Engineering Specialist**

Implement Step 4.4 only.

Do **not** begin Step 4.5 TanStack Query/session/error architecture, Step 4.6 Auth/Profile UI, Step 4.7 Admin UI, Phase 5 ingestion, or Phase 6 real AI/RAG behavior.

Before editing, inspect the actual repository and the canonical PM Decision Log. Expected accepted state:

- backend complete through Step 3.6;
- frontend complete and PM-accepted through Step 4.3;
- Step-4.2 `apiClient`, generated OpenAPI types, and `features/conversation/api.ts` are the required HTTP boundary;
- Step-4.3 `LessonPage` and structural `LessonChatRegion` are the accepted placement baseline;
- D-019 through D-026 define the accepted Conversation/Message backend contract;
- D-027 through D-038 are DECIDED and authoritative where applicable;
- TanStack Query is not yet installed/used;
- no standalone `/chat` route exists;
- no real LLM/RAG/provider logic exists in the frontend.

If the execution checkout materially differs, if the actual Conversation OpenAPI/backend contract contradicts D-019–D-026/D-037, or if correct implementation requires polling, streaming, a new backend endpoint, global server state, or another material convention not frozen here, stop and report `BLOCKED` with evidence rather than inventing architecture.

---

# 1. Objective

Implement the learner-facing Lesson-scoped AI Chat UI connected to the accepted persistent Conversation API.

Required mental model:

```text
Lesson UI
→ LessonChatRegion / ChatPanel
→ handwritten Conversation feature API
→ central apiClient
→ FastAPI Conversation API
→ persisted Conversation / Message state
→ frontend renders backend-confirmed state
```

The frontend must **not** implement:

```text
LLM provider logic
RAG
retrieval
reranking
embedding
AI grading
citation generation
provider credential handling
```

MVP scope remains:

```text
scope = LESSON only
```

No GLOBAL Chat.

---

# 2. Source of Truth

## Primary Step

Use:

```text
Spec-CURRENT/Phase4/Step 4.4 — AI Chat UI.md
```

If using the bundled source pack, use the Step-4.4 section in:

```text
02_APP_ENGINEERING_SPECS_PHASE3-4.md
```

## Required decisions

Read the latest canonical PM Decision Log before editing and preserve at least:

```text
D-019 — Conversation public API/privacy/soft delete
D-020 — Message pagination semantics
D-021 — Message sequence allocation / Conversation activity
D-022 — Assistant retry eligibility/concurrency
D-023 — AIChatService + send/retry failure HTTP contract
D-025 — canonical MessageResponse + chat availability error
D-026 — Periodic-Test/chat snapshot semantics

D-027 — frontend runtime/npm workflow
D-028 — approved React Router route baseline
D-029 — frontend testing baseline
D-030 — OpenAPI generated-contract ownership
D-031 — central apiClient / ApiError contract

D-037 — explicit Conversation creation UX
D-038 — safe Assistant Markdown rendering
```

## Precedence

If sources differ:

1. latest canonical PM Decision Log;
2. authoritative Step 4.4 specification;
3. later accepted refinement intentionally changing an earlier example;
4. accepted backend/frontend implementation and generated OpenAPI;
5. earlier notes/examples;
6. this reviewed execution packet.

Known documentation drift that is already resolved:

```text
older Step-4.4 example:
{ scope: "LESSON", lesson_id }

accepted public request:
{ lesson_id }
```

Do **not** add `scope` to the create request.

---

# 3. Current Accepted Frontend State

Relevant existing files include:

```text
frontend/src/features/conversation/
├── LessonChatRegion.tsx
└── api.ts

frontend/src/features/lesson/LessonPage.tsx
frontend/src/types/api.generated.ts
frontend/src/lib/api/client.ts
frontend/src/lib/api/errors.ts
frontend/src/index.css
```

Current `LessonChatRegion` is only structural. Evolve that accepted Lesson slot into the interactive Step-4.4 surface rather than moving Chat outside the Lesson experience.

Current Conversation API functions already exist and should be reused:

```text
createConversation
listConversations
getConversation
renameConversation
deleteConversation
getMessages
sendMessage
retryAssistantMessage
```

Do not add another HTTP client or duplicate these endpoint wrappers.

Current production frontend dependencies do **not** yet contain Markdown rendering. D-038 requires adding only the focused runtime dependency:

```text
react-markdown
```

No backend code/API change is expected for Step 4.4.

---

# 4. Accepted Conversation / Message Contracts

## 4.1 Create Conversation

Generated request is equivalent to:

```ts
{
  lesson_id: string
}
```

Never send:

```text
scope
user_id
owner
```

Backend derives:

```text
current User
scope = LESSON
```

## 4.2 Conversation response

Use generated `ConversationResponse` equivalent to:

```text
id
scope = LESSON
lesson_id
title
created_at
updated_at
```

Do not expose ownership/debug information.

## 4.3 Message response

Use generated canonical `MessageResponse`:

```text
id
conversation_id
sequence_number
role = USER | ASSISTANT
content = string | null
status = PENDING | COMPLETED | FAILED
reply_to_message_id = UUID | null
created_at
```

Do not create handwritten duplicate Message DTOs.

## 4.4 Send success

`sendMessage(...)` returns:

```text
SendMessageResponse
├── user_message
└── assistant_message
```

Successful synchronous response contains the finalized Assistant Message.

## 4.5 Retry success

`retryAssistantMessage(failedAssistantMessageId)` returns the newly created Assistant `MessageResponse`.

---

# 5. Suggested Feature Structure

Use a small feature-oriented structure. Equivalent:

```text
frontend/src/features/conversation/
├── api.ts                         # existing; do not duplicate transport
├── LessonChatRegion.tsx           # Lesson entry + panel ownership
├── ChatPanel.tsx
├── ConversationList.tsx
├── ConversationHeader.tsx
├── ConversationEmptyState.tsx
├── MessageList.tsx
├── UserMessage.tsx
├── AssistantMessage.tsx
├── AssistantMarkdown.tsx
├── MessageComposer.tsx
└── step44-chat.test.tsx           # or equivalent focused test file
```

Exact filenames may differ if the implementation remains clear.

Do not create empty boilerplate files just to reproduce this tree.

Do not build a generic chat framework unrelated to the current Lesson use case.

---

# 6. Placement and Responsive Interaction

AI Chat stays embedded in the Lesson experience.

Preserve:

```text
/lessons/:lessonId
```

Do not add:

```text
/chat
/global-chat
```

## Desktop

Use interaction equivalent to:

```text
LessonChatRegion
→ AI Tutor entry/button
→ right-side/fixed ChatPanel
```

The panel may overlay part of the viewport but must provide an explicit Close action so Lesson content remains recoverable.

## Mobile

Use a simple:

```text
full-screen overlay
```

rather than a gesture-heavy bottom-sheet implementation.

Requirements:

- message history scrollable;
- Composer usable with mobile keyboard;
- controls touch-friendly;
- explicit Close returns learner to Lesson;
- no animation/gesture library;
- existing CSS conventions only.

Do not add Tailwind/MUI/design system merely for Chat.

---

# 7. Lesson Context

Pass the accepted Lesson context from `LessonPage` into the Chat region as presentation data, for example:

```text
lessonId
lessonNumber
hskLabel when available
```

Display lightweight context equivalent to:

```text
AI Tutor
HSK 1 • Lesson 3
```

Gracefully omit HSK label if unavailable.

Do not add any selector that can change the Lesson of an existing Conversation.

Conversation scope remains backend-authoritative.

---

# 8. Mandatory D-037 — Explicit Conversation Creation

Opening the Chat panel alone must not create persistent state.

## 8.1 Panel open

```text
learner opens Chat
→ load current Lesson Conversation list
→ no createConversation call solely because panel opened
```

## 8.2 No Conversations

Render empty state equivalent to:

```text
Ask AI about this lesson

[Start a conversation]
```

Composer is not a first-send Conversation-creation shortcut.

## 8.3 Explicit Start

Only explicit learner action calls:

```ts
createConversation({
  lesson_id: currentLessonId,
})
```

On success:

```text
created Conversation
→ selected Conversation ID
→ refresh Conversation list page 1
→ show Message Composer
→ empty Message history
```

Do not automatically send a Message as part of creation.

## 8.4 Existing Conversations

On opening a Lesson with existing Conversations:

```text
load list page 1
```

Use this deterministic presentation convention:

```text
if no current selection exists and page 1 contains Conversations
→ select the first Conversation in backend-returned order
→ load only that Conversation's Message history
```

This is UI selection only; it creates no backend state.

Also expose explicit:

```text
New conversation
```

which uses the same D-037 Start/create behavior and never sends a Message automatically.

---

# 9. Conversation List and Pagination

Use current Lesson filter:

```ts
listConversations({
  lesson_id: currentLessonId,
  page: 1,
  page_size: 20,
})
```

The backend list order is authoritative:

```text
updated_at DESC
id DESC
```

Do not locally invent another recent-activity ordering.

Display learner-facing metadata only:

```text
title
last updated
```

For null title, use a simple presentation fallback such as:

```text
Untitled conversation
```

Do not persist a fallback title automatically.

## Load more Conversations

Use bounded page pagination:

```text
page 1
→ page 2
→ ...
```

Append subsequent Conversation pages in backend-returned order and dedupe by Conversation ID.

Use `total/page/page_size` to determine whether another page may exist.

No infinite-scroll infrastructure.

## Backend-authoritative activity ordering

After successful:

```text
create
rename
send
retry
delete
```

reload Conversation list from page 1 when needed so `updated_at` ordering remains backend-authoritative.

Do not manufacture `updated_at` timestamps locally.

When reloading from page 1:

- reset Conversation pagination to page 1;
- preserve the current selected ID if it still exists;
- otherwise use the selection rules below.

---

# 10. Selecting Conversations

Selecting one Conversation:

```text
selectedConversationId = id
→ load only that Conversation's newest Message page
```

Do not preload complete Message history for every Conversation.

When selection changes:

- clear Message pagination state for the old Conversation;
- clear old action-scoped Chat-disabled state;
- clear old rename edit state;
- keep Composer draft scoped to the selected Conversation only, or clear it when switching to avoid sending text to the wrong Conversation;
- use an effect-lifetime/request-generation guard so stale async responses from the previously selected Conversation cannot overwrite the newly selected Conversation state.

Do not add AbortSignal semantics to `apiClient` in this Step.

---

# 11. Rename

Support title-only rename using:

```text
renameConversation(conversationId, { title })
```

Use lightweight local edit state.

Do not expose controls for:

```text
lesson_id
scope
owner
user_id
```

On successful rename:

```text
update selected Conversation presentation from backend response
→ reload Conversation list page 1
```

Backend validation remains authoritative for title length/whitespace.

No form library is required.

---

# 12. Delete

Use existing soft-delete API:

```text
deleteConversation(conversationId)
```

Provide lightweight confirmation before deletion.

Do not implement Message deletion.

After successful delete:

```text
refresh Conversation list page 1
```

If deleted Conversation was selected:

```text
refreshed list has items
→ select first Conversation in backend-returned order
→ load its newest Message page

refreshed list empty
→ selectedConversationId = null
→ show Conversation empty state
```

If deleted Conversation was not selected, preserve current selection when it remains valid.

Do not attempt normal detail/history/send/retry operations against the deleted Conversation after successful deletion.

---

# 13. Message History — D-020 Pagination

Use:

```text
getMessages(conversationId, {
  page,
  page_size: 50,
})
```

Backend page semantics are fixed:

```text
page 1
→ newest N Messages

page 2
→ next older N Messages
```

Each page already returns its own items:

```text
sequence_number ASC
```

## Initial load

```text
select Conversation
→ getMessages(page=1)
→ dedupe by Message ID
→ sort final loaded set by sequence_number ASC
→ render oldest-to-newest within loaded window
```

## Load older

```text
current loaded oldest page = N
→ getMessages(page=N+1)
→ prepend older page
→ dedupe by Message ID
→ sort final loaded set by sequence_number ASC
```

Canonical Message order is:

```text
sequence_number
```

Do not order primarily by `created_at`.

Use Message `id` only for:

```text
React key
deduplication
```

## Older-page availability

Use backend:

```text
total
page
page_size
```

to determine whether another older page can exist.

No cursor pagination.
No infinite scroll.

---

# 14. Message Merge Helper

A small local helper is encouraged to keep all server-returned merge behavior consistent.

Equivalent logic:

```text
existing Messages
+ incoming backend Messages
→ dedupe by id
→ sort by sequence_number ASC
```

Do not merge by timestamp.
Do not create temporary backend IDs.
Do not overwrite one Assistant processing attempt with another merely because they share `reply_to_message_id`.

Multiple Assistant retry attempts are distinct persisted Messages and must remain visible in sequence order.

---

# 15. USER / ASSISTANT Presentation

Render roles visually distinctly.

## USER

- plain learner text;
- preserve line breaks safely;
- no Markdown requirement;
- React escapes raw HTML naturally;
- do not render internal metadata.

## ASSISTANT

Status controls presentation:

```text
PENDING
COMPLETED
FAILED
```

Do not expose:

```text
conversation_id
reply_to_message_id
provider internals
retrieval internals
database/debug fields
```

unless needed internally for action wiring.

---

# 16. PENDING / COMPLETED / FAILED

## PENDING persisted Message

If backend history actually returns:

```text
role = ASSISTANT
status = PENDING
```

render lightweight state such as:

```text
AI is thinking…
```

Do not create fake answer content.

## COMPLETED

Render backend Assistant `content` through the D-038 safe Markdown component.

## FAILED

Keep:

```text
original USER Message
failed Assistant attempt
```

visible.

Expose Retry only for a failed Assistant Message.

Backend remains final retry-eligibility authority and may return `INVALID_MESSAGE_RETRY` for an older/invalid attempt.

---

# 17. PENDING Observability — No Polling

Do **not** add polling merely to make PENDING visible.

The accepted send/retry HTTP flow is synchronous.

Successful Send returns finalized USER + Assistant Messages.
Successful Retry returns finalized new Assistant Message.

Persistent PENDING may still appear when history observes an already-started in-flight turn.
Render it correctly when returned.

During the local synchronous Send/Retry request, a separate UI action indicator may display:

```text
AI is thinking…
```

but this must **not** create a fake persisted Message object or fake Message ID.

Do not add:

```text
setInterval polling
background polling timer
SSE
WebSocket
streaming
```

---

# 18. Composer

Provide:

```text
textarea
Send button
```

Local state only:

```text
composerText
sendPending
local send error
```

## Keyboard

```text
Enter
→ Send

Shift + Enter
→ newline
```

Use textarea key handling without breaking IME/composition input. Do not submit while `event.nativeEvent.isComposing` / equivalent composition state is active.

## Validation

Whitespace-only submission:

```text
blocked locally
```

Backend remains authoritative for accepted content length/validation.

## Duplicate prevention

While Send is pending:

```text
Send disabled
Enter send ignored
```

## Draft ownership

Do not persist draft to:

```text
localStorage
sessionStorage
backend draft
global store
```

Do not carry a draft across Conversation selection in a way that can accidentally send it to another Conversation.

---

# 19. Normal Send Success

Flow:

```text
MessageComposer
→ sendMessage(selectedConversationId, { content })
→ backend persists USER + Assistant processing lifecycle
→ successful SendMessageResponse
→ merge user_message + assistant_message
→ dedupe
→ sequence_number sort
→ clear Composer draft
→ scroll newest when appropriate
→ refresh Conversation list page 1 for backend activity ordering
```

No history refetch is required to obtain normal successful Message bodies.

Do not create an optimistic USER Message or fake Assistant Message before backend confirmation.

An action-level pending indicator is sufficient while awaiting the HTTP response.

---

# 20. Send — `AI_RESPONSE_FAILED`

Accepted backend semantics:

```text
USER Message already persisted
ASSISTANT Message already persisted FAILED
HTTP 502 AI_RESPONSE_FAILED
```

Therefore:

```text
sendMessage(...)
→ ApiError.code == AI_RESPONSE_FAILED
→ clear Composer draft because USER Message persisted
→ refresh newest Message page (page=1)
→ merge/dedupe/sort persisted USER + FAILED Assistant
→ refresh Conversation list page 1
→ display persisted failure + Retry
```

Do not automatically send the original USER text again.

Do not create a fake failure Message from error details.

---

# 21. Send — Technical / Network Failure

For errors such as:

```text
NETWORK_ERROR
HTTP_ERROR
unexpected technical failure
```

where persistence cannot safely be assumed:

```text
preserve Composer draft
show local technical error
create no fake Message
perform no automatic resend
```

Provide explicit:

```text
Refresh conversation
```

which reloads Message page 1 from backend-authoritative persisted history.

Do not build idempotency/retry orchestration in Step 4.4.

---

# 22. Retry — D-022/D-025

Use only:

```ts
retryAssistantMessage(failedAssistantMessageId)
```

UI Retry candidate:

```text
role = ASSISTANT
status = FAILED
```

Do not:

```text
copy original USER content
call sendMessage for Retry
create another USER Message
remove original failed Assistant attempt
```

## Retry success

```text
retryAssistantMessage(...)
→ new Assistant MessageResponse
→ merge
→ sequence_number sort
→ refresh Conversation list page 1
→ scroll newest when appropriate
```

The previous FAILED Assistant remains in history.

## Retry `AI_RESPONSE_FAILED`

Backend already persisted a **new** FAILED Assistant attempt.

Use:

```text
ApiError.code == AI_RESPONSE_FAILED
→ refresh newest Message page
→ merge newly persisted failed retry attempt
→ preserve previous failed attempt
→ refresh Conversation list page 1
```

Do not synthesize the new Message from error details.

## `INVALID_MESSAGE_RETRY`

If backend rejects an older/non-latest FAILED Assistant:

```text
show local conflict message
→ refresh newest Message page
```

Do not locally reinterpret retry eligibility beyond backend state.

---

# 23. `AI_CHAT_DISABLED_DURING_TEST`

This backend error may occur on:

```text
send Message
retry Assistant
```

It does **not** block:

```text
create Conversation
list
history load
rename
delete
```

A rejected blocked send/retry creates no Message.

Do not create a long-lived frontend Periodic-Test business flag.

## Blocked Send

On:

```text
sendMessage
→ AI_CHAT_DISABLED_DURING_TEST
```

store action-scoped local state equivalent to:

```text
type = SEND
conversationId
preserved draft
```

Then:

- show a specific Chat-disabled notice;
- disable the normal Composer Send path while this blocked operation state applies;
- keep the blocked draft visible/preserved;
- expose `Try again`.

`Try again`:

```text
→ same sendMessage(selectedConversationId, preservedDraft)
→ backend re-evaluates current availability
```

If backend succeeds:

```text
clear blocked state
→ normal Send-success merge
```

If backend returns the same code:

```text
remain blocked
```

## Blocked Retry

Store action-scoped state equivalent to:

```text
type = RETRY
conversationId
failedAssistantMessageId
```

`Try again` must call the same:

```text
retryAssistantMessage(failedAssistantMessageId)
```

not `sendMessage`.

## Clearing local blocked state

Because this is action-scoped rather than an authoritative long-lived business state, clear it when:

```text
selected Conversation changes
Chat panel closes
operation succeeds
```

Backend will re-evaluate availability on the next explicit operation.

Do not:

```text
poll Assessment state
infer Periodic Test activity from frontend-local state
add a Chat availability endpoint
permanently disable Chat based on one historical 409
```

Normal Lesson Exercise must not locally disable Chat.

---

# 24. Conversation Empty State vs Chat-Disabled State

Keep these concepts distinct:

```text
no Conversation exists
→ empty Conversation lifecycle state

Conversation exists but last send/retry was blocked
→ action-scoped Chat-disabled presentation

Message history loaded and empty
→ valid empty Message history

network/history load failed
→ technical load error
```

Do not collapse them into one generic error screen.

---

# 25. Auto-scroll

Use local DOM refs/state only. No scrolling package.

Recommended state:

```text
messageScrollRef
nearBottom flag
previous scrollHeight
```

## First Conversation open

After newest Message page renders:

```text
scroll to bottom
```

## Own send/retry result

When learner-triggered successful Send/Retry result is incorporated:

```text
scroll to bottom
```

## New backend state while already near bottom

If learner is still near bottom:

```text
new incorporated Message
→ keep bottom
```

## Learner reading older history

If learner intentionally scrolls upward beyond a small threshold:

```text
do not force scroll to bottom
```

## Load older

Before prepend:

```text
capture old scrollHeight + scrollTop
```

After older Messages render:

```text
new scrollTop = old scrollTop + (new scrollHeight - old scrollHeight)
```

or an equivalent local DOM approach that preserves visible position.

Tests may mock DOM scroll metrics in jsdom; do not introduce a scrolling library just to test this.

---

# 26. Mandatory D-038 — Safe Assistant Markdown

Add runtime dependency:

```text
react-markdown
```

Use normal npm/package-lock workflow. Do not PM-pin a patch version manually.

Update:

```text
frontend/package.json
frontend/package-lock.json
```

No other Markdown/rich-text dependency is allowed in this Step.

## 26.1 Assistant-only rendering

Only Assistant COMPLETED content requires Markdown.

USER content remains plain React text.

## 26.2 Security configuration

Use `react-markdown` with security behavior equivalent to:

```tsx
<Markdown
  skipHtml
  allowedElements={[
    'p',
    'ul',
    'ol',
    'li',
    'strong',
    'em',
    'code',
    'br',
  ]}
>
  {content}
</Markdown>
```

You may use `unwrapDisallowed` if needed to preserve plain text inside unsupported Markdown constructs, but do not broaden the allowed element set without an approved requirement.

Do not add/use:

```text
rehype-raw
remark-gfm
MDX
syntax highlighting
rich-text editor
citation plugin
HTML plugin
dangerouslySetInnerHTML
custom regex Markdown parser
```

Raw AI HTML must not execute.

No `<script>`, raw `<img onerror>`, iframe, or raw HTML element may become active DOM content from Assistant text.

## 26.3 Required formatting

Support the accepted small subset:

```text
paragraphs
unordered lists
ordered lists
list items
bold
emphasis
inline/code text
line breaks
Chinese/Vietnamese text
```

Do not add table/task-list/code-highlighter behavior.

## 26.4 Citations

Do not synthesize:

```text
Sources
References
citation chips
retrieval badges
source links
```

from Message text.

Real citations remain future Phase-6 behavior.

If backend text contains ordinary bracketed text, render it as content only; do not turn it into grounded citation UI.

---

# 27. Local State / Step-4.5 Boundary

Step 4.4 deliberately predates the global state/session architecture.

Allowed:

```text
useState
useEffect
useRef
local helper functions

panel open/closed
Conversation page/list state
selected Conversation ID
Message pages
composer text
rename draft
local load errors
local mutation pending flags
action-scoped disabled state
scroll state
```

Do not install/use:

```text
@tanstack/react-query
Redux
Zustand
custom global Conversation store
global request cache
query invalidation framework
session bootstrap
ProtectedRoute/AdminRoute
automatic 401 refresh/replay
global retry policy
global toast/error framework
```

Step 4.5 owns those concerns.

Use effect-lifetime guards for asynchronous component-local loads where necessary so stale requests cannot overwrite newer Lesson/Conversation selection.

Do not modify central `apiClient` to add retry/session/polling behavior.

---

# 28. Error Presentation

Keep Step-4.4 error handling local and specific.

Distinguish at least:

```text
Conversation-list load error
Message-history load error
send technical error
retry conflict/error
AI_RESPONSE_FAILED persisted state
AI_CHAT_DISABLED_DURING_TEST action block
rename/delete error
```

Use `ApiError.code`/`status` where behavior differs.

Do not parse `message` text to choose application behavior.

Do not add global toast architecture.

---

# 29. Testing Strategy

Use existing:

```text
Vitest
jsdom
React Testing Library
```

Mock the Step-4.2 Conversation feature API module.

Do not mock lower-level `fetch` in component behavior tests unless testing the API layer itself; Step 4.4 should verify the UI against feature-level mocked contracts.

Prefer behavior-oriented tests over large snapshots.

A focused test file equivalent to:

```text
frontend/src/features/conversation/step44-chat.test.tsx
```

is appropriate.

---

# 30. Required Tests — Placement / Creation

Test at minimum:

```text
Lesson Chat entry is rendered inside Lesson
opening panel works
no /chat route is added
opening panel alone does not call createConversation

zero Conversations
→ explicit empty state
→ Start a conversation

Start a conversation
→ createConversation({ lesson_id })
→ exact request contains no scope/user_id/owner
→ created Conversation becomes selected
→ Composer becomes available

existing Conversations
→ opening panel does not create another Conversation
```

---

# 31. Required Tests — Conversation List / Select / Rename / Delete

Cover:

```text
listConversations uses current lesson_id
page=1/page_size bounded request
zero and multiple Conversations
backend order retained
Load more Conversations
no duplicate Conversation IDs after page merge

initial selected Conversation loads only its history
selecting another Conversation loads only that history
stale previous load does not overwrite new selection

rename sends title only
rename refreshes backend ordering

delete confirmation
delete selected Conversation
→ first remaining backend-ordered Conversation selected

delete last Conversation
→ empty state

no Message deletion control
```

---

# 32. Required Tests — Message Pagination / Ordering

Use representative pages such as:

```text
page 1: sequence 51..100
page 2: sequence 1..50
```

Assert:

```text
initial page renders ASC
Load older calls page=2
older page prepends
dedupe by Message id
final render order is sequence_number ASC
created_at is not used as canonical ordering
Load older disappears/disables when total exhausted
```

Do not implement/test cursor pagination.

---

# 33. Required Tests — Composer / Send

Cover:

```text
whitespace-only blocked
Enter sends
Shift+Enter inserts newline
IME composition Enter does not accidentally submit
duplicate Send disabled while request pending

success
→ sendMessage called once
→ USER + ASSISTANT returned Messages rendered
→ no temporary Message ID
→ composer clears

successful send
→ Conversation list refreshed for backend ordering
```

---

# 34. Required Tests — Send Failures

## `AI_RESPONSE_FAILED`

Assert:

```text
USER draft is not resent
new fake Message is not constructed
newest history is refreshed
persisted USER remains visible
persisted FAILED Assistant appears
Composer draft is cleared for this specific persisted-turn failure
```

## Technical/network uncertainty

Assert:

```text
no optimistic/fake Message
Composer draft preserved
local error shown
Refresh conversation action loads newest history
no automatic resend
```

---

# 35. Required Tests — Status / Retry

Cover persisted Message rendering:

```text
PENDING
→ thinking state
→ no fake answer content

COMPLETED
→ Assistant content

FAILED
→ visible failure
→ Retry action
→ original USER still visible
```

Retry tests:

```text
retry calls retryAssistantMessage(failedAssistantId)
retry does not call sendMessage
retry does not create USER duplicate

retry success
→ new Assistant attempt added in sequence order
→ old FAILED Assistant remains

retry AI_RESPONSE_FAILED
→ newest history refreshed
→ newly persisted FAILED retry attempt appears
→ prior FAILED attempt remains

INVALID_MESSAGE_RETRY
→ local conflict presentation
→ refresh history
```

---

# 36. Required Tests — `AI_CHAT_DISABLED_DURING_TEST`

Send block:

```text
send returns AI_CHAT_DISABLED_DURING_TEST
→ specific notice
→ draft preserved
→ normal Send path disabled
→ no Message inserted

Try again
→ same sendMessage operation/data
→ backend revalidation

retry succeeds
→ blocked state clears
→ persisted response incorporated
```

Retry block:

```text
retry returns AI_CHAT_DISABLED_DURING_TEST
→ same failed Assistant ID preserved
→ Try again calls retryAssistantMessage with same ID
→ never calls sendMessage for original USER content
```

Also verify:

```text
changing Conversation clears action-scoped blocked state
closing/reopening does not preserve a fake long-lived business lock
normal Lesson Exercise state does not locally disable Chat
```

---

# 37. Required Tests — Markdown / Security

Use actual `AssistantMarkdown`/rendering component, not a mocked Markdown renderer, for the security/presentation tests.

Test:

```text
paragraphs render
unordered list renders
ordered list renders
bold renders
emphasis renders
inline/code text renders
Chinese text renders
Vietnamese text renders
```

Security:

```text
<script>window.__pwned = true</script>
→ no script element executes/renders as active HTML

<img src=x onerror="...">
→ no active raw image/event handler

raw HTML tags
→ skipped / not active DOM
```

Assert the UI does **not** invent:

```text
Sources
References
citation/source badges
```

from Assistant content.

Do not test internal implementation details of `react-markdown` beyond the project's security/rendering contract.

---

# 38. Required Tests — Auto-scroll

With mocked DOM scroll metrics where necessary, cover:

```text
first Conversation history load
→ newest position

own successful Send/Retry
→ newest position

learner near bottom + new incorporated Message
→ newest position

learner intentionally reading older history
→ new generic render does not force bottom

Load older prepend
→ visible scroll position preserved
```

No scrolling library.

---

# 39. Boundary / Security Tests

Extend the existing API-boundary/security checks where appropriate.

Assert no Step-4.4 component/source introduces:

```text
direct fetch(
VITE_API_BASE_URL
Authorization: Bearer
localStorage/sessionStorage Chat drafts
provider API key
OpenAI/provider SDK
GLOBAL scope creation
/chat route
TanStack Query
Redux
Zustand
setInterval polling
EventSource
WebSocket
streaming
```

Also assert package dependency policy:

```text
react-markdown present
rehype-raw absent
remark-gfm absent
MDX-related dependency absent
Markdown HTML plugin absent
```

---

# 40. Styling / Accessibility

Keep styling functional and small.

Use existing `index.css` conventions or focused feature CSS if repository convention justifies it.

Ensure:

```text
Chat open/close controls have accessible names
Conversation selection is keyboard-usable
rename/delete buttons are labeled
Message Composer has an accessible label
Send button communicates disabled/pending state
Load older button is keyboard-usable
Retry and Try again controls are real buttons
```

Do not use color alone to distinguish:

```text
USER vs ASSISTANT
PENDING vs FAILED
```

Avoid focus traps unless implemented correctly; a simple overlay with explicit Close is sufficient for this Step. Do not add a modal library.

---

# 41. Expected Files / Changes

Likely frontend changes:

```text
frontend/package.json
frontend/package-lock.json

frontend/src/features/conversation/
  LessonChatRegion.tsx
  ChatPanel.tsx                         # if useful
  ConversationList.tsx                  # if useful
  ConversationHeader.tsx                # if useful
  ConversationEmptyState.tsx            # if useful
  MessageList.tsx                       # if useful
  UserMessage.tsx                       # if useful
  AssistantMessage.tsx                  # if useful
  AssistantMarkdown.tsx                 # recommended focused renderer
  MessageComposer.tsx                   # if useful
  step44-chat.test.tsx                  # or equivalent

frontend/src/features/lesson/LessonPage.tsx
frontend/src/index.css
frontend/src/app/router/routes.test.tsx   # only if needed to preserve no /chat route
frontend/src/test/api-boundary.test.ts    # extend scope/security guardrails if useful

docs/frontend/step-4.4-ai-chat-ui.md
```

Do not change backend code unless a genuine backend contract defect is discovered. If one is discovered, stop and report `BLOCKED`; do not silently patch backend semantics.

Expected **not** to change:

```text
frontend/src/types/api.generated.ts
backend routes/services/schemas/models/migrations
```

because Step 4.4 introduces no API-contract change.

Do not manually edit generated OpenAPI types.

---

# 42. Dependency Changes

Add exactly the justified Step-4.4 runtime dependency:

```text
react-markdown
```

using npm/package-lock.

Do not add:

```text
rehype-raw
remark-gfm
MDX
syntax highlighter
rich text editor
scrolling library
modal/drawer library
TanStack Query
Redux
Zustand
Axios
```

unless execution discovers a genuine blocker and reports it instead of installing extra technology.

---

# 43. Config / Environment

No new environment variables.

Continue using the Step-4.2 API transport indirectly through Conversation feature API functions.

Do not add:

```text
LLM/provider key
OpenAI key
Chat endpoint URL
WebSocket URL
SSE URL
```

to frontend env.

---

# 44. No Backend Changes Expected

Step 4.4 consumes the accepted Step-3.6 Conversation API.

Do not modify:

```text
Conversation database model
Message model
migrations
Conversation router/service/repository
AIChatService
chat availability rules
pagination semantics
retry semantics
Message response schema
```

If a contradiction prevents implementation, report it rather than changing backend behavior.

---

# 45. Step Note

Create:

```text
docs/frontend/step-4.4-ai-chat-ui.md
```

The Step Note must contain:

## Objective

Why the Lesson-scoped Chat UI exists and what Step 4.4 adds.

## Why

Persistent Conversation history, backend-owned Message lifecycle, learner-focused AI interaction.

## Mental Model

```text
Lesson
→ Chat Panel
→ Conversation
→ persisted Messages
→ backend processing state
→ UI rendering
```

## Core Knowledge

At minimum:

```text
persistent Conversation vs local UI state
page-based Message history
sequence_number ordering
backend-confirmed mutation
Message processing states
retry attempt semantics
action-scoped business error state
safe Markdown rendering
```

## Data Flow

Include:

```text
open panel
→ list Conversations
→ select Conversation
→ get Message history

Send
→ backend persists USER + Assistant lifecycle
→ response or persisted failure
→ UI merge/refetch
```

## Key Design Decisions

Record D-037/D-038 and the accepted pagination/send/retry/disabled-state semantics.

## Reusable Approach

Explain how to approach persistent chat/message UIs in other applications without putting transport/AI/business authority into components.

## Common Mistakes

Include:

```text
creating Conversation on panel mount
scope/user_id spoofing
optimistic fake Message IDs
ordering by timestamps
resending USER text for Assistant retry
turning one 409 into a permanent local business rule
polling just to show PENDING
unsafe raw HTML
fake citations
pulling global state in too early
```

## Definition of Done

Reflect actual implementation/testing.

---

# 46. Concepts Discovered — Expected

Only record concepts actually used in implementation.

Expected candidates:

| Concept | Category | Role |
|---|---|---|
| Persistent Conversation | SYSTEM | Backend-owned learner chat thread |
| Message history | SYSTEM | Persistent interaction history |
| Page-based pagination | SYSTEM | Bounded list/history retrieval |
| Deterministic ordering | SYSTEM | `sequence_number` orders Messages |
| Local UI/form state | SYSTEM | Panel, selection, composer, rename |
| Backend-confirmed mutation | SYSTEM | Avoids fake persisted Message state |
| Idempotent merge/deduplication | SYSTEM | Combines server pages/results safely |
| Processing state | BOTH | PENDING/COMPLETED/FAILED AI lifecycle |
| Retry attempt | BOTH | New Assistant attempt for existing USER turn |
| Backend-authoritative Chat availability | BOTH | Periodic Test blocks Chat server-side |
| Safe Markdown rendering | SYSTEM | Formats Assistant text without raw HTML execution |

Do not add RAG/retrieval/citation concepts as implemented concepts in this Step.

---

# 47. Tools Used — Expected

Only record tools actually used.

Expected:

| Tool | Category | Role |
|---|---|---|
| React | SYSTEM | Chat UI/local state |
| TypeScript | SYSTEM | Generated Message/Conversation contracts |
| React Router | SYSTEM | Existing Lesson route context only |
| Step-4.2 Conversation API | SYSTEM | HTTP integration boundary |
| react-markdown | SYSTEM | Safe Assistant Markdown presentation |
| CSS | SYSTEM | Responsive panel/message presentation |
| Vitest | SYSTEM | Behavior tests |
| React Testing Library | SYSTEM | Learner interaction tests |

Do not list TanStack Query because it must not be used yet.

---

# 48. Verification

From `frontend/`:

Initial dependency update may use normal npm workflow to add `react-markdown` and refresh the lockfile.

Final clean verification must run:

```text
node --version
npm --version
npm ci
npm run build
npm run test -- --run
```

Normal Step-4.4 verification must not require FastAPI/PostgreSQL because component tests mock the accepted Conversation feature API.

`api:generate` / `api:check` are **not required merely for Step 4.4** because no public backend contract change is expected. If generated types unexpectedly need change, stop and report a contract issue instead of editing them.

If practical, also run:

```text
npm run lint
```

but lint is supplementary; required acceptance is build + tests.

---

# 49. Acceptance Criteria

Implementation is complete only when all are true:

## Placement

- [ ] AI Chat remains inside Lesson experience.
- [ ] No `/chat` route exists.
- [ ] Desktop panel/drawer-equivalent is usable.
- [ ] Mobile full-screen overlay-equivalent is usable.
- [ ] Explicit Close restores Lesson access.

## Conversation lifecycle

- [ ] Opening panel alone creates no Conversation.
- [ ] Empty state offers explicit Start Conversation.
- [ ] Start sends only `{ lesson_id }`.
- [ ] No `scope`, `user_id`, or owner is sent.
- [ ] Multiple Conversations per Lesson are supported.
- [ ] Existing Conversation list is filtered to current Lesson.
- [ ] List pagination is bounded.
- [ ] Backend list order is preserved.
- [ ] Rename changes title only.
- [ ] Delete uses backend soft-delete endpoint.
- [ ] Selected delete chooses first remaining backend-ordered Conversation or empty state.

## Message history

- [ ] Only selected Conversation history is loaded.
- [ ] Page 1 is newest bounded window.
- [ ] Load older fetches page N+1.
- [ ] Older page prepends correctly.
- [ ] Message IDs are deduped.
- [ ] Final order is `sequence_number ASC`.
- [ ] No timestamp-primary ordering.

## Send

- [ ] Empty/whitespace-only Message blocked locally.
- [ ] Enter sends; Shift+Enter newlines.
- [ ] IME composition does not accidentally send.
- [ ] Duplicate Send prevented while pending.
- [ ] No temporary persisted Message IDs.
- [ ] Normal success merges returned USER + ASSISTANT.
- [ ] Normal success does not require Message refetch for body content.
- [ ] `AI_RESPONSE_FAILED` refreshes persisted history and does not resend original USER text.
- [ ] Technical/network uncertainty preserves draft and creates no fake Message.

## Status / Retry

- [ ] PENDING renders processing state without fake answer content.
- [ ] COMPLETED renders backend content.
- [ ] FAILED remains visible with Retry.
- [ ] Original USER Message remains visible after Assistant failure.
- [ ] Retry calls only retry endpoint with failed Assistant ID.
- [ ] Retry creates no duplicate USER Message.
- [ ] Retry success adds new Assistant attempt while preserving previous failed attempt.
- [ ] Retry AI failure refreshes persisted new FAILED attempt.

## Chat availability

- [ ] `AI_CHAT_DISABLED_DURING_TEST` has specific UI.
- [ ] Blocked Send draft is preserved.
- [ ] Blocked Retry target is preserved.
- [ ] `Try again` repeats the same blocked operation.
- [ ] Backend re-evaluates availability on each attempt.
- [ ] No polling/local Periodic-Test inference.
- [ ] Normal Lesson Exercise does not locally disable Chat.

## Markdown/security

- [ ] `react-markdown` is used for Assistant content.
- [ ] `skipHtml` is enabled.
- [ ] Only the small approved element subset is allowed.
- [ ] Raw HTML does not execute.
- [ ] No `dangerouslySetInnerHTML`.
- [ ] No `rehype-raw` / `remark-gfm` / MDX / HTML plugin.
- [ ] Paragraphs/lists/bold/emphasis/code/line breaks render.
- [ ] Chinese/Vietnamese text remains readable.
- [ ] No fake citation/source UI.

## Scrolling

- [ ] Initial selected history opens at newest position.
- [ ] Own send/retry moves to newest appropriately.
- [ ] Learner reading older history is not forcibly pulled down.
- [ ] Prepending older page preserves visual position.

## Boundaries

- [ ] Components use Step-4.2 Conversation feature API; no direct fetch.
- [ ] No provider API/provider secret exists in frontend.
- [ ] No real LLM/RAG/retrieval/citations.
- [ ] No GLOBAL Chat.
- [ ] No polling/SSE/WebSocket/streaming.
- [ ] No TanStack Query/Redux/Zustand/global cache.
- [ ] No backend changes.
- [ ] No generated OpenAPI edits.

## Verification/docs

- [ ] `npm ci` passes.
- [ ] `npm run build` passes.
- [ ] `npm run test -- --run` passes.
- [ ] Existing Step 4.1–4.3 frontend tests remain passing.
- [ ] Step Note exists and reflects actual implementation.
- [ ] Concepts/Tools report contains only actually used items.

---

# 50. Explicit Non-Goals

Do not implement:

```text
real LLM provider
RAG
embeddings
retrieval
reranking
external search
citation generation
retrieval traces

GLOBAL Chat
standalone /chat route

SSE
WebSocket
token streaming
polling architecture

voice/audio
pronunciation scoring

TanStack Query
session bootstrap
route guards
automatic 401 refresh/replay
global error/retry/toast architecture
Redux
Zustand

Conversation analytics
Message deletion
Conversation export/share
search across Conversations

advanced Markdown plugins
raw HTML
syntax highlighting
rich-text editor
```

---

# 51. Stop Conditions

Stop and report `BLOCKED` rather than guessing if execution discovers that:

1. actual createConversation contract accepts/requires fields beyond the frozen `{ lesson_id }` in a materially conflicting way;
2. actual Message pagination does not follow D-020 page semantics;
3. send/retry persistence behavior contradicts D-023/D-025;
4. correct handling of `AI_CHAT_DISABLED_DURING_TEST` would require a new backend availability endpoint or polling architecture;
5. PENDING correctness would require periodic polling/streaming rather than simply rendering returned state;
6. `react-markdown` cannot satisfy D-038 under the accepted dependency/runtime environment without adding another security/content-processing dependency;
7. Step 4.4 cannot be implemented correctly without introducing Step-4.5 global state/session behavior;
8. a backend code/API/schema change appears necessary.

Do not silently expand scope in any of these cases.

---

# 52. Completion Report Required from Codex

When complete, return a concise implementation handoff containing:

```text
Step
Status
Implementation plan executed
Files created
Files modified
Dependencies added/removed

Placement/responsive behavior
Conversation creation behavior
Conversation list/select/pagination behavior
Rename/delete behavior
Message history pagination/ordering behavior
Composer/send behavior
PENDING/COMPLETED/FAILED behavior
Retry behavior
AI_RESPONSE_FAILED behavior
AI_CHAT_DISABLED_DURING_TEST behavior
Auto-scroll behavior
Safe Markdown/security behavior
Lesson-context behavior
State-management boundary

Tests added
Exact verification commands/results
Acceptance-criteria status
Step Note path
Concepts actually used
Tools actually used
Deviations
Problems/risks
Decisions needed
Recommended next action
```

Explicitly report:

```text
react-markdown resolved version
whether any extra Markdown plugin/dependency was added
whether any backend/generated-contract file changed
whether any direct fetch/provider call/global state was introduced
number of test files/tests passing
```

If blocked, report the exact source conflict and stop.

Do **not** begin Step 4.5.
