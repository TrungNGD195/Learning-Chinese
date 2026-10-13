# Codex Task — Step 8.1 Focused Product Rework: B1 + B4

**Status:** READY_FOR_PM_FREEZE  
**Owner:** Frontend / Backend-System Specialist  
**Scope:** Step 8.1 launch-blocking product rework only  
**Do not start:** Step 8.2  
**Do not modify:** AI/RAG behavior, grading thresholds, progression semantics, unrelated Admin lifecycle  
**Codex gate:** Do not execute until PM freezes this task.

---

## 1. Context

The Step 8.1 QA harness/evidence implementation is already PM accepted. The Step-7.7 regression blocker is cleared.

Two launch-blocking product failures remain:

- **B1 — Pronunciation completion journey**
- **B4 — Admin curriculum-membership workflow**

Both are implementation gaps on top of already-existing backend contracts. Do not redesign the product or public API.

---

# 2. B1 — Pronunciation Completion Journey

## Root gap

The accepted learner contract already exposes:

```http
GET  /api/v1/pronunciation
POST /api/v1/pronunciation/{section_id}/complete
```

The frontend feature API already exposes equivalent `getSections()` and `completeSection()` operations.

Current product UI only presents the Pronunciation sections and does not expose the explicit completion action, so a new learner cannot complete:

```text
TONES
INITIALS
FINALS
```

and therefore cannot reach the backend-authoritative HSK1 availability transition.

## Current response contract

`PronunciationSectionResponse`:

```text
id: UUID
code: string
title: string | null
description: string | null
order_index: number
completed_at: datetime | null
```

The complete mutation response is not a stable typed business-state DTO. Treat it only as acknowledgement and refetch authoritative reads.

The backend is already authoritative for:

```text
pronunciation completion
HSK availability
curriculum-unit state
dashboard Continue Learning
progress
```

Do not calculate unlock state in React.

---

## B1 minimum frontend fix

### Query key

Add:

```ts
pronunciation: ['pronunciation']
```

to the existing `queryKeys`.

### Page query

`PronunciationPage` must load through:

```text
pronunciationApi.getSections()
→ queryKeys.pronunciation
```

Use normal bounded read retry conventions already configured by the app.

### Section UI

For each backend section:

```text
completed_at != null
→ show Completed state
→ no completion button required

completed_at == null
→ show explicit "Mark complete" action
```

Use readable existing section title/code; do not introduce quiz/audio/scoring UI.

### Mutation

Use TanStack Query:

```text
pronunciationApi.completeSection(section.id)
retry: false
```

While one completion mutation is pending:

```text
clicked action → "Completing…"
disable completion actions
prevent duplicate accidental submission
```

Do not optimistically set `completed_at`.

### Success

On success:

```text
invalidate/refetch pronunciation
+
invalidate backend-owned progression surfaces
```

Add a focused helper equivalent to:

```text
invalidatePronunciationCompletion(queryClient)
```

Invalidation set:

```text
queryKeys.pronunciation
queryKeys.dashboard
queryKeys.curriculumLevels
queryKeys.curriculumHskRoot
queryKeys.progressOverview
queryKeys.progressHskRoot
```

Do not manually patch HSK1 state into cache.

The page may show a short action-success acknowledgement, but completed state must ultimately come from refetched `GET /pronunciation`.

After all required sections are complete, HSK1 availability must be observed through existing backend-authoritative Dashboard/Curriculum/Progress reads, not `sections.every(...)` unlock logic in the frontend.

### Error

On completion error:

```text
keep existing section state
show safe inline/action error
re-enable explicit action
no optimistic completion
no automatic mutation replay
```

Use normalized `ApiError` conventions; do not parse human-readable backend messages for business logic.

### Repeated completion

The backend operation is idempotent. The normal UI does not need to keep offering the button once the refetched section is complete.

Do not add client-side idempotency business logic. Preserve backend safety for stale/repeated requests.

---

## B1 expected files

Modify:

```text
frontend/src/features/pronunciation/PronunciationPage.tsx
frontend/src/app/query/keys.ts
```

