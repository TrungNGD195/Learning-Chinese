# Step 5.1 — Define Knowledge Sources

## Objective

Define and persist the minimum source-policy contract that says what may be considered candidate Chinese-learning knowledge. This Step prepares a typed handoff for raw ingestion; it does not acquire or process source content.

## Why

Knowledge records need traceable provenance and an explicit domain boundary. Legacy Documents already in the database have no Step-5.1 provenance, so the database must preserve them without guessing metadata. New ingestion candidates still need complete, valid metadata before they can pass policy.

## Mental Model

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

D-049 compatibility model:

```text
DB nullable
→ backward compatibility

application validation required
→ ingestion correctness

legacy NULL provenance
→ not automatically ingestion eligible
```

The states remain separate: ingestion eligible ≠ human approved ≠ active knowledge. `Document.processing_status` is machine processing, `Document.review_status` is human review, and `KnowledgeVersion.status` owns the knowledge-build/activation lifecycle.

## Core Knowledge

- `KnowledgeSource.source_type` remains `DOCUMENT | LESSON`.
- Document categories are `CURRICULUM_MATERIAL | INTERNAL_AUTHORED`; input formats are `PDF | DOCX | TXT | MD`.
- Candidate source languages are `vi | zh | en`.
- Only an explicitly domain-allowed Chinese-learning candidate can pass the pure eligibility check. No classifier is called or persisted.
- Only `PUBLISHED` Lessons are eligible for the Lesson knowledge flow.
- Human approval only checks the existing Document review boundary. It does not create or activate a `KnowledgeVersion`.
- Source precedence is documented as `Current Published Lesson > CURRICULUM_MATERIAL > INTERNAL_AUTHORED > External Retrieval`; retrieval ranking remains a later concern.

## Data Flow

```text
DocumentSourceMetadata + input format + explicit domain_allowed
→ Step-5.1 validation and eligibility
→ eligible / not eligible
→ Step 5.2 raw-ingestion mechanics
```

External retrieval stays request-scoped. Conversations, learner answers, assessments, prompts, LLM responses, retrieval traces, and runtime logs are not source-policy inputs.

## Key Design Decisions

- Revision `0004_document_source_policy` adds five nullable columns and four CHECK constraints. It preserves pre-Step-5.1 rows and invents no provenance. The finalized physical CHECK names use `op.f(...)` so the repository naming convention is not applied twice.
- The Pydantic `DocumentSourceMetadata` contract requires non-blank title and origin, supported category and language, and permits an optional `usage_rights_note`. Extra metadata is rejected.
- Eligibility helpers are pure. A supported format and valid typed metadata are not enough unless the caller explicitly passes `domain_allowed=True`.
- The existing processing/review fields, approval invariant, KnowledgeSource semantics, Lesson schema, and KnowledgeVersion lifecycle remain unchanged.
- No Document Admin API, frontend workflow, upload mechanics, raw storage, parser, chunking, embedding, or activation behavior is added.
- Downstream schema point: re-check `KnowledgeSource` uniqueness on `document_id` before the later Step 5.6 approval/orchestration path creates or reuses Document KnowledgeSource records. This constraint is not part of Step 5.1.

## Reusable Approach

When a system adds provenance to an established table, add nullable columns in a forward migration to preserve historical rows. Enforce new-candidate completeness at the typed application boundary, keep eligibility separate from approval and activation, and test both database constraints and legacy-row survival.

## Common Mistakes

- Backfilling guessed provenance into legacy rows.
- Treating nullable legacy values as permission to ingest incomplete new candidates.
- Confusing `KnowledgeSource.source_type`, Document category, and file format.
- Treating any Chinese-related topic as Chinese-learning content without an explicit domain decision.
- Collapsing ingestion eligibility, human review, and active knowledge into one status.
- Adding trust scoring, a classifier, Admin endpoints, or upload/storage behavior before its owning Step.

## Definition of Done

- Document provenance columns are nullable and guarded by stable CHECK constraints.
- Legacy Document rows remain unchanged with NULL provenance after migration.
- Typed metadata and pure eligibility/approval helpers define the Step-5.2 handoff.
- Source types, categories, languages, and formats use only the frozen values.
- Document processing/review and knowledge activation boundaries remain distinct.
- No Step-5.2 raw-ingestion behavior or frontend/Admin API work is included.
- Focused tests, migration/schema tests, and full backend regression must pass before this Step is marked done.

## Concepts Actually Used

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

## Tools Actually Used

| Tool | Category | Role |
|---|---|---|
| PostgreSQL | DE | Persistent relational schema |
| SQLAlchemy | DE | ORM representation and constraints |
| Alembic | DE | Forward schema migration |
| Pydantic | SYSTEM | Typed source-metadata validation boundary |
| pytest | SYSTEM | Focused and regression tests |
| uv | SYSTEM | Project Python environment and test execution |
