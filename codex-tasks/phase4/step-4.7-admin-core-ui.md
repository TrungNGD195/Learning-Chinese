# Codex Execution Task — Step 4.7: Admin Core UI

## Execution Gate

This is the **single current Codex execution task** for:

**Step 4.7 — Admin Core UI**

Owner: **App Engineering Specialist**

Implement **Step 4.7 only**.

This task intentionally includes the narrow D-046 backend/OpenAPI contract hardening because PM explicitly approved it as part of Step 4.7. It is still one project Step and one execution task.

Do **not** begin:

- Phase 5 document ingestion/upload;
- Phase 6 AI generation/RAG;
- bulk import;
- rich CMS/versioning;
- a general Admin platform beyond this Step.

Before editing, inspect the actual checkout and the latest canonical PM Decision Log. Expected accepted baseline:

- backend accepted through Step 3.6;
- frontend PM-accepted through Step 4.6;
- D-039 Query read retry / mutation retry policy accepted;
- D-040 central 401 Refresh/replay + single-flight session handling accepted;
- D-041 Admin Forbidden UX accepted;
- D-046 Admin detail/OpenAPI contract hardening DECIDED;
- D-047 `/admin/curriculum` DECIDED;
- D-048 PERIODIC_TEST scope editor deferred;
- TanStack Query is the accepted server-state layer;
- Admin pages are currently structural placeholders;
- no Phase-5 Documents implementation exists.

If the actual checkout materially differs, or correct implementation requires:

- a DB migration;
- business/lifecycle redesign;
- another backend API beyond D-046;
- another runtime dependency;
- a PERIODIC_TEST scope editor/catalog API;
- raw UUID-driven scope UI;
- AI/document functionality;
- a new material Admin convention;

stop and report `BLOCKED` with evidence instead of inventing behavior.

---

# 1. Objective

Implement the minimum usable Admin application surface required to operate core curriculum/content and view MVP statistics.

Required Admin capabilities:

```text
/admin
/admin/curriculum
/admin/lessons
/admin/lessons/:lessonId
/admin/assessments
/admin/assessments/:assessmentId
/admin/documents    → structural only
/admin/stats
```

In scope:

- Admin dashboard/navigation;
- HSK display-metadata editing;
- HSK curriculum ordering editor;
- Lesson list/create/detail/edit;
- Lesson Publish / Archive;
- Lesson Vocabulary create-and-attach/edit/detach;
- Lesson Grammar create-and-attach/edit/detach;
- Assessment list/create/detail/edit;
- Question CRUD with type-specific forms;
- Assessment Submit Review / Publish / Archive;
- Admin Stats:
  - Total Users;
  - Users by Current HSK;
  - Average Exercise Score.

Architecture:

```text
Admin UI
→ Admin feature API
→ central apiClient
→ FastAPI Admin service/domain
→ PostgreSQL
→ authoritative backend response/refetch
```

Frontend is **not** lifecycle, authorization, progression, grading, or statistics authority.

---

# 2. Source of Truth and Precedence

Read the latest canonical PM Decision Log before editing.

At minimum, preserve:

```text
D-009  V0 Question payload/grading contract
D-027  frontend runtime/package workflow
D-028  React Router Data Mode
D-029  frontend testing baseline
D-030  OpenAPI generation ownership
D-031  central apiClient boundary
D-039  bounded Query reads + mutation retry=false
D-040  central 401 recovery / single-flight Refresh
D-041  authenticated non-admin → Forbidden
D-046  focused Admin detail/OpenAPI hardening
D-047  /admin/curriculum
D-048  PERIODIC_TEST scope editor deferred
```

Precedence:

1. latest canonical PM Decision Log;
2. authoritative Step 4.7 specification;
3. later accepted refinements;
4. actual accepted backend/frontend implementation;
5. earlier notes/examples;
6. this execution packet.

Do not silently reinterpret earlier examples against later frozen decisions.

---

# 3. Required Internal Execution Order

Perform Step 4.7 in this order:

```text
1. D-046 backend/schema contract hardening
2. targeted backend tests
3. regenerate frontend OpenAPI TypeScript
4. update Admin API wrappers
5. add Admin Query keys/server-state infrastructure
6. add /admin/curriculum + Admin navigation
7. implement HSK/Curriculum UI
8. implement Lesson/Vocabulary/Grammar UI
9. implement Assessment/Question/Lifecycle UI
10. implement Stats UI
11. focused + full backend/frontend verification
12. Step Note
```

Do not build frontend workarounds before finishing D-046.

---

# 4. D-046 — Focused Backend/OpenAPI Contract Hardening

D-046 explicitly approves a narrow public-interface refinement.

## 4.1 Canonical Admin Lesson detail read

Add:

```http
GET /api/v1/admin/lessons/{lesson_id}
```

Response:

```text
LessonAdminResponse
```

Unknown Lesson:

```text
404 NOT_FOUND
```

Use the existing Admin authorization dependency.

Implementation should reuse existing repository/service reads.

Do not scan paginated Lesson collections.

Do not use PATCH as a fake GET.

## 4.2 Canonical Admin Assessment detail read

Add:

```http
GET /api/v1/admin/assessments/{assessment_id}
```

Return the canonical Admin Assessment metadata needed by the editor.

The smallest accepted response may reuse the hardened `AssessmentAdminResponse` if it contains all Step-4.7 editor metadata:

```text
id
type
lesson_id
title
description
status
pass_threshold
published_at
```

Do **not** add D-048 deferred scope arrays merely for this endpoint.

Unknown Assessment:

```text
404 NOT_FOUND
```

Do not scan paginated Assessment collections.

## 4.3 Harden stable Admin response typing

Use backend schema types/Literals reflecting existing runtime values.

At minimum generated TypeScript must make these stable response fields typed:

