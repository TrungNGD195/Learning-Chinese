# Step 1.3 — Component Responsibilities

## 1. Project Context

Project là web app học tiếng Trung cho người Việt từ zero đến HSK 3.

Architecture hiện tại:

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

Step này chỉ định nghĩa ownership/boundary của component. Không implement code.

---

# 2. Component Responsibilities

## Frontend

Responsible for:

- UI rendering;
- user input;
- API calls;
- loading/error/result display;
- temporary UI state.

Must not be authoritative for:

- grading;
- lesson/test completion;
- unlocking;
- authorization;
- learning progress.

---

## Auth Module

Responsible for:

- register/login/logout;
- reset-password workflow;
- password security;
- authentication;
- learner/admin roles.

Not responsible for curriculum or progress.

---

## Curriculum Module

Responsible for:

- HSK;
- lessons;
- curriculum order;
- vocabulary;
- grammar;
- published/unpublished state.

Does not own learner progress.

---

## Exercise/Test Module

Responsible for:

- questions and answers;
- deterministic grading;
- requesting AI grading for free-form answers;
- calculating final score;
- storing attempts.

After grading, it provides results to Progress.

It must not directly unlock curriculum units.

---

## Progress Module

Responsible for:

- pronunciation foundation completion;
- theory completion;
- lesson completion;
- test completion;
- current HSK/current lesson;
- progress percentage;
- unlock decisions.

Existing rules:

```text
lesson:
theory complete + score >= 90%
→ complete

test:
score >= 90%
→ complete
```

Progress business rules must remain server-side.

---

## Admin Module

Responsible for orchestrating Admin workflows:

- content management;
- AI generation requests;
- draft review/edit;
- approval/publish;
- document approval;
- basic statistics.

Actual lesson content remains owned by Curriculum.

---

## AI Layer

Responsible for AI-specific capabilities:

- lesson-aware Q&A;
- retrieval/RAG orchestration;
- external knowledge fallback;
- free-form grading;
- exercise/test generation;
- LLM provider abstraction.

AI Layer must not:

- unlock lessons;
- mark progress complete directly;
- publish generated content;
- bypass Admin approval.

---

## Ingestion Module

Responsible for:

```text
Raw File
→ Extract
→ Clean / Normalize
→ Preview
→ Prepare Knowledge
```

Content must not enter active Knowledge Index until Admin approval.

---

## Knowledge Index

Responsible for:

- retrieval-oriented knowledge;
- chunk/vector representation;
- searching relevant chunks;
- returning source metadata.

It does not generate final AI answers.

---

## Main Database

Responsible for persistent application state.

Business decisions belong to backend modules, not the database itself.

---

## File Storage

Responsible only for persistent raw uploaded files and file retrieval.

Parsing/extraction belongs to Ingestion.

---

## Email Service

Responsible only for email delivery.

Auth module owns:

- when password reset is allowed;
- token generation/validation;
- reset workflow.

---

# 3. Required Interaction Rules

## Objective Grading

```text
Answer
→ Exercise/Test
→ Deterministic Grading
→ Result
```

## Free-form Grading

```text
Answer
→ Exercise/Test
→ AI Layer
→ LLM
→ Structured Grade
→ Exercise/Test
→ Final Score
```

AI must not control the 90% progression rule.

## Progress

```text
Final Result
→ Progress
→ Complete/Unlock Decision
→ Persist
```

## AI Q&A

```text
Frontend
→ Backend
→ AI Layer
→ Knowledge Retrieval
→ LLM
→ Backend
→ Frontend
```

## Document Processing

```text
Upload
→ File Storage
→ Ingestion
→ Preview
→ Admin Approval
→ Knowledge Index
```

## AI Content Generation

```text
Admin
→ AI Layer
→ Draft
→ Admin Review/Edit
→ Curriculum
→ Publish
```

---

# 4. Admin Statistics

Do not create a dedicated analytics service for MVP.

Backend may calculate directly:

- total users;
- total lessons;
- total tests;
- users by HSK;
- average exercise score.

---

# 5. Constraints

Do not:

- move business rules into frontend;
- let AI modify progress directly;
- let AI publish content;
- let Ingestion activate knowledge without approval;
- let Knowledge Index generate answers;
- duplicate ownership of the same business rule across modules;
- introduce microservices or new infrastructure.

---

# 6. Technology Decisions

No technology selection in this Step.

Do not select or change:

- framework;
- database;
- vector store;
- LLM provider;
- storage provider;
- deployment environment.

---

# 7. Acceptance Criteria

- [ ] Every major component has a clear responsibility.
- [ ] Frontend is not authoritative for business rules.
- [ ] Exercise/Test owns scoring.
- [ ] Progress owns completion/unlock.
- [ ] AI Layer owns AI behavior only.
- [ ] Curriculum owns learning content.
- [ ] Admin owns approval workflows.
- [ ] Ingestion prepares knowledge but cannot activate it automatically.
- [ ] Knowledge Index performs retrieval only.
- [ ] File Storage only stores files.
- [ ] Responsibility duplication is avoided.

---

# 8. Expected Deliverable

```text
docs/system-design/
└── step-1.3-component-responsibilities.md
```

No executable implementation required.

Next Step:

**Step 1.4 — End-to-End Data Flow**