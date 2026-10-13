# Step 3.4 — Business APIs

## Goal

Implement the core REST business API layer for the Chinese-learning application.

This step covers:

- curriculum;
- dashboard;
- pronunciation;
- lessons;
- theory viewing;
- assessments;
- attempts;
- grading contract;
- progress;
- learner history;
- Admin lesson/content/assessment workflows.

Authentication and Conversation APIs are handled in later Backend Foundation steps.

---

# General API Rules

Use:

```text
/api/v1
```

as the business API prefix.

Learner-specific endpoints must rely on authenticated user context once Step 3.5 is implemented.

Do not design learner mutation endpoints that accept arbitrary `user_id` values from the client.

Use `/me/...` for user-specific resources where appropriate.

---

# HTTP Errors

Use the approved error shape:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description",
    "details": null
  }
}
```

Use machine-readable business error codes.

Initial codes should support cases such as:

```text
LESSON_LOCKED
PRONUNCIATION_NOT_COMPLETED
ASSESSMENT_LOCKED
ATTEMPT_ALREADY_SUBMITTED
INVALID_CURRICULUM_TRANSITION
CONTENT_ARCHIVED
```

Do not require frontend code to parse human-readable error strings.

---

# Curriculum APIs

Implement:

```http
GET /api/v1/hsk-levels
```

and:

```http
GET /api/v1/hsk-levels/{hsk_id}/curriculum
```

Curriculum ordering must come from:

```text
curriculum_units.order_index
```

Each curriculum unit returned to a learner should expose an appropriate derived state:

```text
LOCKED
AVAILABLE
COMPLETED
```

Backend is authoritative for curriculum access state.

---

# Dashboard API

Implement:

```http
GET /api/v1/me/dashboard
```

The endpoint should provide the data required to render:

- current HSK;
- current curriculum unit;
- current lesson when applicable;
- progress percentage;
- Continue Learning target.

Prefer server-side aggregation rather than requiring the frontend to reconstruct learning state through many unrelated requests.

---

# Lesson API

Implement:

```http
GET /api/v1/lessons/{lesson_id}
```

Before returning learning content:

```text
validate learner access
```

If locked:

```text
HTTP 403
error.code = LESSON_LOCKED
```

Do not rely on frontend navigation restrictions for enforcement.

Lesson response may include:

- lesson metadata;
- vocabulary;
- grammar;
- theory progress;
- related lesson assessments.

Never expose internal fields unrelated to learner use.

---

# Theory Progress APIs

Implement idempotent vocabulary viewing:

```http
POST /api/v1/lessons/{lesson_id}/theory/vocabulary/{lesson_vocabulary_id}/view
```

Implement idempotent grammar viewing:

```http
POST /api/v1/lessons/{lesson_id}/theory/grammar/{lesson_grammar_id}/view
```

Repeated requests must not create duplicate progress records.

Do not expose a generic client-controlled `mark theory complete` endpoint.

Backend must derive theory completion:

```text
all required lesson vocabulary viewed
AND
all required lesson grammar viewed
→ theory_completed_at
```

---

# Pronunciation APIs

Implement:

```http
GET /api/v1/pronunciation
```

and:

```http
POST /api/v1/pronunciation/{section_id}/complete
```

Pronunciation sections are:

```text
TONES
INITIALS
FINALS
```

Completion of all required sections enables progression into the first HSK1 curriculum unit.

There is no pronunciation quiz in MVP.

The completion endpoint must be safe when repeated.

---

# Assessment Retrieval

Implement:

```http
GET /api/v1/assessments/{assessment_id}
```

Learner response may expose:

- assessment title/type;
- question prompts;
- valid options;
- points;
- required learner-facing configuration.

Before submission, never expose:

```text
correct option flags
reference answers
rubrics
answer keys
```

Validate that the assessment is available to the learner.

---

# Start Assessment Attempt

Implement:

```http
POST /api/v1/assessments/{assessment_id}/attempts
```

The operation creates or returns:

```text
AssessmentAttempt
status = IN_PROGRESS
```

Each learner may have at most one active IN_PROGRESS attempt for one Assessment.

If an active attempt already exists:

```text
return/resume existing attempt
```

Do not create another active attempt.

After an attempt has been submitted, a retry creates the next attempt number.

---

# Submit Attempt

Implement:

```http
POST /api/v1/assessment-attempts/{attempt_id}/submit
```

Logical request:

```text
answers:
- question_id
- answer
```

Validate:

- attempt belongs to current learner;
- attempt is IN_PROGRESS;
- Assessment remains valid/accessible;
- submitted question IDs belong to that Assessment;
- answer payload matches supported question type requirements.

Do not permit submitting one completed attempt twice.

---

# Grading Architecture

Provide a grading boundary with at least:

```text
DeterministicGrader
AIGrader interface
```

Deterministically gradable questions must use deterministic logic.

Do not connect a real LLM provider in this step.

An AIGrader stub/fake implementation may be used for tests so business flows involving free-form answers can be verified deterministically.

The real AI grading implementation belongs to Phase 6.

---

# Score Calculation

Calculate percentage using only gradable questions:

```text
earned points
/
maximum gradable points
× 100
```

If:

```text
grading_status = UNCERTAIN
```

exclude that question from both numerator and denominator.

Do not mark uncertain AI grading as incorrect.

---

# Submission Transaction Flow

Avoid holding a database transaction open while waiting for external AI work.

Preferred structure:

```text
1. Read and validate attempt/question state.
2. Complete necessary database reads.
3. Perform grading.
4. Start short transaction.
5. Persist AttemptAnswer results.
6. Finalize AssessmentAttempt.
7. Update learner Progress.
8. Apply curriculum unlock.
9. Commit.
```

If the persistence/progress transaction fails:

```text
ROLLBACK
```

Do not leave attempt/progress state partially updated.

---

# Progress Rules

After grading, invoke ProgressService.

Lesson completion:

```text
theory completed
AND
assessment score >= assessment.pass_threshold
→ lesson complete
```

Periodic test completion:

```text
score >= assessment.pass_threshold
→ periodic test complete
```

Completed required curriculum unit:

```text
→ unlock next curriculum unit
```

Progress mutations must only happen through valid business operations.

Do not implement a generic learner-controlled progress update endpoint.

---

# Assessment History

Implement:

```http
GET /api/v1/me/assessment-attempts
```

Support appropriate pagination and optional whitelisted filters such as:

```text
assessment_id
lesson_id
assessment_type
```

Implement:

```http
GET /api/v1/me/assessment-attempts/{attempt_id}
```

Detail response should provide:

- attempt metadata;
- score;
- passed status;
- start/submission time;
- individual answers;
- grading result;
- correct/incorrect/uncertain state;
- learner feedback.

A learner must not be able to access another learner's attempt.

---

# Progress Read APIs

Implement:

```http
GET /api/v1/me/progress
GET /api/v1/me/progress/hsk/{hsk_id}
GET /api/v1/me/progress/lessons/{lesson_id}
```

Do not implement:

```http
PUT /api/v1/me/progress
```

as a generic progress mutation mechanism.

---

# Admin API Namespace

Use:

```text
/api/v1/admin
```

for Admin-only business operations.

Actual authentication/authorization enforcement is completed in Step 3.5, but service/router boundaries should already allow role protection to be applied cleanly.

---


# Admin HSK / Curriculum APIs

Support Admin operations equivalent to:

```http
GET   /api/v1/admin/hsk-levels
PATCH /api/v1/admin/hsk-levels/{hsk_id}
GET   /api/v1/admin/hsk-levels/{hsk_id}/curriculum
PUT   /api/v1/admin/hsk-levels/{hsk_id}/curriculum
```

The curriculum write operation manages ordered `CurriculumUnit` membership/order as one use case. Do not expose raw junction-table CRUD to the frontend.

V0 HSK 1–3 seed identity remains controlled by migrations/seeds; do not invent arbitrary new HSK levels unless product scope is changed.

---

# Admin Lesson APIs

Support operations equivalent to:

```http
GET   /api/v1/admin/lessons
POST  /api/v1/admin/lessons
PATCH /api/v1/admin/lessons/{lesson_id}

