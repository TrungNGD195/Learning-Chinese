# Codex Execution Task — Step 3.4: Business APIs

## Status / Execution Gate

This is the **single current Codex execution task** for:

**Step 3.4 — Business APIs**

Owner: **App Engineering Specialist**

Do not implement Step 3.5 or any later Step.

Before editing, inspect the actual repository. If the repository materially differs from the accepted Step 3.1–3.3 state described below, or if the current PM Decision Log conflicts with this task, stop and report `BLOCKED` rather than redesigning the system.

Do not run this task against a non-test database.

---

## Objective

Implement the core REST business API layer for the Chinese-learning application on top of the accepted Step 3.3 PostgreSQL persistence foundation.

Step 3.4 must provide the learner and Admin business flows for:

- HSK/curriculum;
- dashboard;
- pronunciation;
- lesson/theory;
- assessments and attempts;
- deterministic grading plus the `AIGrader` application boundary;
- progress/unlock;
- learner assessment history;
- Admin curriculum/content/assessment lifecycle;
- Admin MVP statistics.

The backend remains authoritative for:

- access;
- grading;
- completion;
- progression/unlock;
- lifecycle transitions;
- ownership.

Do **not** implement real authentication or real AI infrastructure in this Step.

---

# 1. Source of Truth

## Primary

- `Spec-CURRENT/Phase3/Step 3.4 — Business APIs.md`

## Required dependencies

Read these before editing:

- `Spec-CURRENT/PROJECT_CONTEXT.md`
- approved Phase 2 data-model/schema specifications relevant to application data
- accepted Step 3.3 implementation/repository state
- `Spec-CURRENT/PM-Control/04-Decision-Log-and-Open-Gates.md`
- `Spec-CURRENT/PM-Control/05-Codex-Execution-Protocol.md`

Relevant architecture references:

- Phase 1 component responsibilities
- Phase 1 data-flow / module-boundary specifications
- accepted Step 3.1 modular-monolith boundary
- accepted Step 3.2 Settings contract
- accepted Step 3.3 session/transaction foundation

## Precedence

Use this precedence if documents differ:

1. PM Decision Log.
2. Current authoritative Step 3.4 specification.
3. A later specification that intentionally refines an earlier contract.
4. Earlier Phase specifications.
5. Notes/examples/plans.

Do not silently invent a resolution to a real conflict.

---

# 2. PM Decisions That Are Mandatory for This Step

## D-008 — Temporary Current-User Boundary

Step 3.4 must preserve learner APIs based on current-user context, including `/me/...`.

Rules:

- learner APIs must **not** accept arbitrary client-controlled `user_id`;
- use an internal injectable current-user dependency/boundary;
- tests may override the dependency with an actual persisted learner;
- runtime must not hard-code or fabricate a learner identity;
- services receive a resolved learner identity/context from the application boundary and remain independent of how authentication works;
- do not implement login, registration, JWT validation, cookies, passwords, refresh tokens, real authenticated-user resolution, or real Admin authorization;
- Step 3.5 will replace the temporary boundary with real `get_current_user()` and later add `require_admin()`.

## D-009 — Canonical V0 Question Payload and Grading Contract

Preserve the existing relational schema.

Use:

- `questions.config JSONB`;
- `questions.reference_answer`;
- `question_options`;
- `attempt_answers.user_answer JSONB`.

### multiple_choice

Learner answer:

```json
{
  "option_id": "<question_option_uuid>"
}
```

Requirements:

- the option must belong to that Question;
- grade using `QuestionOption.is_correct`;
- do not duplicate the answer key in `questions.config`.

### fill_blank

Learner answer:

```json
{
  "text": "<learner answer>"
}
```

Canonical answer:

- `Question.reference_answer`.

Optional alternatives:

```json
{
  "accepted_answers": [
    "<alternative answer>"
  ]
}
```

V0 comparison:

```text
trim leading/trailing whitespace
→ exact comparison
```

Do not add fuzzy/semantic/LLM matching.

### matching

Question config:

```json
{
  "left_items": [
    {"id": "<opaque item id>", "text": "<display text>"}
  ],
  "right_items": [
    {"id": "<opaque item id>", "text": "<display text>"}
  ],
  "correct_pairs": [
    {"left_id": "<left item id>", "right_id": "<right item id>"}
  ]
}
```

Learner answer:

```json
{
  "pairs": [
    {"left_id": "<left item id>", "right_id": "<right item id>"}
  ]
}
```

