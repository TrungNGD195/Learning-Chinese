# Step 8.3 — Modal BGE Runtime Validation — Stage A

## Status

**Stage A implementation draft; real Modal validation not run.** This code prepares the existing embedding and reranking provider boundaries for hosted inference. Local providers remain the default for development and tests. No Modal authentication, deployment, remote call, GPU allocation, or paid usage occurred in Stage A.

## Problem

The frozen BGE embedding and reranking models are too heavy for the production FastAPI process under D-111. D-112 selects Modal as the hosted inference vendor, while leaving the production GPU tier open. D-113 requires Modal embedding provenance to remain honest, and D-114 requires inference at the application boundary to be asynchronous.

## Concept

The application continues to own retrieval, persistence, RAG fallback, citations, and business rules. `ModalBgeClient` owns only class lookup, native async invocation, and safe transport error normalization. The Modal runtime owns model loading and inference only.

Frozen provider identities:

| Capability | Provider identity | Model identity |
| --- | --- | --- |
| Embedding | `MODAL` / `modal-bge-runtime/v1` | `BAAI/bge-m3` / `5617a9f61b028005a4858fdac845db406aefb181`, 1024 dimensions, input `v1`, normalized dense vectors |
| Reranking | `MODAL` / `modal-bge-runtime/v1` | `BAAI/bge-reranker-v2-m3` / `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`, input `v1`, raw scores |

The current ACTIVE `EmbeddingProfile` identity guard remains unchanged. If runtime embedding identity is Modal while the ACTIVE profile remains LOCAL, retrieval fails safely. Stage A creates no production Modal profile and re-embeds no production data.

## Mental Model

```text
FastAPI request
  → existing async provider protocol
  → local provider (default) or Modal adapter
  → ModalBgeClient awaits method.remote.aio(...)
  → inference-only Modal class
```

Local SentenceTransformers and PyTorch computation remains synchronous inside the new `async def` provider methods; no thread pool or `asyncio.to_thread` is added. Embedding retrieval still closes its profile-read transaction before awaiting inference and starts a separate short transaction for vector retrieval.

## Data Flow

1. Settings choose `EMBEDDING_PROVIDER` and `RERANKER_PROVIDER`, each defaulting to `local`.
2. Factories return the existing local providers or the corresponding Modal adapters.
3. Internal and trusted-external reranking await the same async reranker protocol. Candidate limits, sequential batches of eight, raw scores, deterministic ordering, Top 5, trusted-domain rules, and calibrated threshold behavior remain unchanged.
4. The Modal class returns primitive envelopes containing contract, operation, exact model/revision, runtime versions, device, and result data. Adapters validate the envelope and outputs before returning them to the existing services.

## Configuration and errors

Modal selection requires server-side `MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET`, `MODAL_ENVIRONMENT`, `MODAL_BGE_APP_NAME`, and `MODAL_BGE_CLASS_NAME`. Token settings use `SecretStr`; example values are blank. Production Settings require both BGE providers to be Modal. Development and test stay local unless explicitly selected.

Deterministic remote errors map to existing application errors: embedding/reranker input too long and invalid outputs retain their existing codes. Modal lookup/auth failures stay provider availability failures; inference/transport failures stay technical failures. Error messages do not expose SDK details, credentials, request text, vectors, or tensors. Reranker inference has no automatic retry and no local threshold; `RAG_MIN_RERANK_SCORE` is unchanged.

## Modal runtime definition

`backend/modal_bge/runtime.py` defines the inference-only class, exact frozen revisions, a cache-population function for later authorized use, and a validation-only resource definition of T4, zero minimum containers, maximum two containers, and zero retries. Inference is configured for Hugging Face offline mode after the exact model revisions are staged. Dynamic batching, in-container concurrency, memory snapshots, quantization, and precision overrides are absent. T4 is only the first Stage B evidence candidate; it does not freeze production GPU placement.

## Stage A proof

