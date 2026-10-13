# Step 2.2 — Relational Data Model

## Goal

Chuyển logical entities từ Step 2.1 thành relational model với relationships, cardinality và ownership rõ ràng.

Không implement SQL/migrations trong Step này.

---

# Core Relations

## User

Use one User entity with:

```text
role = LEARNER | ADMIN
```

No separate Role table required for MVP.

---

## HSK and Lessons

```text
HSKLevel 1:N Lesson
```

Lesson order is scoped to an HSK level.

HSK1 Lesson 1 and HSK2 Lesson 1 are different lessons.

Logical uniqueness requirement:

```text
(hsk_level_id, order_index)
```

Do not make lesson order globally unique.

---

# Pronunciation

Persist PronunciationSection records:

```text
TONES
INITIALS
FINALS
```

Relationship:

```text
User 1:N PronunciationProgress
PronunciationSection 1:N PronunciationProgress
```

Require logical uniqueness:

```text
(user_id, pronunciation_section_id)
```

---

# Vocabulary

Use reusable Vocabulary entities.

Relationship:

```text
Lesson N:N Vocabulary
```

implemented logically through:

```text
LessonVocabulary
```

LessonVocabulary should support:

```text
order_index
lesson_specific_note optional
lesson_specific_example optional
```

---

# Grammar

Use:

```text
Lesson N:N Grammar
```

through:

```text
LessonGrammar
```

LessonGrammar requires lesson-scoped ordering.

---

# Assessment

Use one Assessment model with:

```text
type =
LESSON_EXERCISE
PERIODIC_TEST
```

## Lesson Exercise

```text
Lesson 1:N Assessment
```

For `LESSON_EXERCISE`, the assessment belongs to one lesson.

A lesson may contain multiple exercise sets.

## Periodic Test

Periodic test may cover multiple lessons.

Use:

```text
AssessmentLesson
```

for lesson scope.

Exact selected knowledge must also be representable through:

```text
AssessmentVocabulary
AssessmentGrammar
```

---

# Questions

```text
Assessment 1:N Question
Question 1:N QuestionOption
```

Question belongs to one Assessment.

QuestionOption should be represented relationally rather than storing all options as one JSON blob.

Objective questions require answer-key representation.

Free-form questions may use reference answer/rubric.

---

# Attempts

```text
User 1:N AssessmentAttempt
Assessment 1:N AssessmentAttempt

AssessmentAttempt 1:N AttemptAnswer
Question 1:N AttemptAnswer
```

AttemptAnswer must support logical data for:

```text
user_answer
score
is_correct
feedback
grading_status
```

Exact column types belong to Step 2.3.

---

# Learning Progress

Use:

```text
LearnerLessonProgress
```

with logical uniqueness:

```text
(user_id, lesson_id)
```

Use:

```text
LearnerHSKProgress
```

with:

```text
(user_id, hsk_level_id)
```

---

# Theory Content Progress

Do not use a polymorphic structure such as:

```text
content_type
content_id
```

Use separate relations:

```text
LearnerVocabularyProgress
→ LessonVocabulary

LearnerGrammarProgress
→ LessonGrammar
```

This preserves foreign-key integrity and tracks progress in the context of a specific lesson.

---

# Conversation

V0 supports Lesson-scoped conversations only.

Relationships:

```text
User 1:N Conversation
Lesson 1:N Conversation
Conversation 1:N Message
```

Required relation:

```text
Conversation.lesson_id
→ NOT NULL
```

Do not add a `GLOBAL` conversation scope or standalone General Chat API in V0. If product scope later adds global chat, extend persistence and API through an explicit forward change instead of pre-building unused behavior.

AI chat must be disabled while learner is taking a test. This is an application/business rule, not a database relationship.

Message role:

```text
USER
ASSISTANT
```

---

# Knowledge Data

Use:

```text
Document 1:N Chunk
Chunk 1:N Embedding
```

Multiple Embedding records per Chunk are intentional.

They must allow different embedding model/version representations without overwriting previous representations.

---

# Lifecycle

Document:

```text
UPLOADED
PROCESSING
REVIEW
ACTIVE
REJECTED
ARCHIVED
```

Assessment:

```text
DRAFT
REVIEW
PUBLISHED
ARCHIVED
```

Lesson:

```text
DRAFT
PUBLISHED
ARCHIVED
```

---

# Relational Model

```text
User
│
├── PronunciationProgress ───────── PronunciationSection
├── LearnerHSKProgress ──────────── HSKLevel
├── LearnerLessonProgress ───────── Lesson
├── LearnerVocabularyProgress ───── LessonVocabulary
├── LearnerGrammarProgress ──────── LessonGrammar
│
├── AssessmentAttempt ───────────── Assessment
│    └── AttemptAnswer ──────────── Question
│
└── Conversation
     └── Message


HSKLevel
└── Lesson
     ├── LessonVocabulary ───────── Vocabulary
     ├── LessonGrammar ──────────── Grammar
     └── Assessment [LESSON_EXERCISE]
          └── Question
               └── QuestionOption


Assessment [PERIODIC_TEST]
├── AssessmentLesson ────────────── Lesson
├── AssessmentVocabulary ────────── Vocabulary
├── AssessmentGrammar ───────────── Grammar
└── Question


Document
└── Chunk
     └── Embedding
```

---

# Constraints

Do not:

- make Lesson order globally unique;
- duplicate Vocabulary for every lesson;
- duplicate Grammar for every lesson;
- create separate attempt hierarchies for exercises and tests;
- use generic polymorphic content IDs for theory progress;
- require every Conversation to belong to a Lesson;
- overwrite old Embedding representations when embedding model changes;
- model test-chat disabling as a database relation.

---

# Acceptance Criteria

- [ ] HSKLevel has many Lessons.
- [ ] Lesson ordering is scoped to HSKLevel.
- [ ] Vocabulary and Grammar use N:N junction entities.
- [ ] Lesson-specific order can be stored.
- [ ] Lesson exercises use Assessment.
- [ ] Periodic tests use the same Assessment model.
- [ ] Periodic-test lesson and knowledge scope is representable.
- [ ] Questions belong to Assessments.
- [ ] Question options are relational.
- [ ] Attempts and per-question answers are preserved.
- [ ] Learner progress is unique per appropriate curriculum entity.
- [ ] Vocabulary/Grammar viewing progress preserves FK integrity.
- [ ] V0 Conversation is Lesson-scoped and requires `lesson_id`.
- [ ] Message belongs to Conversation.
- [ ] Document contains many Chunks.
- [ ] Chunk can contain multiple Embedding versions.

---

# Expected Deliverable

```text
docs/data/
└── step-2.2-relational-data-model.md
```

Next Step:

**Step 2.3 — PostgreSQL Schema**