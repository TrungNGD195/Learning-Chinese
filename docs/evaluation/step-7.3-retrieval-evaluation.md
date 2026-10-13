# Step 7.3 — Retrieval Evaluation & Rerank Threshold Calibration

## Objective

Measure the accepted Lesson Chat RAG retrieval path against the approved Step 7.2 `v0.8.0` dataset, then produce a development-only raw reranker-threshold candidate and a frozen holdout verification. The run is evidence for PM review; it does not approve or install a runtime threshold.

## Why

Recall before reranking distinguishes missing candidate evidence from ranking loss. A development/holdout split lets PM review a measured threshold trade-off without tuning on holdout data or inventing a numeric quality gate.

## Mental Model

```text
accepted fixture sources
→ dedicated test database
→ existing Lesson/Document ingestion and chunk services
→ real embeddings, readiness, and activation
→ production semantic retrieval Top 20
→ production reranking of the same candidates
→ metrics and development threshold sweep
→ frozen holdout verification
```

Only the current question is sent to retrieval for multi-turn cases. Conversation history is not used to rewrite the query. `NO_EVIDENCE_REFUSAL` measures the returned semantic neighbors and raw scores; it does not require an empty result. OOD cases are excluded.

## Core Knowledge

- **Retrieval evaluation | AI** — measure evidence-group coverage at Top 20 and Top 5.
- **Evidence equivalence group | AI** — any retrieved member with the same `requirement_id` satisfies that required fact group.
- **Graded relevance | AI** — REQUIRED is grade 2, ACCEPTABLE is grade 1, and unrelated is grade 0. Required relevance wins when identities overlap.
- **Rerank threshold calibration | AI** — inspect development score boundaries without normalizing raw model logits.
- **Holdout verification | AI** — apply the one frozen development recommendation without tuning it.
- **Evaluation run artifact | SYSTEM** — store dataset, model, bootstrap, map, attempts, metrics, and calibration identity together.
- **Reproducible evaluation | BOTH** — pin fixture/model/chunking identities and retain the run-local fixture-to-Chunk mapping.

## Data Flow

1. Validate the accepted fixture manifest and exact source content hashes; validate the official `v0.8.0` dataset gate.
2. Verify `APP_ENV=test`, the effective database identity, and separation from configured normal `DATABASE_URL`.
3. Materialize three published fixture Lessons and one approved `INTERNAL_AUTHORED` Document in the dedicated database.
4. Invoke existing ingestion, chunking, embedding, vector-readiness, and activation services. Persist semantic fixture provenance in the existing Chunk JSON metadata.
5. Resolve all fixture and dataset evidence locators from persisted chunk provenance. Never compare text or use similarity to resolve identity.
6. Run 58 DEVELOPMENT and 15 HOLDOUT internal-tier attempts through `SemanticRetrievalService` and `RerankingService`; no external retrieval or LLM is called.
7. Sweep every unique finite DEVELOPMENT reranked Top 5 score plus `nextafter(max, +inf)`. Select the transparent PM-review candidate, freeze it, and verify it on HOLDOUT.
8. Write `manifest.json`, `cases.jsonl`, `summary.json`, `threshold-calibration.json`, `fixture-bootstrap.json`, and `fixture-runtime-map.json` under `evaluation/runs/<run_id>/`.

## Key Design Decisions

- No database schema, runtime retrieval, model, or dependency change is required. Fixture ownership is isolated by the dedicated test/evaluation database.
- The bootstrap consumes the accepted checked-in fixture bytes and fails closed on fixture drift, unknown database identity, contamination, incomplete embeddings, failed vector readiness, or missing provenance.
- Evaluator tier filters come from the shared production `build_scope_filter` policy. `CURRENT_LESSON` uses its trusted Lesson filter. `INTERNAL_KB` resolves to the Step 6.8-A unrestricted ACTIVE internal scope (`None` filter), which includes published Lesson knowledge and approved active Documents; the V0 source model has no external source family.
- The three Lessons use the accepted raw Lesson snapshot and ingestion path. The accepted internal fixture uses the existing Document approval and KnowledgeSource/Version/Chunk path.
- Stable locators and their block/source identities are written into the existing JSONB Chunk metadata after the existing chunk service creates real Chunks. Resolution supports multiple locators per merged Chunk and multiple Chunks per split locator.
- `--ensure` reuses a matching, healthy bootstrap. `--reset` first verifies the database safety guard and removes only fixture-owned corpus rows. UUIDs remain in run artifacts, never in dataset ground truth.
- Threshold candidates use raw reranker scores. The policy minimizes false evidence acceptance, then maximizes true acceptance, tier-minimum true acceptance, and threshold value. A recommendation that accepts no evidence returns `REVIEW_REQUIRED`.
- Runtime `RAG_MIN_RERANK_SCORE` is observed and left untouched. No numeric quality threshold or PM approval is implied.

## Reusable approach

For a later evaluation, validate immutable fixture bytes first, bootstrap only in an isolated database through current production services, resolve evidence from provenance, separate development selection from holdout verification, and retain all identity and raw score artifacts.

## Common Mistakes

- Do not use answer text, fuzzy matching, embeddings, or guessed chunk indexes to resolve fixture evidence.
- Do not activate evaluation knowledge in a normal development or production database.
- Do not send conversation history as a query rewrite.
- Do not call raw reranker logits probabilities or normalize them.
- Do not use HOLDOUT to pick a threshold, alter dataset ground truth, or claim PM threshold approval.
- Do not force no-evidence retrieval to return an empty list.

## Definition of Done

- The approved dataset remains unchanged and the official gate passes.
- All 26 accepted locators resolve to ACTIVE fixture Chunks in the dedicated database.
- Real pinned embedding and reranking providers run through existing retrieval/reranking boundaries.
- Metrics, scope results, development sweep, recommendation, and frozen holdout result are recorded.
- The Step 7.3 evaluator, real retrieval/reranking integration, evaluation-dataset, provider-focused, and broader Step 6.1–6.5 / Step 6.8-A regression tests pass on a clean isolated test database. The `INTERNAL_KB` scope regression proves retrieval can return both an eligible Lesson and approved internal Document.
- The runtime threshold, Step 7.2 ground truth, schema, and Step 6.8-B remain unchanged.

## Concepts Discovered

| Concept | Category |
|---|---|
| Retrieval evaluation | AI |
| Evidence equivalence group | AI |
| Graded relevance | AI |
| Rerank threshold calibration | AI |
| Holdout verification | AI |
| Evaluation run artifact | SYSTEM |
| Reproducible evaluation | BOTH |

## Tools Used

- Python | SYSTEM
- uv | SYSTEM
- PostgreSQL and pgvector | DE
- SQLAlchemy | SYSTEM
- sentence-transformers | AI
- Transformers | AI
- PyTorch | AI
- pytest | SYSTEM

## Step Specification

Implementation command:

```powershell
cd backend
uv run python -m app.evaluation.step73.cli --ensure
```

Use `--reset` only for the verified dedicated `chinese_learning_test` database. The frozen task defines the exact dataset split, attempt planning, scope rules, metrics, calibration sweep, recommendation tie-break, holdout verification, and artifact contract. A result is a specialist-review handoff. It does not modify runtime configuration or close the Step 6.8-A gate.
