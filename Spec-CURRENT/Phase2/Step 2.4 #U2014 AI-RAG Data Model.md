# Step 2.4 — AI/RAG Data Model

## Goal

Define the physical/logical data model required for internal RAG knowledge.

The design must support:

- uploaded documents;
- published lesson content;
- chunking;
- embeddings;
- versioning;
- safe re-indexing;
- vector retrieval;
- citation;
- retrieval tracing;
- future evaluation.

Do not implement retrieval algorithms, reranking, prompts or generation behavior in this step.

---

# KnowledgeSource

Use one common abstraction:

```text
knowledge_sources
```

Required fields:

```text
id UUID PK
source_type TEXT NOT NULL
document_id UUID NULL FK → documents.id
lesson_id UUID NULL FK → lessons.id
created_at
updated_at
```

Supported source types:

```text
DOCUMENT
LESSON
```

Constraints:

```text
DOCUMENT
→ document_id NOT NULL
→ lesson_id NULL

LESSON
→ lesson_id NOT NULL
→ document_id NULL
```

Do not use a polymorphic generic `source_id` without real foreign keys.

One Lesson maps logically to one KnowledgeSource.

Do not create a separate KnowledgeSource for every vocabulary or grammar record.

---

# KnowledgeVersion

Use:

```text
knowledge_versions
```

Required logical fields:

```text
id UUID PK
knowledge_source_id UUID NOT NULL FK
version_number INTEGER NOT NULL
status TEXT NOT NULL

chunking_strategy TEXT
chunk_size INTEGER
chunk_overlap INTEGER

created_at
activated_at NULL
```

Statuses:

```text
PROCESSING
ACTIVE
SUPERSEDED
FAILED
```

Require logical uniqueness:

```text
UNIQUE(
  knowledge_source_id,
  version_number
)
```

Only one version per KnowledgeSource may be ACTIVE at a time.

---

# Safe Version Activation

Never destroy or deactivate current production knowledge before a replacement version is successfully processed.

Required flow:

```text
Current Version ACTIVE

Create New Version PROCESSING
→ extract/transform
→ chunk
→ embed all required chunks

if successful:
    New Version → ACTIVE
    Previous Version → SUPERSEDED

if failed:
    New Version → FAILED
    Previous Version remains ACTIVE
```

A partially processed version must never become active.

---

# Chunk

Use:

```text
chunks
```

Required fields:

```text
id UUID PK
knowledge_version_id UUID NOT NULL FK

content TEXT NOT NULL
content_type TEXT NOT NULL
chunk_index INTEGER NOT NULL

token_count INTEGER NULL

page_number INTEGER NULL
section TEXT NULL
lesson_id UUID NULL FK

metadata JSONB NULL

created_at
```

Constraint:

```text
UNIQUE(
  knowledge_version_id,
  chunk_index
)
```

---

# Chunk Content Type

Supported V0 values:

```text
DOCUMENT_TEXT
VOCABULARY
GRAMMAR
LESSON_GENERAL
```

`source_type` and `content_type` must remain separate concepts.

Example:

```text
knowledge_source.source_type = LESSON
chunk.content_type = VOCABULARY
```

Do not add speculative content types without an actual product requirement.

---

# Chunk Metadata

Prefer explicit relational columns for metadata that is commonly filtered, inspected or cited:

```text
content_type
page_number
section
lesson_id
```

Use:

```text
metadata JSONB
```

for less stable auxiliary metadata only.

Do not place all chunk metadata inside one opaque JSON object.

---

# Chunking Configuration

Store the configuration used to produce a version on KnowledgeVersion:

```text
chunking_strategy
chunk_size
chunk_overlap
```

Do not create explicit database relationships between overlapping chunks.

Use `chunk_index` to preserve source ordering.

---

# EmbeddingProfile

Use:

```text
embedding_profiles
```

instead of marking individual embedding rows as active.

Required logical fields:

```text
id UUID PK
provider TEXT NOT NULL
model_name TEXT NOT NULL
model_version TEXT NULL
dimensions INTEGER NOT NULL
status TEXT NOT NULL
created_at
```

Initial status model:

```text
ACTIVE
INACTIVE
```

Retrieval must use the configured active profile.

Do not hard-code embedding provider/model across retrieval code.

---

# Embedding

Use:

```text
embeddings
```

Required fields:

```text
id UUID PK
chunk_id UUID NOT NULL FK → chunks.id
embedding_profile_id UUID NOT NULL FK → embedding_profiles.id
vector VECTOR NOT NULL
created_at
```

Constraint:

```text
UNIQUE(
  chunk_id,
  embedding_profile_id
)
```

A Chunk may have multiple embeddings generated using different EmbeddingProfiles.

Do not overwrite historical embeddings when changing model/profile.

---

# Vector Storage

MVP physical architecture:

```text
PostgreSQL
+
vector capability
```

Do not introduce a standalone vector-database service.

A PostgreSQL vector extension such as pgvector is an acceptable implementation for the approved architecture.

Keep logical separation between:

```text
Application Data
Knowledge/Retrieval Data
```

even when both are physically stored in PostgreSQL.

---

# Document Knowledge Flow

Only approved documents may become active internal knowledge.

Required flow:

```text
Document upload
→ processing
→ preview
→ Admin approval
→ KnowledgeSource
→ KnowledgeVersion PROCESSING
→ Chunk
→ Embedding
→ KnowledgeVersion ACTIVE
```

Rejected documents must not have active retrieval knowledge.

---

# Lesson Knowledge Flow

Published Lesson content is an internal knowledge source.

Required flow:

```text
Lesson PUBLISHED
→ KnowledgeSource
→ KnowledgeVersion
→ Chunk
→ Embedding
→ ACTIVE
```

When a published lesson changes:

```text
Lesson updated
→ create new KnowledgeVersion
→ process
→ safely activate
```

Existing learner progress must not be reset.

---

# Citation Source of Truth

Internal citation must remain traceable through:

```text
Chunk
→ KnowledgeVersion
→ KnowledgeSource
→ Document / Lesson
```

Document citation may expose:

```text
source name
page
section
```

Lesson citation may expose:

```text
HSK/lesson identity
content type
section
```

Do not duplicate source identity unnecessarily inside generated AI output.

---

# MessageRetrieval

Persist RAG retrieval traces:

```text
message_retrievals
```

Required logical fields:

```text
id UUID PK
message_id UUID NOT NULL FK → messages.id
chunk_id UUID NOT NULL FK → chunks.id

rank INTEGER NOT NULL
retrieval_score NUMERIC NULL
rerank_score NUMERIC NULL

created_at
```

This table is required for future:

- debugging;
- retrieval evaluation;
- generation-vs-retrieval failure analysis;
- observability.

`rerank_score` may remain NULL until reranking is implemented.

---

# Message Citation

Continue using the canonical `message_citations` model from Step 2.3.

Support:

```text
source_kind = INTERNAL_CHUNK
source_kind = EXTERNAL_URL
```

Internal citations use nullable `chunk_id` plus snapshotted display provenance. External citations use trusted URL/domain provenance from the runtime source map. `source_label` is message-local (`S1..Sn`) and must be unique per assistant message.

Step 6.10 owns citation parsing/validation and may reconcile the physical table through a forward migration if implementation history requires it; it must not introduce a second incompatible citation representation.

---

# External Retrieval Policy

External retrieval is request-scoped by default.

Required behavior:

```text
Internal Knowledge insufficient
→ External Retrieval
→ use result for current response
→ persist citation as needed
```

Do not automatically:

```text
External page
→ Chunk
→ Embedding
→ permanent internal KB
```

External content may become internal knowledge only through the normal ingestion + admin approval workflow.

---

# Failure Rules

If embedding generation fails for only part of a KnowledgeVersion:

```text
KnowledgeVersion → FAILED
```

Do not expose partially indexed versions to production retrieval.

Keep the previous ACTIVE version available.

---

# Logical Model

```text
Document ─────────┐
                  │
Lesson ───────────┤
                  ↓
           KnowledgeSource
                  │
                  ↓
           KnowledgeVersion
                  │
                  ↓
                Chunk
                  │
                  ↓
              Embedding
                  │
                  ↓
          EmbeddingProfile
```

Runtime trace:

```text
Message
├── MessageRetrieval ── Chunk
└── MessageCitation
```

External knowledge:

```text
External Retrieval
→ MessageCitation
```

without automatic permanent indexing.

---

# Constraints

Do not:

- create separate retrieval pipelines with incompatible data models for Document and Lesson;
- create KnowledgeSource for every vocabulary/grammar item;
- overwrite active chunks during re-index;
- activate partially processed versions;
- put all metadata into JSONB;
- overwrite embeddings when changing embedding model;
- permanently index external retrieval results automatically;
- introduce a standalone vector database;
- implement reranking in this step.

---

# Acceptance Criteria

- [ ] Document and Lesson use a shared KnowledgeSource model.
- [ ] Source relations preserve real foreign keys.
- [ ] Knowledge versions are retained.
- [ ] Only fully processed versions become ACTIVE.
- [ ] Previous ACTIVE version remains available during re-indexing.
- [ ] Chunk content and ordering are persisted.
- [ ] Chunk source/citation metadata is recoverable.
- [ ] Chunk content type is represented.
- [ ] Chunking configuration is reproducible.
- [ ] Multiple embedding models/profiles are supported.
- [ ] Embeddings are not overwritten when model changes.
- [ ] Vector data can live in PostgreSQL.
- [ ] Retrieval traces can be persisted per AI message.
- [ ] Reranking score can be added later without schema redesign.
- [ ] Internal citations are source-traceable.
- [ ] External retrieval stays request-scoped by default.
- [ ] Failed/partial indexing cannot replace active knowledge.

---

# Expected Deliverable

```text
docs/data/
└── step-2.4-ai-rag-data-model.md
```

Next Step:

**Step 2.5 — Migration & Seed Strategy**