# Step 1.1 — System Context Specification

## 1. Purpose

Document này định nghĩa System Context V0 cho web application học tiếng Trung dành cho người Việt.

Mục tiêu là xác định:

- system boundary;
- external actors;
- external dependencies;
- high-level interaction rules.

Không implement application code trong Step này.

Không phân rã internal system thành detailed components tại Step này.

---

# 2. Product Context

Product là một web application dành cho người Việt bắt đầu học tiếng Trung từ số 0 đến HSK 3.

Core product:

```text
Pronunciation Foundations
→ HSK Curriculum
→ Vocabulary
→ Grammar
→ Exercise
→ Periodic Tests
→ AI Assistance
```

Có hai role:

```text
Learner
Admin
```

AI hỗ trợ:

- lesson Q&A;
- vocabulary/grammar explanation;
- free-form grading;
- admin exercise generation;
- admin test generation.

---

# 3. System of Interest

System of interest được gọi conceptual là:

```text
Chinese Learning Web System
```

System này bao gồm toàn bộ product responsibility.

Internal decomposition chưa được định nghĩa chính thức tại Step này.

Conceptually system eventually contains capabilities such as:

- web interface;
- application/backend logic;
- persistent application data;
- AI/RAG;
- knowledge ingestion;
- knowledge storage.

Không coi các item trên là final component architecture tại Step 1.1.

---

# 4. External Actor — Learner

Learner tương tác với Chinese Learning Web System.

Learner capabilities đã được chốt gồm:

- register/login;
- reset password;
- view dashboard;
- complete Pronunciation Foundations;
- access sequential HSK curriculum;
- learn vocabulary;
- learn grammar;
- complete exercises;
- complete periodic tests;
- receive grading/feedback;
- ask lesson-aware AI;
- view learning progress;
- view attempt history;
- view AI conversation history;
- manage basic profile.

Learner không trực tiếp giao tiếp với external LLM provider.

---

# 5. External Actor — Admin

Admin sử dụng cùng Chinese Learning Web System.

Admin capabilities:

- manage HSK/course;
- manage lesson;
- manage vocabulary;
- manage grammar;
- create lesson exercises;
- create periodic tests;
- generate exercises/tests using AI;
- review/edit AI-generated drafts;
- approve/publish content;
- upload documents;
- review extracted documents;
- approve documents for active knowledge;
- view Admin Dashboard statistics.

Admin không trực tiếp gọi LLM provider ngoài application.

---

# 6. One Web Application

MVP sử dụng một web application chung cho Learner và Admin.

Conceptual model:

```text
Chinese Learning Web Application
├── Learner Experience
└── Admin Experience
```

Access được phân biệt bằng role/authorization.

Không xây hai independent applications trong MVP.

---

# 7. LLM Provider Boundary

LLM runtime ban đầu dự kiến sử dụng external API.

System architecture trong các Step sau phải tránh coupling business logic trực tiếp vào một specific provider khi hợp lý.

Conceptual flow:

```text
Chinese Learning System
        ↓
AI Capability Layer
        ↓
LLM Provider
```

Initial deployment có thể sử dụng một provider.

Future architecture nên cho phép đổi provider mà không rewrite core learning/business logic.

Không chọn provider cụ thể trong Step 1.1.

---

# 8. Browser-to-LLM Rule

Frontend/browser không được gọi external LLM provider trực tiếp.

All AI interactions phải đi:

```text
Browser
→ Chinese Learning Backend/System
→ AI Capability
→ LLM Provider
```

Lý do architectural requirement:

- server controls credentials;
- server controls lesson context;
- server controls prompts;
- server controls grading behavior;
- server controls domain restrictions;
- server controls usage/rate limits;
- server can log/evaluate AI behavior later.

---

# 9. Learner AI Chat Interaction

Conceptual flow:

```text
Learner
→ Web App
→ Chinese Learning System
→ AI/RAG Capability
→ LLM Provider
→ Chinese Learning System
→ Web App
→ Learner
```

AI/RAG capability eventually must have access to:

- learner question;
- current lesson context;
- conversation context;
- internal knowledge;
- external knowledge fallback when required.

Detailed architecture is not defined here.

---

# 10. AI Grading Interaction

Free-form exercise grading is server-controlled.

Conceptual flow:

```text
Learner Answer
→ Chinese Learning System
→ AI Grading Capability
→ LLM Provider
→ Structured Grading Result
→ Chinese Learning System
```

Learner must not control direct provider request configuration.

