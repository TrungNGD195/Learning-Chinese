# Codex Task — Step 8.3 / D-004 BGE Runtime Profiling

**Role:** AI / RAG Specialist implementation support  
**Target:** produce profiling evidence only  
**Status before execution:** READY_FOR_PM_FREEZE — design only  

## Hard guardrails

Do **not** deploy production, choose a hosting vendor, choose local-vs-hosted BGE, change embedding/reranking semantics, change models, quantize, optimize, add workers/queues, or modify public APIs/persistence.

D-004 requires measurement first. D-005 remains bounded synchronous ingestion with `DOCUMENT_MAX_UPLOAD_MB=20`; this task profiles only the embedding portion of ingestion.

## Current implementation to measure

Inspect the current checkout first and verify these accepted identities before running:

- Embedding provider boundary: `EmbeddingProvider`; local implementation `SentenceTransformerEmbeddingProvider`.
- Embedding model: `BAAI/bge-m3`.
- Embedding revision currently frozen in Settings: `5617a9f61b028005a4858fdac845db406aefb181`.
- Dense dimensions: 1024; input version `v1`; normalization enabled.
- Embedding device: `EMBEDDING_DEVICE=auto`; batch size default 32.
- Embedding provider factory is process-cached. Record whether the actual current provider loads eagerly or on first use; do not guess.
- Reranker provider boundary: `RerankerProvider`; current local implementation `TransformersRerankerProvider` using `AutoTokenizer` + `AutoModelForSequenceClassification`.
- Reranker model: `BAAI/bge-reranker-v2-m3`.
- Reranker revision: `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`.
- Reranker device: `RERANKER_DEVICE=auto`; batch size 8; production candidate pool <=20; top-k 5; input version `v1`.
- Reranker provider factory uses `lru_cache(maxsize=1)` and the model is lazy-loaded on first use then retained per process.
- Relevant locked ML dependencies currently include `sentence-transformers==6.1.0`, `transformers==5.18.0`, `torch==2.14.1`; record actual installed versions at benchmark time rather than trusting the task text.

Current learner path to preserve/measure conceptually:

```text
RagOrchestrator._score_tier
→ SemanticRetrievalService.retrieve
→ get_embedding_provider()
→ embed_query(normalized_query)
→ vector search/hydration (NOT benchmarked here)
→ RerankingService.rerank
→ get_reranker_provider()
→ validate pair lengths
→ sequential score batches of size 8
```

Current ingestion embedding path to preserve/measure conceptually:

```text
persisted Chunk[]
→ EmbeddingInputFormatter/v1
→ configured sequential batches (default 32)
→ EmbeddingProvider.embed_documents(...)
→ vector validation/persistence
```

Profile only formatter + embedding inference throughput; do not benchmark parsing/transformation/chunking or DB persistence for D-004.

## Representative data

Prefer current repo-controlled Phase-7/evaluation fixtures and existing permitted knowledge fixtures. Never use production/private learner data.

Selection must be deterministic and written into the evidence manifest:

1. **Learner query set:** select 10 APPROVED DEVELOPMENT questions from internal-BGE-relevant buckets, prioritizing `CURRENT_LESSON_ANSWERABLE` and `INTERNAL_KB_FALLBACK`, sorted by stable `case_id`.
2. **Reranker sets:** use real repo-controlled passage/candidate text associated with those cases where current evaluation fixtures/artifacts expose it. Benchmark exactly 20 passages per measured rerank case when enough candidates exist, matching the production candidate pool. Do not duplicate text just to reach 20; if a case has fewer, choose another eligible case and record the selected case IDs.
3. **Ingestion embedding set:** use 64 unique repo-controlled Chunk/knowledge fixture inputs, deterministically ordered by stable locator/chunk order, and run them through the current `EmbeddingInputFormatter/v1`. This gives two default 32-item batches. If the current permitted fixture corpus has fewer than 64 unique inputs, use all available, record the count, and mark the throughput evidence limitation; do not synthesize a large corpus.

If Phase-7 fixture layout differs, reuse its existing loader/manifest conventions rather than copying a new parallel evaluation framework. The output JSON must list exact source fixture paths, dataset version when available, selected case IDs/stable locators, counts, and text-size statistics; do not copy private source text into the report unless already safe repo fixture content.

## Tooling

Use existing project tooling first.

For process RSS, Python `tracemalloc` is insufficient. If `psutil` is not already available, add **psutil only to the backend dev/profiling dependency group**, update `uv.lock`, and never import it from production application modules.

Use `psutil.Process(os.getpid()).memory_info().rss` for current RSS and a lightweight sampling thread (default 50 ms interval) for observed peak RSS. This captures process-level native ML allocations visible in host RSS.

If CUDA/MPS is actually selected, optionally record PyTorch device-memory counters when available, but host RSS remains mandatory. State clearly that RSS does not include all accelerator VRAM.

No live OpenAI, Tavily, web, database vendor, or other external service calls are allowed.

Set offline model-loading environment for benchmark child processes (`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1` or the equivalent supported by the installed stack). Model files must already exist in the local cache. Download time is not part of cold-load evidence.