POST /api/v1/admin/lessons/{lesson_id}/publish
POST /api/v1/admin/lessons/{lesson_id}/archive
```

Do not hard-delete published learning content with historical learner data.

---

# Vocabulary and Grammar Admin APIs

Design APIs around product use cases rather than exposing junction tables directly.

Support operations equivalent to:

```http
GET    /api/v1/admin/lessons/{lesson_id}/vocabulary
POST   /api/v1/admin/lessons/{lesson_id}/vocabulary
PATCH  /api/v1/admin/lessons/{lesson_id}/vocabulary/{lesson_vocabulary_id}
DELETE /api/v1/admin/lessons/{lesson_id}/vocabulary/{lesson_vocabulary_id}

GET    /api/v1/admin/lessons/{lesson_id}/grammar
POST   /api/v1/admin/lessons/{lesson_id}/grammar
PATCH  /api/v1/admin/lessons/{lesson_id}/grammar/{lesson_grammar_id}
DELETE /api/v1/admin/lessons/{lesson_id}/grammar/{lesson_grammar_id}
```

Delete here means detach/remove draft lesson content when safe. Published/historical content must follow archival/history-preservation rules rather than hard-delete data needed by attempts/progress.

The frontend should not need knowledge of the persistence junction structure merely to manage lesson content.

---

# Admin Assessment APIs

Support:

```http
GET   /api/v1/admin/assessments
POST  /api/v1/admin/assessments
PATCH /api/v1/admin/assessments/{assessment_id}

GET    /api/v1/admin/assessments/{assessment_id}/questions
POST   /api/v1/admin/assessments/{assessment_id}/questions
PATCH  /api/v1/admin/assessments/{assessment_id}/questions/{question_id}
DELETE /api/v1/admin/assessments/{assessment_id}/questions/{question_id}