Rules:

- submitted IDs must belong to that Question;
- grading is exact pair-set equality;
- `correct_pairs` is answer-key material and must not appear in learner assessment retrieval before submission.

### reorder_sentence

Question config:

```json
{
  "items": [
    {"id": "<opaque item id>", "text": "<display text>"}
  ],
  "correct_order": [
    "<item id>"
  ]
}
```

Learner answer:

```json
{
  "item_ids": [
    "<item id>"
  ]
}
```

Rules:

- submitted IDs must form a valid ordering of the configured items;
- grading is exact sequence equality;
- `correct_order` must not appear before submission.

### Free-form

These types use `AIGrader`:

```text
translate_vi_zh
translate_zh_vi
sentence_writing
```

Learner answer:

```json
{
  "text": "<learner answer>"
}
```

A real LLM grader is forbidden in Step 3.4.

### Deterministic scoring

All deterministic question types use all-or-nothing scoring:

```text
correct   → full Question.points
incorrect → 0
```

No partial-credit rules in Step 3.4.

Before submission, learner assessment payloads must not expose:

- `QuestionOption.is_correct`;
- `reference_answer`;
- `rubric`;
- `accepted_answers`;
- `correct_pairs`;
- `correct_order`;
- any equivalent answer-key data.

## D-010 — AI Grading Unavailable / GRADING_FAILED

Step 3.4 defines the `AIGrader` application interface.

Tests may inject a deterministic `FakeAIGrader`.

Normal runtime must **not** return a fake grade.

When a submission contains a free-form question and no real AI grader exists:

- the default/unavailable grader raises a typed technical grading failure;
- this is not `UNCERTAIN`;
- persist the attempt as:

```text
status       = GRADING_FAILED
submitted_at = current UTC time
score        = null
passed       = null
```

Preserve submitted learner answers.

Deterministically graded answers that were successfully evaluated may remain:

```text
grading_status = GRADED
score           = calculated points
is_correct      = true/false
```

Affected free-form answer:

```text
grading_status = FAILED
score          = null
is_correct     = null
```

No learner-progress, lesson-completion, periodic-test-completion, or unlock mutation may occur for a `GRADING_FAILED` attempt.

Persist the failure in a short transaction. A separately committed intermediate `SUBMITTED` state is not required.

After the failure state is committed, return:

```http
HTTP 503
```

```json
{
  "error": {
    "code": "AI_GRADING_UNAVAILABLE",
    "message": "AI grading is not available",
    "details": null
  }
}
```

A later retry creates the next attempt number and does not rewrite the failed historical attempt.

`UNCERTAIN` is reserved for semantic abstention from a functioning grader.

## D-011 — Temporary Missing-Identity Behavior

For learner endpoints requiring the temporary current-user boundary:

```text
no resolved identity
→ HTTP 401
→ AUTHENTICATION_REQUIRED
```

Response:

```json
{
  "error": {
    "code": "AUTHENTICATION_REQUIRED",
    "message": "Authentication is required",
    "details": null
  }
}
```

Do not:

- fabricate a learner;
- hard-code a learner UUID;
- accept learner `user_id` from request body/query/path for `/me` or learner mutations;
- throw an unhandled `NotImplementedError`/500.

This does not add Admin authentication in Step 3.4.

---

# 3. Accepted Current Repository State

Steps 3.1, 3.2 and 3.3 are accepted and closed.

Relevant current structure:

```text
backend/
├── pyproject.toml
├── uv.lock
├── alembic.ini
├── migrations/
│   ├── env.py
│   └── versions/
│       └── 0001_initial_schema.py
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   └── errors.py
│   ├── database/
│   │   ├── base.py
│   │   ├── engine.py
│   │   ├── session.py
│   │   ├── readiness.py
│   │   ├── models/
│   │   └── seeds/
│   ├── auth/__init__.py
│   ├── curriculum/__init__.py
│   ├── exercise/__init__.py
│   ├── progress/__init__.py
│   ├── admin/__init__.py
│   ├── ai/grading/__init__.py
│   └── ...
└── tests/
```

Important accepted behavior:

- Python `>=3.12,<3.13`;
- FastAPI;
- `uv`;
- PostgreSQL;
- async SQLAlchemy + psycopg 3;
- Alembic;
- request-scoped `AsyncSession`;
- generic DB/session infrastructure does **not** auto-commit;
- application/service layer owns transactions;
- `/health` does not query DB;
- `/ready` only performs lightweight DB readiness;
- Phase 2 ORM/schema is already materialized;
- test database isolation is already enforced;
- no business routers/services/repositories exist yet.