## Minimum files

Follow actual repo conventions, but keep this minimal:

```text
backend/scripts/profile_bge_runtime.py
docs/ai/step-8.3-d004-bge-runtime-profiling.md
docs/ai/evidence/step-8.3-d004-bge-runtime-profile.json
```

A tiny fake-provider/unit test for pure statistics/output serialization may be added if useful, but do not put real-model profiling in the normal unit-test suite.

The JSON/Markdown evidence is profiling evidence, not a production runtime artifact.

## Harness architecture

Use a parent process that invokes fresh child processes for scenarios where clean model residency matters. A single script may expose internal subcommands; do not create a profiling framework.

Recommended scenarios:

```text
environment
baseline
embedding-only
reranker-only
both-loaded
warm-embedding
warm-reranking
concurrency-2
ingestion-embedding
```

A child process must import the normal application/provider code and use the current provider/service boundaries. Do not copy model-loading logic into the profiler.

### Baseline definition

Define baseline RSS as a fresh process after importing the normal backend application/config/provider modules needed for profiling and resolving Settings, but before forcing either BGE model resident. Record the exact baseline definition in JSON/Markdown.

## Environment identity

Record at minimum:

- UTC timestamp;
- git commit (`git rev-parse HEAD`) when available, otherwise null + explanation;
- OS/platform/release/machine;
- CPU model string;
- physical/logical core counts when available;
- total RAM;
- Python version;
- installed `sentence-transformers`, `transformers`, `torch`, `numpy`, and `psutil` versions when present;
- requested and resolved embedding device;
- requested and resolved reranker device;
- exact provider identities/model names/revisions/input versions;
- embedding dimensions/normalization/batch size;
- reranker batch size/top-k/candidate count configuration.

Do not infer the resolved device from config alone; query the actual provider/runtime.

## Memory methodology

Measure host process RSS in bytes and MiB.

Required states:

```text
baseline RSS
embedding-only steady RSS
reranker-only steady RSS
both-loaded steady RSS
observed peak RSS for each load/inference scenario
```

For steady RSS, after model load + one warm inference, wait briefly (for example 1 second) while sampling and report the median of the final steady samples. Do not force framework caches to free memory; retained allocator/model memory is deployment-relevant.

For both-loaded state, load the embedding and reranker in the **same process**, run one representative embedding and rerank operation, then sample steady and peak RSS.

Cold-load scenarios must use fresh processes so previous provider/model caches do not contaminate the result.

## Cold-load methodology

Run **3 fresh-process repetitions per model**.

Measure the current implementation's model-residency transition without changing provider architecture.

- If the actual provider exposes an existing internal loader used by production, the profiling script may call that existing loader for measurement only.
- Do not add a new production `load()` API solely for profiling.
- If a provider only loads through first public inference, measure and label it honestly as `cold_first_use_ms`; do not pretend it is pure load time.

Report each repetition and median. Cold means fresh Python/application process with model files already in local cache; it does **not** mean uncached model download or guaranteed cold OS page cache.

## Warm embedding latency

Measure current query-embedding behavior only; no vector DB query.

- provider/service path: current `EmbeddingProvider.embed_query` path;
- deterministic 10-query fixture rotation;
- 5 warm-up calls excluded from statistics;
- 30 measured calls;
- one query per measured call, matching learner retrieval behavior;
- record query character/UTF-8 byte statistics (and token length if cheaply available through the current tokenizer without changing semantics);
- report raw sample durations plus p50 and p95.

Use nearest-rank p95 (document the exact calculation) and standard median p50.

## Warm reranking latency

Measure `RerankingService.rerank(...)` (not only raw model.forward) so formatter/input validation/configured batching reflect current application behavior while DB/retrieval remain excluded.

- candidate count: 20 per measured case;
- configured batch size: 8;
- 3 warm-up reranks excluded;
- 30 measured reranks;
- deterministic rotation across eligible real fixture cases;
- record query length and passage min/median/max/total character or byte statistics;
- report raw samples, p50, p95, error count, candidate count, batch count.

Do not change rerank batching, top-k, score semantics, or input formatting for the benchmark.

## Both-loaded application-like state

After both models are resident in one process, execute a representative internal tier scoring workload:

```text
embed_query(query)
→ rerank(query, 20 fixture candidates)
```

Record end-to-end BGE-only workload latency and RSS/peak RSS. No DB, OpenAI, Tavily, prompt generation, or network calls.

Note in the report that current RAG may execute more than one internal tier when fallback occurs; do not extrapolate a two-tier latency number unless a separate measured scenario is actually run.

## Concurrency methodology

Measure **exactly the current same-process call behavior**, not a hypothetical optimized runtime.

Primary scenario:

```text
2 learner-style BGE-only workloads arrive together
Each workload:
  embed_query(query)
  → rerank(query, 20 candidates)
```