```text
LessonAdminResponse.status
→ "DRAFT" | "PUBLISHED" | "ARCHIVED"

AssessmentAdminResponse.type
→ "LESSON_EXERCISE" | "PERIODIC_TEST"

AssessmentAdminResponse.status
→ "DRAFT" | "REVIEW" | "PUBLISHED" | "ARCHIVED"

QuestionAdminResponse.type
→ "multiple_choice"
 | "fill_blank"
 | "matching"
 | "reorder_sentence"
 | "translate_vi_zh"
 | "translate_zh_vi"
 | "sentence_writing"

AdminCurriculumUnitResponse.unit_type
→ "LESSON" | "PERIODIC_TEST"
```

Do not invent new enum values.

A clean implementation may define reusable Literal aliases in the backend Admin schema module.

## 4.4 Harden Admin Stats bucket typing

Replace the loose:

```text
users_by_current_hsk: list[dict]
```

with a typed nested response model equivalent to:

```text
AdminHskUserCountResponse
- hsk_level: int
- users: int
```

Then:

```text
AdminStatsResponse.users_by_current_hsk
→ list[AdminHskUserCountResponse]
```

Runtime statistics semantics must not change.

## 4.5 Expected backend files

Expected focused changes are approximately:

```text
backend/app/admin/router.py
backend/app/admin/schemas.py
backend/app/admin/service.py
backend/tests/... focused Admin contract tests
```

Repository changes are not expected because existing canonical read functions already exist.

Do not modify:

```text
database models
Alembic migrations
business lifecycle rules
progression rules
authorization model
```

unless an actual contradiction is found; if so stop.

## 4.6 D-046 backend tests

Add behavior/contract tests proving at minimum:

```text
GET Admin Lesson detail
→ 200 exact resource
→ 404 NOT_FOUND

GET Admin Assessment detail
→ 200 exact resource
→ 404 NOT_FOUND

OpenAPI response schema exposes typed:
Lesson status
Assessment type/status
Question type
Curriculum unit_type
Admin Stats HSK buckets
```

Existing Admin authorization tests must remain passing.

---

# 5. OpenAPI Synchronization

After backend contract hardening:

```text
FastAPI
→ /openapi.json
→ openapi-typescript
→ frontend/src/types/api.generated.ts
```

Use the accepted D-030/D-032 workflow.

Do not manually edit:

```text
frontend/src/types/api.generated.ts
```

Run the canonical local backend when synchronizing the contract.

Expected generated changes are limited to D-046:

- two new GET operations on existing Admin detail paths;
- hardened Admin enum response fields;
- typed Admin Stats HSK bucket;
- schema references necessary for those changes.

If generated output shows an unrelated material API drift:

```text
STOP
→ investigate
→ report evidence
```

After generation run:

```text
npm run api:check
```

with the accepted FastAPI application running.

---

# 6. Admin API Wrapper Changes

Continue using:

```text
Page / feature
→ feature Admin API function
→ apiClient
→ FastAPI
```

Do not call `fetch` directly.

Add explicit generated-contract-based wrappers equivalent to:

```text
getAdminLesson(lessonId)
getAdminAssessment(assessmentId)
```

Keep existing wrappers for:

```text
HSK
Curriculum
Lesson CRUD/lifecycle
Vocabulary/Grammar
Assessment CRUD/lifecycle
Question CRUD
Stats
```

Do not hand-write duplicate response DTO interfaces.

Generated schema types remain authoritative.

---

# 7. Admin Query Keys

Extend the existing `queryKeys` with stable Admin namespaces.

Equivalent design:

```text
adminHskLevels
→ ["admin", "hsk-levels"]

adminCurriculum(hskId)
→ ["admin", "curriculum", hskId]

adminLessonsRoot
→ ["admin", "lessons"]

adminLessons(filters)
→ ["admin", "lessons", filters]

adminLesson(lessonId)
→ ["admin", "lesson", lessonId]

adminLessonVocabulary(lessonId)
→ ["admin", "lesson", lessonId, "vocabulary"]

adminLessonGrammar(lessonId)
→ ["admin", "lesson", lessonId, "grammar"]

adminAssessmentsRoot
→ ["admin", "assessments"]

adminAssessments(filters)
→ ["admin", "assessments", filters]

adminAssessment(assessmentId)
→ ["admin", "assessment", assessmentId]

adminQuestions(assessmentId)
→ ["admin", "assessment", assessmentId, "questions"]

adminStats
→ ["admin", "stats"]
```

Filter-key objects must contain only normalized filter/pagination values.

Server resources belong to Query.

Do **not** put into Query cache:

```text
unsaved metadata fields
curriculum reorder draft
question editor draft
selected editor mode/tab
confirmation state
```

No second global Admin store.

---

# 8. D-047 — Admin Route / Navigation

Add:

```text
/admin/curriculum
```

under the existing `AdminRoute` + `AdminLayout`.

Admin navigation must include:

```text
Dashboard
Curriculum
Lessons
Assessments
Documents
Stats
```

`/admin` remains a small entry/navigation page.

`/admin/documents` remains structural only.

Do not add any:

```text
upload
document CRUD
ingestion
Phase-5 behavior
```

Update route/navigation tests accordingly.

---

# 9. Admin Dashboard

Keep `/admin` minimal.

Use simple navigation cards/links for:

```text
Curriculum
Lessons
Assessments
Stats
```

Documents may remain represented in the existing navigation but must stay structural.

Do not calculate or duplicate Stats on the dashboard.

---

# 10. HSK Admin Design

HSK records are a fixed catalog.

Admin may edit only:

```text
title
description
```

Read-only:

```text
level_number
order_index
id
```

No:

```text
create HSK
delete HSK
reorder HSK records
edit level_number
edit HSK order_index
```

The Curriculum page is the natural place to show selected-HSK metadata editing.

Use:

```text
listHskLevels()
updateHskLevel(...)
```

Mutation:

```text
retry = false
```

On success refetch/invalidate only affected Admin + learner Queries defined below.

Backend remains validation authority.

---

# 11. Curriculum Ordering Editor

Route:

```text
/admin/curriculum
```

Flow:

```text
select HSK
→ get canonical curriculum
→ initialize local reorder draft
→ Move Up / Move Down
→ explicit Save order
→ lightweight confirmation
→ PUT full replacement
→ authoritative refetch
```

Do not add drag/drop.

## 11.1 Local reorder state

Local draft contains only the current canonical unit identity needed to submit:

```text
unit_type
target_id
order_index
```

Derive `target_id` from:

```text
LESSON
→ lesson_id

PERIODIC_TEST
→ assessment_id
```

Do not expose/persist `CurriculumUnit.id` as the Admin mental model.

After every move, local submitted order must be normalized to:

```text
1..N
```

## 11.2 Full replacement payload

Exact body:

```json
{
  "units": [
    {
      "unit_type": "LESSON",
      "target_id": "<uuid>",
      "order_index": 1
    }
  ]
}
```

Do not add/remove membership in this Step.

This page is an ordering editor for existing units.

## 11.3 Dirty-state preservation

Do not overwrite an unsaved reorder draft merely because TanStack Query performs a background refetch.

Equivalent rule:

```text
query data changes
AND draft is not dirty
→ sync draft

draft is dirty
→ preserve local draft
```

After successful Save + authoritative refetch, reset the local draft/baseline from server state.

Changing selected HSK may reset the previous local reorder draft; no persistence/autosave is required.

## 11.4 Failure

For backend:

```text
INVALID_CURRICULUM
INVALID_CURRICULUM_TARGET
NOT_FOUND
```

show inline/error state using `ApiError.code`.

Keep local draft for retry unless server conflict requires an explicit Reload/refetch.

No automatic mutation retry.

---

# 12. Lesson List

Implement `/admin/lessons` using the existing paginated Admin endpoint.

Support simple existing filters:

```text
status
hsk_level_id
page
page_size
```

Use ordinary page controls such as:

```text
Previous
Next
```

No infinite scrolling requirement.

Render useful fields:

```text
HSK
lesson_number
title
status
```

Expose:

```text
Create Lesson
Open Editor
```

## 12.1 Create Lesson

Form fields:

```text
HSK
lesson_number
title
description
```

HSK uses loaded HSK choices; do not ask Admin to type a raw HSK UUID.

Exact backend body:

```text
hsk_level_id
lesson_number
title
description?
```

Do not send status.

On success:

```text
invalidate Admin Lesson list
→ navigate/open created Lesson editor
```

No learner invalidation is required merely for creating a DRAFT Lesson.

---

# 13. Admin Lesson Editor

Route:

```text
/admin/lessons/:lessonId
```

Canonical load:

```text
getAdminLesson(lessonId)
```

Do not derive editor authority from collection cache.

Load Lesson Vocabulary/Grammar as separate Admin server resources.

Display immutable identity:

```text
HSK
lesson_number
status
published_at
```

Metadata form:

```text
title
description
```

Do not expose:

```text
hsk_level_id edit
lesson_number edit
status dropdown
```

## 13.1 Metadata editability

Actual backend:

```text
DRAFT
→ metadata editable

PUBLISHED
→ metadata editable

ARCHIVED
→ metadata immutable
```

Do not simplify Published to immutable.

After successful metadata save:

```text
invalidate/refetch:
Admin Lesson detail
Admin Lesson list
bounded learner resources
```

No optimistic success state.

## 13.2 Lesson lifecycle buttons

Exactly:

```text
DRAFT
→ Publish

PUBLISHED
→ Archive

ARCHIVED
→ no lifecycle action
```

No unpublish.

No unarchive.

No arbitrary status dropdown.

Archive requires lightweight confirmation.

On:

```text
INVALID_LIFECYCLE_TRANSITION
```

show action-specific conflict and refetch authoritative Lesson detail/list.

---

# 14. Vocabulary Within Lesson

Use:

```text
GET    /admin/lessons/{lessonId}/vocabulary
POST   /admin/lessons/{lessonId}/vocabulary
PATCH  /admin/lessons/{lessonId}/vocabulary/{linkId}
DELETE /admin/lessons/{lessonId}/vocabulary/{linkId}
```

User-facing model must distinguish:

## Canonical Vocabulary content

```text
hanzi
pinyin
vietnamese_meaning
part_of_speech
```

## Lesson association/placement

```text
order_index
note
example
```

The response `id` is the LessonVocabulary association ID used for patch/detach.

`vocabulary_id` identifies canonical shared Vocabulary but is not a normal Step-4.7 form input.

## 14.1 Attach UX

Implement only:

```text
Create new Vocabulary and attach
```

Form sends:

```text
hanzi
pinyin
vietnamese_meaning
part_of_speech?
order_index
note?
example?
```

Do not send `vocabulary_id` in new-item mode.

Do not expose raw existing Vocabulary UUID entry.

Do not build global Vocabulary search.

## 14.2 Update

Allow editing:

```text
canonical content
+
Lesson association fields
```

Visually distinguish the two groups.

A small note may explain that canonical Vocabulary content is shared data.

## 14.3 Detach

Detach is available only when current Lesson status is:

```text
DRAFT
```

Do not show/enable detach for PUBLISHED or ARCHIVED.

Require lightweight confirmation.

Handle:

```text
LESSON_CONTENT_DETACH_DRAFT_ONLY
ITEM_HAS_LEARNER_HISTORY
LESSON_CONTENT_IMMUTABLE
NOT_FOUND
```

using code-driven behavior.

No automatic mutation retry.

---

# 15. Grammar Within Lesson

Same architecture as Vocabulary.

