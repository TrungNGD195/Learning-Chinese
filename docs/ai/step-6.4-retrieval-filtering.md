# Step 6.4 — Filtering / Retrieval Scope

## Objective

Constrain semantic retrieval to backend-authorized eligible knowledge before vector Top-K.

## Why

Global Top-K followed by filtering can lose relevant in-scope candidates and violate Lesson-scoped product policy.

## Mental Model

```text
ACTIVE safety
→ eligibility filter
→ semantic ranking
→ reranking later
```

## Core Knowledge

- predicate pushdown;
- trusted context vs caller-controlled filter;
- RetrievalScope vs RetrievalFilter;
- AND across dimensions / OR within dimension;
- empty filter collection fail-closed;
- active lifecycle gates remain separate from filtering.

## Data Flow

`CURRENT_LESSON`:

```text
validated Conversation
→ Conversation.lesson_id
→ RetrievalScope.CURRENT_LESSON
→ build_scope_filter(... trusted_lesson_id ...)
→ RetrievalFilter(source_types={LESSON}, lesson_ids={trusted_lesson_id})
→ SemanticRetrievalService.retrieve(query_text, retrieval_filter=...)
→ Step 6.2 SQL: ACTIVE gates + source_type/lesson_id predicates
→ cosine ORDER BY, then candidate_k LIMIT
→ candidate metadata hydration and rank from 1
```

Step 6.4 does not read Conversation; later business orchestration owns the validated `Conversation.lesson_id`.

`INTERNAL_KB`:

```text
RetrievalScope.INTERNAL_KB
→ build_scope_filter(...)
→ None
→ all ACTIVE internal Lesson and Document knowledge
```

There is no automatic scope fallback. For either flow, SQL filter predicates are applied in the same Step 6.2 nearest-vector query before cosine ordering and Top-K limiting.

## Key Design Decisions

- CURRENT_LESSON = strict LESSON KnowledgeSource + trusted lesson ID;
- Documents excluded from CURRENT_LESSON;
- INTERNAL_KB = all ACTIVE internal sources;
- `Chunk.lesson_id` is provenance, not canonical scope ownership;
- SQL filtering occurs before vector `ORDER BY/LIMIT`;
- no schema migration/index explosion;
- Step 6.3 unfiltered behavior preserved.

## Reusable approach

Separate:

```text
production availability
business eligibility
ranking
```

and push eligibility predicates into the data query before Top-K.

## Common Mistakes

- trusting frontend lesson/filter IDs as authoritative;
- filtering global Top-K in Python;
- treating ACTIVE as optional filter;
- including all curriculum Documents in CURRENT_LESSON;
- using empty list as unrestricted;
- adding score boosts in filtering step;
- inventing a generic query DSL;
- duplicating metadata into vectors.

## Definition of Done

- immutable typed filter supports only the six frozen dimensions;
- empty collections, unknown canonical values, and the frozen Document/Lesson contradiction fail closed;
- CURRENT_LESSON requires a trusted Lesson ID and filters by KnowledgeSource ownership;
- INTERNAL_KB maps to no policy filter;
- ACTIVE profile/version gates and cosine ordering remain in Step 6.2;
- filter predicates run before `ORDER BY/LIMIT` in the same SQL query;
- `retrieve(query_text, retrieval_filter=None)` keeps the Step 6.3 behavior and candidate contract;
- no per-call `candidate_k`, threshold, reranking, fallback, public route, or schema migration.

## Concepts Discovered

| Concept | Category | Step | Role / Why it matters |
|---|---|---|---|
| Retrieval Scope | AI | 6.4 | Represents backend-owned knowledge tier such as CURRENT_LESSON or INTERNAL_KB. |
| Retrieval Filter | AI | 6.4 | Typed eligibility constraints applied before vector ranking. |
| Predicate Pushdown | BOTH | 6.4 | Applies relational eligibility inside SQL before Top-K, preserving retrieval quality and DB efficiency. |
| Trusted Context Derivation | SYSTEM | 6.4 | Prevents the learner/frontend from inventing authoritative retrieval scope. |
| Filter Composition | AI | 6.4 | Defines AND-across-dimensions / OR-within-dimension retrieval semantics. |
| Fail-closed Filter Validation | SYSTEM | 6.4 | Prevents malformed/empty filters from silently broadening retrieval scope. |
| ACTIVE Retrieval Gate | BOTH | 6.4 | Reuses production lifecycle safety independently from request-specific filtering. |

## Tools Used

| Tool | Category | Step | Role / Why used |
|---|---|---|---|
| PostgreSQL | DE | 6.4 | Executes relational filter predicates before vector Top-K. |
| pgvector | BOTH | 6.4 | Preserves exact cosine ranking inside the filtered eligible corpus. |
| SQLAlchemy async | DE | 6.4 | Builds joins/predicates and preserves repository/session conventions. |
| pytest | SYSTEM | 6.4 | Verifies scope, SQL semantics, ACTIVE safety, and regressions. |
