# Codex Task — Step 5.1 Define Knowledge Sources

## Task status

FROZEN FOR IMPLEMENTATION after Data Engineering JIT review against the accepted repository snapshot after Step 4.7.

Implement **only Step 5.1 — Define Knowledge Sources**.

Do not implement Step 5.2+ behavior opportunistically.

---

## Context

The repository already contains the Phase 3–4 application foundation and the Phase 2 physical data model. Step 5.1 establishes the source-policy/domain boundary that later raw ingestion will consume.

Current accepted repository facts:

- `backend/app/database/models/document.py` already has `processing_status` and `review_status` as independent state fields.
- `backend/app/database/models/knowledge.py` already has:
  - `KnowledgeSource.source_type` constrained to `DOCUMENT | LESSON`;
  - `KnowledgeVersion.status` constrained to `PROCESSING | ACTIVE | SUPERSEDED | FAILED`;
  - the partial unique index enforcing at most one ACTIVE version per KnowledgeSource.
- `backend/app/database/models/curriculum.py` already constrains `Lesson.status` to `DRAFT | PUBLISHED | ARCHIVED`.
- Current Alembic chain is linear:
  - `0001_initial_schema`
  - `0002_auth_token_tables`
  - `0003_conversation_message_flow` (current head)
- The current `Document` model does **not** contain Step-5.1 provenance/source-policy fields.
- `backend/app/ingestion/__init__.py` exists only as an empty domain boundary.
- There is no Admin Document backend endpoint/schema/service yet.
- `/admin/documents` on the frontend remains structural-only.
- Generated frontend OpenAPI types contain no Document-management contract.
- Expected application errors use `ApplicationError`; FastAPI/Pydantic request validation is normalized globally to `INVALID_REQUEST` with HTTP 422.

---

## Objective

Implement the smallest backend/data foundation needed to make the frozen Step-5.1 source policy explicit, persisted, validated, testable, and directly consumable by Step 5.2.

The Step must answer:

```text
What data are we willing to treat as candidate knowledge?
```

It must **not** acquire raw bytes, parse documents, process documents, chunk content, embed content, activate knowledge, or build the Document frontend workflow.

---

## Frozen source-policy decisions

### KnowledgeSource source type

Preserve exactly:

```text
DOCUMENT
LESSON
```

Do not redesign `KnowledgeSource.source_type`.

Do not create one KnowledgeSource per Vocabulary/Grammar item.

### Document source category

Support exactly:

```text
CURRICULUM_MATERIAL
INTERNAL_AUTHORED
```

Meaning:

```text
CURRICULUM_MATERIAL
→ HSK1–3 textbook/curriculum material

INTERNAL_AUTHORED
→ internally authored/curated note, explanation, or example
```

Do not add categories such as `REFERENCE`, `SUPPLEMENTARY_MATERIAL`, authority tiers, trust levels, or scores.

### Supported source languages

Support exactly:

```text
vi
zh
en
```

### Supported input formats policy

The V0 policy remains:

```text
PDF
DOCX
TXT
MD
```

Step 5.1 may expose these as policy constants/checks for eligibility, but it must not implement upload/file-signature/MIME/raw-storage mechanics. Those belong to Step 5.2.

### Knowledge domain

Candidate internal knowledge must belong to the Chinese-learning domain, including:

- pronunciation;
- vocabulary;
- grammar;
- Chinese language learning;
- culture directly relevant to language usage.

Do not treat general Chinese-related content as eligible by default. Examples outside the domain include general politics, general news, general history, and unrelated travel content.

Do not add an LLM/domain-classifier service.

There is currently no accepted persistent domain-classification field in the repository. Keep domain approval as an explicit input to the source-policy eligibility boundary; do not add a speculative database column for it in Step 5.1.

---

## Current schema reconciliation

### Existing Document physical representation

Current fields:

```text
id
original_filename
file_type
storage_reference
processing_status
review_status
uploaded_by
approved_by
approved_at
created_at
updated_at
```

Current constraints preserve:

```text
processing_status ∈ {
  UPLOADED,
  PROCESSING,
  PREVIEW_READY,
  FAILED
}

review_status ∈ {
  PENDING,
  APPROVED,
  REJECTED
}

review_status = APPROVED
→ processing_status = PREVIEW_READY
→ approved_by IS NOT NULL
→ approved_at IS NOT NULL
```

### Missing Step-5.1 representation

