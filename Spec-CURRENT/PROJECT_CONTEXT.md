# PROJECT_CONTEXT — LLM + RAG Web App học tiếng Trung

## 1. Project Goal

Xây dựng một web application cho người Việt bắt đầu học tiếng Trung từ số 0, với curriculum có cấu trúc từ Pronunciation Foundations đến HSK 1–3.

Mục tiêu kỹ thuật của project là xây một hệ thống end-to-end có giá trị học tập cao cho Data Engineering / AI Engineering Intern, nhưng không over-engineer.

Core product mental model:

```text
Structured Learning Platform
+
AI Learning Assistant
```

AI hỗ trợ curriculum; AI không thay thế curriculum.

## 2. Users

MVP có hai role:

```text
LEARNER
ADMIN
```

Learner học theo progression tuần tự, làm exercise/test, nhận AI assistance và lưu progress.

Admin quản lý curriculum/content, document knowledge, assessment content và dùng AI như authoring assistant.

## 3. MVP Learning Flow

```text
Pronunciation Foundations
        ↓
HSK Curriculum
        ↓
Lesson
        ↓
Vocabulary + Grammar
        ↓
Exercise / Periodic Test
        ↓
Evaluation
        ↓
Progression / Unlock
```

Lesson pass threshold hiện tại:

```text
exercise_score >= 90%
```

Learner có thể retry; một lần pass không bị đảo ngược bởi attempt thấp hơn sau đó.

Standalone General/Global Chat không thuộc MVP. Learner AI chat là lesson-aware.

## 4. AI Capabilities in MVP

Ba capability chính:

1. Lesson-aware RAG chat.
2. Free-form AI grading.
3. AI-assisted exercise/test generation cho admin.

RAG phải dựa trên usable evidence, không được coi việc vector search trả candidate là bằng chứng đủ tốt.

Internal knowledge retrieval được implement/validate trước. Trusted external retrieval là nhánh sau, chỉ được bật khi provider + domain allowlist đã được PM chốt.

## 5. High-Level Architecture

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
   PostgreSQL         AI Layer        File Storage
   + pgvector            │                 │
              ┌──────────┼───────┐         ▼
              ▼          ▼       ▼      Ingestion
          Internal    External   LLM        │
          Retrieval   Retrieval Provider    │
              │                            │
              ▼                            │
        Knowledge Index ◀──────────────────┘

Backend → Email Service
```

Frontend không gọi LLM provider trực tiếp.

Backend là **Modular Monolith**, không phải microservices.

## 6. Logical Backend Boundaries

```text
backend/
├── auth/
├── curriculum/
├── exercise/
├── progress/
├── admin/
├── ai/
│   ├── chat/
│   ├── retrieval/
│   ├── grading/
│   ├── generation/
│   ├── prompts/
│   └── providers/
├── ingestion/
├── database/
└── shared/
```

Domain logic phải ở đúng module. Không tạo một generic service layer chứa mọi responsibility.

## 7. Frontend Boundary

Một frontend duy nhất:

```text
frontend/
├── auth/
├── dashboard/
├── curriculum/
├── lesson/
├── exercise/
├── ai-chat/
├── admin/
└── shared/
```

Không tạo hai app riêng cho Learner/Admin trong MVP.

## 8. Data Boundary

Application/transactional data dùng PostgreSQL.

Vector retrieval dùng pgvector trong PostgreSQL cho V0.

Application representation và retrieval representation là hai concerns khác nhau:

```text
Approved Content
      ↓
Knowledge Processing
      ↓
Chunks + Metadata
      ↓
Embeddings
      ↓
pgvector Retrieval Index
```

Uploaded raw documents đi qua ingestion pipeline trước khi knowledge có thể trở thành retrieval-active.

Human approval và machine processing/knowledge activation là state khác nhau; approval không tự động đồng nghĩa retrieval-active.

## 9. V0 Technology Decisions

Các quyết định đã frozen cho baseline:

- Python `>=3.12,<3.13`.
- FastAPI backend.
- `uv` package/environment workflow.
- `pydantic-settings` configuration.
- PostgreSQL.
- async SQLAlchemy + psycopg3 + Alembic.
- pgvector.
- React + TypeScript + Vite.
- `openapi-typescript` cho API type generation.
- TanStack Query cho server state.
- Auth: short-lived JWT access + rotating/revocable refresh tokens trong HttpOnly cookies.
- Password hashing: Argon2id.
- Direct project services cho RAG; không LangChain/LlamaIndex trong V0.
- Embedding baseline: `BAAI/bge-m3` (1024 dimensions), local trước.
- Reranker baseline: `BAAI/bge-reranker-v2-m3`, local trước.
- Dev raw storage: local file storage sau abstraction.
- Không queue/worker mặc định trong V0.

Authoritative wording nằm ở `PM-Control/04-Decision-Log-and-Open-Gates.md`.

## 10. Architecture Decisions for Simplicity

```text
Same-site logical web topology
One LLM provider + one model at a time for V0
Internal RAG first; external trusted retrieval later
Local embedding/reranker first; benchmark before production decision
Synchronous ingestion first; default max upload 20 MB; measure before queue/worker
Cloud/vendor selections deferred to deployment phase
```

Concrete LLM provider/model chỉ được chọn ngay trước Step 6.7 theo requirement, cost, structured-output support và latency.

## 11. Engineering Principles

```text
Problem
→ Concept
→ Mental Model
→ Data Flow
→ Design
→ Tool
→ Implementation
→ Test
→ Review
```

Và:

```text
Simplest working version
→ observe limitation
→ measure
→ introduce complexity only when justified
```

Không tự thêm technology/service dành cho tương lai.

## 12. Codex Execution Contract

Codex phải:

- implement đúng một frozen Step mỗi task;
- không tự đổi architecture/product scope;
- không implement future Steps opportunistically;
- không thêm framework/service/dependency ngoài scope nếu không được spec yêu cầu;
- tuân thủ current Step + dependencies + Decision Log;
- chạy tests/verification được task chỉ định;
- báo rõ deviations/blockers thay vì tự invent architecture.

Nếu Codex task conflict với Step Specification, Step Specification thắng. Nếu Step Specification conflict với Decision Log mới hơn, dừng và đưa về PM để re-freeze Step.

## 13. Current Project State

```text
Phase 0–2: design foundation reviewed/frozen
Phase 3: implementation begins
Current Wave: Wave 1
First executable Step: 3.1 — Backend Skeleton
```

Future Steps chỉ được mở sau PM acceptance của dependency cần thiết.