Create a small helper if consistent with current feature conventions:

```text
frontend/src/features/pronunciation/invalidation.ts
```

The existing:

```text
frontend/src/features/pronunciation/api.ts
```

should be reused and should not require a public-contract change.

Focused tests:

```text
frontend/src/features/pronunciation/step81-pronunciation.test.tsx
```

Backend production code: no change expected.

Extend existing focused backend regression coverage in:

```text
backend/tests/test_business_flow.py
```

only for missing B1/B4 assertions; do not redesign backend behavior.

---

# 3. B1 Tests

Cover at minimum:

1. `GET /pronunciation` data renders all incomplete sections as actionable.
2. Clicking one incomplete section calls `completeSection()` with that backend section ID.
3. Pending mutation prevents duplicate completion submission.
4. Completion failure is surfaced and does not fake completed state.
5. Successful mutation invalidates/refetches `queryKeys.pronunciation`.
6. Refetched `completed_at` drives the Completed UI.
7. A fresh mount/reload reads the persisted completed state from backend data.
8. Completion invalidates Dashboard, curriculum-level, curriculum-HSK-root, progress-overview, and progress-HSK-root caches.
9. After the final required completion, an existing Dashboard/Curriculum/Progress read returning HSK1 `AVAILABLE` is rendered as such.
10. No test should rely on frontend calculation of HSK unlock.
11. Backend regression proves repeated POST of the same section remains safe/idempotent and canonical GET remains completed.

Preserve existing backend tests that already prove:

```text
all pronunciation sections complete
→ backend curriculum first unit AVAILABLE
→ backend Dashboard Continue Learning becomes LESSON
→ backend Progress HSK state AVAILABLE
```

---

# 4. B4 — Admin Curriculum Membership Workflow

## Root gap

Current `AdminCurriculumPage` loads canonical curriculum units and supports only local Move Up / Move Down before saving.

It does **not** let Admin add a newly-created/published Lesson or Periodic Test to curriculum membership, nor detach an existing membership.

Lesson publishing and curriculum membership are separate business actions.

Do not change Lesson publishing to auto-add membership.

---

## Exact current PUT contract

Existing endpoint:

```http
PUT /api/v1/admin/hsk-levels/{hsk_id}/curriculum
```

Request:

```ts
type CurriculumPutRequest = {
  units: CurriculumUnitInput[]
}

type CurriculumUnitInput = {
  unit_type: 'LESSON' | 'PERIODIC_TEST'
  target_id: string
  order_index: number
}
```

The request represents the **complete desired ordered membership**.

Current backend validation already requires:

```text
order_index values = unique consecutive 1..N
no duplicate (unit_type, target_id)
LESSON target exists
LESSON belongs to selected HSK
LESSON is not ARCHIVED
PERIODIC_TEST target exists
target type = PERIODIC_TEST
PERIODIC_TEST is not ARCHIVED
```

The service replaces membership/order transactionally and returns canonical curriculum.

Do not create per-row add/delete endpoints.

Do not expose `AdminCurriculumUnitResponse.id` as the product workflow identifier.

For save payloads use only:

```text
unit_type
target_id
order_index
```

---

# 5. B4 Candidate Discovery

Reuse existing generated/API surfaces.

## Lesson candidates

Use:

```text
listAdminLessons({
  status: 'PUBLISHED',
  hsk_level_id: selectedHskId,
  page,
  page_size
})
```

Only offer `PUBLISHED` Lessons as **new membership candidates**.

This is a product-UI eligibility guard. Do not rewrite backend validation solely to enforce this rework.

Do not remove an already-existing curriculum row from the local draft merely because its lifecycle status is not available in `AdminCurriculumUnitResponse`; current membership remains authoritative until Admin explicitly removes it.

## Periodic Test candidates

Use:

```text
listAdminAssessments({
  status: 'PUBLISHED',
  assessment_type: 'PERIODIC_TEST',
  page,
  page_size
})
```

The current Assessment list contract does not expose an HSK ownership/scope field.

Therefore:

```text
do NOT invent a client-side HSK filter
do NOT inspect raw scope/junction data
do NOT add a new endpoint
```

Offer published Periodic Tests returned by the accepted Admin list API; the curriculum PUT remains backend authority for target validity.

## Pagination

Use existing bounded pagination conventions.

Do not recursively fetch all pages to manufacture a client-side catalog.

Candidate paging/filter changes must not discard the unsaved curriculum draft.

---

# 6. B4 Minimum Admin Workflow

Maintain one local desired-membership draft initialized from canonical:

```text
GET admin curriculum
→ [{unit_type, target_id, title, order_index}, ...]
```

### Add

For a candidate not already present:

```text
Add to curriculum
→ append to local desired membership
→ normalize displayed order 1..N
→ mark draft dirty
```

No backend mutation yet.

### Remove

For an existing local member:

```text
Remove from curriculum
→ remove only from local desired membership
→ normalize order 1..N
→ mark draft dirty
```

This means **detach curriculum membership**, not delete/archive the Lesson or Assessment.

Use clear product copy such as:

```text
Remove from curriculum
```

Never:

```text
Delete CurriculumUnit
Delete junction row
```

### Reorder

Keep existing Move Up / Move Down behavior.

Add/remove/reorder must compose in the same local desired-membership draft.

### Save

Rename the action/copy from order-only semantics to membership + order semantics, for example:

```text
Save curriculum
```

Confirmation:

```text
Save this curriculum membership and order?
```

Submit exactly:

```json
{
  "units": [
    {
      "unit_type": "...",
      "target_id": "...",
      "order_index": 1
    }
  ]
}
```

with order normalized to consecutive `1..N`.

Mutation remains:

```text
retry: false
```

Disable duplicate save while pending.

### Success

On success:

```text
invalidate/refetch canonical Admin curriculum
→ reset local baseline from canonical response
```

Broaden the existing curriculum invalidation helper to cover all backend-owned learner surfaces affected by membership/order:

```text
queryKeys.adminCurriculum(hskId)
queryKeys.curriculumLevels
queryKeys.curriculumHsk(hskId)
queryKeys.progressOverview
queryKeys.progressHsk(hskId)
queryKeys.dashboard
```

No global cache clear.

### Failure

On PUT failure:

```text
keep local unsaved desired membership/order
show safe Admin error
allow explicit retry
```

Reuse existing `adminErrorText()` mappings, including:

```text
INVALID_CURRICULUM
INVALID_CURRICULUM_TARGET
NOT_FOUND
ADMIN_REQUIRED
```

Do not parse backend message strings.

---

# 7. B4 Expected Files

Modify:

```text
frontend/src/features/admin/AdminCurriculumPage.tsx
frontend/src/features/admin/invalidation.ts
frontend/src/features/admin/step47-admin.test.tsx
```

Reuse without public-contract redesign:

```text
frontend/src/features/admin/api.ts
frontend/src/app/query/keys.ts
frontend/src/types/api.generated.ts
```

Do not manually edit `api.generated.ts`.

Backend production code: no change expected.

Extend existing backend regression assertions in:

```text
backend/tests/test_business_flow.py
```

for membership add/remove behavior if not already covered.

---

# 8. B4 Tests

Cover at minimum:

1. Current canonical curriculum membership loads.
2. Current unit response `id` is not exposed as a raw junction-table workflow.
3. Published same-HSK Lesson appears as an add candidate.
4. Draft/Archived Lesson is not offered as a new candidate.
5. Lesson publish action alone does not add curriculum membership.
6. Add Lesson membership updates only the local desired draft before Save.
7. Published Periodic Test appears as an add candidate.
8. Add Periodic Test uses `target_id = assessment.id`.
9. Remove membership detaches locally without calling Lesson/Assessment delete/archive.
10. Existing members can be reordered after add/remove.
11. Save sends one complete `CurriculumPutRequest`.
12. Save normalizes `order_index` exactly to `1..N`.
13. Save uses `lesson.id` / `assessment.id` as `target_id`; never response `CurriculumUnit.id`.
14. Save pending prevents duplicate mutation.
15. Successful save refetches canonical Admin curriculum.
16. Successful save invalidates learner curriculum/progress/dashboard surfaces listed above.
17. A refresh/remount preserves membership and order from backend response.
18. PUT validation error preserves the local unsaved draft and is surfaced safely.
19. Learner curriculum does not gain a published Lesson merely because Lesson publish succeeded.
20. After valid membership PUT, canonical learner curriculum response containing that published Lesson is rendered by the existing learner page.
21. No raw junction-table CRUD/button/ID field appears in the Admin UI.
22. Candidate pagination does not trigger recursive all-page crawling or discard unsaved membership edits.