Canonical Grammar content:

```text
name
structure
explanation
usage
```

Lesson association:

```text
order_index
note
example
```

Attach only through:

```text
Create new Grammar and attach
```

Do not expose raw `grammar_id`.

Do not build global Grammar search.

Detach only for DRAFT Lesson with lightweight confirmation.

Respect:

```text
LESSON_CONTENT_IMMUTABLE
LESSON_CONTENT_DETACH_DRAFT_ONLY
ITEM_HAS_LEARNER_HISTORY
```

---

# 16. Lesson Content Mutation Rules

Actual backend:

```text
DRAFT
→ Vocabulary/Grammar attach/update/detach

PUBLISHED
→ Vocabulary/Grammar attach/update
→ no detach

ARCHIVED
→ content immutable
```

UI controls must mirror these rules.

Do not optimistically add fake server records before backend confirmation.

After successful attach/update/detach:

```text
invalidate/refetch relevant Admin Lesson content
+
bounded learner Lesson/progress resources
```

---

# 17. Assessment List

Implement `/admin/assessments` with existing pagination/filters:

```text
status
assessment_type
page
page_size
```

Render:

```text
type
title
status
pass_threshold
lesson target where applicable
```

Expose:

```text
Create Assessment
Open Editor
```

No arbitrary status mutation.

---

# 18. Assessment Create

Fields:

```text
type
title
description
pass_threshold
```

For:

```text
LESSON_EXERCISE
```

require a human-readable Lesson target selector.

Do **not** expose raw Lesson UUID input.

Use existing Admin Lesson list API to populate a bounded/paginated selector. A simple HSK/filter/page or Load More interaction is acceptable; do not add a discovery dependency.

Exact LESSON_EXERCISE payload:

```text
type = LESSON_EXERCISE
lesson_id
title
description?
pass_threshold
```

For:

```text
PERIODIC_TEST
```

exact Step-4.7 UI payload omits:

```text
lesson_id
lesson_ids
vocabulary_ids
grammar_ids
```

and sends:

```text
type = PERIODIC_TEST
title
description?
pass_threshold
```

Do not build D-048 scope UI.

On create success:

```text
invalidate Admin Assessment list
→ navigate/open new Assessment editor
```

DRAFT creation does not require broad learner invalidation.

---

# 19. D-048 — PERIODIC_TEST Scope Preservation

Do not render controls for:

```text
lesson_ids
vocabulary_ids
grammar_ids
```

Do not render raw UUID or JSON fields.

Current backend PATCH semantics are partial:

```text
scope fields omitted
→ existing persisted scope stays unchanged

scope field present
→ only that scope set is replaced
```

Therefore every Step-4.7 metadata PATCH for an existing PERIODIC_TEST must construct the request body explicitly from only supported visible fields:

```text
title
description
pass_threshold
```

Never spread an existing generated Assessment object into the PATCH body.

Never include deferred scope fields as:

```text
undefined
null
[]
```

simply because the form does not expose them.

The goal is:

```text
edit unrelated metadata
→ deferred backend scope preserved
```

If actual checkout semantics differ:

```text
STOP
→ BLOCKED
```

instead of erasing scope.

---

# 20. Admin Assessment Editor

Route:

```text
/admin/assessments/:assessmentId
```

Canonical load:

```text
getAdminAssessment(assessmentId)
```

Load Questions separately:

```text
listAssessmentQuestions(assessmentId)
```

Do not use collection cache as editor authority.

Immutable identity after creation:

```text
type
lesson_id
```

Editable metadata only where backend permits:

```text
title
description
pass_threshold
```

Assessment metadata/Questions are editable:

```text
DRAFT
REVIEW
```

Immutable:

```text
PUBLISHED
ARCHIVED
```

Do not expose type/status arbitrary edit controls.

---

# 21. Assessment Lifecycle

Exact legal actions:

```text
DRAFT
→ Submit Review
→ REVIEW

REVIEW
→ Publish
→ PUBLISHED

PUBLISHED
→ Archive
→ ARCHIVED

ARCHIVED
→ none
```

Submit Review requires at least one Question.

Archive requires lightweight confirmation.

No optimistic status transition.

After mutation confirmation:

```text
invalidate/refetch:
Admin Assessment detail
Admin Assessment list
Questions where relevant
bounded learner resources
```

Handle:

```text
ASSESSMENT_HAS_NO_QUESTIONS
INVALID_LIFECYCLE_TRANSITION
ASSESSMENT_IMMUTABLE
```

with action-specific UI.

A 409 lifecycle conflict must refetch authoritative current Assessment state.

---

# 22. Question CRUD

Supported types are exactly:

```text
multiple_choice
fill_blank
matching
reorder_sentence
translate_vi_zh
translate_zh_vi
sentence_writing
```

Question type:

```text
chosen on Create
→ immutable afterward
```

Do not implement a generic JSON editor.

Do not expose AI generation.

Common fields:

```text
prompt
order_index
points
```

Use numeric input constraints for positive `order_index` and `points`, but backend remains final validation authority.

---

# 23. Multiple Choice Question Editor

Create/edit UX:

```text
Prompt
Order
Points
Option rows
one correct-option radio
```

Backend create payload:

```text
type = multiple_choice
prompt
order_index
points
options: [
  {
    option_text,
    is_correct
  }
]
```

At least two options.

Exactly one correct.

Do not put an answer key into config.

On edit, type is displayed read-only and must not be sent in PATCH.

---

# 24. Fill Blank Question Editor

Fields:

```text
Prompt
Order
Points
Reference answer
Accepted-answer rows (optional)
```

Config:

```json
{
  "accepted_answers": ["..."]
}
```

Create requires a reference answer.

On update, preserve valid existing values not being edited.

---

# 25. Matching Question Editor

Fields:

```text
Prompt
Order
Points
Left item rows
Right item rows
Pair mapping
```

Config:

```text
left_items:
- id
- text

right_items:
- id
- text

correct_pairs:
- left_id
- right_id
```

For newly-created local rows generate opaque string IDs using a browser-native mechanism such as:

```text
crypto.randomUUID()
```

or an equivalent dependency-free opaque-ID helper.

When editing existing Matching Questions:

```text
preserve backend-returned existing item IDs
```

Do not regenerate IDs merely because text changes.

Do not cast the entire Question response to a handwritten DTO.

Narrow generated config structurally/type-safely.

---

# 26. Reorder Sentence Question Editor

Fields:

```text
Prompt
Order
Points
Item rows
Move Up
Move Down
```

Each item:

```text
id
text
```

New local item IDs use dependency-free opaque IDs.

Existing IDs are preserved.

Submitted config:

```text
items
correct_order
```

where:

```text
correct_order
```

exactly follows the current local item order.

No drag/drop dependency.

---

# 27. Free-Form Question Editors

For:

```text
translate_vi_zh
translate_zh_vi
sentence_writing
```

render:

```text
Prompt
Order
Points
Reference answer (optional if contract allows)
Rubric (optional if contract allows)
```

No config editor is needed.

Do not implement AI grading/generation controls.

---

# 28. Question Update/Delete Rules

Question metadata/config is editable only while Assessment is:

```text
DRAFT
REVIEW
```

PUBLISHED/ARCHIVED:

```text
Questions immutable
```

Type is immutable after creation.

Handle:

```text
QUESTION_TYPE_IMMUTABLE
QUESTIONS_IMMUTABLE
INVALID_QUESTION
QUESTION_HAS_HISTORY
NOT_FOUND
```

Delete requires lightweight confirmation.

After successful Question CRUD:

```text
invalidate/refetch:
Admin Questions
Admin Assessment detail if current UI derives lifecycle readiness
bounded learner Assessment query where relevant
```

No optimistic fake Question IDs.

---

# 29. Admin Stats

Route:

```text
/admin/stats
```

Use the backend response exactly.

Render:

## Total Users

Metric card:

```text
total_users
```

## Users by Current HSK

Simple table:

```text
HSK Level
Users
```

using typed:

```text
users_by_current_hsk[]
```

If empty:

```text
No learner HSK data yet.
```

## Average Exercise Score

Metric card:

```text
average_exercise_score
```

If null:

```text
No graded lesson-exercise attempts yet.
```

Do not:

```text
fetch all Users
fetch all Attempts
recalculate counts
recalculate averages
add a chart library
```

Stats remain backend aggregates.

---

# 30. Bounded Query Invalidation Matrix

Do **not** call:

```text
queryClient.clear()
```

after normal Admin mutations.

Do **not** invalidate the entire application.

Use targeted Admin and learner cache convergence.

## 30.1 HSK metadata update

Admin:

```text
adminHskLevels
adminCurriculum(hskId)
```

Learner:

```text
curriculumLevels
curriculumHsk(hskId)
progressOverview
progressHsk(hskId)
dashboard
```

## 30.2 Curriculum reorder

Admin:

```text
adminCurriculum(hskId)
```

Learner:

```text
curriculumHsk(hskId)
progressHsk(hskId)
dashboard
```

## 30.3 Lesson create

Admin:

```text
adminLessonsRoot
```

No broad learner invalidation for a new DRAFT Lesson.

## 30.4 Lesson metadata update

Admin:

```text
adminLesson(lessonId)
adminLessonsRoot
```

Learner:

```text
lesson(lessonId)
curriculumHsk(hskId)
progressHsk(hskId)
dashboard
```

Use the loaded/returned Lesson's actual `hsk_level_id`.

## 30.5 Vocabulary/Grammar attach/update/detach

Admin:

```text
adminLessonVocabulary(lessonId)
or
adminLessonGrammar(lessonId)

adminLesson(lessonId) where useful
```

Learner:

```text
lesson(lessonId)
lessonProgress(lessonId)
curriculumHsk(hskId)
progressHsk(hskId)
dashboard
```

Do not locally recalculate learner completion.

## 30.6 Lesson Publish / Archive

Admin:

```text
adminLesson(lessonId)
adminLessonsRoot
adminCurriculum(hskId)
```

Learner:

```text
lesson(lessonId)
curriculumLevels
curriculumHsk(hskId)
progressOverview
progressHsk(hskId)
dashboard
```

Backend publication state remains authoritative.

## 30.7 Assessment create

Admin:

```text
adminAssessmentsRoot
```

No broad learner invalidation for a new DRAFT Assessment.

## 30.8 Assessment metadata / Question CRUD

Admin:

```text
adminAssessment(assessmentId)
adminAssessmentsRoot where metadata changed
adminQuestions(assessmentId)
```

Learner:

```text
assessment(assessmentId)
```

where the learner Query is relevant.

Do not invent progression updates.

## 30.9 LESSON_EXERCISE lifecycle Publish / Archive

In addition to Admin Assessment invalidation, invalidate:

```text
assessment(assessmentId)
lesson(lesson_id)
```

Reason:

```text
LessonResponse.assessment_ids
→ backend returns only PUBLISHED LESSON_EXERCISE IDs
```

Therefore publishing/archiving a Lesson Exercise changes learner Lesson server state.

This is a narrow cache-coherence refinement based on the actual accepted backend contract.

Do not calculate or patch `assessment_ids` locally.

## 30.10 PERIODIC_TEST lifecycle Publish / Archive

The current Admin Assessment response does not expose one reliable HSK owner.

Use bounded learner roots:

```text
curriculumHskRoot
progressHskRoot
dashboard
progressOverview
curriculumLevels
assessment(assessmentId)
```

Do not invalidate the whole QueryClient.