Step 3.4 should use the accepted physical schema rather than changing it.

---

# 4. Architecture Boundary

Preserve:

```text
Router
→ Service
→ Repository
→ AsyncSession / ORM
```

Responsibilities:

### Router
- HTTP input/output;
- dependency injection;
- request validation;
- status code;
- service calls;
- no grading/progression/lifecycle rules.

### Service
Owns:
- access checks;
- ownership;
- progression;
- grading orchestration;
- lifecycle transitions;
- transactions;
- stable business errors.

### Repository
Owns:
- controlled SELECT/INSERT/UPDATE/DELETE;
- FLUSH when needed;
- no `commit()`.

Do not create one generic repository for all domains.

Domain ownership:

- `curriculum`: HSK, lesson, curriculum order, vocabulary, grammar;
- `exercise`: assessments, questions, attempts, grading;
- `progress`: pronunciation, theory completion, lesson/HSK completion, unlock/access;
- `admin`: Admin HTTP/use-case orchestration and statistics;
- `auth`: only the temporary current-user seam.

Avoid circular service imports.

---

# 5. Files / Components

Inspect first; reconcile instead of duplicating.

Expected creations:

```text
backend/app/auth/current_user.py

backend/app/curriculum/
├── router.py
├── schemas.py
├── service.py
└── repository.py

backend/app/exercise/
├── router.py
├── schemas.py
├── service.py
├── repository.py
└── grading.py

backend/app/progress/
├── router.py
├── schemas.py
├── service.py
└── repository.py

backend/app/admin/
├── router.py
├── schemas.py
├── service.py
└── repository.py   # only if Admin-specific aggregate queries justify it
```

Expected modifications:

```text
backend/app/main.py
backend/tests/conftest.py
```

Add focused Step 3.4 test files.

Create:

```text
docs/backend/step-3.4-business-apis.md
```

Do **not** create a new Alembic revision unless an unavoidable accepted-schema defect is discovered. If a schema change appears necessary, stop and report `BLOCKED`; do not change Phase 2 persistence semantics autonomously.

No new runtime library is expected.

---

# 6. Temporary Current-User Seam

Implement a small injectable FastAPI dependency under `auth`.

Default Step-3.4 runtime has no authenticator, so the dependency returns the exact D-011 normalized 401.

Tests override the dependency with an **actual persisted LEARNER**.

Services receive a resolved learner identifier/context; they do not know about JWT/cookies/passwords.

Do not add fake runtime identities.

Do not implement real Admin protection. Keep Admin router/service signatures ready for Step 3.5 `require_admin()`.

---

# 7. Router Registration

Register business routers using:

```text
settings.api_v1_prefix
```

Default:

```text
/api/v1
```

Do not create a second conflicting hard-coded API root.

---

# 8. Learner Curriculum APIs

Implement:

```http
GET /api/v1/hsk-levels
GET /api/v1/hsk-levels/{hsk_id}/curriculum
```

Ordering comes from:

```text
curriculum_units.order_index
```

Expose derived state:

```text
LOCKED
AVAILABLE
COMPLETED
```

Rules:

- pronunciation gates first HSK1 curriculum access;
- progression is sequential;
- later HSK requires all required units of previous HSK complete;
- completion is not erased by reordering;
- do not persist a client-controlled unlock flag;
- do not expose unrestricted ORM objects.

---

# 9. Dashboard

Implement:

```http
GET /api/v1/me/dashboard
```

Return server-derived data for:

- current HSK;
- current curriculum unit;
- current lesson if applicable;
- progress percentage;
- Continue Learning target.

Progress:

```text
completed required units
/
total required units
* 100
```

Do not persist percentage.

If required-unit count is zero, use deterministic `0` rather than divide by zero.

Before pronunciation completion, Continue Learning points to the next incomplete pronunciation section; do not pretend Lesson 1 is available.

Do not invent HSK 4+.

---

# 10. Lesson / Theory

Implement:

```http
GET /api/v1/lessons/{lesson_id}

POST /api/v1/lessons/{lesson_id}/theory/vocabulary/{lesson_vocabulary_id}/view
POST /api/v1/lessons/{lesson_id}/theory/grammar/{lesson_grammar_id}/view
```

