# Step 2.1 — Identify Data Entities

## 1. Project Context

Project là web application học tiếng Trung cho người Việt từ zero đến HSK 3.

Core system gồm:

- Learner/Admin;
- Pronunciation Foundations;
- HSK curriculum;
- Lesson;
- Vocabulary/Grammar;
- Lesson exercises;
- Periodic tests;
- Progress tracking;
- AI lesson chat;
- AI grading;
- AI content generation;
- Document ingestion/RAG.

Architecture V0 sử dụng Modular Monolith Backend và relational application data store.

Step này chỉ xác định logical data entities. Không tạo database schema hoặc migration.

---

# 2. Step Goal

Xác định tập entity/domain object chính thức làm đầu vào cho Step 2.2 — Relational Data Model.

Không định nghĩa:

- SQL;
- table columns đầy đủ;
- primary key;
- foreign key;
- indexes;
- ORM;
- migrations.

---

# 3. Approved Entities

## User

Một entity chung:

```text
User
```

Có role:

```text
LEARNER
ADMIN
```

Không tạo Learner và Admin thành hai user entity/table độc lập.

---

## HSKLevel

Curriculum hiện chỉ có:

```text
HSK1
HSK2
HSK3
```

Dùng:

```text
HSKLevel
```

Không tạo `Course` riêng ở MVP.

---

## PronunciationSection

Pronunciation Foundations là domain riêng gồm:

- tones;
- initials;
- finals.

Use:

```text
PronunciationSection
```

Không model nó như regular HSK Lesson.

---

## Lesson

Each Lesson belongs to one HSKLevel.

Lesson cần khả năng có:

- curriculum order;
- title;
- description;
- publish/lifecycle state.

Exact attributes belong to later modeling.

---

## Vocabulary

Use reusable base entity:

```text
Vocabulary
```

Do not directly assume one Vocabulary belongs permanently to one Lesson.

Use relationship entity:

```text
LessonVocabulary
```

Conceptually:

```text
Lesson
→ LessonVocabulary
→ Vocabulary
```

This allows vocabulary reuse across lessons.

---

## Grammar

Use:

```text
Grammar
LessonGrammar
```

Grammar may be reused across multiple lessons.

---

# 4. Assessment Model

Use one generic entity:

```text
Assessment
```

with logical type:

```text
LESSON_EXERCISE
PERIODIC_TEST
```

Do not create completely duplicated Exercise and Test domain trees.

---

## Lesson Exercise

A lesson may contain one or multiple Assessments where:

```text
type = LESSON_EXERCISE
```

A lesson exercise is scoped to knowledge of one lesson.

---

## Periodic Test

A periodic test uses:

```text
type = PERIODIC_TEST
```

It may cover vocabulary/grammar from multiple previously learned lessons and occupy a position in curriculum progression.

Exact relationships will be designed in Step 2.2.

---

# 5. Question

Assessment contains Questions:

```text
Assessment
└── Question
```

Question types required by product include:

- multiple_choice;
- fill_blank;
- matching;
- reorder_sentence;
- translate_vi_zh;
- translate_zh_vi;
- sentence_writing.

Exact question payload/schema is not defined here.

---

# 6. Assessment Attempts

Use:

```text
AssessmentAttempt
```

for both lesson exercise and periodic-test attempts.

Attempt must eventually support:

- learner;
- target Assessment;
- start/submission time;
- score;
- pass status;
- attempt history.

Exact fields are not yet final.

---

## AttemptAnswer

Each attempt must preserve per-question answers/results:

```text
AssessmentAttempt
└── AttemptAnswer
```

This is required for:

- answer history;
- correct/incorrect feedback;
- LLM grading result;
- uncertain grading state;
- future evaluation/debugging.

---

# 7. Progress Entities

Use separate domain progress models rather than one generic Progress entity:

```text
PronunciationProgress
LearnerHSKProgress
LearnerLessonProgress
LearnerLessonContentProgress
```