---

# 11. AI Content Generation Interaction

Only Admin can invoke product-level exercise/test generation.

Conceptual flow:

```text
Admin
→ Chinese Learning System
→ AI Content Generation
→ LLM Provider
→ Draft
→ Admin Review/Edit
→ Approve
→ Publish
```

Learner cannot invoke Admin generation capability directly.

---

# 12. External Knowledge Retrieval Boundary

Internal knowledge is preferred for AI Q&A.

When internal knowledge is insufficient and the question remains in allowed Chinese-learning domain:

```text
Chinese Learning System
→ External Knowledge Retrieval
→ Trusted External Sources
→ Chinese Learning System
```

External retrieval may represent:

- search API;
- dictionary API;
- trusted web retrieval;
- combination.

Provider is not selected yet.

System design must treat it as an external dependency/interface.

---

# 13. External Knowledge Requirements

External retrieval must eventually support:

- trusted-source preference;
- source metadata;
- citations;
- fallback behavior.

It must not be assumed that external retrieval is always available.

Detailed failure handling belongs to later design Steps.

---

# 14. Email Service Boundary

MVP supports password reset by email.

Conceptual flow:

```text
Learner
→ Request Password Reset
→ Chinese Learning System
→ Email Service
→ Learner Email
```

Email verification during initial registration is not currently mandatory.

Email provider is not selected.

---

# 15. File Storage Requirement

Admin can upload:

```text
PDF
DOCX
TXT
MD
```

Raw files require persistent storage.

Conceptual flow:

```text
Admin
→ Upload
→ Chinese Learning System
→ File Storage
```

"File Storage" is a logical capability.

Implementation may later be:

- local filesystem;
- object storage;
- another persistent file-storage mechanism.

No storage technology is selected at Step 1.1.

---

# 16. Document Processing Flow

Document processing does not require an external parser service as an architectural requirement.

Conceptual flow:

```text
Admin Upload
→ Chinese Learning System
→ Ingestion Process
→ Extract / Process
→ Admin Preview
→ Admin Approve
→ Knowledge Base
```

Parser libraries/services will be chosen in Data Ingestion phase if needed.

---

# 17. Knowledge Sources

Internal knowledge is expected to be built from:

```text
HSK 1–3 Source Materials
+
Admin Uploaded & Approved Documents
+
Approved Learning/Lesson Content
```

Only approved content is eligible for production knowledge usage.

---

# 18. Application Data vs Retrieval Data

At system-context level, maintain logical distinction between:

## Application / Transactional Data

Examples:

- users;
- roles;
- curriculum;
- lessons;
- progress;
- exercise attempts;
- test attempts;
- conversations;
- document metadata.

## Retrieval-oriented Data

Examples:

- processed knowledge;
- chunks;
- embeddings;
- retrieval index.

This is a logical separation only.

No physical database architecture has been approved.

---

# 19. Monitoring

No external monitoring/analytics provider is required in System Context V0.

Monitoring capability will be designed during Monitoring/LLMOps phases.

Do not add a third-party monitoring platform now.

---

# 20. Hosting Environment

System will eventually require a runtime/hosting environment.

Possible future implementations could include:

- VPS;
- cloud virtual machine;
- managed application platform;
- other hosting infrastructure.

No hosting vendor or deployment architecture is selected at Step 1.1.

Do not make a vendor choice here.

---

# 21. System Context Diagram

Canonical V0 context:

```text
                         Learner
                            │
                            │
                            ▼
                ┌─────────────────────────┐
                │                         │
                │ Chinese Learning        │
                │ Web System              │
                │                         │
                └────────────┬────────────┘
                             ▲
                             │
                           Admin


External dependencies:

Chinese Learning Web System
├── LLM Provider
├── External Knowledge Retrieval
├── Email Service
└── File Storage
```

Hosting environment is infrastructure executing the system, not a product actor.

---

# 22. External Dependency Summary

## LLM Provider

Purpose:

- AI lesson Q&A;
- free-form grading;
- exercise generation;
- test generation.

## External Knowledge Retrieval

Purpose:

- trusted-source fallback when internal KB is insufficient.

## Email Service

Purpose:

- password reset emails.

## File Storage

Purpose:

- persistent storage of admin-uploaded source documents.

No providers are selected.

---

# 23. Current Architecture State

Current system design is only at Context level.

Approved:

```text
System Boundary            YES
Actors                      YES
External Dependencies       YES
Interaction Direction       YES
```

