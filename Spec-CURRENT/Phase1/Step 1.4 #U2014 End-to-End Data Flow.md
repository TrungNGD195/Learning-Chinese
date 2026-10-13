# Step 1.4 — End-to-End Data Flow

## 1. Project Context

Project là web app học tiếng Trung cho người Việt từ zero đến HSK 3.

Current architecture:

```text
Frontend
→ Modular Monolith Backend
→ Main Database

Backend
→ AI Layer
→ Knowledge Index / External Retrieval / LLM

Backend
→ File Storage
→ Ingestion

Backend
→ Email Service
```

Major backend responsibilities đã được tách thành:

- Auth
- Curriculum
- Exercise/Test
- Progress
- Admin
- AI

Step này chỉ định nghĩa data flow. Không implement code.

---

# 2. Learning Flow

## Lesson Access

```text
Frontend
→ Backend
→ Progress: validate unlocked
→ Curriculum
→ Main Database
→ Lesson Data
→ Frontend
```

Locked content must not be returned as accessible learning content.

---

## Theory Tracking

Track progress at vocabulary-item / grammar-section granularity.

```text
Viewed Item
→ Backend
→ Progress
→ Main DB
```

Rule:

```text
all required vocabulary viewed
AND
all required grammar viewed
→ theory_completed
```

Tracking must support resume after user leaves and returns.

---

# 3. Objective Exercise Grading

```text
Frontend submits answers
→ Exercise/Test
→ load expected answers
→ deterministic grading
→ calculate score
→ save complete attempt
→ Progress
→ update completion/unlock
→ Main DB
→ return result
```

Do not call LLM for objectively gradable questions when deterministic grading is sufficient.

---

# 4. Free-form Exercise Grading

```text
Frontend
→ Exercise/Test
→ AI Layer
→ LLM Provider
→ Structured Grading Result
→ Exercise/Test
→ Final Score
→ save attempt
→ Progress
→ Main DB
→ Frontend
```

Expected AI grading output must support:

```text
score
is_correct
feedback
grading_status
```

AI does not decide lesson completion.

---

# 5. Uncertain Grading

When:

```text
grading_status = uncertain
```

the question:

- must not be counted as incorrect;
- must be excluded from score calculation;
- must retain its grading result for later inspection.

Exercise/Test owns final score calculation.

---

# 6. Lesson AI Q&A

Required flow:

```text
Learner Question
→ Frontend
→ Backend
→ AI Layer
→ load Current Lesson Context
→ Internal Retrieval
→ Knowledge Index
```

If sufficient knowledge exists:

```text
Retrieved Chunks
→ LLM
→ Answer + Citation
```

Otherwise:

```text
Internal Retrieval Insufficient
→ External Retrieval
→ Trusted Sources
→ LLM
→ Answer + Citation
```

Internal relevant knowledge must remain preferred.

---

# 7. Conversation Persistence

Conversation is associated with:

```text
Learner
+
Lesson
```

Message flow:

```text
User Message
→ persist

AI processing

AI Message
→ persist
```

If AI processing fails, retain the user message and an appropriate failure state rather than silently deleting the interaction.

Conversation history must remain retrievable until learner deletes the conversation.

---

# 8. Admin Manual Content

Manual lesson creation:

```text
Admin
→ Backend
→ Admin
→ Curriculum
→ Main DB
```

Content starts as draft and may later be previewed/published.

---

# 9. AI Lesson Exercise Generation

```text
Admin selects:
- Lesson
- generation configuration

→ Backend
→ Curriculum loads lesson knowledge
→ AI Layer
→ LLM
→ Generated Draft
→ Main DB
→ Admin Review/Edit
→ Publish
```

Generated drafts must be persisted so Admin can leave and resume editing later.

Generated lesson exercises must remain within selected lesson knowledge.

---

# 10. AI Periodic Test Generation

```text
Admin selects vocabulary/grammar
from multiple lessons
→ Backend validates selection
→ AI Layer
→ LLM
→ Test Draft
→ Main DB
→ Admin Review/Edit
→ Publish
```

The AI must not extend knowledge scope beyond Admin selection.

