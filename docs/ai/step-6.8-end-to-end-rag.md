# Step 6.8-A — Internal End-to-End RAG Bootstrap / Score Collection

## Objective

Connect the accepted internal retrieval, reranking, prompt, memory, generation,
and citation components for Lesson Chat. Provide a score-only calibration seam
for Step 7.3.

## Why

The existing components have separate ownership and cannot safely infer a
learner answer by themselves. An application orchestrator must apply the
calibrated evidence gate, select one internal tier, and return a typed runtime
result for atomic persistence. Calibration must happen before the learner path
uses a numeric evidence threshold.

## Mental Model

```text
Candidate generation
→ rerank once
→ evidence decision
→ grounded generation OR deterministic no-evidence
```

```text
runtime result
!=
persistence transaction
```

## Core Knowledge

| Concept | Category | Role |
|---|---|---|
| RAG orchestration | AI | Coordinates existing RAG stages without merging their responsibilities |
| Evidence gate | AI | Converts reranker scores into tier usability after calibration |
| Calibration score seam | AI | Supplies retrieval/rerank evidence for Step 7.3 without generation |
| Runtime DTO boundary | BOTH | Separates AI execution result from DB persistence |
| Atomic finalization | SYSTEM | Prevents partial successful Assistant state |
| PostgreSQL session advisory lock | SYSTEM | Cross-process duplicate-processing guard without schema state |
| Short transaction boundary | BOTH | Prevents slow AI work from holding DB transactions |

## Data Flow

### Calibration

`collect_calibration_scores()` always measures CURRENT_LESSON and INTERNAL_KB
independently. It returns ranks, retrieval scores, rerank scores, and source
scope identity. It performs no prompt, memory, LLM, citation, or persistence
work.

### Learner runtime

The learner path is disabled while calibration mode is true or the threshold is
missing. Otherwise it retrieves and reranks CURRENT_LESSON first. INTERNAL_KB
runs only when that tier has no candidate at or above the threshold. A grounded
answer uses only the selected tier's Top-K prompt candidates while retaining
all scored selected-tier candidates in its runtime trace. If both tiers are
insufficient, the exact D-091 response is completed without evidence rows.

ConversationService commits Transaction A before RAG and holds a session
advisory lock for the Assistant attempt without an open transaction. Success
commits Transaction B before releasing the lock. A technical failure commits
the PENDING-to-FAILED transition before releasing the same lock, so a duplicate
processor cannot enter during failure finalization.

## Key Design Decisions

- Inherit Step-6.9 D-084/D-085 attempt-scoped memory and bounded transient retry.
- Inherit D-086 external citation trust ownership; no external retrieval is
  enabled here.
- Preserve D-087/D-088 calibration-only behavior and calibration-flag
  precedence.
- Preserve D-089 selected-tier retrieval persistence.
- Preserve D-090 PostgreSQL session lock keyed by stable SHA-256-derived signed
  64-bit identity. A theoretical collision can cause rare false contention.
- Preserve exact D-091 deterministic no-evidence text.
- Preserve D-092 dual reranker views from one inference: all scored candidates
  and Top-K.
- Schema, migration, dependency, and public API changes: none.

## Reusable Approach

Keep model/data stages focused, return a typed runtime result, and persist once
at the application boundary.

## Common Mistakes

- Treating candidate existence or Top-K membership as evidence.
- Reranking a second time for diagnostics.
- Building prompts for each tier or allowing memory to affect retrieval.
- Holding a database transaction around reranking or LLM work.
- Persisting rejected-tier traces.
- Marking a duplicate caller's Assistant FAILED.
- Using Python `hash()` for a cross-process advisory key.

## Definition of Done

- Calibration mode measures both internal tiers without generation or writes.
- Learner mode requires calibration disabled and a configured finite threshold.
- CURRENT_LESSON has priority; technical errors do not trigger tier fallback.
- One selected tier feeds prompt, memory, generation, and citation validation.
- Transaction B atomically writes selected-tier retrievals, citations, and
  Assistant completion.
- D-090 prevents duplicate processing through success or failure commit and
  uses only short DB transactions.
- No schema, migration, new dependency, public calibration route, or external
  retrieval behavior is introduced.

## Concepts Discovered

- RAG orchestration | AI
- Evidence gate | AI
- Calibration score seam | AI
- Runtime DTO boundary | BOTH
- Atomic finalization | SYSTEM
- PostgreSQL session advisory lock | SYSTEM
- Short transaction boundary | BOTH