- both models already warm/resident;
- 2 warm-up workloads before concurrency samples;
- 10 repetitions of a pair of 2 concurrent arrivals;
- use the current synchronous provider/service calls inside an asyncio-style same-process harness if that matches the actual FastAPI path;
- do **not** use `asyncio.to_thread`, a thread pool, extra Uvicorn workers, multiprocessing, or a worker queue unless the current production code already does so;
- use one common arrival timestamp per pair so reported per-request latency includes waiting/serialization;
- record both request completion latencies, pair makespan, errors, and peak RSS;
- report whether observed inference sections overlap or effectively serialize based on timestamps/evidence.

Do not extrapolate to concurrency >2 or multiple server processes.

## Ingestion embedding throughput

Use the selected real 64 unique embedding inputs (or all available if fewer) after the current formatter.

- model already warm;
- configured batch size must remain `Settings.embedding_batch_size` (expected current default 32);
- run one warm-up batch excluded from measurement when enough inputs exist;
- then measure the full selected unique set once; optionally repeat the complete fixed set 3 times only if total runtime is reasonable, reporting each run rather than multiplying/duplicating inputs inside one run;
- record chunk/input count;
- total/mean/min/max character or UTF-8 byte volume;
- batch size and number of batches;
- elapsed seconds;
- chunks/sec;
- steady and peak RSS when practical;
- errors.

Do not include parsing, cleaning, transformation, chunking, DB persistence, vector indexing, or activation timing.

## Output schema

Machine-readable JSON should contain sections equivalent to:

```text
schema_version
timestamp_utc
git_commit
environment
models
fixture_manifest
parameters
memory
cold_load
warm_embedding
warm_reranking
both_loaded_workload
concurrency_2
ingestion_embedding
limitations
```

Store raw timing samples as well as aggregates so PM can verify p50/p95 calculations.

The Markdown report should summarize evidence, not repeat every raw sample.

## Interpretation rules

The profiling implementation must **not** choose local-vs-hosted inference or a hosting provider.

It may derive evidence statements only from measured results, for example:

- observed both-loaded RSS already exceeds a candidate host RAM ceiling;
- a host would leave very little measured headroom;
- measured result is inconclusive on another environment;
- concurrency-2 effectively serializes and increases request latency;
- ingestion embedding throughput is X chunks/sec on this environment.

Always recommend some deployment headroom; do not define an arbitrary enterprise target. Clearly label measurements as environment-specific and per-process.

If the future production server uses multiple worker processes, model memory may be duplicated per process; do not multiply until worker count/topology is actually selected.

## Acceptance criteria

- [ ] No production deployment/provider choice is implemented.
- [ ] No embedding/reranking model or semantic behavior is changed.
- [ ] Exact current model names/revisions/config and actual resolved devices are recorded.
- [ ] Environment identity includes OS/CPU/cores/RAM/Python/library versions/git commit when available.
- [ ] RSS is process-level, not `tracemalloc` only.
- [ ] Baseline, embedding-only, reranker-only, both-loaded steady RSS are reported.
- [ ] Observed peak RSS is sampled/reported where measurable.
- [ ] Embedding and reranker cold process-load/first-use behavior is measured independently.
- [ ] Warm embedding reports 5 warmups, 30 samples, p50/p95 and input sizes.
- [ ] Warm reranking reports 3 warmups, 30 samples, 20 candidates, batch configuration, p50/p95 and passage characteristics.
- [ ] Both models are measured resident in the same process.
- [ ] Two concurrent learner-style BGE workloads are measured for 10 pair repetitions without introducing thread/worker parallelism absent from current code.
- [ ] Concurrency report includes latency impact, errors, peak RSS and observed serialization/overlap evidence.
- [ ] Ingestion embedding throughput uses real repo-controlled inputs and reports count/volume/batch/elapsed/chunks-sec/memory.
- [ ] No live OpenAI/Tavily/web calls occur.
- [ ] Models are loaded from local cache during benchmark; network download time is excluded.
- [ ] Fixture/data identity is sufficient to reproduce the run and contains no private production/user data.
- [ ] JSON evidence + Markdown report are produced.
- [ ] `psutil`, if needed, is dev/profiling-only.
- [ ] No Redis/Celery/queue/worker/background architecture is added.
- [ ] No Step 8.3 deployment implementation is started.

## Verification

Run the profiler from the locked backend environment. Also run a lightweight script/unit check for JSON schema/statistics helpers if added, plus existing relevant AI tests to prove no production semantics changed.

Report exact commands and results.

## Required handoff

Return:

```text
Step / Subtask
Status
Repository state verified
Files changed
Dependencies/tooling change
Exact environment/model identity
Fixture/data identity
Benchmark parameters
Memory results
Cold-load results
Warm embedding p50/p95
Warm reranking p50/p95
Both-loaded result
Concurrency-2 result
Ingestion embedding throughput
Measurement limitations
Decisions needed
Evidence JSON path
Markdown report path
Recommended next action
```

Expected implementation handoff status:

```text
PASS_FOR_SPECIALIST_REVIEW — D-004 BGE RUNTIME PROFILE EVIDENCE
```

Do not claim the D-004 local-vs-hosted decision yourself. PM freezes that decision only after reviewing measured evidence against candidate production host limits.