Backend regression should additionally prove, using the existing PUT:

```text
published Lesson not in curriculum
→ publish alone does not create CurriculumUnit

PUT desired membership including Lesson
→ GET Admin curriculum contains it

PUT desired membership omitting Lesson
→ GET Admin curriculum no longer contains it

reorder + membership replacement
→ canonical order persists
```

Do not change progression semantics in these tests.

---

# 9. Browser QA Rerun

After implementation and smaller regressions pass, rerun only the existing accepted Step-8.1 browser scenarios:

```text
B1 — Pronunciation completion journey
B4 — Admin curriculum-membership workflow
```

Use the existing Step-8.1 QA harness and deterministic fixtures.

Do not create a second E2E framework or rewrite the accepted harness.

Update the existing Step-8.1 evidence/report for B1/B4 with the rerun result.

Do not mark overall Step 8.1 DONE from this implementation task; PM owns final QA acceptance.

---

# 10. Smallest Regression Suites

## Frontend focused

Run the new/updated B1 test plus existing Admin core test:

```text
frontend/src/features/pronunciation/step81-pronunciation.test.tsx
frontend/src/features/admin/step47-admin.test.tsx
```

Also retain learner progression regressions in:

```text
frontend/src/features/step43-learning.test.tsx
```

## Backend focused

Current combined business-flow regression file already covers pronunciation unlock and curriculum reorder:

```text
backend/tests/test_business_flow.py
```

Extend it narrowly for repeated pronunciation completion and curriculum add/remove membership.

No backend production-code change is expected.

## Full regression

Run existing normal project verification after focused tests:

```text
backend full pytest suite
frontend full Vitest suite
frontend build
frontend lint
api:check
```

No OpenAPI regeneration should be needed because no public contract changes are expected.

---

# 11. API / Schema / Migration Impact

Expected:

```text
new endpoint: NO
changed public API: NO
changed generated OpenAPI: NO
database migration: NO
backend production logic change: NO
new runtime dependency: NO
```

If actual implementation proves any of those are required, stop and report:

```text
BLOCKED — DECISION NEEDED
```

Do not silently expand scope.

---

# 12. Scope Guardrails

Do not implement:

```text
pronunciation quiz
pronunciation score
audio/STT/TTS
speech recognition
voice AI

frontend unlock/progression calculation
generic progress mutation

Lesson publish → automatic curriculum membership
raw CurriculumUnit CRUD
junction-table editor
new curriculum endpoint
new schema/migration

AI/RAG changes
assessment threshold changes
unrelated Admin lifecycle changes
Step 8.2 work
```

---

# 13. Completion Handoff Required

Return:

```text
Step
Status

B1 files changed
B1 UI action/pending/error/completed behavior
B1 query invalidation
B1 focused tests

B4 files changed
B4 candidate discovery
B4 add/remove/reorder workflow
B4 exact PUT payload
B4 invalidation
B4 focused tests

Backend production changes
API/OpenAPI changes
Migration changes
Dependencies changed

Focused backend verification
Focused frontend verification
Full backend suite
Full frontend suite
Build
Lint
api:check

Step-8.1 B1 browser rerun
Step-8.1 B4 browser rerun
Evidence/report updated

Problems/risks
Deviations
Decisions needed
Recommended next action
Focused review ZIP path
```

Do not claim:

```text
Step 8.1 DONE
PRODUCT RELEASE READY
Step 8.2 started
```

PM performs the final Step-8.1 gate.