## Tools Used

- PostgreSQL advisory locks | SYSTEM
- SQLAlchemy AsyncSession / AsyncConnection | BOTH
- pgvector | BOTH
- tiktoken | AI
- OpenAI async provider integration | AI

## Step 6.8-B — Trusted External Fallback

### Objective

Attempt TRUSTED_EXTERNAL only after CURRENT_LESSON and INTERNAL_KB are both
semantically insufficient. Tavily Basic Search supplies candidates; it does
not establish trust or answer quality.

### Why

Internal knowledge may not contain enough evidence. A small reviewed external
tier extends coverage while the exact-host gate prevents open-web grounding.

### Mental Model

```text
internal truth first
→ reviewed external fallback
→ local trust gate
→ same reranker/evidence discipline
```

### Core Knowledge

| Concept | Category | Role |
|---|---|---|
| External Retrieval Provider | AI | Vendor-neutral candidate generation boundary |
| Trusted domain allowlist | AI/SYSTEM | Restricts evidence to D-094 reviewed hosts |
| Defense in depth | SYSTEM | Combines Tavily filtering with local URL validation |
| Exact-host validation | SYSTEM | Rejects lookalike and unreviewed subdomain hosts |
| External reranking | AI | Scores trusted candidates with the configured BGE reranker |
| ContextEvidence adapter | AI | Shares prompt packing without fabricating internal identifiers |
| External citation provenance | AI | Resolves labels to backend-owned trusted URLs |

### Data Flow

CURRENT_LESSON → INTERNAL_KB → Tavily Basic Search → local HTTPS exact-host
filter → external-only rerank → configured calibrated score gate → Top 5 →
common ContextEvidence prompt → generation and external citation validation.
External success writes zero MessageRetrieval rows and validated EXTERNAL_URL
citations in Transaction B. External semantic emptiness returns exact D-091
without prompt, memory, LLM, or citations.

### Key Design Decisions

- Preserve D-093 threshold `-1.0815147161483765`; it is a score, not a probability.
- Preserve D-094 Tavily Basic Search and the exact hosts `www.open.edu`,
  `en.wiktionary.org`, and `www.chinesetest.cn`.
- External reranker failure is technical failure; provider ordering is never a
  success fallback.
- Keep external provenance runtime-only; no schema or migration is added.

### Reusable Approach

Separate candidate generation, trust validation, relevance scoring, prompt
adaptation, citation provenance, and persistence.

### Common Mistakes

- Trusting provider filtering without local validation or suffix-matching hosts.
- Mixing internal and external candidates in one rerank pool.
- Using provider score as calibrated rerank score or falling back to provider
  order after reranker failure.
- Fetching arbitrary webpages, auto-ingesting results, or fabricating Chunk IDs.
- Persisting external URLs in MessageRetrieval or running external search after
  an internal technical failure.

### Definition of Done

- External fallback runs only after both internal tiers fail semantically.
- Exact-host filtering and the configured reranker/evidence gate protect every
  external context block; generated citations resolve to trusted backend URLs.
- External success persists citations but no internal retrieval traces; no
  evidence preserves D-091 and all frozen transaction/retry behavior.
- No schema, migration, new API, or Step 6.11+ behavior is added.

### Concepts Discovered

| Concept | Category | Step | Role / Why it matters |
|---|---|---|---|
| External Retrieval Provider | AI | 6.8-B | Vendor-neutral candidate-generation boundary |
| Trusted domain allowlist | BOTH | 6.8-B | Restricts runtime evidence to reviewed hosts |
| Defense in depth | SYSTEM | 6.8-B | Provider filtering plus authoritative local validation |
| Exact-host validation | SYSTEM | 6.8-B | Rejects lookalike and unreviewed subdomains |
| External reranking | AI | 6.8-B | Applies the existing configured relevance model |
| ContextEvidence adapter | AI | 6.8-B | Shares prompt construction without fake internal IDs |
| External citation provenance | AI | 6.8-B | Resolves source labels to backend-owned trusted URLs |

### Tools Used

| Tool | Category | Step | Role / Why it matters |
|---|---|---|---|
| Tavily Search API / Basic Search | AI | 6.8-B | External candidate generation |
| httpx AsyncClient | SYSTEM | 6.8-B | Non-blocking Tavily HTTP integration |
| Existing BGE reranker / RerankerProvider | AI | 6.8-B | External evidence relevance scoring |