---

## PronunciationProgress

Tracks learner completion of Pronunciation Foundations.

---

## LearnerHSKProgress

Tracks learner state for an HSK level.

---

## LearnerLessonProgress

Tracks lesson-level lifecycle such as:

- started;
- theory completed;
- completed;
- timing/progress state.

Exact fields are deferred.

---

## LearnerLessonContentProgress

Tracks whether required lesson content has been viewed.

Must support progress for individual:

- vocabulary items;
- grammar sections/items.

This data is used to derive theory completion.

---

# 8. Conversation Entities

Use:

```text
Conversation
└── Message
```

Conversation belongs logically to:

```text
Learner + Lesson
```

Each conversation contains multiple messages.

Message must eventually support user/AI message distinction and processing status.

---

# 9. Document Entity

Use:

```text
Document
```

for uploaded source files.

Document must eventually represent:

- original filename/type;
- file storage reference;
- processing state;
- approval state;
- source metadata.

Supported current input types:

- PDF;
- DOCX;
- TXT;
- MD.

---

# 10. Retrieval Data

Maintain logical retrieval entities/representations:

```text
Knowledge Source / Document
→ Chunk
→ Embedding Representation
```

A Chunk must eventually retain source metadata needed for citation.

Do not select a vector database or physical embedding schema yet.

---

# 11. AI-generated Drafts

Do not create a separate `GeneratedDraft` entity for exercises/tests.

AI-generated exercise/test should use the same:

```text
Assessment
```

entity with lifecycle state such as:

```text
DRAFT
→ REVIEWED
→ PUBLISHED
```

Admin may edit the draft before publication.

---

# 12. Statistics

Do not create persistent entities solely for:

- total users;
- total lessons;
- total tests;
- users by HSK;
- average exercise score.

These are derived/aggregated from source entities.

---

# 13. Logical Entity Map

```text
User
│
├── PronunciationProgress
├── LearnerHSKProgress
├── LearnerLessonProgress
├── LearnerLessonContentProgress
│
├── AssessmentAttempt
│    └── AttemptAnswer
│
└── Conversation
     └── Message


HSKLevel
└── Lesson
     ├── LessonVocabulary ── Vocabulary
     ├── LessonGrammar ───── Grammar
     └── Assessment
          └── Question


Document
└── Chunk
     └── Embedding Representation
```

Periodic tests are also represented by `Assessment`, not a separate duplicated assessment hierarchy.

---

# 14. Constraints

Do not:

- create Course without a new product requirement;
- create separate Learner/Admin identity models;
- duplicate ExerciseAttempt/TestAttempt unnecessarily;
- model statistics as source entities;
- couple Vocabulary permanently to one Lesson;
- couple Grammar permanently to one Lesson;
- create a separate AI draft data model without need;
- define final SQL schema in this Step.

---

# 15. Acceptance Criteria

- [ ] User is one entity with role.
- [ ] HSKLevel exists without unnecessary Course layer.
- [ ] PronunciationSection is separate from regular Lesson.
- [ ] Lesson belongs to HSKLevel.
- [ ] Vocabulary is reusable through LessonVocabulary.
- [ ] Grammar is reusable through LessonGrammar.
- [ ] Lesson Exercise and Periodic Test share Assessment abstraction.
- [ ] Assessment owns Questions.
- [ ] AssessmentAttempt supports both assessment types.
- [ ] AttemptAnswer preserves per-question history.
- [ ] Progress is separated by domain.
- [ ] Item-level theory progress can be represented.
- [ ] Conversation/Message can represent AI history.
- [ ] Document can represent ingestion lifecycle.
- [ ] Chunk/embedding representation exists logically.
- [ ] AI drafts use Assessment lifecycle.
- [ ] Statistics remain derived values.

---

# 16. Expected Deliverable

```text
docs/data/
└── step-2.1-data-entities.md
```

No database implementation is required.

Next Step:

**Step 2.2 — Relational Data Model**