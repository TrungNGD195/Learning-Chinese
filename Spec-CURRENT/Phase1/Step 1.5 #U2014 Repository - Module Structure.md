# Step 1.5 — Repository / Module Structure

## 1. Project Context

Project là web app học tiếng Trung cho người Việt từ zero đến HSK 3.

Architecture V0 sử dụng:

- một Frontend;
- một Modular Monolith Backend;
- Main Database;
- AI Layer;
- Knowledge Index;
- File Storage;
- Ingestion;
- external LLM / retrieval / email dependencies.

Backend responsibility boundaries đã được chốt:

- Auth
- Curriculum
- Exercise/Test
- Progress
- Admin
- AI
- Ingestion

Mục tiêu Step này chỉ là định nghĩa logical repository structure. Không implement business feature.

---

# 2. Required Repository Structure

Sử dụng một repository:

```text
chinese-learning-app/
│
├── frontend/
│   ├── auth/
│   ├── dashboard/
│   ├── curriculum/
│   ├── lesson/
│   ├── exercise/
│   ├── ai-chat/
│   ├── admin/
│   └── shared/
│
├── backend/
│   ├── auth/
│   ├── curriculum/
│   ├── exercise/
│   ├── progress/
│   ├── admin/
│   ├── ai/
│   │   ├── chat/
│   │   ├── retrieval/
│   │   ├── grading/
│   │   ├── generation/
│   │   ├── prompts/
│   │   └── providers/
│   ├── ingestion/
│   ├── database/
│   └── shared/
│
├── data/
│   ├── samples/
│   └── seeds/
│
└── docs/
    ├── product/
    └── system-design/
```

Concrete framework may later require additional framework-specific files/directories, but the logical boundaries above must remain recognizable.

---

# 3. Frontend Rules

Organize frontend primarily by feature.

Do not create completely separate Learner and Admin applications.

Admin-only functionality belongs under:

```text
frontend/admin/
```

Cross-feature reusable code may live under:

```text
frontend/shared/
```

Do not use `shared/` as a generic dumping directory.

---

# 4. Backend Rules

Backend is a Modular Monolith.

Domain logic must stay within the appropriate module.

Examples:

```text
authentication → auth/

HSK/lesson/vocabulary/grammar → curriculum/

exercise score/attempts → exercise/

completion/unlock → progress/

admin approval workflows → admin/

LLM/RAG behavior → ai/

document processing → ingestion/
```

Do not move unrelated responsibilities into one generic service/module.

---

# 5. AI Module

Maintain separate AI capabilities:

```text
ai/
├── chat/
├── retrieval/
├── grading/
├── generation/
├── prompts/
└── providers/
```

Expected responsibility:

- `chat/`: lesson-aware AI Q&A workflow.
- `retrieval/`: internal/external retrieval orchestration.
- `grading/`: free-form answer evaluation.
- `generation/`: exercise/test generation.
- `prompts/`: AI prompt definitions/templates.
- `providers/`: LLM provider integration/abstraction.

Do not scatter direct LLM provider calls across Curriculum, Exercise, Progress or Admin modules.

---

# 6. Ingestion

Keep ingestion inside backend for V0:

```text
backend/ingestion/
```

It remains a logical process/module, not a standalone service.

It will eventually own:

```text
File
→ Extract
→ Clean/Normalize
→ Prepare Knowledge
```

Do not introduce a separate ingestion microservice.

---

# 7. Database Organization

Use:

```text
backend/database/
```

for shared database infrastructure such as:

- connection/configuration;
- migration infrastructure;
- shared database setup.

Domain-specific queries/repositories should remain near the corresponding domain module when practical.

Example:

```text
curriculum/
→ curriculum data access

progress/
→ progress data access
```

Avoid one giant centralized data-access layer containing every query in the application.

---

# 8. Development Data

Use:

```text
data/
├── samples/
└── seeds/
```

for development/sample data only.

Must not commit:

- production learner data;
- credentials/secrets;
- private data;
- copyrighted source textbooks unless repository usage rights explicitly permit it.

---

# 9. Documentation

Current documentation structure:

```text
docs/
├── product/
└── system-design/
```

Do not pre-create future areas such as:

```text
evaluation/
monitoring/
infra/
docker/
```

They should be added only when the corresponding project Phase begins.

---

# 10. Testing

Exact test folder convention may depend on the frameworks chosen later.

The eventual test structure should reflect module boundaries rather than mixing all system behaviors together.

Do not make a framework-specific test decision in this Step.

---

# 11. Constraints

Do not:

- split project into multiple repositories;
- create microservice folders;
- create standalone RAG service;
- create standalone ingestion service;
- duplicate AI provider calls across business modules;
- place Progress business rules in Frontend;
- use `shared/` for domain-specific logic;
- create unused future-phase infrastructure.

---

# 12. Technology Decisions Not Made

This Step does not choose:

- frontend framework;
- backend framework;
- package manager;
- relational database;
- ORM;
- vector store;
- LLM provider;
- testing framework;
- Docker/deployment tooling.

Do not infer these choices from the folder structure.

---

# 13. Acceptance Criteria

- [ ] One repository is used.
- [ ] Frontend is feature-based.
- [ ] Learner/Admin remain one web application.
- [ ] Backend module boundaries reflect system design.
- [ ] AI capabilities are separated internally.
- [ ] Provider integration is isolated.
- [ ] Ingestion remains inside Backend.
- [ ] Database infrastructure and domain logic are not unnecessarily mixed.
- [ ] Shared directories contain only reusable code.
- [ ] Development data is separated from source code.
- [ ] No future-phase directories are created without need.

---

# 14. Expected Deliverable

```text
docs/system-design/
└── step-1.5-repository-module-structure.md
```

If a repository skeleton is being created, it should reflect the approved logical structure without implementing application functionality.