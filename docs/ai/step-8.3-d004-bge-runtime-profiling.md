# Step 8.3 / D-004 — BGE Runtime Profiling

## Harness state

**Implemented; measurement semantics corrected and safe tests pass.** The profiling harness uses the accepted provider/service seams and does not copy model loading into another provider. `psutil` remains a backend dev/profiling dependency only. Production AI/RAG behavior, model identities, Settings schema, deployment configuration, and D-005 are unchanged.

The profiler offers `--preflight`, `--scenario baseline`, the seven heavy scenarios, and `--aggregate <scenario-json...> --output <profile.json>`. Baseline imports the normal config/provider modules but does not check heavy-model RAM, inspect model caches, construct providers, or load models. Every heavy scenario applies the configured profiler-machine RAM guard, then compares current Settings to both frozen D-004 model identities, then verifies the exact local cache revisions, all before provider construction. A model mismatch returns `ENVIRONMENT_GATE / MODEL_CONFIG_MISMATCH` with expected/actual model and revision. Child model-loading processes force Hugging Face offline mode.

Concurrency schedules two asyncio tasks at a single recorded arrival barrier and awaits the existing async embedding/reranking provider boundary on the event loop. Local PyTorch/SentenceTransformers computation remains synchronous inside those async methods, preserving the current serialization behavior. Request **latency** is measured from common arrival through completion, including time waiting behind another request. Request **execution** is measured from that request's actual start through completion. It records both start/completion offsets, both metrics, pair makespan, errors, and peak RSS. `overlap_observed` is derived from timestamp interval intersection. Two learner-shaped warm-up workloads precede exactly ten measured pairs of two arrivals; no thread, process pool, worker, queue, or extra server process is introduced.

Ingestion throughput prepares deterministic contexts and formatter output before timing, embeds one warm-up batch before timing, then times a full pass over every selected unique fixture input. It records character and UTF-8 size statistics, configured batch size, measured/warm-up batch counts, elapsed seconds, throughput, errors, and RSS. The accepted fixture pack currently provides 26 unique blocks; none are duplicated to reach 64.

The both-loaded scenario records embedding and reranker first-use durations separately, then times one warm `embed_query → RerankingService.rerank` workload after both models have been used. Cold embedding and reranker scenarios each use a parent process to launch exactly three fresh Python child processes and preserve raw first-use samples plus the median, along with all steady/peak RSS samples and summaries.

Canonical aggregation accepts only all eight complete scenario files marked as real provider measurements with `ENVIRONMENT_GATE=PASSED`. It exposes non-empty `memory.baseline`, `memory.embedding_only`, `memory.reranker_only`, and `memory.both_loaded` sections directly in the final profile. It rejects missing sections, gated/fake measurements, invalid cold repetition/RSS summaries, missing warm samples, inconsistent concurrency timing, incomplete concurrency pairs, or failed/empty ingestion evidence. It writes the canonical full profile only after this validation.

## Safe verification and current evidence

Verified from the locked backend `uv` environment using `UV_CACHE_DIR` in the user temp directory (the default AppData uv cache was access-denied) and offline mode:

- `uv run --offline python -m py_compile scripts/profile_bge_runtime.py tests/test_profile_bge_runtime.py` — PASS.
- `uv run --offline pytest tests/test_profile_bge_runtime.py -q -p no:cacheprovider` — **33 passed**.
- `uv run --offline pytest tests/test_step61_embedding_provider.py tests/test_step61_embedding_formatter.py tests/test_step65_reranker_provider.py tests/test_step65_reranking_service.py tests/test_step65_rerank_formatter.py -q -p no:cacheprovider` — **67 passed**.
- `scripts/profile_bge_runtime.py --preflight --output docs/ai/evidence/step-8.3-d004-bge-runtime-preflight.json` — PASS. The inherited `DEBUG=release` value was invalid for Settings, so the command was run with process-local `DEBUG=false`; no Settings schema or project configuration was changed.
- `scripts/profile_bge_runtime.py --scenario baseline` — PASS, no model/provider construction or BGE load. Baseline process RSS: 64,479,232 bytes; steady: 64,499,712 bytes; peak: 64,499,712 bytes. This result was inspected from stdout and not persisted as a completed D-004 profile.

