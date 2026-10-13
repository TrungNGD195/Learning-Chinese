# Step 7.3 — Retrieval Evaluation

## Implementation Contract

Implement the frozen task at `codex-tasks/phase7/step-7.3-retrieval-evaluation-codex-task.md`. This specification records its implementation-facing runtime contract.

### Inputs

- Approved Lesson Chat RAG evaluation dataset `v0.8.0`, 60/60 approved. The evaluator excludes the 7 OOD cases and does not write to the dataset.
- Accepted fixture pack `evaluation/fixtures/lesson_chat_rag/v0.1.0`, 3 Lesson sources, 1 `INTERNAL_KB` source, 26 unique stable locators, and no trusted external fixture sources.
- Exact model revisions configured by Step 6.1 and Step 6.5.

### Isolated fixture runtime

The bootstrap runs only against a verified dedicated test/evaluation PostgreSQL database, never a normal Development/Production target. It materializes real Lesson and approved internal Document source records, then uses existing source/version/chunking, embedding, vector readiness, and activation services. No schema or production retrieval behavior is added. Fixture provenance and stable locators live in the existing Chunk JSON metadata and are resolved without text comparison or similarity.

`--ensure` reuses only an integrity-matching bootstrap. `--reset` fails closed unless the database identity is verified and only fixture-owned corpus is present. Run artifacts preserve generated physical IDs; dataset cases continue to use stable logical locators.

### Evaluation behavior

- Use actual `SemanticRetrievalService` Top 20 and actual `RerankingService` ordering of that same pool; report semantic Top 5 versus reranked Top 5.
- Build tier filters through shared `build_scope_filter`: `CURRENT_LESSON` uses the trusted Lesson scope, while `INTERNAL_KB` resolves to `None`, matching Step 6.8-A's broader ACTIVE internal policy over published Lessons and approved active Documents. Do not narrow it to Documents only; do not call external retrieval.
- Multi-turn retrieval receives `question` only. OOD is excluded. No LLM or external retrieval call is made.
- Expected v0.8.0 attempt totals: DEVELOPMENT 58 (20 positive CURRENT_LESSON, 12 positive INTERNAL_KB, 16 negative CURRENT_LESSON, 10 negative INTERNAL_KB); HOLDOUT 15 (5, 3, 4, 3 respectively).
- REQUIRED evidence grades 2, ACCEPTABLE 1, unrelated 0. REQUIRED references with the same `requirement_id` form an equivalence group. Any valid member is a group hit.
- Report Recall@20, semantic/reranked Recall@5, Precision@5, nDCG@5 and reranker deltas. Negative-attempt recall metrics are N/A. Scope violation rate is reported; it is a zero-tolerance invariant.
- `NO_EVIDENCE_REFUSAL` is diagnostic and may return semantic neighbors. It is not required to return an empty list.

### Calibration

Use all DEVELOPMENT attempts only. Candidate thresholds are every unique finite raw rerank score in DEVELOPMENT reranked Top 5 plus `math.nextafter(max_score, +inf)`. Report the complete sweep and Pareto frontier. Apply the frozen policy: minimize overall false evidence acceptance, maximize overall true evidence acceptance, maximize the minimum tier-specific true acceptance, then choose the higher threshold.

Freeze the resulting recommendation and verify it on all HOLDOUT attempts without retuning. If samples are missing or the candidate accepts zero true evidence overall or in a tier, return `REVIEW_REQUIRED` with no numeric recommendation. Do not change `RAG_MIN_RERANK_SCORE`; the recommendation is for PM review, not runtime approval.

### Artifacts and command

Run output goes to `evaluation/runs/<run_id>/`: manifest, per-case JSONL, summary, threshold calibration, fixture bootstrap identity, and stable-locator runtime map. Execute from `backend/`:

```powershell
uv run python -m app.evaluation.step73.cli --ensure
```

The result is ready for independent specialist review only after the frozen tests and real run complete. Step 6.8-B remains not started; Step 7.2 ground truth remains unchanged.
