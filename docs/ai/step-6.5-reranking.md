# Step 6.5 — Reranking / Evidence Score

## Objective

Refine already-filtered semantic candidates with a local multilingual query-passage reranker and return a deterministic Top-K ordering.

## Why

Dense retrieval efficiently generates plausible candidates. A cross-encoder scores each query/passage pair jointly and can improve relevance ordering before later context construction.

## Mental Model

```text
Eligibility and semantic retrieval
→ relevance refinement
→ context construction later
```

## Core Knowledge

- Cross-encoder reranking scores query and passage together.
- The raw model logit is a relevance signal, not a probability.
- Original semantic rank and retrieval score remain diagnostic fields.
- Model revision and input format are part of reranker identity and later calibration.
- Pair lengths are checked without truncation.
- Technical failure is distinct from semantic insufficiency.

## Data Flow

```text
normalized query + filtered RetrievalCandidate[]
→ validate candidate identity/content
→ candidates[:20]
→ RerankPassageFormatter/v1
→ validate query/passage lengths without truncation
→ sequential bounded batches
→ validate raw logits
→ rerank_score DESC, semantic rank ASC, chunk_id ASC
→ assign runtime rerank_rank
→ RERANKER_TOP_K
```

## Key Design Decisions

- Local `BAAI/bge-reranker-v2-m3`, pinned revision `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`.
- `transformers` and PyTorch are used through a small `RerankerProvider` boundary; model loading is lazy and cached per process.
- Deterministic Document and Lesson passage formats are separate from the embedding formatter.
- Only the first 20 semantic candidates enter reranking; every selected candidate is scored before Top-K.
- Batches run sequentially, default size 8 (range 1–20); result Top-K defaults to 5 (range 1–5).
- Raw logits are preserved without sigmoid, normalization, clamping, thresholding, or fusion with retrieval score.
- Any technical or partial-batch failure discards all rerank output and raises a typed error.
- Reranking has no database session, query, transaction, or persistence boundary.
- No `RAG_MIN_RERANK_SCORE`; Step 7 calibration owns that decision.

## Reusable approach

```text
freeze model identity
→ define deterministic model input
→ validate lengths before inference
→ score a bounded candidate set
→ validate all outputs
→ preserve upstream diagnostics
→ leave threshold policy to evaluation
```

## Common Mistakes

- Reranking before scope/filter enforcement.
- Including rank, IDs, or retrieval scores in model passage text.
- Silently truncating model input.
- Overwriting semantic rank or retrieval score.
- Treating raw logits as probabilities.
- Returning semantic-order success after technical failure.
- Applying a threshold before calibration.

## Definition of Done

The frozen Step 6.5 contract is implemented and covered by focused tests; Step 6.1–6.4 and Phase 5.5–5.7 regressions pass; no migration or threshold is introduced; the handoff is ready for independent specialist review.

## Concepts Discovered

| Concept | Category | Step | Role / Why it matters |
|---|---|---:|---|
| Cross-encoder reranking | AI | 6.5 | Jointly scores query/passage pairs to refine semantic candidate ordering. |
| Reranker model identity/versioning | AI | 6.5 | Keeps rerank scores reproducible and makes threshold calibration version-specific. |
| Raw relevance logit | AI | 6.5 | Preserves provider-native score semantics without unjustified normalization. |
| Deterministic rerank tie-breaking | BOTH | 6.5 | Makes runtime/evaluation outputs reproducible. |
| Bounded sequential inference batching | AI | 6.5 | Controls local inference memory/latency without queue complexity. |
| Technical failure vs semantic no-evidence | BOTH | 6.5 | Prevents infrastructure/model failure from corrupting fallback/evidence policy. |

## Tools Used

| Tool | Category | Step | Role / Why used |
|---|---|---:|---|
| Hugging Face Transformers | AI | 6.5 | Loads, tokenizes, and runs the pinned BGE sequence-classification reranker using the existing ML runtime. |
| PyTorch | AI | 6.5 | Provides the local inference tensor runtime. |