Locked lesson:

```text
HTTP 403
LESSON_LOCKED
```

Requirements:

- backend validates access;
- learner APIs do not expose draft/unpublished content;
- theory view validates junction ownership;
- theory-view operations are idempotent;
- repeated calls do not create duplicate progress;
- no generic `mark theory complete` endpoint.

Derive:

```text
all required LessonVocabulary viewed
AND
all required LessonGrammar viewed
→ theory_completed_at
```

Once theory completion is persisted, do not clear it later.

Archived content must not re-enter active progression. Historical progress/attempt data remains preserved/queryable.

---

# 11. Pronunciation

Implement:

```http
GET /api/v1/pronunciation
POST /api/v1/pronunciation/{section_id}/complete
```

Return seeded sections in `order_index` order.

Completion is idempotent.

All required sections complete:

```text
first HSK1 curriculum unit
→ may become AVAILABLE
```

No quiz, STT, TTS, audio or pronunciation scoring.

---

# 12. Assessment Retrieval

Implement:

```http
GET /api/v1/assessments/{assessment_id}
```

Validate learner availability.

Before submission strip answer-key material:

- MCQ: no `is_correct`;
- fill blank: no `reference_answer`, `accepted_answers`;
- matching: no `correct_pairs`;
- reorder: no `correct_order`;
- free-form: no `reference_answer` or `rubric`.

Return only learner-facing configuration.

GET must not mutate persistence.

---

# 13. Start / Resume Attempt

Implement:

```http
POST /api/v1/assessments/{assessment_id}/attempts
```

Rules:

- current learner only;
- validate availability;
- at most one active `IN_PROGRESS` attempt for learner + assessment;
- resume existing active attempt;
- otherwise create `max(attempt_number) + 1`;
- terminal attempts are immutable historical data;
- `GRADING_FAILED` also counts as historical.

Make start/resume transactionally safe against duplicate concurrent starts using the existing PostgreSQL/session stack. A row lock on an existing stable parent row is acceptable. Do not add a distributed lock or new infrastructure.

New attempt may return 201; resumed existing attempt may return 200.

---

# 14. Submit Attempt

Implement:

```http
POST /api/v1/assessment-attempts/{attempt_id}/submit
```

Body:

```json
{
  "answers": [
    {
      "question_id": "<uuid>",
      "answer": {}
    }
  ]
}
```

Validate:

- ownership;
- attempt is `IN_PROGRESS`;
- assessment remains valid;
- question belongs to assessment;
- no duplicate question IDs;
- D-009 payload shape;
- option/config IDs belong to exact Question.

Treat submission as final: require one valid answer entry per Assessment Question. Do not silently omit unanswered deterministic questions from the score denominator.

Validation failure must not partially persist answers.

Duplicate terminal submit:

```text
HTTP 409
ATTEMPT_ALREADY_SUBMITTED
```

---

# 15. Grading Boundary

Provide an application-level boundary, e.g.:

```text
DeterministicGrader
AIGrader interface/protocol
UnavailableAIGrader
GradeResult
```

No LLM SDK.

Future Step 6.11 must be able to replace `AIGrader` without changing assessment persistence/public API.

A functioning grader result supports:

```text
grading_status = GRADED | UNCERTAIN
score           = points or null
is_correct      = bool or null
feedback        = learner-safe text or null
```

Technical failure is separate.

Test-only `FakeAIGrader` may return deterministic `GRADED` or `UNCERTAIN`.

---

# 16. Deterministic Grading

Implement D-009 exactly:

- MCQ by `QuestionOption.is_correct`;
- fill blank trim + exact reference/accepted answer match;
- matching exact pair-set equality;
- reorder exact sequence equality;
- all-or-nothing points;
- no fuzzy match;
- no LLM for deterministic types.

Malformed persisted question config is a data/server failure, not a learner wrong answer. Do not silently repair invalid stored answer-key config.

---

# 17. Score Calculation

Successful gradable submission:

```text
earned gradable points
/
maximum gradable points
* 100
```

`UNCERTAIN`:

- excluded from numerator;
- excluded from denominator;
- never treated as incorrect.

If all questions are excluded and denominator becomes zero:

```text
attempt.status = GRADED
score          = null
passed         = null
```

No progress completion/unlock mutation occurs for a null overall score.

Do not fabricate a numeric score for zero denominator.

---

# 18. Submission Transaction Flow

Application/service owns commit/rollback.