## 30.11 Admin Stats

Do not invalidate `adminStats` after every content mutation by default.

The canonical metrics concern:

```text
Users
current HSK progression
graded lesson-exercise score
```

Content-edit operations do not automatically imply those aggregate values changed.

Normal Query refetch or explicit Stats-page Retry remains sufficient.

---

# 31. Authorization / Session Behavior

Preserve D-041 exactly.

```text
AUTHENTICATED LEARNER + /admin
→ Forbidden
```

Backend Admin APIs remain protected by `require_admin`.

For an Admin request returning:

```text
403 ADMIN_REQUIRED
```

show authorization error state.

Do **not**:

```text
logout
clear current User
redirect globally to /login
```

Ordinary 403 remains authorization/business access, not generic authentication failure.

`ACCOUNT_DISABLED` continues through the already-accepted session mechanism.

Do not change D-040.

---

# 32. Admin Error Handling

Use:

```text
ApiError.status
ApiError.code
ApiError.details
```

Do not parse `ApiError.message` to make behavior decisions.

Known relevant codes include:

```text
NOT_FOUND

INVALID_FIELDS
INVALID_CURRICULUM
INVALID_CURRICULUM_TARGET

INVALID_LESSON
LESSON_IMMUTABLE
LESSON_CONTENT_IMMUTABLE
LESSON_CONTENT_DETACH_DRAFT_ONLY
INVALID_ITEM_MODE
ITEM_HAS_LEARNER_HISTORY

INVALID_ASSESSMENT_TARGET
INVALID_ASSESSMENT
INVALID_ASSESSMENT_SCOPE
ASSESSMENT_IMMUTABLE
ASSESSMENT_HAS_NO_QUESTIONS

INVALID_QUESTION
QUESTION_TYPE_IMMUTABLE
QUESTIONS_IMMUTABLE
QUESTION_HAS_HISTORY

INVALID_LIFECYCLE_TRANSITION
INVALID_REQUEST

ADMIN_REQUIRED
```

Behavior classes:

## Validation / shape

```text
422 + validation code
→ form/action feedback
→ preserve unsaved edit state
```

## Lifecycle/history conflict

```text
409
→ action-specific feedback
→ refetch authoritative affected entity/resource
```

## Not found

```text
404 NOT_FOUND
→ resource-not-found editor state
```

## Authorization

```text
403 ADMIN_REQUIRED
→ authorization error
→ no logout
```

## Technical

```text
NETWORK_ERROR / 5xx
→ recoverable error
→ no automatic mutation retry
```

No toast dependency.

---

# 33. Mutation / Pending Policy

Preserve D-039:

```text
ALL Admin mutations
→ retry = false
```

This includes:

```text
HSK update
Curriculum replace
Lesson create/update/publish/archive
Vocabulary attach/update/detach
Grammar attach/update/detach
Assessment create/update
Question create/update/delete
Submit Review
Publish Assessment
Archive Assessment
```

Use:

```text
mutation.isPending
```

or an equivalent per-entity keyed local pending mechanism where multiple item mutations can be concurrent.

Disable duplicate **exact** action.

Do not globally disable unrelated item actions without a requirement.

---

# 34. Form / Edit State

Unsaved Admin edits remain local React state.

Examples:

```text
HSK title/description draft
Curriculum order draft
Lesson metadata form
Vocabulary/Grammar form
Assessment form
Question type-specific form
```

Do not copy them into Query cache.

Do not add a form library.

Do not duplicate complete backend validation logic.

Client validation should cover obvious UX constraints only:

```text
required fields
positive order values
pass threshold 0..100
password-style security not applicable
question option count/correct choice
obvious type-specific form completeness
```

Backend remains final authority.

---

# 35. Loading / Empty / Background Refetch

Preserve Step-4.5 model.

```text
primary Query pending
→ page/section loading

existing data + background refetch
→ keep existing content visible

successful []
→ empty state

Query error
→ explicit Retry

mutation pending
→ action loading
→ disable duplicate exact action
```

Do not use `!data` alone to conflate loading/empty/error.

Do not blank an editor unnecessarily during background refetch.

Unsaved local form state must not be silently overwritten by a background refetch.

---

# 36. Confirmation UX

Use the smallest dependency-free confirmation consistent with the repository, such as native `window.confirm` or simple inline confirmation.

Required for:

```text
Archive Lesson
Archive Assessment
Detach Vocabulary
Detach Grammar
Delete Question
Save full-replacement Curriculum order
```

Do not build a generic modal framework.

Tests may mock the native confirmation interaction.

---

# 37. Suggested Frontend Structure

Keep `features/admin` split by actual domain rather than one giant file.

A reasonable structure is:

```text
features/admin/
  api.ts
  AdminDashboardPage.tsx
  AdminCurriculumPage.tsx
  AdminLessonsPage.tsx
  AdminLessonEditorPage.tsx
  AdminAssessmentsPage.tsx
  AdminAssessmentEditorPage.tsx
  AdminStatsPage.tsx
  QuestionEditor.tsx
  ...small focused helpers if genuinely useful
```

Exact names may follow repository conventions.

Do not introduce deep abstraction layers solely for aesthetics.

Replace structural `AdminPages` placeholders for implemented routes.

Keep Documents structural.

---

# 38. CSS / Accessibility

Use existing CSS conventions and extend `index.css` only as needed.

Do not add a component/UI framework.

Forms must have:

```text
labels associated with controls
descriptive buttons
visible error text
pending/disabled states
```

Status/action availability must not rely on color alone.

Tables should use semantic table markup where applicable.

---

# 39. Exact Scope Guardrails

Do **not** implement:

```text
AI content generation
AI question generation
Document upload
Document CRUD
ingestion
bulk import
rich text editor
CMS version history
content diff
BI/warehouse dashboard
chart library
drag/drop library
form/validation library
UI framework
Redux/Zustand/global Admin store
global Vocabulary search
global Grammar search
raw UUID normal-form inputs
PERIODIC_TEST scope editor
generic JSON Question editor
arbitrary lifecycle Status dropdown
frontend authorization authority
frontend progression/grading/statistics calculations
application-wide Query invalidation
```

Do not create a new backend endpoint family beyond D-046.

---

# 40. Expected Backend Files / Components Changed

Expected:

```text
backend/app/admin/router.py
backend/app/admin/schemas.py
backend/app/admin/service.py

backend/tests/<focused Step-4.7 Admin contract test files>
```

Not expected:

```text
database model changes
migration files
auth architecture changes
progression service redesign
```

If repository helper organization requires a very small adjacent test/helper edit, document it.

---

# 41. Expected Frontend Files / Components Changed

Expected approximately:

```text
frontend/src/types/api.generated.ts

frontend/src/features/admin/api.ts
frontend/src/features/admin/AdminPages.tsx   # replace/remove structural ownership as appropriate
frontend/src/features/admin/<focused Admin pages/components>
frontend/src/app/query/keys.ts
frontend/src/app/router/routes.tsx
frontend/src/app/router/routes.test.tsx
frontend/src/app/layouts/AdminLayout.tsx
frontend/src/index.css
frontend/src/test/api-boundary.test.ts or focused boundary tests where appropriate
frontend/src/features/admin/<focused tests>

docs/frontend/step-4.7-admin-core-ui.md
```

Do not manually edit generated TypeScript.

No package manifest/lockfile change is expected.

---

# 42. Testing Requirements

Tests must focus on rendered behavior/contracts rather than snapshots.

## 42.1 D-046 backend/OpenAPI

Required:

```text
GET Admin Lesson detail success/not-found
GET Admin Assessment detail success/not-found
typed Admin enum schemas
typed Admin Stats HSK bucket
Admin authorization preserved
```

## 42.2 Admin route/navigation

Required:

```text
/admin/curriculum resolves
Curriculum navigation exists
/admin remains Dashboard
/admin/documents stays structural
LEARNER → D-041 Forbidden
ADMIN → Admin content
```

## 42.3 HSK

Required:

```text
load HSKs
level_number read-only
edit title/description exact PATCH
pending duplicate-submit disabled
success invalidation/refetch
error mapping
```

## 42.4 Curriculum

Required:

```text
select HSK
load canonical order
Move Up
Move Down
draft becomes 1..N
Save confirmation
exact full-replacement payload
successful authoritative refetch
failure preserves usable draft
no drag/drop
no membership builder
```

## 42.5 Lessons

Required:

```text
paginated list
direct canonical GET detail/deep-link
create exact payload
metadata update exact payload
hsk_level_id/lesson_number immutable

DRAFT:
metadata editable
content attach/update/detach
Publish

PUBLISHED:
metadata editable
content attach/update
detach unavailable
Archive

ARCHIVED:
metadata/content immutable
no lifecycle action

INVALID_LIFECYCLE_TRANSITION
LESSON_IMMUTABLE
LESSON_CONTENT_IMMUTABLE
```

## 42.6 Vocabulary

Required:

```text
list
create-new-and-attach exact payload
canonical vs association fields
update
DRAFT detach
PUBLISHED detach unavailable
confirmation
ITEM_HAS_LEARNER_HISTORY
no raw UUID normal form
```

## 42.7 Grammar

Same boundaries as Vocabulary.

## 42.8 Assessments

Required:

```text
paginated list
direct canonical GET detail/deep-link

create LESSON_EXERCISE:
human-readable lesson selector
exact lesson_id payload

create PERIODIC_TEST:
no scope arrays

metadata PATCH:
exact visible fields only
deferred scope fields omitted

DRAFT/REVIEW editable
PUBLISHED/ARCHIVED immutable
```

## 42.9 Questions

Cover **every** supported type:

```text
multiple_choice
fill_blank
matching
reorder_sentence
translate_vi_zh
translate_zh_vi
sentence_writing
```

Required:

```text
create
update
delete
exact payloads
immutable type
type-specific UI
matching IDs preserved across edit
reorder correct_order follows row order
delete confirmation
QUESTION_HAS_HISTORY
QUESTIONS_IMMUTABLE
INVALID_QUESTION
no raw JSON editor
```

## 42.10 Assessment lifecycle

Required:

```text
DRAFT → Submit Review → REVIEW
REVIEW → Publish → PUBLISHED
PUBLISHED → Archive → ARCHIVED
no other lifecycle buttons
ASSESSMENT_HAS_NO_QUESTIONS
INVALID_LIFECYCLE_TRANSITION
authoritative refetch
```

## 42.11 Stats

Required:

```text
Total Users = exact backend response
HSK distribution = exact backend response
Average Exercise Score = exact backend response
null average neutral state
empty HSK distribution
no frontend aggregation
no chart dependency
```

## 42.12 Query/cache behavior

Required:

```text
Admin Query keys feature-scoped
bounded Admin invalidation
bounded learner invalidation
no queryClient.clear() for normal Admin mutations
all mutations retry=false
duplicate action prevention
LESSON_EXERCISE Publish/Archive invalidates learner lesson detail
PERIODIC_TEST lifecycle uses bounded HSK-root invalidation
```

## 42.13 Error/Auth regression

Required:

```text
ADMIN_REQUIRED does not logout
D-039 still passes
D-040 still passes
D-041 still passes
Step-4.6 Auth/Profile still passes
learner routes still pass
Chat tests still pass
```

## 42.14 Scope/boundary scan

Prove no:

```text
AI generation UI
Document functionality
Phase-5 ingestion
new dependency
raw UUID scope fields
PERIODIC_TEST scope editor
drag/drop
chart library
form library
global Admin store
```

---

