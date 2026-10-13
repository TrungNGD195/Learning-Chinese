# Step 4.7 — Admin Core UI

## Objective

Provide the existing Admin capability with working Dashboard, Curriculum, Lessons, Assessments, Documents placeholder, and Stats pages. Add the two canonical Admin detail reads and harden their OpenAPI types.

## Why

Admins need to manage the current curriculum, lesson content, and assessments through the same contracts used by the learner application. Canonical reads and generated API types keep detail views aligned with backend state.

## Mental Model

FastAPI and its OpenAPI schema own the contract and lifecycle rules. TanStack Query holds server state; form values and reorder drafts remain local until an explicit mutation succeeds. Admin authorization is enforced by the existing route and backend guards.

## Data Flow

```text
Admin page → typed feature wrapper → apiClient → Admin API
Admin API → query cache → rendered canonical server state
local form/draft → explicit mutation → bounded Admin and learner invalidation
FastAPI OpenAPI → openapi-typescript → api.generated.ts
```

## Core Knowledge

### Backend/OpenAPI contract hardening

D-046 adds direct Admin Lesson and Assessment detail reads using the existing domain read services. Admin unit, lifecycle, and question response values use stable Literals; the Admin Stats HSK bucket has a typed response model. The generated TypeScript is produced from the live FastAPI OpenAPI schema and checked for drift.

### Admin CRUD vs lifecycle actions

Metadata and content edits use their existing CRUD operations. Publish, Review, and Archive are separate lifecycle actions; the UI only presents transitions allowed from the canonical status.

### Server state vs form/edit state

Lists and details come from feature-scoped TanStack Query entries. User edits remain in component state, survive background refresh while dirty, and are replaced by the authoritative response after a successful save.

### Curriculum full-replacement ordering

Curriculum editing preserves existing membership. Move Up/Down changes only the local order, normalized to `1..N`; Save requires confirmation and sends the complete exact ordered unit array. A failed save leaves the draft usable.

### Lesson lifecycle and content mutability

Lesson identity fields remain fixed. Draft and Published metadata/content edits follow backend rules; only Draft content associations can be detached, with confirmation. Archived content is read-only.

### Vocabulary/Grammar canonical vs Lesson association data

Create-and-attach forms collect canonical Vocabulary or Grammar fields together with Lesson placement. Edit forms distinguish canonical content from the Lesson association. The UI does not ask for raw canonical UUIDs.

### Assessment lifecycle

Lesson Exercises use a paginated, readable Lesson selector. Periodic Tests omit deferred scope fields. Metadata edits send only visible metadata; Review, Publish, and Archive use explicit backend transitions.

### Question type-specific editing

Editors exist for all supported question types: multiple choice, fill blank, matching, reorder sentence, Vietnamese-to-Chinese translation, Chinese-to-Vietnamese translation, and sentence writing. Structured types have typed controls; matching item IDs persist during edits, and reorder answers follow row order. No raw JSON editor is exposed.

For nullable free-form Question PATCH fields, omission means unchanged and explicit `null` means clear. Editing an existing answer or rubric to blank sends `null`; creating a new question still omits blank optional values.

### Backend-authoritative errors

Stable `ApiError` codes produce safe feedback. Lifecycle/history conflicts refresh canonical server state where needed. An `ADMIN_REQUIRED` response does not log out the current User.

### Query invalidation / learner-cache coherence

Admin keys are feature-scoped. Mutations invalidate only related Admin entries and learner curriculum, lesson, assessment, progress, or dashboard entries. Periodic Test lifecycle updates use bounded HSK-root invalidation; normal Admin mutations do not clear the whole Query cache.

### Authorization

The existing Admin route guard and `require_admin` backend dependency remain authoritative. Authenticated Learners continue to see the D-041 Forbidden surface.

### Admin Stats as backend aggregates

Stats display total users, current-HSK distribution, and average graded Lesson Exercise score directly from the backend. The frontend does not aggregate data or add charts.

## Key Design Decisions

- Reuse domain canonical reads for the new Admin detail endpoints.
- Generate the API contract from FastAPI OpenAPI instead of hand-editing it.
- Keep Curriculum membership immutable in this UI and submit full order replacements.
- Use typed per-question editors and preserve stable structured IDs.
- Keep Documents as the existing structural placeholder.
- Do not add dependencies, migration changes, scope editing, or future-step behavior.

## How to approach similar Admin systems

Start from the backend contract and lifecycle rules. Separate canonical server state from unsaved form state, use explicit mutation boundaries, refetch after conflicts, and keep invalidation specific to the affected resource and learner views.

## Common Mistakes

- Treating a local draft as authoritative after a failed save.
- Sending only changed curriculum rows when the contract requires full replacement.
- Editing immutable identity fields or inventing lifecycle transitions.
- Confusing shared canonical content with its Lesson association.
- Sending deferred Periodic Test scope fields.
- Storing question configuration as arbitrary JSON.
- Logging out after an ordinary authorization failure or clearing unrelated Query data.
- Manually changing generated API types without regenerating from OpenAPI.

## Definition of Done

- D-046 detail endpoints, stable response types, and behavioral tests are in place.
- Generated OpenAPI types match the live FastAPI schema.
- Admin Curriculum, Lesson, Assessment/Question, and Stats workflows follow the backend contracts.
- D-048 scope semantics and the existing Admin authorization boundary are preserved.
- The required frontend and backend verification passes and the Step Note and review handoff are produced.

## Concepts actually used

| Concept | Category |
| --- | --- |
| Admin CRUD | SYSTEM |
| Backend-authoritative lifecycle | SYSTEM |
| Server state | SYSTEM |
| Form/edit state | SYSTEM |
| Query invalidation | SYSTEM |
| Cross-feature cache coherence | SYSTEM |
| Authorization | SYSTEM |
| Lifecycle transition | SYSTEM |
| Canonical resource read | SYSTEM |
| OpenAPI contract authority | SYSTEM |
| Full-replacement ordering | SYSTEM |
| Aggregate metric | SYSTEM |

## Tools actually used

| Tool | Category |
| --- | --- |
| FastAPI | SYSTEM |
| Pydantic | SYSTEM |
| openapi-typescript | SYSTEM |
| React | SYSTEM |
| TypeScript | SYSTEM |
| React Router | SYSTEM |
| TanStack Query | SYSTEM |
| apiClient / ApiError | SYSTEM |
| Vitest | SYSTEM |
| React Testing Library | SYSTEM |