Stage A uses local unit fakes only. Fake Modal methods expose `.remote.aio`; calling blocking `.remote()` fails the test. Configuration, identity, envelope, dimensionality, normalization, batching, finite-score, safe-error, and semantic evidence-completeness checks do not contact Modal. A fake/injected Modal lookup is explicitly marked non-real and cannot pass pending or final evidence validation, even when it returns otherwise complete fake runtime data. The real evidence flag is derived from the non-injected Modal SDK client and matching runtime metadata for the frozen model revisions, CUDA device, GPU, and package versions. The Stage-B harness refuses real execution unless both its explicit command flag and `STEP83_STAGE_B_AUTHORIZED=true` are provided. It captures a billing-before reference before running; measurements are written as `BILLING_AFTER_PENDING` and cannot pass canonical validation until an offline finalize action adds a valid billing-after reference.

No real Modal token was read by the SDK. No Modal deployment, cache population, volume creation, remote inference, GPU allocation, or Stage-B evidence file was created.

## Stage B authorization and validation plan

Stage B requires a Modal workspace, successful authentication, a verified billing/credit state, explicit user authorization for any usage, and separate PM approval. If available credit or cost is unclear, stop before invocation. The harness records git commit, SDK/app/class/contract identity, GPU/VRAM, runtime package/model identities, deterministic local-versus-Modal parity, cold initialization, warm embedding (5 warmups and 30 samples), 20-candidate reranking (3 warmups and 30 samples), combined workloads, ten same-arrival concurrency pairs, VRAM readings, and billing references. The parity gate scores all 20 candidates locally and remotely in sequential batches of 8, 8, and 4; the evidence validator requires the complete score/order/threshold-decision arrays and records this batching for parity, warm reranking, and combined workloads. Each concurrency request records common-arrival latency and execution duration; each pair records makespan. A threshold-decision parity mismatch stops before performance measurements.

Parity compares vector dimensions, finite/unit-norm state and numeric deltas; reranker parity compares raw scores, order, and the frozen `RAG_MIN_RERANK_SCORE` decisions. Any changed threshold decision stops measurement for specialist/PM review; it does not retune the threshold.

Production Modal `EmbeddingProfile` creation/activation and production corpus re-embedding remain deferred to an authorized rollout plan. Production GPU tier and backend host are not selected here.

## Scope and risks

- Public APIs, schemas, database tables, migrations, ingestion rules, RAG tiers, and citation behavior are unchanged.
- Step 6.8-B still uses the shared reranker boundary and keeps its separate candidate pool.
- D-005 and `RAG_MIN_RERANK_SCORE` are unchanged.
- Local model code remains in the dependency set and is not optimized in this task.
- Modal SDK behavior, deployed class lookup, actual model parity, latency, cold start, VRAM, and cost remain unverified until Stage B.
- Async local model methods still run their CPU/GPU computation on the event loop. This preserves the accepted local implementation behavior; it is not the production Modal path.

## Step Note

**Concepts**

- Async AI provider boundary | SYSTEM
- Hosted BGE inference boundary | SYSTEM
- Provider/model identity compatibility | BOTH
- Modal runtime contract | SYSTEM
- Stage-B runtime validation evidence | SYSTEM

**Tools**

- Python | SYSTEM
- FastAPI | SYSTEM
- Modal | SYSTEM
- PyTorch | SYSTEM
- SentenceTransformers | SYSTEM
- Transformers | SYSTEM
- pytest | SYSTEM
- uv | SYSTEM

## Decision state

- D-111: implemented in production Settings validation; production must select Modal for both BGE providers.
- D-112: Modal adapter boundary authored; production GPU tier remains OPEN.
- D-113: Modal identity is `MODAL / modal-bge-runtime/v1`; existing profile guard stays authoritative.
- D-114: embedding and reranker inference interfaces/call sites are async; Modal invocation uses `.remote.aio`.
- D-005: unchanged.
- Stage B, GPU allocation, and production profile migration: not started.