POST /api/v1/admin/assessments/{assessment_id}/submit-review
POST /api/v1/admin/assessments/{assessment_id}/publish
POST /api/v1/admin/assessments/{assessment_id}/archive
```

Question mutation is allowed only in lifecycle states where editing is legal. Preserve historical learner attempt data. Do not implement actual LLM generation yet; Step 6.12 will create drafts through these same domain boundaries.

---

# Admin Statistics API

Implement one Admin-only read endpoint equivalent to:

```http
GET /api/v1/admin/stats
```

Return at least:

```text
total_users
users_by_current_hsk[]
average_exercise_score
```

`users_by_current_hsk` must distinguish learners by their current HSK level using the same progression semantics as learner progress; do not derive an unrelated approximation in the router.

`average_exercise_score` is the aggregate over completed lesson-exercise attempts according to the canonical attempt scoring model. Define null/empty behavior explicitly (for example `null` when no completed exercise attempts exist) and test it.

Do not add a warehouse/BI stack for these MVP statistics.

---

# Lifecycle Enforcement

Do not let clients bypass lifecycle rules through arbitrary status assignment.

Prefer explicit actions:

```text
submit-review
publish
archive
```

Assessment transitions:

```text
DRAFT
→ REVIEW
→ PUBLISHED
→ ARCHIVED
```

Lesson transitions:

```text
DRAFT
→ PUBLISHED
→ ARCHIVED
```

Service layer must validate legal transitions.

---

# Pagination

Collection APIs that may grow should support:

```text
page
page_size
```

Default example:

```text
page = 1
page_size = 20
```

Cap:

```text
page_size <= 100
```

Cursor pagination is not required for MVP.

---

# Filtering and Sorting

Expose only explicitly supported filters/sorts.

Do not dynamically map arbitrary client-provided strings to database columns or SQL expressions.

Repository queries should remain controlled by application code.

---

# HTTP Status Convention

Use standard semantics:

```text
200 → normal success
201 → resource created
204 → successful no-content action where appropriate

400/422 → invalid input
401 → unauthenticated
403 → forbidden
404 → resource not found
409 → business-state conflict
```

Do not expose internal exception messages or stack traces to clients.

---

# API Model Principle

Do not mirror database tables one-to-one merely because they exist.

Use:

```text
API Contract
→ product/use-case model
```

while:

```text
Database Schema
→ persistence model
```

The Service/Repository layers bridge the two.

---

# Deferred Features

Do not implement in this step:

- login/register;
- password reset;
- authenticated user resolution;
- JWT/session token mechanics;
- full role enforcement;
- Conversation APIs;
- LLM provider;
- real AI grading;
- RAG;
- AI content generation;
- document upload;
- ingestion processing;
- admin document approval;
- external retrieval.

---

# Tests

Add service/API tests covering at least:

- curriculum ordering;
- locked lesson rejection;
- theory-view idempotency;
- derived theory completion;
- pronunciation completion;
- attempt creation/resume;
- duplicate submit rejection;
- deterministic grading;
- uncertain-question score exclusion;
- lesson completion rule;
- periodic-test completion rule;
- next-unit unlock;
- attempt-history ownership;
- illegal Admin lifecycle transition;
- archived-content behavior.

Use dedicated test database infrastructure from previous steps.

Use fake/stub AI grading where needed.

---

# Acceptance Criteria

- [ ] HSK/curriculum APIs expose server-derived learner states.
- [ ] Dashboard data can be retrieved through one aggregate endpoint.
- [ ] Locked lesson content is enforced server-side.
- [ ] Theory viewing operations are idempotent.
- [ ] Theory completion cannot be directly set by learner.
- [ ] Pronunciation completion drives initial HSK unlock.
- [ ] Assessment answers never expose answer keys before submission.
- [ ] Assessment attempt lifecycle supports resume and unlimited retries.
- [ ] Submitted attempts cannot be submitted twice.
- [ ] Deterministic and AI grading have separate interfaces.
- [ ] Real LLM integration is not introduced yet.
- [ ] Uncertain grading does not penalize the learner.
- [ ] Assessment result can atomically update progress/unlock state.
- [ ] Learners can inspect their own history/progress.
- [ ] Generic client-side progress mutation is impossible.
- [ ] Admin APIs are use-case-oriented.
- [ ] Lifecycle transitions are service-controlled.
- [ ] Pagination is bounded.
- [ ] Filtering/sorting are whitelisted.
- [ ] Business errors have stable machine-readable codes.

- [ ] Admin HSK/curriculum ordering can be read and updated through use-case-oriented APIs.
- [ ] Admin vocabulary and grammar CRUD/detach flows are explicit.
- [ ] Admin assessment question CRUD is explicit and lifecycle-aware.
- [ ] Admin stats returns Total Users, Users by Current HSK, and Average Exercise Score.

# Expected Deliverable

Business API foundation plus:

```text
docs/backend/
└── step-3.4-business-apis.md
```

Next Step:

**Step 3.5 — Authentication & User Context**