The following required provenance fields have no existing equivalent and must be added:

```text
title
source_category
source_origin
source_language
```

The current repository also has no lightweight usage-rights field; add:

```text
usage_rights_note
```

Do **not** add optional fields that the current repository does not already represent, such as:

```text
author_or_organization
publisher
edition_or_version
original_reference
description
```

Those remain optional future provenance and are not required to complete Step 5.1.

`original_filename` is file-upload metadata and is **not** the canonical Document `title`.

---

## Migration requirement

**Migration required: YES.**

Create exactly one new forward Alembic revision after `0003_conversation_message_flow`.

Expected file name:

```text
backend/migrations/versions/0004_document_source_policy.py
```

Expected revision identity:

```text
revision = "0004_document_source_policy"
down_revision = "0003_conversation_message_flow"
```

Do not edit/rewrite `0001`, `0002`, or `0003`.

### Columns to add

Add to `documents`:

```text
title TEXT NULL
source_category VARCHAR/TEXT NULL
source_origin TEXT NULL
source_language VARCHAR/TEXT NULL
usage_rights_note TEXT NULL
```

Use the existing ORM/migration type conventions (`Text` for free text; `String` is appropriate for enum-like constrained strings).

### Why nullable in the physical migration

The migration must preserve any Document rows created under the pre-Step-5.1 schema. Do not invent source category, language, or origin for existing rows.

Therefore the newly added columns are nullable at the database compatibility layer.

This does **not** mean an incomplete Document is ingestion eligible.

The Step-5.1 domain/source-policy contract must require these fields for a candidate Document entering ingestion:

```text
title              required + non-blank
source_category    required + supported value
source_origin      required + non-blank
source_language    required + supported value
```

`usage_rights_note` remains optional/lightweight.

### Database checks

Add CHECK constraints consistent with current repository naming conventions so that non-NULL values cannot violate frozen source policy.

Required logical checks:

```text
source_category IS NULL
OR source_category IN ('CURRICULUM_MATERIAL', 'INTERNAL_AUTHORED')

source_language IS NULL
OR source_language IN ('vi', 'zh', 'en')

title IS NULL
OR length(btrim(title)) > 0

source_origin IS NULL
OR length(btrim(source_origin)) > 0
```

Use stable constraint names equivalent to:

```text
ck_documents_source_category_values
ck_documents_source_language_values
ck_documents_title_non_blank
ck_documents_source_origin_non_blank
```

Do not add authority/trust fields or numeric source-quality fields.

Downgrade must drop the new constraints and new columns only.

---

## ORM changes

Modify:

```text
backend/app/database/models/document.py
```

Add ORM fields matching the migration:

```text
title
source_category
source_origin
source_language
usage_rights_note
```

Add ORM `CheckConstraint`s matching the physical migration.

Preserve all current processing/review fields, indexes, and approval invariant unchanged.

Do not change `KnowledgeSource`, `KnowledgeVersion`, `Chunk`, `Embedding`, or `Lesson` schemas in Step 5.1.

---

## Source-policy domain contract

Create:

```text
backend/app/ingestion/source_policy.py
```

Keep this module small and framework-light. It is the explicit Step-5.1 handoff contract for Step 5.2.

It should define/reuse typed policy values equivalent to:

```text
DocumentSourceCategory = CURRICULUM_MATERIAL | INTERNAL_AUTHORED
DocumentSourceLanguage = vi | zh | en
SUPPORTED_DOCUMENT_FORMATS = PDF | DOCX | TXT | MD
```

Provide a small source-metadata contract equivalent to:

```text
DocumentSourceMetadata
├── title
├── source_category
├── source_origin
├── source_language
└── usage_rights_note?
```

Using Pydantic is acceptable and preferred because it is already a project dependency and gives Step 5.2 a reusable typed validation boundary.

Required validation behavior:

- `title` cannot be blank/whitespace-only;
- `source_origin` cannot be blank/whitespace-only;
- only the two frozen source categories are accepted;
- only `vi | zh | en` are accepted;
- `usage_rights_note` is optional;
- extra speculative metadata fields are not required.

Provide pure policy helpers equivalent to:

```text
is_document_ingestion_eligible(...)
is_published_lesson_eligible(...)
is_document_approved_for_knowledge(...)
```

Exact names may differ slightly only if repository conventions strongly justify it, but responsibilities must remain explicit.

### Document ingestion eligibility

A Document is eligible to enter raw ingestion only when all are true:

```text
supported V0 input format
AND
allowed Chinese-learning domain confirmed by caller
AND
valid/non-blank source metadata
AND
valid source_category
AND
supported source_language
```

The domain decision should be passed explicitly to the helper (for example `domain_allowed: bool`) rather than persisted through a new speculative field or inferred through an LLM.

### Document approval vs ingestion eligibility

Preserve:

```text
INGESTION ELIGIBLE
!= APPROVED
!= ACTIVE KNOWLEDGE
```

`is_document_approved_for_knowledge(...)` should only express/check the existing human-review boundary (`review_status == APPROVED`). It must not activate a KnowledgeVersion or perform chunking/embedding.

### Lesson eligibility

Only:

```text
Lesson.status == PUBLISHED
```

is eligible for internal Lesson knowledge flow.

`DRAFT` and `ARCHIVED` must not be treated as active candidate Lesson knowledge.

Do not add `Document.source_category` semantics to Lesson.

---

## Error / validation design

Reuse current conventions.

The application currently normalizes FastAPI/Pydantic request validation failures to:

```text
HTTP 422
error.code = INVALID_REQUEST
```

Step 5.1 does not need a new large error taxonomy.

For the source-metadata typed contract, invalid category/language/blank required metadata may remain normal validation failures. Do not invent many new `ApplicationError` codes just to mirror Pydantic field validation.

Step 5.2 may introduce upload/storage-specific business errors when raw ingestion mechanics actually exist.

---

## Admin contract boundary

Do **not** add Document endpoints in Step 5.1.

Current Admin backend has no Document router/schema/service contract, and current frontend `/admin/documents` is intentionally structural-only.

The reusable `DocumentSourceMetadata` / source-policy contract in `app/ingestion/source_policy.py` is the preparation boundary for future Admin upload/create flow.

Do not modify:

```text
backend/app/admin/router.py
backend/app/admin/service.py
frontend/src/features/admin/*
frontend/src/types/api.generated.ts
```

unless an unavoidable compile/test dependency is discovered. If such a dependency appears, stop and report it rather than opportunistically creating the Document workflow.

No OpenAPI Document-management endpoint should be added in Step 5.1.

---

## Approval / activation boundary

Do not collapse the existing state machines.

Preserve:

```text
Document.processing_status
→ machine processing

Document.review_status
→ human review

KnowledgeVersion.status
→ knowledge-build / activation lifecycle
```

Do not implement KnowledgeVersion activation.

Only approved Documents may eventually become production knowledge, but Step 5.1 does not create/activate KnowledgeVersions.

Existing `KnowledgeVersion.status` and one-active-version index must remain unchanged.

---

## External retrieval boundary

External retrieval remains request-scoped.

Do not implement:

```text
external result
→ Document
→ Chunk
→ Embedding
→ permanent internal KB
```

If external content is retained in a future step, it must become a normal Document and pass the same source policy + ingestion + human approval boundaries.

---

## Non-knowledge data boundary

Do not model these as automatic knowledge sources:

```text
Conversation
Message
Learner answer
AssessmentAttempt
Progress
Prompt
LLM response
Retrieval trace
AI runtime log
```

AI-generated draft content becomes internal knowledge only after human review and transformation into an accepted Published Lesson or Approved Document.

No runtime-data ingestion behavior is required in Step 5.1.

---

## Source precedence documentation

Document, but do not implement retrieval ranking for:

```text
Current Published Lesson
>
CURRICULUM_MATERIAL
>
INTERNAL_AUTHORED
>
External Retrieval
```

Retrieval policy implementation belongs to Phase 6.

---

## Step-5.2 handoff contract

At the end of Step 5.1, Step 5.2 must be able to consume a stable boundary equivalent to:

```text
candidate Document metadata
+
input format
+
domain-allowed decision
↓
Step-5.1 source-policy validation
↓
ingestion eligible / not eligible
↓
Step 5.2 raw-ingestion mechanics
```

Step 5.2, not Step 5.1, owns:

- upload streaming;
- MIME/signature validation;
- local file storage abstraction;
- server-generated storage key;
- SHA-256;
- duplicate detection;
- file-size limits;
- raw artifact persistence;
- raw lesson snapshot persistence.

---

## Exact files expected to change/create

### Modify

```text
backend/app/database/models/document.py
backend/tests/test_database.py
backend/tests/test_migration_preservation.py
```

### Create