Not yet approved:

```text
Internal Components         NO
Component Responsibilities  NO
Detailed Data Flow          NO
Repository Structure        NO
Physical Database           NO
API Contract                NO
Deployment Topology         NO
```

---

# 24. Technology Decisions Already Made

Only the following design direction is approved:

1. One web application supports Learner and Admin.
2. Role-based access separates their capabilities.
3. Initial LLM usage will be through an external provider/API.
4. AI access is mediated through backend/system logic.
5. Architecture should avoid unnecessary provider lock-in.
6. Internal knowledge may fallback to external knowledge retrieval.
7. Password reset uses email.
8. Uploaded documents require persistent file storage.
9. No specific hosting platform has been selected.
10. No monitoring provider has been selected.

---

# 25. Technology Decisions NOT Made

Do not select:

- frontend framework;
- backend framework;
- LLM provider;
- database;
- vector database;
- ORM;
- external search provider;
- email provider;
- object storage provider;
- document parser;
- cloud/VPS provider;
- monitoring platform.

---

# 26. Constraints

Future component architecture must preserve:

- Learner/Admin role separation;
- single web application for MVP;
- server-controlled AI interactions;
- internal knowledge priority;
- external retrieval fallback;
- source traceability;
- Admin-only content generation;
- human review before publishing;
- document approval before active knowledge use.

Expected MVP load remains:

```text
10–50 concurrent users
```

Do not over-engineer architecture for massive scale.

---

# 27. Things That Must Not Change

Without explicit Product Owner decision, future implementation must not:

1. Split Learner and Admin into unrelated products.
2. Allow browser to expose LLM API credentials.
3. Allow learner to invoke Admin AI-generation features.
4. Bypass backend/domain logic for AI grading.
5. Automatically publish generated content.
6. Automatically activate uploaded documents without Admin approval.
7. Treat external knowledge as preferred over relevant internal lesson/KB knowledge.
8. Add new external dependencies without a justified requirement.

---

# 28. Edge Cases for Later Design

Later Steps must consider:

- LLM provider unavailable;
- external retrieval unavailable;
- email provider failure;
- file storage failure;
- uploaded file lost/corrupted;
- provider timeout;
- provider rate limit;
- switching LLM provider;
- internal KB insufficient;
- source disagreement.

Do not solve these in Step 1.1.

---

# 29. Acceptance Criteria

Step 1.1 is complete when:

- [ ] System of interest is defined.
- [ ] Learner is identified as external actor.
- [ ] Admin is identified as external actor.
- [ ] Learner/Admin use one web application.
- [ ] LLM Provider is identified as external dependency.
- [ ] External Knowledge Retrieval is identified as external dependency.
- [ ] Email Service is identified as external dependency.
- [ ] File Storage requirement is identified.
- [ ] Browser-to-LLM direct access is prohibited.
- [ ] AI grading is server-controlled.
- [ ] Admin AI generation is server-controlled.
- [ ] Internal knowledge sources are identified.
- [ ] Hosting provider remains undecided.
- [ ] Monitoring provider remains undecided.
- [ ] No premature technology stack selection is made.

---

# 30. Verification Checklist

Before closing Step:

- [ ] Exactly two product roles remain: Learner and Admin.
- [ ] One web app remains the MVP direction.
- [ ] Role separation is preserved.
- [ ] LLM provider remains replaceable at design level.
- [ ] No LLM API key is expected in frontend.
- [ ] External retrieval exists only as a logical dependency.
- [ ] Password reset email dependency exists.
- [ ] File storage exists as a logical requirement.
- [ ] Local vs object storage remains unresolved.
- [ ] Database technology remains unresolved.
- [ ] Vector technology remains unresolved.
- [ ] Hosting remains unresolved.
- [ ] Monitoring provider remains unresolved.

---

# 31. Expected Deliverable

Recommended documentation:

```text
docs/system-design/
└── step-1.1-system-context.md
```

No executable application implementation is required.

---

# 32. State After Step 1.1

```text
Phase 0 — Product Definition        COMPLETE

Phase 1 — System Design

1.1 System Context                 COMPLETE
1.2 High-Level Architecture        NEXT
1.3 Component Responsibilities     NOT YET
1.4 End-to-End Data Flow           NOT YET
1.5 Repository / Module Structure  NOT YET
```

Next Step:

**Step 1.2 — High-Level Architecture**

Step 1.2 must use this System Context as input and decompose the Chinese Learning Web System into its major internal components.