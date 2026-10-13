# Step 4.4 - AI Chat UI

## Objective

Add a Lesson-scoped AI Chat panel for persistent Conversations and Messages using the existing Step-4.2 API wrappers. The UI presents backend processing and availability decisions without creating client-side chat records.

## Why

Conversation history and Message lifecycle belong to the backend. A focused panel lets the learner discuss the active Lesson while keeping the Lesson route and its Exercise links available as context.

## Mental Model

```text
Lesson
-> Chat Panel
-> Conversation
-> persisted Messages
-> backend processing state
-> UI rendering
```

## Core Knowledge

- Persistent Conversation data is separate from panel visibility, current selection and the unsent composer draft.
- Conversation and Message history are retrieved in bounded pages.
- `sequence_number` is the ordering field for Messages; `created_at` is not used to sort them.
- Create, send, rename, delete and retry use backend-returned objects. The UI does not invent persisted Messages.
- `PENDING` Assistant content is hidden, `COMPLETED` content is rendered, and `FAILED` shows its own retry action.
- Retrying a FAILED Assistant Message creates another attempt for the original USER turn and leaves prior attempts in history.
- A Load Older scroll snapshot remains request-local until the request succeeds for the still-selected Conversation; failed or stale requests cannot affect later renders.
- A technical network failure keeps the draft and offers an explicit history refresh. `AI_RESPONSE_FAILED` means the USER Message was saved, so the UI refreshes history rather than resending it.
- `AI_CHAT_DISABLED_DURING_TEST` is returned by the backend. The UI preserves and retries the affected send or retry action; it does not infer availability from Lesson Exercises.
- While that action is blocked for the selected Conversation, Try again is the only Message mutation path. Normal Send and Retry controls are both disabled and guarded in their handlers.
- Assistant Markdown is rendered with `react-markdown`, raw HTML is skipped, and only the approved paragraph/list/emphasis/code/line-break elements are allowed. Links, images, HTML and citation UI are not activated.

## Data Flow

Opening Chat loads page 1 for the active `lesson_id`; it does not create a Conversation. The explicit Start/New action calls `createConversation({ lesson_id })`, then refreshes page 1 and loads the selected Conversation history. Selection loads only that Conversation. The existing wrappers own HTTP transport.

Send and Retry merge only server-confirmed Message responses and refresh the Conversation list. `AI_RESPONSE_FAILED` triggers a history refresh to show the persisted failed attempt. A transport failure does not create a local Message. Loading an older history page prepends unique IDs in `sequence_number` order while preserving the visible scroll position.

## Key Design Decisions

- **D-037:** Conversation creation sends only `{ lesson_id }`; the client does not supply scope, user identity or ownership.
- **D-038:** Markdown is rendered using `react-markdown` with `skipHtml` and the approved element allowlist. No raw HTML or Markdown plugins are installed.
- Conversation selection follows backend page order. A refreshed page is deduplicated by Conversation ID; older pages append unique rows.
- Chat-disabled retry state is scoped to its selected Conversation and action. Changing Conversation or closing the panel clears that local state.
- Load Older publishes its captured scroll geometry for restoration only after a successful current response. Selecting another Conversation clears consumable restoration state.
- Scroll follows new history while the learner is at or near the bottom. Reading older content does not force a jump, and older-page prepend restores the previous position.
- State stays inside the mounted panel. This Step does not add shared server-state or global client state.

## Reusable Approach

For backend-owned workflows, call the typed feature wrapper, render returned state, and create or update local state only for UI concerns. Treat ambiguous transport outcomes separately from explicit business errors. For paginated history, deduplicate by stable IDs and sort by the server's documented sequence field.

## Common Mistakes

- Creating a Conversation just because the panel opened.
- Sending owner, user ID or scope values that the backend derives.
- Showing a locally constructed USER Message before the server confirms it.
- Resending after `AI_RESPONSE_FAILED`, which would duplicate a saved USER turn.
- Keeping a scroll-restoration snapshot in shared state while Load Older is unresolved, failed or stale.
- Allowing a normal Send or Retry to replace the preserved operation after Chat is disabled.
- Sorting history by timestamp or replacing an existing failed Assistant attempt.
- Inferring Chat availability from Exercise presence in the Lesson.
- Rendering Assistant text as raw HTML or enabling links/images/plugins outside the approved Markdown subset.
- Adding global state, streaming, provider configuration, retrieval or citation behavior in this Step.

## Definition of Done

- Chat is reachable only from the active Lesson's AI Chat region; there is no `/chat` route.
- Conversation lifecycle, bounded history, send, status, retry, business-error and responsive panel behavior use existing API wrappers.
- Assistant Markdown follows D-038 and the UI preserves Lesson context and Exercise links.
- Frontend build and test commands pass; no backend or generated API contract files change.
- Implementation is handed to the App Engineering Specialist for independent review. PM acceptance remains separate.

## Concepts Discovered

| Concept | Category | Role |
|---|---|---|
| Persistent Conversation | SYSTEM | Backend-owned learner chat thread |
| Message history | SYSTEM | Persistent interaction history |
| Page-based pagination | SYSTEM | Bounded list and history retrieval |
| Deterministic ordering | SYSTEM | `sequence_number` orders Messages |
| Local UI/form state | SYSTEM | Panel, selection, composer and rename |
| Backend-confirmed mutation | SYSTEM | Avoids fake persisted Message state |
| Idempotent merge/deduplication | SYSTEM | Combines server pages and results safely |
| Processing state | BOTH | PENDING/COMPLETED/FAILED AI lifecycle |
| Retry attempt | BOTH | New Assistant attempt for an existing USER turn |
| Backend-authoritative Chat availability | BOTH | Periodic Test blocks Chat server-side |
| Safe Markdown rendering | SYSTEM | Formats Assistant text without activating raw HTML |

## Tools Used

| Tool | Category | Role |
|---|---|---|
| React | SYSTEM | Chat UI and local state |
| TypeScript | SYSTEM | Generated Conversation/Message contracts |
| React Router | SYSTEM | Existing Lesson route context |
| Step-4.2 Conversation API | SYSTEM | HTTP integration boundary |
| react-markdown | SYSTEM | Safe Assistant Markdown presentation |
| CSS | SYSTEM | Responsive panel and message presentation |
| Vitest | SYSTEM | Behavior tests |
| React Testing Library | SYSTEM | Learner interaction tests |
