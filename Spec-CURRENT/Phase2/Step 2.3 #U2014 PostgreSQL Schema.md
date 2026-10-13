# Step 2.3 — PostgreSQL Schema

## Goal

Define the approved physical PostgreSQL application schema from the Step 2.2 relational model.

This specification covers:

- tables;
- columns;
- primary keys;
- foreign keys;
- uniqueness;
- check constraints;
- basic indexes.

Do not implement RAG Chunk/Embedding physical storage in this step.

---

# Global Conventions

Use:

```text
UUID primary keys
snake_case identifiers
```

Use appropriate timestamps:

```text
created_at
updated_at
started_at
submitted_at
completed_at
published_at
viewed_at
approved_at
```

Prefer:

```text
TEXT/VARCHAR + CHECK
```

over PostgreSQL native ENUM for application lifecycle/type values.

Do not hard-delete learning content/history when archival is sufficient.

---

# users

```text
id UUID PK
email TEXT NOT NULL UNIQUE
password_hash TEXT NOT NULL
full_name TEXT NOT NULL
role TEXT NOT NULL
is_active BOOLEAN NOT NULL DEFAULT TRUE
created_at
updated_at
```

Constraint:

```text
role IN ('LEARNER', 'ADMIN')
```

---

# hsk_levels

```text
id UUID PK
level_number INTEGER NOT NULL UNIQUE
title TEXT
description TEXT
order_index INTEGER NOT NULL
```

Initial records:

```text
1
2
3
```

---

# lessons

```text
id UUID PK
hsk_level_id UUID NOT NULL FK → hsk_levels.id
lesson_number INTEGER NOT NULL
title TEXT NOT NULL
description TEXT NULL
status TEXT NOT NULL
created_at
updated_at
published_at NULL
```

Constraints:

```text
UNIQUE(hsk_level_id, lesson_number)

status IN (
  'DRAFT',
  'PUBLISHED',
  'ARCHIVED'
)
```

Lesson number is scoped to an HSK.

Do not use it as the full curriculum ordering mechanism.

---

# curriculum_units

Use this table as the authoritative curriculum progression ordering.

```text
id UUID PK
hsk_level_id UUID NOT NULL FK → hsk_levels.id
unit_type TEXT NOT NULL
lesson_id UUID NULL FK → lessons.id
assessment_id UUID NULL FK → assessments.id
order_index INTEGER NOT NULL
```

Constraints:

```text
unit_type IN (
  'LESSON',
  'PERIODIC_TEST'
)

UNIQUE(hsk_level_id, order_index)
```

Require exactly the appropriate target:

```text
LESSON
→ lesson_id NOT NULL
→ assessment_id NULL

PERIODIC_TEST
→ assessment_id NOT NULL
→ lesson_id NULL
```

---

# pronunciation_sections

```text
id UUID PK
code TEXT NOT NULL UNIQUE
title TEXT
description TEXT
order_index INTEGER NOT NULL
```

Seed:

```text
TONES
INITIALS
FINALS
```

---

# pronunciation_progress

```text
id UUID PK
user_id UUID NOT NULL FK → users.id
pronunciation_section_id UUID NOT NULL FK → pronunciation_sections.id
completed_at NULL
created_at
updated_at
```

Constraint:

```text
UNIQUE(user_id, pronunciation_section_id)
```

---

# vocabulary

```text
id UUID PK
hanzi TEXT NOT NULL
pinyin TEXT NOT NULL
vietnamese_meaning TEXT NOT NULL
part_of_speech TEXT NULL
created_at
updated_at
```

Do not create VocabularyMeaning table in MVP.

---

# lesson_vocabulary

```text
id UUID PK
lesson_id UUID NOT NULL FK → lessons.id
vocabulary_id UUID NOT NULL FK → vocabulary.id
order_index INTEGER NOT NULL
note TEXT NULL
example TEXT NULL
```

Constraints:

```text
UNIQUE(lesson_id, vocabulary_id)
UNIQUE(lesson_id, order_index)
```

---

# grammar

```text
id UUID PK
name TEXT NOT NULL
structure TEXT NULL
explanation TEXT NOT NULL
usage TEXT NULL
created_at
updated_at
```

---

# lesson_grammar

```text
id UUID PK
lesson_id UUID NOT NULL FK → lessons.id
grammar_id UUID NOT NULL FK → grammar.id
order_index INTEGER NOT NULL
note TEXT NULL
example TEXT NULL
```

Constraints:

```text
UNIQUE(lesson_id, grammar_id)
UNIQUE(lesson_id, order_index)
```

---

# assessments

```text
id UUID PK
type TEXT NOT NULL
lesson_id UUID NULL FK → lessons.id
title TEXT NOT NULL
description TEXT NULL
status TEXT NOT NULL
pass_threshold INTEGER NOT NULL DEFAULT 90
created_at
updated_at
published_at NULL
```

Types:

```text
LESSON_EXERCISE
PERIODIC_TEST
```

Statuses:

```text
DRAFT
REVIEW
PUBLISHED
ARCHIVED
```

Constraints:

```text
pass_threshold BETWEEN 0 AND 100
```

Require:

```text
LESSON_EXERCISE → lesson_id NOT NULL
PERIODIC_TEST   → lesson_id NULL
```

---

# assessment_lessons

```text
assessment_id UUID FK → assessments.id
lesson_id UUID FK → lessons.id
```

Constraint:

```text
UNIQUE(assessment_id, lesson_id)
```

Used primarily for PERIODIC_TEST scope.

---

# assessment_vocabulary

```text
assessment_id UUID FK → assessments.id
vocabulary_id UUID FK → vocabulary.id
```

Constraint:

```text
UNIQUE(assessment_id, vocabulary_id)
```

---

# assessment_grammar

```text
assessment_id UUID FK → assessments.id
grammar_id UUID FK → grammar.id
```

Constraint:

```text
UNIQUE(assessment_id, grammar_id)
```

---

# questions

```text
id UUID PK
assessment_id UUID NOT NULL FK → assessments.id
type TEXT NOT NULL
prompt TEXT NOT NULL
order_index INTEGER NOT NULL
reference_answer TEXT NULL
rubric TEXT NULL
config JSONB NULL
points NUMERIC NOT NULL DEFAULT 1
created_at
updated_at
```

Support required question types including:

```text
multiple_choice
fill_blank
matching
reorder_sentence
translate_vi_zh
translate_zh_vi
sentence_writing
```

Use `config JSONB` only for type-specific structured configuration.

Do not over-design matching/reorder physical structures yet.

---

# question_options

```text
id UUID PK
question_id UUID NOT NULL FK → questions.id
option_text TEXT NOT NULL
order_index INTEGER NOT NULL
is_correct BOOLEAN NOT NULL DEFAULT FALSE
```

Primarily used for suitable objective question types such as MCQ.

---

# assessment_attempts

```text
id UUID PK
user_id UUID NOT NULL FK → users.id
assessment_id UUID NOT NULL FK → assessments.id
attempt_number INTEGER NOT NULL
status TEXT NOT NULL
started_at
submitted_at NULL
score NUMERIC NULL
passed BOOLEAN NULL
```

Constraint:

```text
UNIQUE(
  user_id,
  assessment_id,
  attempt_number
)
```

Statuses:

```text
IN_PROGRESS
SUBMITTED
GRADED
GRADING_FAILED
```

Unlimited retries are represented as additional attempts.

---

# attempt_answers

```text
id UUID PK
assessment_attempt_id UUID NOT NULL FK → assessment_attempts.id
question_id UUID NOT NULL FK → questions.id
user_answer JSONB NULL
score NUMERIC NULL
is_correct BOOLEAN NULL
grading_status TEXT NOT NULL
feedback TEXT NULL
created_at
```

Constraint:

```text
UNIQUE(
  assessment_attempt_id,
  question_id
)
```

Grading statuses:

```text
PENDING
GRADED
UNCERTAIN
FAILED
```

`UNCERTAIN` answers must be excluded from final score calculation.

`user_answer` uses JSONB because answer shapes vary by question type.

---

# learner_lesson_progress

```text
id UUID PK
user_id UUID NOT NULL FK → users.id
lesson_id UUID NOT NULL FK → lessons.id
started_at NULL
theory_completed_at NULL
completed_at NULL
created_at
updated_at
```

Constraint:

```text
UNIQUE(user_id, lesson_id)
```

Do not persist `best_score` here.

Derive score information from assessment_attempts.

---

# learner_hsk_progress

```text
id UUID PK
user_id UUID NOT NULL FK → users.id
hsk_level_id UUID NOT NULL FK → hsk_levels.id
started_at NULL
completed_at NULL
created_at
updated_at
```

Constraint:

```text
UNIQUE(user_id, hsk_level_id)
```

Do not persist percentage progress.

Derive from curriculum unit completion.

---

# learner_vocabulary_progress

```text
id UUID PK
user_id UUID NOT NULL FK → users.id
lesson_vocabulary_id UUID NOT NULL FK → lesson_vocabulary.id
viewed_at NOT NULL
```

Constraint:

```text
UNIQUE(user_id, lesson_vocabulary_id)
```

---

# learner_grammar_progress

```text
id UUID PK
user_id UUID NOT NULL FK → users.id
lesson_grammar_id UUID NOT NULL FK → lesson_grammar.id
viewed_at NOT NULL
```

Constraint:

```text
UNIQUE(user_id, lesson_grammar_id)
```

---

# conversations

V0 supports Lesson-scoped chat only.

```text
id UUID PK
user_id UUID NOT NULL FK → users.id
lesson_id UUID NOT NULL FK → lessons.id
title TEXT NULL
created_at
updated_at
```

Do not add a `GLOBAL` scope column/enum solely for a deferred feature. If standalone global chat is approved later, add it through a forward migration and explicit API/product change.

Test-time AI chat disabling is application logic and must not be modeled as a relational relationship.

---

# messages

```text
id UUID PK
conversation_id UUID NOT NULL FK → conversations.id
role TEXT NOT NULL
content TEXT NULL
status TEXT NOT NULL
created_at
```