For success:

```text
1. Read + validate attempt/questions/answers.
2. Materialize grading inputs.
3. End/release the read transaction before any AI boundary call.
4. Grade.
5. Start one short persistence transaction.
6. Persist AttemptAnswer rows.
7. Finalize AssessmentAttempt.
8. Invoke ProgressService.
9. Persist progress/completion changes.
10. Commit.
```

Repositories do not commit.

Persistence/progress failure:

```text
ROLLBACK
```

No partial graded attempt/progress state.

For D-010 unavailable AI:

- persist `GRADING_FAILED` and submitted answers in a short transaction;
- deterministic results may remain;
- affected free-form answer = `FAILED`;
- no ProgressService mutation;
- commit historical failure;
- then return 503 `AI_GRADING_UNAVAILABLE`.

No slow external call belongs inside a long PostgreSQL transaction.

---

# 19. Progress Rules

Progress module is authoritative.

## Lesson

```text
theory completed
AND
at least one valid GRADED passing LESSON_EXERCISE attempt for the lesson
→ lesson completed
```

Use historical attempts; do not add `best_score` to progress table.

If multiple lesson-exercise Assessments exist, current schema has no required/optional marker. Do not add one in Step 3.4. One valid passing lesson-exercise attempt satisfies the exercise side of the current completion rule.

Once completed:

- later lower retry does not clear it;
- later lesson edit does not reset it.

## Periodic test

```text
GRADED
AND
score >= pass_threshold
→ periodic curriculum unit complete
```

## Sequential unlock

A unit is AVAILABLE only if all required prior units are complete and the HSK prerequisite is satisfied.

Later HSK requires prior HSK complete.

Do not persist generic unlock booleans.

## HSK progress

Use `LearnerHSKProgress` lifecycle timestamps where appropriate.

Percentage/current unit remain derived.

---

# 20. Learner History / Progress APIs

Implement:

```http
GET /api/v1/me/assessment-attempts
GET /api/v1/me/assessment-attempts/{attempt_id}

GET /api/v1/me/progress
GET /api/v1/me/progress/hsk/{hsk_id}
GET /api/v1/me/progress/lessons/{lesson_id}
```

No generic progress mutation endpoint.

Attempt ownership is mandatory.

History list:

```text
page      default 1
page_size default 20
page_size max 100
```

Whitelisted filters only:

- `assessment_id`;
- `lesson_id`;
- `assessment_type`.

Use a stable page envelope equivalent to:

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0
}
```

Attempt detail includes learner-safe post-submit result/history data and may expose the answer/reference information required for result review only after submission.

Do not expose unrestricted ORM/config internals.

---

# 21. Admin Namespace

Use:

```text
/api/v1/admin
```

No real auth/authorization yet.

Do not fabricate Admin identity.

Keep routes compatible with Step 3.5 `require_admin()`.

Do not allow arbitrary lifecycle `status` assignment through generic PATCH.

---

# 22. Admin HSK / Curriculum

Implement:

```http
GET   /api/v1/admin/hsk-levels
PATCH /api/v1/admin/hsk-levels/{hsk_id}
GET   /api/v1/admin/hsk-levels/{hsk_id}/curriculum
PUT   /api/v1/admin/hsk-levels/{hsk_id}/curriculum
```

Rules:

- HSK 1–3 seed identity only;
- no HSK 4+ creation;
- no `level_number` mutation;
- PATCH safe display metadata only;
- curriculum PUT is one transaction;
- no raw junction CRUD endpoint.

Validate:

- target exists;
- lesson target belongs to HSK;
- periodic target has `PERIODIC_TEST` type;
- no duplicates;
- deterministic unique order;
- archived targets are not added.

Reorder never deletes attempts/progress or clears completion timestamps. Derived learner state follows current authoritative `curriculum_units.order_index`.

---

# 23. Admin Lesson Lifecycle

Implement:

```http
GET   /api/v1/admin/lessons
POST  /api/v1/admin/lessons
PATCH /api/v1/admin/lessons/{lesson_id}

POST /api/v1/admin/lessons/{lesson_id}/publish
POST /api/v1/admin/lessons/{lesson_id}/archive
```

Lifecycle:

```text
DRAFT → PUBLISHED → ARCHIVED
```

Rules:

- create DRAFT;
- PATCH cannot set status;
- publish only DRAFT;
- archive only PUBLISHED;
- illegal transition → stable 409 business error;
- set `published_at` on publish;
- no hard-delete published/historical lesson;
- editing completed lesson does not reset learner completion;
- archived data remains preserved.

---

# 24. Admin Vocabulary / Grammar

Implement:

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

Preserve:

```text
Vocabulary / Grammar
→ reusable shared entity