---

# 11. Document Upload and Ingestion

## Stage A — Upload / Processing

```text
Admin
→ Backend
→ File Storage
→ save Document Metadata
→ Ingestion
→ Extract
→ Clean / Normalize
→ Preview
```

Supported inputs:

```text
PDF
DOCX
TXT
MD
```

---

## Stage B — Approval / Indexing

If Admin approves:

```text
Admin Approval
→ Knowledge Processing
→ Chunk
→ Embedding
→ Knowledge Index
→ Document status = ACTIVE
```

Only ACTIVE/approved knowledge may be used by production retrieval.

If Admin rejects:

```text
Document status = REJECTED
```

Keep the raw file for possible inspection/reprocessing.

Do not index rejected content into active knowledge.

---

# 12. Published Lesson to Knowledge

Published lesson content is also an internal knowledge source.

Required logical flow:

```text
Published Lesson
→ Knowledge Processing
→ Retrieval Representation
→ Knowledge Index
```

Application lesson data and retrieval data remain separate representations.

---

# 13. Lesson Update

When published lesson content changes:

```text
Edit Lesson
→ Save Application Data
→ Reprocess Retrieval Representation
→ Update Knowledge Index
```

Existing learner completion/progress must not automatically reset.

---

# 14. Password Reset

```text
Learner submits email
→ Auth
→ generate/store reset token state
→ Email Service
→ learner opens reset link
→ Auth validates token
→ update password
```

Email Service only delivers email.

Auth owns token generation, validation and password-update rules.

---

# 15. Admin Statistics

Statistics must use normal application data flow:

```text
Admin UI
→ Backend
→ Main DB
→ Aggregate
→ Response
```

Current required metrics:

- total users;
- total lessons;
- total tests;
- users by current HSK;
- average exercise score.

Do not involve AI or Knowledge Index.

---

# 16. Canonical Data Flows

Five major flows must be preserved:

```text
A. Learning
Lesson → Exercise → Grading → Progress
```

```text
B. AI Q&A
Question → Retrieval → LLM → Citation → Conversation Storage
```

```text
C. AI Content Generation
Admin Scope → LLM → Draft → Review → Publish
```

```text
D. Knowledge Ingestion
Upload → Extract → Review → Chunk/Embed → Knowledge Index
```

```text
E. Authentication
Login/Reset → Auth → Main DB / Email
```

---

# 17. Constraints

Do not:

- let Frontend decide unlock state;
- let AI grading directly modify Progress;
- let LLM calculate curriculum progression;
- activate unapproved documents;
- discard failed AI user messages silently;
- lose previous attempts;
- publish generated content without review;
- mix raw file storage responsibility with document parsing;
- treat application lesson representation as identical to retrieval representation.

---

# 18. Technology Decisions

No technology selection is required.

Do not choose or introduce:

- message queues;
- workflow engines;
- ETL orchestrators;
- database products;
- vector stores;
- LLM providers;
- external search providers;
- background workers.

These decisions belong to later Steps.

---

# 19. Acceptance Criteria

- [ ] Lesson access checks unlock state.
- [ ] Theory progress is tracked at item/section level.
- [ ] Objective questions follow deterministic grading flow.
- [ ] Free-form questions follow AI grading flow.
- [ ] Uncertain grading is excluded from score.
- [ ] Attempts are persisted.
- [ ] Progress is updated only after valid results.
- [ ] Lesson AI uses current lesson context.
- [ ] Internal retrieval precedes external fallback.
- [ ] Conversation messages are persisted.
- [ ] AI generation creates persistent drafts.
- [ ] Documents require review before indexing.
- [ ] Rejected raw files are retained.
- [ ] Published lessons can feed the Knowledge Index.
- [ ] Lesson knowledge can be reprocessed after edits.
- [ ] Password reset flows through Auth and Email Service.
- [ ] Statistics are calculated from application data.

---

# 20. Expected Deliverable

```text
docs/system-design/
└── step-1.4-end-to-end-data-flow.md
```

No executable implementation required.

Next Step:

**Step 1.5 — Repository / Module Structure**