Roles:

```text
USER
ASSISTANT
```

Statuses:

```text
PENDING
COMPLETED
FAILED
```

Content invariant:

```text
USER + COMPLETED       → content NOT NULL and non-empty
ASSISTANT + PENDING    → content MAY be NULL
ASSISTANT + FAILED     → content MAY be NULL
ASSISTANT + COMPLETED  → content NOT NULL and non-empty
```

The database/model must not require placeholder text for a `PENDING` assistant message. Enforce the invariant with validation and, where practical, a CHECK constraint.

---

# message_citations

Canonical V0 citation persistence must match the later Step 6.10 runtime contract rather than require a second incompatible table.

```text
id UUID PK
message_id UUID NOT NULL FK → messages.id
source_label TEXT NOT NULL
source_kind TEXT NOT NULL
chunk_id UUID NULL  # FK added after `chunks` exists in Step 2.4
title TEXT NOT NULL
url TEXT NULL
domain TEXT NULL
source_type TEXT NULL
locator JSONB NULL
metadata JSONB NULL
created_at
```

Constraints/behavior:

```text
UNIQUE(message_id, source_label)
message_id ON DELETE CASCADE
after `chunks` exists: chunk_id FK ON DELETE SET NULL
source_kind IN (INTERNAL_CHUNK, EXTERNAL_URL)
```

Persist display-safe provenance snapshots so historical citations survive source metadata changes/deletion. Do not store all citations only as one opaque JSON blob. Step 6.10 may add a forward migration only if the already-applied physical schema needs reconciliation; it must not create a duplicate citation model.

---

# documents

Only application-side document metadata is defined in this step. Machine processing and human review are independent state machines.

```text
id UUID PK
original_filename TEXT NOT NULL
file_type TEXT NOT NULL
storage_reference TEXT NOT NULL
processing_status TEXT NOT NULL
review_status TEXT NOT NULL
uploaded_by UUID NOT NULL FK → users.id
approved_by UUID NULL FK → users.id
approved_at NULL
created_at
updated_at
```

Processing statuses:

```text
UPLOADED
PROCESSING
PREVIEW_READY
FAILED
```

Review statuses:

```text
PENDING
APPROVED
REJECTED
```

Required invariant:

```text
review_status = APPROVED
→ processing_status = PREVIEW_READY
→ approved_by/approved_at present
```

Document approval does **not** mean a KnowledgeVersion is retrieval-active. Chunking/embedding/vector readiness and atomic KnowledgeVersion activation are separate later stages. Archival, if/when exposed, is an independent lifecycle policy and must not collapse the two state machines above.

Do not define final Chunk/Embedding physical storage yet. That belongs to Step 2.4.

---

# Archive Strategy

Do not cascade-delete historical learning data when content is archived.

Use lifecycle state for:

```text
Lesson
Assessment
Document
```

Disable User accounts through:

```text
is_active = FALSE
```

Attempts, answers and learner progress must remain available as historical records.

Exact FK `ON DELETE` strategies will be finalized with migration implementation.

---

# Initial Indexes

Beyond indexes created by PK/UNIQUE constraints, plan indexes for common access patterns:

```text
lessons(hsk_level_id)

curriculum_units(
  hsk_level_id,
  order_index
)

assessment_attempts(
  user_id,
  assessment_id
)

conversations(
  user_id,
  updated_at
)

messages(
  conversation_id,
  created_at
)

documents(processing_status)
documents(review_status)
```

Do not perform premature index optimization.

---

# Out of Scope

Do not select or implement yet:

- ORM;
- migration framework;
- vector extension/store;
- Chunk schema;
- Embedding schema;
- embedding model;
- detailed matching/reorder model;
- production database hosting;
- backup implementation.

---

# Acceptance Criteria

- [ ] All application entities from Step 2.2 map to PostgreSQL tables.
- [ ] UUID is used for entity primary keys.
- [ ] HSK-local lesson numbering is enforced.
- [ ] Curriculum ordering supports lessons and periodic tests.
- [ ] Vocabulary/Grammar reuse is preserved.
- [ ] Assessment handles both lesson exercises and periodic tests.
- [ ] Periodic-test scope can be represented.
- [ ] Per-question answers are retained.
- [ ] Uncertain AI grading is representable.
- [ ] Unlimited assessment attempts are supported.
- [ ] Theory viewing progress is persisted at item level.
- [ ] Lesson and HSK progress avoid unnecessary duplicated derived values.
- [ ] V0 AI conversations are Lesson-scoped and require a Lesson FK.
- [ ] Citations have structured persistent representation.
- [ ] Document lifecycle is supported.
- [ ] Historical learning data survives content archival.
- [ ] Basic query indexes are defined.
- [ ] Chunk/Embedding physical storage remains deferred to AI/RAG Data Model.

---

# Expected Deliverable

```text
docs/data/
└── step-2.3-postgresql-schema.md
```

This schema is the approved database design baseline for future migrations.

Next Step:

**Step 2.4 — AI/RAG Data Model**