```text
backend/app/ingestion/source_policy.py
backend/migrations/versions/0004_document_source_policy.py
backend/tests/test_step51_source_policy.py
docs/data/step-5.1-define-knowledge-sources.md
```

Create `docs/data/` if it does not exist.

No other file should be changed unless required by a direct import/test failure caused by these exact changes. If broader changes appear necessary, report the reason instead of expanding scope silently.

---

## Migration tests / schema verification

Update database tests so the expected migration head becomes:

```text
0004_document_source_policy
```

Verify `documents` contains the five new columns.

Verify database CHECK constraints enforce the supported source-category/language values and non-blank semantics for non-NULL title/source_origin.

Extend migration-preservation coverage with a representative pre-Step-5.1 Document row:

1. apply existing revisions through `0003_conversation_message_flow`;
2. insert a valid existing user and a legacy Document using only the old Document columns;
3. apply `0004_document_source_policy`;
4. verify the legacy row still exists unchanged;
5. verify new provenance columns are `NULL` for that legacy row;
6. verify migration head is `0004_document_source_policy`;
7. verify invalid non-NULL category/language and blank non-NULL title/origin are rejected by DB constraints.

Do not backfill invented provenance values.

---

## Focused Step-5.1 tests

Create:

```text
backend/tests/test_step51_source_policy.py
```

Cover at least:

1. `CURRICULUM_MATERIAL` accepted.
2. `INTERNAL_AUTHORED` accepted.
3. Unsupported source category rejected.
4. `vi` accepted.
5. `zh` accepted.
6. `en` accepted.
7. Unsupported source language rejected.
8. Missing/blank/whitespace-only `source_origin` rejected for candidate ingestion metadata.
9. Missing/blank/whitespace-only `title` rejected.
10. Supported file formats are limited to `PDF`, `DOCX`, `TXT`, `MD` at the policy boundary.
11. Domain-not-allowed causes ingestion eligibility to be false/rejected without calling an LLM/classifier.
12. `Lesson.status == PUBLISHED` is eligible for Lesson knowledge flow.
13. `DRAFT` is not eligible.
14. `ARCHIVED` is not eligible as active candidate Lesson knowledge.
15. A `PENDING` or `REJECTED` Document is not approved for knowledge build.
16. An `APPROVED` Document satisfies only the human-approval boundary; the helper does not mutate/create/activate KnowledgeVersion.
17. No authority/trust score/category exists in the policy contract.
18. Transactional/runtime entities are not accepted/modelled as source-policy inputs.

Use pure/unit tests for source policy; they should not require file storage, parser, embeddings, external network, or LLM credentials.

---

## Regression verification

Run the focused tests above plus the full backend regression suite using the project-managed `uv` environment and test PostgreSQL configuration.

At minimum report:

```text
focused Step-5.1 tests
migration/schema tests
full backend pytest result
```

If the environment cannot run DB tests, do not silently mark them passing. Report the environment blocker precisely.

---

## Step Note / knowledge capture

Create:

```text
docs/data/step-5.1-define-knowledge-sources.md
```

It must contain:

- Objective
- Why
- Mental Model
- Core Knowledge
- Data Flow
- Key Design Decisions
- reusable approach for similar projects
- Common Mistakes
- Definition of Done

Include this mental model explicitly:

```text
Source Policy
→ What data are we willing to treat as candidate knowledge?

Raw Ingestion
→ How do we safely acquire and persist that source?

Processing
→ How do we turn raw source into clean structured data?

Knowledge Activation
→ Which processed version may serve production retrieval?
```

Do not collapse these concerns.

---

## Concepts actually used in this Step

Record only concepts actually implemented/documented:

| Concept | Category | Role |
|---|---|---|
| Knowledge Source Policy | DE | Defines candidate knowledge boundary |
| Source Taxonomy | DE | Separates source type, Document category, and file format |
| Data Provenance | DE | Makes knowledge sources traceable |
| Ingestion Eligibility | DE | Gate before raw ingestion |
| Processing vs Review State | DE | Separates machine lifecycle from human review |
| Knowledge Activation Boundary | BOTH | Separates approved source from retrieval-active knowledge |
| Schema Reconciliation | DE | Compares logical requirements with current physical schema |
| Forward Database Migration | DE | Evolves schema without rewriting applied migrations |
| CHECK Constraint | DE | Protects constrained-string values at the database boundary |

Do not add concepts that are merely future/out-of-scope mentions.