LessonVocabulary / LessonGrammar
→ lesson-specific association/order/note/example
```

POST may either:

- attach existing shared item by ID; or
- create shared item + association atomically.

Require exactly one mode.

PATCH may update explicit association fields and explicit canonical shared fields.

A shared-field edit affects all lessons referencing that shared entity. Do not silently fork/duplicate it.

DELETE means detach association only when safe.

If historical learner progress references the association, return a stable 409 and preserve the row/history.

Do not hard-delete shared Vocabulary/Grammar simply because one lesson detaches it.

---

# 25. Admin Assessment / Questions

Implement:

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

Lifecycle:

```text
DRAFT → REVIEW → PUBLISHED → ARCHIVED
```

Rules:

- create DRAFT;
- PATCH cannot assign status;
- submit-review only DRAFT;
- publish only REVIEW;
- archive only PUBLISHED;
- Question create/update/delete only DRAFT or REVIEW;
- PUBLISHED/ARCHIVED questions immutable;
- historical attempts/answers never deleted;
- no GeneratedDraft entity.

Preserve DB target rule:

```text
LESSON_EXERCISE → lesson_id required
PERIODIC_TEST   → lesson_id null
```

Periodic-test scope uses existing:

- `assessment_lessons`;
- `assessment_vocabulary`;
- `assessment_grammar`;

through Assessment use cases, not raw junction APIs.

Question create/update validates D-009.

MCQ options are managed as part of Question use case; no raw question-option CRUD endpoint required.

No AI generation.

---

# 26. Admin Statistics

Implement:

```http
GET /api/v1/admin/stats
```

Return at least:

```text
total_users
users_by_current_hsk[]
average_exercise_score
```

Rules:

- derive from application tables;
- no warehouse/BI layer;
- current HSK uses same ProgressService semantics as learner API;
- average uses `GRADED` LESSON_EXERCISE attempts;
- no attempts → `average_exercise_score = null`;
- do not persist aggregates.

---

# 27. Error Contract

Use the normalized application error envelope.

Required stable codes include:

```text
AUTHENTICATION_REQUIRED
LESSON_LOCKED
PRONUNCIATION_NOT_COMPLETED
ASSESSMENT_LOCKED
ATTEMPT_ALREADY_SUBMITTED
INVALID_CURRICULUM_TRANSITION
CONTENT_ARCHIVED
AI_GRADING_UNAVAILABLE
```

Add narrow stable codes where needed for:

- not found;
- invalid lifecycle;
- invalid answer/config;
- content/history conflict.

Do not require frontend parsing of human-readable strings.

Status conventions:

```text
200 success/idempotent success
201 created
204 successful detach with no body
400/422 invalid input
401 missing current-user identity
403 locked/forbidden learner access
404 not found
409 lifecycle/business conflict
503 AI grading unavailable
```

If FastAPI/Pydantic request validation errors are part of the public API, normalize them to the project error envelope rather than creating a second deliberate error format.

Never expose SQLAlchemy/psycopg exception text or stack traces.

---

# 28. Pagination / Filtering

For growing collections:

```text
page >= 1
page_size >= 1
page_size <= 100
```

Default `1 / 20`.

Only whitelisted filters/sorts.

Do not dynamically map arbitrary client strings into DB columns, SQL text or `order_by`.

Use stable deterministic ordering.

---

# 29. Phase 2 Fidelity / No Migration

Preserve:

- UUID identities;
- attempt history;
- normalized Vocabulary/Grammar;
- unique learner progress rows;
- Assessment for both lesson exercises and periodic tests;
- JSONB `user_answer`;
- no generic persisted percentage;
- no generic persisted unlock boolean;
- no duplicate `best_score` field;
- `UNCERTAIN` distinct from incorrect;
- no broad hard-delete cascade;
- historical learner data survives content archival.

API schemas remain distinct from ORM models.

If Step 3.4 seems to require a schema change, stop as `BLOCKED` and explain why.

---

# 30. Out of Scope

Do not implement:

- registration/login/logout;
- password behavior;
- Argon2;
- JWT;
- cookies;
- refresh tokens;
- real current-user resolution;
- real Admin authorization;
- Conversation API;
- real LLM provider;
- real AI grading;
- RAG;
- ingestion;
- AI assessment generation;
- frontend;
- Docker/deployment;
- queue/worker;
- microservice;
- cache layer.

---

# 31. Test Data / Isolation

Use accepted dedicated PostgreSQL test infrastructure.

Never destructive-test runtime/production DB.

Tests may create User rows directly because registration is Step 3.5.

Learner fixture:

```text
role = LEARNER
```

Use only a placeholder hash string required by schema; do not implement password behavior.

Tests own cleanup/lifecycle.

Do not weaken Step 3.3 test-DB guards.

---

# 32. Required Tests

At minimum cover:

## Identity / ownership
- missing current-user → exact D-011 401;
- persisted learner dependency override;
- no arbitrary learner `user_id`;
- cross-user attempt detail/history rejection.

## Curriculum / dashboard
- `order_index` ordering;
- LOCKED/AVAILABLE/COMPLETED states;
- pronunciation prerequisite;
- first HSK1 unlock;
- current HSK/unit;
- percentage;
- Continue Learning.

## Lesson / theory
- locked lesson;
- no draft leak;
- vocab view idempotency;
- grammar view idempotency;
- derived theory completion;
- no duplicate progress;
- completion permanence.

## Assessment secrecy
For every supported type verify pre-submit answer keys are absent:
- MCQ `is_correct`;
- fill reference/accepted answers;
- matching `correct_pairs`;
- reorder `correct_order`;
- free-form reference/rubric.

## Attempt lifecycle
- create;
- resume;
- no duplicate active;
- retry next number;
- duplicate submit rejected;
- GRADING_FAILED retained historically.

## Deterministic grading
- MCQ;
- fill trim/exact;
- accepted fill alternatives;
- matching exact pair set;
- reorder exact order;
- all-or-nothing points;
- deterministic questions never call AIGrader.

## AI boundary
With FakeAIGrader:
- confident correct;
- confident incorrect;
- UNCERTAIN;
- UNCERTAIN denominator exclusion;
- zero-denominator result.

With default unavailable grader:
- 503 exact D-010;
- attempt GRADING_FAILED;
- submitted_at set;
- score/passed null;
- learner answer preserved;
- free-form answer FAILED;
- deterministic results preserved if already graded;
- no progress mutation.

## Submission validation
- ownership;
- non-IN_PROGRESS;
- wrong-question ID;
- duplicate question ID;
- missing answer;
- malformed D-009 payload;
- no partial persistence after validation failure.

## Progress
- theory + pass → lesson complete;
- pass before theory does not complete until theory complete;
- lower retry does not undo;
- periodic pass gate;
- failed periodic attempt does not unlock;
- next unit sequential;
- next HSK only after prior HSK complete;
- no generic progress mutation endpoint.

## Atomicity
Force persistence/progress failure and verify rollback:
- no partial AttemptAnswer set;
- no half-finalized attempt;
- no partial progress/unlock.

## History
- pagination;
- whitelisted filters;
- ownership;
- historical attempts retained;
- result detail.

## Admin
- HSK identity immutable;
- curriculum reorder success/failure;
- lesson legal/illegal lifecycle;
- assessment legal/illegal lifecycle;
- arbitrary status PATCH rejected;
- question editing DRAFT/REVIEW only;
- published question mutation rejected;
- vocabulary/grammar attach/create/update/detach;
- history-referenced detach rejected;
- completed learner progress survives content edit;
- stats total users/current HSK/average score;
- empty average = null.

## Regression
Run all accepted Step 3.1–3.3 tests.

---

# 33. Verification

At minimum:

```bash
cd backend
uv sync
uv run python -c "from app.main import app; assert app is not None"
uv run alembic check
uv run pytest -q
```

Use real isolated PostgreSQL test DB.

No SQLite substitution.

If required PostgreSQL verification cannot run, report `PARTIAL`/`BLOCKED`; do not claim full DONE from mocked DB behavior.

---

# 34. Acceptance Criteria

## Architecture
- [ ] Router → Service → Repository → AsyncSession.
- [ ] Routers contain no business logic.
- [ ] Repositories never commit.
- [ ] Services own transactions.
- [ ] ProgressService owns progression/unlock.
- [ ] No migration/schema change.

## D-008 / D-011
- [ ] `/me` uses injectable current-user boundary.
- [ ] No client-controlled learner `user_id`.
- [ ] No fabricated runtime identity.
- [ ] Missing identity → exact 401 `AUTHENTICATION_REQUIRED`.
- [ ] No Step 3.5 auth implementation.

## Learner business flow
- [ ] Curriculum states server-derived.
- [ ] Dashboard aggregate endpoint works.
- [ ] Locked lessons enforced.
- [ ] Theory view idempotent and theory completion derived.
- [ ] Pronunciation gates HSK1.
- [ ] Progression is sequential.

## Assessment
- [ ] No pre-submit answer-key leakage.
- [ ] D-009 exact.
- [ ] Active attempt resumes.
- [ ] Historical retries preserved.
- [ ] Duplicate submit rejected.
- [ ] Deterministic grading uses no AI.
- [ ] AIGrader boundary injectable.
- [ ] Fake grader test-only.
- [ ] D-010 exact.
- [ ] UNCERTAIN excluded and distinct from technical failure.
- [ ] Successful attempt + progress persistence atomic.

## History / Admin
- [ ] Learner sees only own history/progress.
- [ ] Pagination bounded and filters whitelisted.
- [ ] Admin APIs are use-case-oriented.
- [ ] Lifecycle transitions service-controlled.
- [ ] Historical data not hard-deleted.
- [ ] Admin stats use canonical progression/scoring semantics.

## Scope
- [ ] No JWT/login/password/cookies/refresh tokens.
- [ ] No real Admin auth.
- [ ] No Conversation API.
- [ ] No real LLM/provider.
- [ ] No RAG/ingestion/frontend.
- [ ] No unnecessary new dependency/infrastructure.
- [ ] Step Note created.
- [ ] Required tests + regressions pass.

---

# 35. Step Note

Create:

```text
docs/backend/step-3.4-business-apis.md
```

Include:

- Objective
- Why
- Mental Model
- Core Knowledge
- Data Flow
- Key Design Decisions
- Reusable approach
- Common Mistakes
- Definition of Done
- Concepts Actually Used
- Tools Actually Used

Keep reusable concepts; do not document every route line-by-line.

---

# 36. Expected Concepts

Only record those actually used.

| Concept | Category | Role |
|---|---|---|
| REST / use-case API contract | SYSTEM | Maps HTTP to product use cases instead of exposing tables. |
| Router → Service → Repository | SYSTEM | Preserves dependency direction. |
| Dependency injection / current-user seam | SYSTEM | Decouples business logic from future auth. |
| Transaction atomicity | SYSTEM | Keeps attempts/results/progress consistent. |
| Idempotency | SYSTEM | Prevents duplicate theory/pronunciation progress. |
| Lifecycle state machine | SYSTEM | Controls legal transitions. |
| Derived progression/unlock state | SYSTEM | Keeps backend authoritative without redundant unlock flags. |
| Deterministic grading | SYSTEM | Grades objective questions from stored rules. |
| AIGrader application boundary | AI | Replaceable boundary for future LLM grading. |
| Ownership enforcement | SYSTEM | Prevents cross-learner access. |
| Pagination / whitelisted filtering | SYSTEM | Safe collection access. |

---

# 37. Expected Tools

No new framework expected.

| Tool | Category |
|---|---|
| Python | SYSTEM |
| uv | SYSTEM |
| FastAPI | SYSTEM |
| Pydantic | SYSTEM |
| SQLAlchemy | SYSTEM |
| psycopg 3 | SYSTEM |
| PostgreSQL | DE |
| pytest | SYSTEM |

No LLM SDK.

---

# 38. Required Completion Report

Return:

```text
Step: 3.4 — Business APIs
Status: DONE | PARTIAL | BLOCKED

Implementation plan executed:
- ...

Files created:
- ...

Files modified:
- ...

Dependencies added/removed:
- ...

Public APIs implemented:
- ...

D-008 current-user boundary:
- ...

D-009 question/grading contract:
- ...

D-010 GRADING_FAILED behavior:
- ...

D-011 missing identity behavior:
- ...

Service/repository/transaction design:
- ...

Progress/unlock behavior:
- ...

Admin lifecycle/history behavior:
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
Do not begin Step 3.5.
```

Do not claim `DONE` if:

- required PostgreSQL integration verification did not run;
- D-008 through D-011 are not implemented exactly;
- a schema/API/transaction conflict required an invented architecture change;
- Step 3.5+ scope was pulled forward.
