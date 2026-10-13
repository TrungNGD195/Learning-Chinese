# Step 6.10 — Citations

## Objective

Define a deterministic, provider independent citation contract for assistant answers. Validate message-local `[S<number>]` markers against the current trusted source map, persist only the unique cited provenance snapshots with the assistant message, and expose safe citation fields in message responses.

## Why

Conversation history outlives the retrieval request that supplied its evidence. Persisted snapshots keep historical citation displays stable if a Chunk is deleted or its live metadata changes. Model generated text may choose a source label, but only trusted runtime provenance may supply citation metadata.

## Mental Model

```text
generated text + current source map + citation_required
    -> context-aware parser
    -> deterministic provenance validator
    -> unique display snapshots
    -> caller-owned short finalization transaction
    -> MessageCitation rows and learner-safe API DTOs
```

Conversation memory provides continuity only. It is not current citation provenance. Step 6.10 provides validation and persistence seams; future RAG orchestration owns choosing `citation_required` and wiring retrieval results into them.

## Core Knowledge

- **Message-local source labels:** `S1`, `S2`, etc. identify entries from one current `PromptPackage.source_map`; they are not global identifiers.
- **Markdown-context-aware parsing:** only exact positive labels in eligible plain text count. Fenced code, inline code, and Markdown link labels are excluded. Malformed citation-like text in eligible prose fails validation.
- **Provenance resolution:** labels resolve to typed internal or external sources. Model prose never provides trusted title, chunk, URL, or domain.
- **Citation-required seam:** `True` requires at least one valid current marker; `False` permits no marker but still validates any marker that appears.
- **Snapshots:** persist one row per unique cited label, preserving first occurrence order. Duplicate mentions count as occurrences but do not create duplicate rows.
- **Atomic finalization:** the caller validates outside a database transaction, then persists citations and marks the Assistant `COMPLETED` in one short transaction. Repository helpers flush but do not commit.
- **Internal/external trust boundary:** internal snapshots use only typed display fields. External snapshots require HTTPS, a hostname, and exact membership in an injected policy. The default trust policy is empty.
- **Memory boundary:** historical assistant markers do not become current evidence. Step 6.9 memory sanitation remains independent.
- **Delete behavior:** the existing schema cascades citations when a Message is deleted and sets `chunk_id` to null when a Chunk is deleted, retaining the snapshot.

## Data Flow

1. A future retrieval/generation use case builds the current `PromptPackage` and decides whether citations are required.
2. `sources_from_prompt_package` copies only the typed label, chunk ID, type, title, page, and section fields.
3. `CitationValidator` parses original text and validates syntax, label membership, source resolution, and external trust in that order.
4. Validation returns the unchanged answer plus unique snapshots and both unique/occurrence counts.
5. In a short caller-owned transaction, the repository inserts citation rows and flushes the completed Assistant message.
6. Message history performs one batched citation query for the page and reconstructs display order from the stored answer.
7. The API returns `citations: []` for User, Pending, Failed, and citation-free messages; successful Assistant snapshots return learner-safe display fields.

## Key Design Decisions

- No Markdown parsing package, external URL client, retrieval behavior, migration, or runtime dependency was added.
- F1 parsing scans original text and keeps offsets into it; it never rewrites or repairs model output.
- `citation_required=False` waives absence only. It does not waive malformed syntax, unknown labels, source resolution, or unsafe URLs.
- External trust is an injected protocol/value object. Production defaults to an empty set; no settings field or real domain was introduced.
- Internal typed locator data persists only page number and section. Generic locator metadata is not copied into learner snapshots.
- The API never exposes internal IDs, generic metadata, storage references, or retrieval/rerank scores.
- Frontend OpenAPI types are generated from the running FastAPI app; no citation UI was added.
- Existing `MessageCitation` metadata and migration history remain unchanged.

## Reusable Approach

- Keep parsing/validation pure and independent from database, model-provider, and retrieval clients.
- Keep repository persistence flush-only. Let the application service own the transaction boundary.
- Keep validated provenance in immutable DTOs and serialize a deliberately small learner-facing response.
- For history pages, batch-load related snapshots rather than issuing one query per message.
- When changing response schemas, regenerate committed OpenAPI types through the repository scripts.

## Common Mistakes

- Treating conversation history or model-authored prose as trusted evidence.
- Counting markers inside code or Markdown link labels.
- Persisting a row for every repeated citation occurrence.
- Allowing invalid citation output to become a successful Assistant response.
- Holding a DB transaction open during model generation or citation validation.
- Accepting an external URL based on scheme alone, suffix matching, or unreviewed production domains.
- Returning database IDs or mutable live source records in learner API responses.
- Manually editing generated frontend API types or adding a citation rendering feature in this step.

## Definition of Done

- Parser and validator tests cover F1 context, malformed syntax, source resolution, requirement semantics, duplicates, and external trust.
- PostgreSQL tests cover schema alignment, atomic persistence, failed finalization, batch API loading, stable snapshots, and FK behavior.
- Focused and regression suites pass; OpenAPI types are regenerated and checked.
- `uv.lock`, frontend lockfile, schema, and migrations remain unchanged.
- Step 6.8-A/B remain unimplemented and the result is ready for independent AI Engineering Specialist review.

## Concepts Discovered

| Concept | Category | Step | Role / Why it matters |
|---|---|---|---|
| Citation Validation | AI | 6.10 | Deterministically validates model citation markers |
| Message-local Source Labels | AI | 6.10 | Keeps S-label identity scoped to one generated answer |
| Citation Provenance Resolution | AI | 6.10 | Resolves model labels only through trusted runtime provenance |
| Citation vs Conversation Memory Boundary | AI | 6.10 | Prevents historical conversation from becoming current evidence |
| Citation-required Seam | AI | 6.10 | Separates evidence-based answers from deterministic no-evidence outcomes |
| External Citation Trust Policy | SYSTEM | 6.10 | Validates trusted HTTPS provenance without external retrieval |
| Citation Snapshot Persistence | SYSTEM | 6.10 | Keeps historical learner citations stable after source changes |
| Atomic Message Finalization | SYSTEM | 6.10 | Prevents completed messages with missing or partial citation rows |
| API Citation Contract | SYSTEM | 6.10 | Exposes learner-safe citation metadata consistently |
| FK/Delete Semantics | SYSTEM | 6.10 | Preserves citation lifecycle under Message/Chunk deletion |

## Tools Used

| Tool | Category | Step | Role / Why used |
|---|---|---|---|
| Python | SYSTEM | 6.10 | Parser, validator, and application logic |
| SQLAlchemy | SYSTEM | 6.10 | Existing MessageCitation persistence |
| PostgreSQL | SYSTEM | 6.10 | Existing citation snapshot storage and verification |
| FastAPI / Pydantic | SYSTEM | 6.10 | Public citations array API schema |
| pytest | SYSTEM | 6.10 | Focused and regression validation |
| Alembic | SYSTEM | 6.10 | Verify no schema drift or new migration |
| openapi-typescript | SYSTEM | 6.10 | Regenerate frontend API contract |
| uv | SYSTEM | 6.10 | Backend environment and lock verification |