# 43. Step Note

Create/update:

```text
docs/frontend/step-4.7-admin-core-ui.md
```

Keep it concise and reusable.

Required sections:

```text
Objective
Why
Mental Model
Data Flow
Core Knowledge

Backend/OpenAPI contract hardening
Admin CRUD vs lifecycle actions
Server state vs form/edit state
Curriculum full-replacement ordering
Lesson lifecycle and content mutability
Vocabulary/Grammar canonical vs Lesson association data
Assessment lifecycle
Question type-specific editing
Backend-authoritative errors
Query invalidation / learner-cache coherence
Authorization
Admin Stats as backend aggregates

Key Design Decisions
How to approach similar Admin systems
Common Mistakes
Definition of Done
Concepts actually used
Tools actually used
```

Do not turn it into a React/TanStack syntax tutorial.

---

# 44. Concepts Actually Expected

Only record concepts actually implemented.

Expected `SYSTEM` concepts:

```text
Admin CRUD
Backend-authoritative lifecycle
Server state
Form/edit state
Query invalidation
Cross-feature cache coherence
Authorization
Lifecycle transition
Canonical resource read
OpenAPI contract authority
Full-replacement ordering
Aggregate metric
```

`Aggregate metric` is `SYSTEM` in this Step because the frontend only consumes backend-calculated statistics; no DE analytics pipeline is implemented.

No new AI concept is implemented.

No core Data Engineering pipeline concept is implemented.

---

# 45. Tools Actually Expected

Expected `SYSTEM` tools:

```text
FastAPI
Pydantic
openapi-typescript
React
TypeScript
React Router
TanStack Query
apiClient / ApiError
Vitest
React Testing Library
```

PostgreSQL is part of the existing backend persistence, but do not add it merely to the Step tool list unless the Step Note records the D-046/backend behavior actually exercised.

No new runtime dependency should be added.

---

# 46. Definition of Done

Step 4.7 is complete only when:

- D-046 backend contract hardening is implemented;
- D-046 backend tests pass;
- generated OpenAPI TypeScript is regenerated from FastAPI;
- `api:check` passes;
- canonical Admin Lesson/Assessment detail reads exist;
- Admin stable response typing is hardened;
- `/admin/curriculum` exists;
- HSK metadata editing works;
- curriculum reorder/save works;
- Lesson list/create/editor/lifecycle works;
- Vocabulary/Grammar create/edit/detach rules work;
- Assessment list/create/editor works;
- D-048 scope remains untouched/preserved;
- every Question type has supported create/edit behavior;
- Assessment lifecycle actions follow backend legal transitions;
- Stats display all three backend aggregates;
- bounded Admin/learner invalidation is implemented;
- Admin authorization behavior is preserved;
- no out-of-scope dependency/feature was introduced;
- frontend full suite/build/lint pass;
- backend full suite passes;
- Step Note reflects actual implementation;
- Codex completion handoff is produced.

---

# 47. Verification Commands

## Backend

From `backend/`:

```text
uv sync
uv run pytest
```

Also run focused new Step-4.7 backend tests directly during implementation.

No DB migration command is expected because D-046 must not add a migration.

## OpenAPI contract sync

Run the accepted backend locally using the repository-locked runner:

```text
cd backend
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then from `frontend/`:

```text
npm run api:generate
npm run api:check
```

Do not commit `openapi.json`.

## Frontend

From `frontend/`:

```text
node --version
npm --version
npm ci
npm run build
npm run test -- --run
npm run lint
```

Expected:

```text
npm ci PASS
build PASS
full frontend tests PASS
focused Step-4.7 tests PASS
lint PASS except unchanged pre-existing warning if it still exists
```

A Vite chunk-size warning alone is not a reason to expand Step 4.7 into code-splitting unless it becomes a real build/runtime failure.

---

# 48. Stop Conditions

Stop and report `BLOCKED` with exact evidence if:

- D-046 detail GET requires a DB/business redesign rather than a narrow read;
- actual PERIODIC_TEST PATCH semantics would erase deferred scope when scope fields are omitted;
- correct Lesson/Assessment editor requires scanning unbounded collection pages;
- correct type-specific Question editing requires a new public contract not approved by D-046;
- a new runtime dependency becomes necessary;
- a new route beyond D-047 becomes materially required;
- Admin content/lifecycle semantics contradict the frozen PM packet;
- correct implementation requires Phase-5 Documents functionality;
- correct implementation requires AI generation/RAG;
- OpenAPI regeneration reveals a material unrelated contract drift;
- a new lifecycle/security/product convention is required.

Do not silently work around these conditions.

---

# 49. Codex Completion Report

Return a focused completion report with:

```text
Step
Status

What was implemented

D-046:
- backend files changed
- new GET detail endpoints
- schema/OpenAPI typing changes
- backend tests

OpenAPI:
- api.generated.ts regenerated?
- api:check result
- unexpected generated drift?

Admin frontend:
- routes/navigation
- HSK/Curriculum
- Lessons
- Vocabulary/Grammar
- Assessments
- Question types
- lifecycle actions
- Stats
- Query keys/invalidation

D-048:
- confirm no PERIODIC_TEST scope UI
- confirm PATCH metadata omits scope arrays

Dependencies added/removed
Backend changed?
DB migration changed?
Generated API changed?

Security/Auth:
- D-041 preserved?
- ADMIN_REQUIRED logout behavior?

Verification:
- backend full test count/result
- frontend full test count/result
- focused Step-4.7 test count/result
- build
- lint
- api:check

Step Note

Deviations
Problems/risks
Decisions needed
Recommended next action
```

Package a **focused Step-4.7 handoff ZIP** containing all files changed by this Step for independent App Engineering Specialist review.

Do **not** claim PM acceptance.

Do **not** begin Phase 5, Phase 6, or another project Step.
