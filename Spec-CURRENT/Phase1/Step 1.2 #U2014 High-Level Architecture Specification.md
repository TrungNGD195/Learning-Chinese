# Step 1.2 — High-Level Architecture Specification

## 1. Project Context

Project là web application học tiếng Trung cho người Việt từ zero đến HSK 3.

Có hai role:

- Learner
- Admin

Core product gồm:

- Pronunciation Foundations
- HSK curriculum
- Vocabulary / Grammar
- Lesson Exercises
- Periodic Tests
- Learning Progress
- Lesson-aware AI
- AI grading
- AI exercise/test generation
- Document-based Knowledge Base

Expected MVP load: 10–50 concurrent users.

---

# 2. Step Goal

Định nghĩa High-Level Architecture V0.

Step này chỉ xác định:

- major internal components;
- high-level communication;
- logical boundaries.

Không implement application code và chưa chọn concrete technology stack.

---

# 3. Approved Architecture

```text
                     Frontend
                  Learner + Admin
                         │
                         ▼
                 Backend Application
                  Modular Monolith
                         │
       ┌─────────────────┼─────────────────┐
       ▼                 ▼                 ▼
   Main Database      AI Layer        File Storage
                         │                 │
              ┌──────────┼───────┐         ▼
              ▼          ▼       ▼      Ingestion
          Internal    External   LLM        │
          Retrieval   Retrieval Provider    │
              │                            │
              ▼                            │
        Knowledge Index ◀──────────────────┘

Backend → Email Service
```

---

# 4. Frontend

Use one frontend application.

```text
Frontend
├── Learner UI
└── Admin UI
```

Learner/Admin capability is separated by role/authorization.

Do not create two independent applications for MVP.

Frontend must not call LLM providers directly.

---

# 5. Backend

Use a Modular Monolith architecture for MVP.

Logical modules currently include:

```text
Backend
├── Auth
├── Curriculum
├── Exercise / Test
├── Progress
├── Admin
└── AI
```

These are logical module boundaries inside one backend application.

Do not create microservices at this stage.

---

# 6. Main Database

One primary relational data store is expected for application/transactional data such as:

- users;
- curriculum;
- lessons;
- vocabulary;
- grammar;
- exercises/tests;
- attempts;
- progress;
- conversations;
- document metadata.

No database product has been selected yet.

---

# 7. Application Data vs Knowledge Data

Do not treat lesson/application representation and retrieval representation as identical.

Application data is structured for product behavior/UI.

Example:

```text
Vocabulary:
character
pinyin
meaning
part_of_speech
examples
```

Knowledge data is transformed for retrieval.

Conceptual example:

```text
Chunk:
text suitable for semantic retrieval

Metadata:
lesson
content_type
source
location
```

Flow may be:

```text
Approved Lesson Content
→ Knowledge Processing
→ Retrieval Representation
→ Knowledge Index
```

The same source knowledge may therefore have both application and retrieval representations.

---

# 8. Knowledge Index

Maintain a logical Knowledge Index component for:

- processed knowledge;
- chunks;
- embeddings;
- retrieval index;
- source metadata.

This is a logical architecture boundary only.

It does not require a separate physical database or service.

The final storage technology will be decided later.

---

# 9. File Storage

Uploaded raw files require persistent file storage.

Supported current formats:

```text
PDF
DOCX
TXT
MD
```

Architecture should refer to this capability as:

```text
File Storage
```

Do not decide yet whether it uses:

- local filesystem;
- object storage;
- another implementation.

---

# 10. Ingestion Pipeline

Document processing is a separate logical process/module.

Required high-level flow:

```text
Upload
→ File Storage
→ Extract
→ Clean / Transform
→ Preview
→ Admin Approval
→ Knowledge Index
```

Only approved content may enter active knowledge.

Do not deploy ingestion as an independent microservice unless a later Step requires it.

---

# 11. AI Layer

All product AI operations go through an AI layer controlled by the backend.

Logical capabilities:

```text
AI Layer
├── Lesson Q&A
├── Free-form Grading
├── Exercise/Test Generation
└── Retrieval
```

The AI layer may call an external LLM provider.

Business modules should not contain provider-specific LLM calls scattered throughout the codebase.

---

# 12. RAG

RAG belongs logically to the AI layer.

High-level flow:

```text
Question
→ AI Layer
→ Internal Retrieval
→ Knowledge Index
→ Context
→ LLM Provider
→ Answer
```

RAG is not a standalone service in MVP.

---

# 13. External Retrieval

When internal knowledge is insufficient:

```text
Internal Retrieval
→ Insufficient
→ External Retrieval
→ Trusted Sources
→ LLM
```

External provider is not selected yet.

Internal relevant knowledge must remain preferred.

---

# 14. Exercise Grading

Required high-level flow:

```text
Learner Answer
→ Exercise Module

Objective Question
→ Deterministic Grading

Free-form Question
→ AI Grading

→ Final Result
→ Progress Module
```

Do not send objective questions to LLM when deterministic grading is sufficient.

---

# 15. Progression Logic

Lesson/test completion and unlock decisions must be controlled by backend business logic.

```text
Exercise/Test Result
→ Progress Logic
→ Determine Completion
→ Determine Unlock
→ Persist State
→ Return Updated State
```

Frontend must not be authoritative for progress/unlock state.

Existing rules remain:

- lesson theory complete + score >=90% → lesson complete;
- periodic test score >=90% → test complete;
- progression is sequential.

---

# 16. Email

Password reset flow:

```text
Frontend
→ Backend
→ Email Service
```

No email provider selected.

---

# 17. Background Processing

Do not introduce a background worker component yet.

Long-running ingestion or AI generation may require it later, but it is currently only an identified future possibility.

---

# 18. External Dependencies

Current external dependencies:

- LLM Provider
- External Knowledge Retrieval
- Email Service

File Storage is represented as a logical storage capability; its deployment form remains undecided.

---

# 19. Constraints

Preserve:

- one frontend application;
- one modular-monolith backend;
- server-controlled AI;
- server-controlled progression;
- internal knowledge priority;
- Admin approval before publishing generated content;
- Admin approval before activating uploaded knowledge;
- architecture appropriate for 10–50 concurrent users.

Do not add unnecessary:

- microservices;
- message brokers;
- distributed infrastructure;
- independent RAG service;
- background workers;

without a later requirement.

---

# 20. Technology Decisions Not Yet Made

Do not select in this Step:

- frontend framework;
- backend framework;
- relational database product;
- vector database/vector extension;
- LLM provider;
- external retrieval provider;
- file storage implementation;
- email provider;
- hosting provider.

---

# 21. Acceptance Criteria

Step is complete when architecture clearly contains:

- [ ] one Frontend;
- [ ] Modular Monolith Backend;
- [ ] Main Database;
- [ ] AI Layer;
- [ ] Knowledge Index;
- [ ] File Storage;
- [ ] Ingestion Pipeline;
- [ ] LLM Provider;
- [ ] External Retrieval;
- [ ] Email Service;
- [ ] server-side grading/progression;
- [ ] distinction between application data and retrieval data;
- [ ] no premature microservice or infrastructure complexity.

---

# 22. Expected Deliverable

```text
docs/system-design/
├── step-1.1-system-context.md
└── step-1.2-high-level-architecture.md
```

No executable implementation is required.

Next Step:

**Step 1.3 — Component Responsibilities**