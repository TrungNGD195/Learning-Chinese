# Step 4.7 — Admin Core UI

## Context
Product requirements require Admin management of HSK/curriculum, lessons, vocabulary, grammar, assessments/questions and basic statistics. Step 3.4 defines the server-side business APIs; AI generation and document ingestion receive dedicated later UIs.

## Objective
Implement the minimum Admin application surface needed to operate core curriculum/content and view MVP statistics.

## Current State
Steps 4.1, 4.2, 4.5 and 4.6 are complete; Step 3.4 Admin contracts exist.

## In Scope
- Admin dashboard/navigation.
- HSK/curriculum ordering editor.
- Lesson list/editor + publish/archive actions.
- Vocabulary and grammar editing within lesson use cases.
- Assessment list/editor, question CRUD, submit-review/publish/archive.
- `/admin/stats`: Total Users, Users by Current HSK, Average Exercise Score.

## Out of Scope
AI content generation UI (6.13), Document workflow UI (5.8), BI warehouse, bulk import, rich CMS/version diffing.

## Functional Requirements
Frontend actions must mirror legal backend lifecycle transitions; do not render arbitrary status mutation. Published/historical content uses archive/unpublish semantics where required. Statistics are displayed exactly from backend aggregates; frontend must not re-derive them from downloaded user/attempt data.

## Technical Requirements
Use generated OpenAPI types, feature APIs and TanStack Query. Admin route protection is UX only; server role authorization remains authoritative. Mutations invalidate/refetch only relevant queries.

## Inputs / Outputs
Inputs: Admin edits, ordering, lifecycle actions, backend validation errors. Outputs: persisted curriculum/content and rendered stats.

## Data Flow
```text
Admin UI → admin feature API → backend service/domain → PostgreSQL
                                      ↓
                                 refreshed UI
```

## Interfaces / API
Use Step 3.4 Admin endpoints including HSK/curriculum, lessons, vocabulary/grammar, assessments/questions and `/admin/stats`.

## Files / Components
Expected under `features/admin` and existing Admin routes/layout. Split by curriculum/lesson/assessment/stats rather than one giant page.

## Config / Env
No new configuration.

## Error Handling
Show validation/lifecycle/authorization conflicts using stable backend codes. Do not optimistically display publish/approval success before server confirmation.

## Testing
Test Admin route protection, curriculum reorder success/failure, lesson lifecycle actions, vocab/grammar changes, assessment question editing, invalid transition handling and all three required stats.

## Acceptance Criteria
- [ ] Admin can manage HSK curriculum ordering.
- [ ] Admin can manage lesson/vocabulary/grammar content.
- [ ] Admin can manage assessments/questions and legal lifecycle actions.
- [ ] Stats page shows all three Phase-0 metrics.
- [ ] Frontend does not expose persistence junction tables as the user model.
- [ ] Learners cannot use Admin functionality through UI and backend denial is handled.

## Constraints / Non-goals
No AI generation, document processing or analytics platform in this Step.

## Open Questions
None that block this Step.