Preflight recorded 2026-10-14. Current available RAM was 1,266,544,640 bytes of 8,299,257,856 total (about 1.18 GiB), below the default 4 GiB profiler-only guard. Both exact model revisions were present in local cache. Resolved frozen subject:

- Embedding: `BAAI/bge-m3`, revision `5617a9f61b028005a4858fdac845db406aefb181`.
- Reranker: `BAAI/bge-reranker-v2-m3`, revision `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`.

The full profile remains absent. On this machine only the preflight evidence file is retained; no BGE model scenario was executed.

| Measurement | State |
| --- | --- |
| Environment identity / exact model cache | Verified by preflight |
| Baseline RSS | Measured safely; console only |
| Cold embedding, 3 fresh processes | NOT MEASURED |
| Cold reranker, 3 fresh processes | NOT MEASURED |
| Embedding-only / reranker-only / both-loaded RSS | NOT MEASURED |
| Observed model-scenario peak RSS | NOT MEASURED |
| Warm embedding: 5 warmups / 30 samples / p50 / nearest-rank p95 | NOT MEASURED |
| Warm reranking: 3 warmups / 30 samples / 20 candidates / p50 / p95 | NOT MEASURED |
| Both-loaded warm workload | NOT MEASURED |
| Concurrency 2: 2 warmups / 10 pairs | NOT MEASURED |
| Ingestion embedding throughput | NOT MEASURED |
| D-004 local-vs-hosted decision | OPEN |

The 4 GiB value protects the profiling run on this machine. It is not a production RAM requirement or a host-sizing conclusion. These checks do not prove that BGE cannot run locally, that Render Free cannot run it, or that hosted inference is required.

## Running on a suitable profiling machine

From `backend/`, run the baseline and each heavy scenario into separate JSON files. The load scenarios automatically collect three fresh-process repetitions apiece.

```powershell
uv run python scripts/profile_bge_runtime.py --preflight --output docs/ai/evidence/step-8.3-d004-bge-runtime-preflight.json
uv run python scripts/profile_bge_runtime.py --scenario baseline --output docs/ai/evidence/d004-baseline.json
uv run python scripts/profile_bge_runtime.py --scenario embedding-load --output docs/ai/evidence/d004-embedding-load.json
uv run python scripts/profile_bge_runtime.py --scenario reranker-load --output docs/ai/evidence/d004-reranker-load.json
uv run python scripts/profile_bge_runtime.py --scenario both-loaded --output docs/ai/evidence/d004-both-loaded.json
uv run python scripts/profile_bge_runtime.py --scenario warm-embedding --output docs/ai/evidence/d004-warm-embedding.json
uv run python scripts/profile_bge_runtime.py --scenario warm-reranking --output docs/ai/evidence/d004-warm-reranking.json
uv run python scripts/profile_bge_runtime.py --scenario concurrency-2 --output docs/ai/evidence/d004-concurrency-2.json
uv run python scripts/profile_bge_runtime.py --scenario ingestion-embedding --output docs/ai/evidence/d004-ingestion-embedding.json
uv run python scripts/profile_bge_runtime.py --aggregate docs/ai/evidence/d004-baseline.json docs/ai/evidence/d004-embedding-load.json docs/ai/evidence/d004-reranker-load.json docs/ai/evidence/d004-both-loaded.json docs/ai/evidence/d004-warm-embedding.json docs/ai/evidence/d004-warm-reranking.json docs/ai/evidence/d004-concurrency-2.json docs/ai/evidence/d004-ingestion-embedding.json --output docs/ai/evidence/step-8.3-d004-bge-runtime-profile.json
```

RSS is host process RSS sampled using `psutil.Process(...).memory_info().rss`; it does not include all accelerator VRAM. The profiler does not force framework cache release. These results are environment-specific and per process. No conclusions should be extrapolated to multiple workers or other hardware. A later deployment recommendation should include reasonable measured headroom; the harness does not choose that amount.

## Scope and handoff

No live OpenAI, Tavily, web, database, or external-provider calls are made. No production provider behavior, RAG orchestration, DB schema, API contract, deployment configuration, worker/queue architecture, or model identity/revision was changed. D-005 is unchanged. No production placement or provider choice is made here.

**D-004 remains OPEN.** Recommended next action: independent AI/RAG Specialist review of the corrected harness, then run the real scenarios on an environment that passes the profiler guard. PM reviews measured evidence and freezes D-004.
