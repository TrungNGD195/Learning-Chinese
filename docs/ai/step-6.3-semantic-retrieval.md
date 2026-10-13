# Step 6.3 — Semantic Retrieval

## Objective

Turn query text into deterministic ranked semantic candidates from ACTIVE internal knowledge.

## Why

Separate semantic retrieval from Conversation, filtering, reranking, and generation.

## Mental Model

```text
query
→ query embedding
→ vector distance
→ semantic candidate
```

Candidate is not final evidence.

## Core Knowledge

MUST KNOW:

- query vs document embedding boundary;
- embedding-space/profile coherence;
- cosine distance vs cosine similarity;
- exact Top-K semantic retrieval;
- ACTIVE safety gates;
- technical failure vs valid empty result;
- transaction boundary around model inference.

SHOULD KNOW:

- Unicode normalization;
- metadata hydration via normalized joins;
- semantic rank vs future rerank score.

AWARENESS ONLY:

- ANN indexes;
- hybrid/BM25 retrieval;
- future retrieval thresholds.

## Data Flow

```text
query_text
→ trim, Unicode NFC, collapse repeated whitespace
→ short read transaction resolves ACTIVE embedding profile and copies its scalar identity
→ transaction ends
→ configured provider identity must exactly match the profile
→ embed_query(normalized_query), outside any database transaction
→ validate dimensions, finite values, and configured normalization
→ short read transaction runs Step 6.2 ACTIVE-gated exact cosine search
→ hydrate Chunk, KnowledgeVersion, KnowledgeSource, optional Document/Lesson/HSKLevel
→ restore the Step 6.2 vector order
→ rank from 1 and compute retrieval_score = 1 - distance
```

The service returns an empty list only when vector search succeeds and finds no candidates. Missing hydrated rows or technical failures produce normalized application errors.

## Key Design Decisions

- all ACTIVE internal corpus baseline;
- lesson filtering deferred to 6.4;
- `candidate_k=20` default with frozen range `1..100`;
- `retrieval_score=1-distance`;
- no threshold;
- no query-vector persistence;
- provider/profile exact identity match;
- no DB transaction during query embedding.

## Reusable approach

Keep the responsibilities separate:

```text
storage search primitive
from semantic retrieval orchestration
from business filtering policy
```

Step 6.2 owns ACTIVE-gated vector search. Step 6.3 owns query preprocessing, embedding, validation, orchestration, and candidate hydration. Step 6.4 owns business retrieval scope and filters.

## Common Mistakes

- calling `embed_documents()` for a query;
- searching under a mismatched profile;
- calling distance a relevance score without mapping;
- clamping cosine similarity;
- filtering global Top-K in Python;
- adding lesson scope prematurely in 6.3;
- returning [] for infrastructure failure;
- holding a DB transaction during inference;
- logging raw queries/vectors.

## Definition of Done

- deterministic trimming, NFC normalization, and whitespace collapsing;
- exactly one ACTIVE profile and exact provider identity matching;
- query vector validation before vector search;
- no transaction during embedding inference;
- Step 6.2 controls ACTIVE profile/version gates and exact cosine ordering;
- candidates preserve vector order and include normalized source provenance;
- score is `1 - distance` without clamping or thresholding;
- technical failures remain distinct from successful empty search;
- no persistence, public route, migration, or Step 6.4 behavior.

## Concepts Discovered

| Concept | Category | Step | Role / Why it matters |
|---|---|---|---|
| Semantic Retrieval | AI | 6.3 | Converts query embeddings into nearest internal knowledge candidates. |
| Query Embedding | AI | 6.3 | Represents learner query in the same vector space as indexed documents/chunks. |
| Embedding-space Coherence | AI | 6.3 | Prevents searching a vector with a different model/profile than stored vectors. |
| Cosine Similarity | AI | 6.3 | User-facing semantic score mapping `1 - cosine_distance`. |
| Candidate Top-K | AI | 6.3 | Bounds baseline semantic candidates before later filtering/reranking stages. |
| Deterministic Query Preprocessing | BOTH | 6.3 | Stabilizes query input without changing semantic intent. |
| Candidate Hydration | DE | 6.3 | Resolves normalized Chunk/source provenance without denormalizing Embedding. |
| Read transaction / inference separation | SYSTEM | 6.3 | Avoids holding DB transactions during model inference. |
| Technical-empty distinction | BOTH | 6.3 | Prevents infrastructure failure from masquerading as no evidence. |

## Tools Used

| Tool | Category | Step | Role / Why used |
|---|---|---|---|
| Python | SYSTEM | 6.3 | Retrieval orchestration and validation. |
| SQLAlchemy async | DE | 6.3 | Candidate metadata hydration/read boundaries. |
| PostgreSQL | DE | 6.3 | Normalized knowledge/provenance reads. |
| pgvector | BOTH | 6.3 | Exact cosine nearest-neighbor storage primitive from Step 6.2. |
| sentence-transformers | AI | 6.3 | Existing Step 6.1 query-embedding provider runtime. |
| pytest | SYSTEM | 6.3 | Focused and regression tests. |