---

## Tools actually used in this Step

Expected tools if implementation follows this task:

| Tool | Category | Role |
|---|---|---|
| PostgreSQL | DE | Persistent relational schema |
| SQLAlchemy | DE | ORM representation + constraints |
| Alembic | DE | Forward schema migration |
| Pydantic | SYSTEM | Typed source-metadata validation boundary |
| pytest | SYSTEM | Focused and regression tests |
| uv | SYSTEM | Project Python environment/test execution |

Do not add a new dependency for Step 5.1.

---

## Explicit non-goals / guardrails

Do **not** implement:

- raw file storage strategy;
- upload endpoint or streaming;
- file hashing;
- duplicate detection;
- PDF parser;
- DOCX parser;
- TXT/MD parser/normalizer;
- cleaning;
- transformation;
- chunking;
- embeddings;
- vector storage;
- semantic retrieval;
- retrieval filtering;
- reranking;
- prompt construction;
- LLM generation;
- URL ingestion;
- HTML ingestion;
- website crawling;
- OCR;
- LLM/domain classifier;
- authority/trust score;
- source quality scoring;
- worker/queue/background architecture;
- Document Admin frontend workflow;
- Document processing/preview/approve endpoints;
- KnowledgeVersion activation;
- changes to frontend generated OpenAPI types.

Do not add LangChain/LlamaIndex or any other dependency.

---

## Important downstream note — do not implement now

The current `KnowledgeSource` model has `UNIQUE(lesson_id)` but not `UNIQUE(document_id)`.

Later Phase-5 orchestration specifies one logical KnowledgeSource per logical source, including one Document → one KnowledgeSource. This is **not required by the Step-5.1 source-policy acceptance criteria or the Step-5.2 raw-ingestion boundary**, so do not add that constraint in this task.

Flag it in the Step Note / handoff as a downstream schema point to re-check before the Step that creates/reuses Document KnowledgeSource records (currently Step 5.6 approval/orchestration path).

Do not silently pull that later lifecycle change into Step 5.1.

---

## Acceptance Criteria

- [ ] Current Document processing/review lifecycle remains unchanged.
- [ ] `KnowledgeSource.source_type` remains exactly `DOCUMENT | LESSON`.
- [ ] `KnowledgeVersion.status` and active-version invariant remain unchanged.
- [ ] Lesson status model remains unchanged.
- [ ] Document ORM now represents `title`, `source_category`, `source_origin`, `source_language`, `usage_rights_note`.
- [ ] One new forward Alembic migration follows revision `0003_conversation_message_flow`.
- [ ] Applied migrations are not rewritten.
- [ ] Existing pre-Step-5.1 Document rows survive the migration without invented provenance.
- [ ] Physical DB accepts NULL legacy provenance but rejects invalid non-NULL category/language and blank non-NULL title/origin.
- [ ] Candidate ingestion metadata requires non-blank title and origin.
- [ ] Source categories are exactly `CURRICULUM_MATERIAL | INTERNAL_AUTHORED`.
- [ ] Source languages are exactly `vi | zh | en`.
- [ ] File-format source policy remains PDF/DOCX/TXT/MD.
- [ ] Knowledge-domain eligibility is explicit and no classifier/database domain field is added.
- [ ] `INGESTION ELIGIBLE != APPROVED != ACTIVE KNOWLEDGE` remains explicit.
- [ ] Only `PUBLISHED` Lesson is eligible for active candidate Lesson knowledge.
- [ ] External retrieval remains request-scoped and is not persisted automatically.
- [ ] Runtime/transactional data is not automatically treated as knowledge.
- [ ] No authority/trust model is added.
- [ ] No Admin Document API/UI workflow is implemented.
- [ ] Step 5.2 can reuse the source-policy contract without redefining source category/language/provenance rules.
- [ ] Focused tests pass.
- [ ] Migration/schema tests pass.
- [ ] Full backend regression suite passes, or an exact environment blocker is reported.
- [ ] Step Note is created and reflects actual implementation.

---

## Required completion report

After implementation, report:

```text
Step:
Status:

What was done:
- ...

Key decisions:
- ...

Files/components changed:
- ...

Concepts added:
- ...

Tools added:
- ...

Tests / verification:
- ...

Problems / risks:
- ...

Decisions needed:
- ...

Recommended next action:
- ...
```

Do not declare the Step complete if migration/tests/documentation are incomplete.
