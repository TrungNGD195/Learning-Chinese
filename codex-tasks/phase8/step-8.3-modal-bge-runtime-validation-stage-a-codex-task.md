# Codex Task — Step 8.3 Modal BGE Runtime Validation — Stage A

**Status: FINAL FOR PM REVIEW — READY TO FREEZE AS CODEX-READY**

> Do not execute this task until PM explicitly freezes this exact packet as `CODEX-READY`.
>
> Stage A is LOCAL-ONLY implementation/testing. It must not authenticate to Modal, deploy a Modal App, create/populate a remote Volume, allocate a GPU, run T4, or incur Modal usage.
>
> Real Modal execution is Stage B and requires a separate PM/user authorization after account + billing/credit preflight.

---

## 1. Objective

Implement the smallest safe provider-boundary change required by the frozen production decisions:

```text
FastAPI modular monolith
→ existing EmbeddingProvider / RerankerProvider boundaries
→ Modal-backed adapters
→ later Stage B Modal inference runtime
```

Stage A must:

- make embedding/reranker inference methods async per D-114;
- preserve local provider behavior as the default;
- add Modal-backed provider adapters without making real Modal calls in tests;
- preserve exact BGE model/revision semantics;
- preserve the existing ACTIVE EmbeddingProfile compatibility guard;
- update every existing call site affected by the async boundary;
- author the inference-only Modal runtime definition and Stage-B validation harness/schema without deploying/running them;
- keep D-005 and public RAG behavior unchanged.

---

## 2. Frozen PM decisions

### D-111 — Production BGE placement

Production must not run both frozen BGE models in the FastAPI process.

Production BGE inference uses hosted/dedicated inference behind the existing provider boundary.

### D-112 — Hosted inference vendor

Modal is the selected production BGE inference vendor.

The production GPU tier remains OPEN.

The first real validation candidate is T4 for evidence collection only.

### D-113 — Modal Embedding Provider Identity

Frozen embedding identity:

```text
provider = MODAL
provider_version = modal-bge-runtime/v1
```

Do not:

- masquerade Modal as `LOCAL`;
- remove/weaken the ACTIVE EmbeddingProfile identity compatibility guard;
- modify the current LOCAL profile;
- create/activate a production Modal EmbeddingProfile in Stage A;
- re-embed production data in Stage A.

### D-114 — Async AI Provider Boundary

Embedding and reranker inference methods become async.

Modal adapters must use native Modal async invocation.

Do not use:

- blocking Modal `.remote()` from the async FastAPI/RAG path;
- `asyncio.to_thread`;
- thread pools;
- workers/queues.

Local model implementations may keep their existing synchronous PyTorch/SentenceTransformers work inside `async def` methods. Optimizing local inference is out of scope.

---

## 3. Frozen model semantics

### Embedding

```text
model_name = BAAI/bge-m3
model_revision = 5617a9f61b028005a4858fdac845db406aefb181
dimensions = 1024
embedding_input_version = v1
normalize_embeddings = true
dense embeddings only
```

### Reranker

```text
model_name = BAAI/bge-reranker-v2-m3
model_revision = 953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e
reranker_input_version = v1
candidate pool <= 20
batch size = 8
top-k = 5
raw score, higher = better
no reranker-local threshold
no automatic retry
```

Do not change `RAG_MIN_RERANK_SCORE`.

---

## 4. Repository reconciliation — current source contracts

Codex must first inspect the exact checkout and reconcile against these accepted current paths/contracts before editing.

If a listed existing path is absent or materially different, STOP and report the conflict rather than creating a duplicate implementation.

### 4.1 Embedding boundary

Accepted Step 6.1 boundary:

```text
backend/app/ai/embeddings/provider.py

EmbeddingProvider
├── identity: EmbeddingProviderIdentity
├── embed_documents(texts, *, batch_size)
└── embed_query(text)

get_embedding_provider()
→ cached SentenceTransformerEmbeddingProvider
→ BAAI/bge-m3
```

Identity fields:

```text
provider
provider_version
model_name
model_version
dimensions
embedding_input_version
normalize_embeddings
```

Existing implementation modules are under:

```text
backend/app/ai/embeddings/
```

including the current provider, local SentenceTransformer provider, service, schemas and errors.

Before patching ingestion, run a source search equivalent to:

```text
rg "embed_documents\(" backend/app backend/tests backend/scripts
```

Update the actual existing Step 6.1 embedding service/call sites; do not create a second embedding service.

### 4.2 Semantic retrieval

Actual current file:

```text
backend/app/ai/retrieval/service.py
```

Current flow:

```text
resolve ACTIVE EmbeddingProfile inside short DB read transaction
→ close transaction
→ exact provider.identity == profile identity check
→ provider.embed_query(...)
→ validate dimensions/finite/norm
→ pgvector retrieval in later short transaction
```

Preserve the exact compatibility check.

Current query provider call is synchronous and must become:

```python
vector = await provider.embed_query(normalized_query)
```

No DB transaction may span remote inference.

### 4.3 Internal reranking

Actual files:

```text
backend/app/ai/reranking/provider.py
backend/app/ai/reranking/transformers_provider.py
backend/app/ai/reranking/service.py
backend/app/ai/reranking/schemas.py
backend/app/ai/reranking/errors.py
```

Current `RerankerProvider`:

```python
class RerankerProvider(Protocol):
    @property
    def identity(self) -> RerankerProviderIdentity: ...

    @property
    def device(self) -> str: ...

    def validate_pair_lengths(self, query: str, passages: list[str]) -> None: ...

    def score(self, query: str, passages: list[str]) -> list[float]: ...
```

Current `RerankingService.rerank()` is synchronous and:

- validates candidate DTOs;
- truncates the scoring pool to max 20;
- uses `RerankPassageFormatter`;
- checks provider identity;
- validates pair lengths;
- processes batches sequentially with configured batch size 8;
- validates finite/count-correct scores;
- sorts by `rerank_score DESC`, semantic rank, chunk id;
- returns Top 5 while retaining all scored candidates;
- does not apply the evidence threshold.

It currently hard-codes expected provider `"LOCAL"`. Update that expected provider according to Settings while preserving model/revision/input-version validation.

### 4.4 Trusted external reranking — required D-114 call site

Actual file:

```text
backend/app/ai/external_retrieval/reranking.py
```

`ExternalRerankingService` uses the same `RerankerProvider`, currently synchronously, and also hard-codes expected provider `"LOCAL"`.

Because D-114 changes the shared provider protocol:

- `ExternalRerankingService.rerank()` must become async;
- await `validate_pair_lengths`;
- await every sequential `score` batch;
- preserve exact trusted-external threshold/order/error semantics;
- update its provider identity expectation for `local|modal`;
- do not alter D-094 allowlist or external evidence behavior.

### 4.5 RAG orchestrator

Actual file:

```text
backend/app/ai/rag/orchestrator.py
```

Current internal tier:

```python
candidates = await retrieval.retrieve(...)
result = self.reranker.rerank(query, candidates)
```

Change only the required boundary:

```python
result = await self.reranker.rerank(query, candidates)
```

Current external branch calls:

```python
external_result = self.external_reranking_service.rerank(...)
```

Change only to:

```python
external_result = await self.external_reranking_service.rerank(...)
```

Do not change tier fallback/evidence semantics.

### 4.6 Existing D-004 profiling harness

Current accepted files:

```text
backend/scripts/profile_bge_runtime.py
backend/tests/test_profile_bge_runtime.py
```

They call:

- `embedding.embed_query(...)`;
- `embedding.embed_documents(...)`;
- `RerankingService.rerank(...)`.

D-114 will otherwise break this accepted tooling.

Update the script/tests only enough to await the now-async local interfaces while preserving the already-frozen D-004 measurement semantics.

Do NOT rerun the real D-004 benchmark in Stage A.
Do NOT reinterpret/replace the accepted CPU evidence.

### 4.7 Settings

Actual file:

```text
backend/app/core/config.py
```

Current fields include:

```text
embedding_provider: Literal["local"] = "local"
reranker_provider: Literal["local"] = "local"

exact frozen embedding/reranker model names and revisions
embedding_batch_size = 32
reranker_batch_size = 8
reranker_top_k = 5
```

Actual example env:

```text
backend/.env.example
```

Local must remain the default.

---

## 5. Final async interfaces

### 5.1 Embedding provider

Preserve the actual `batch_size` keyword argument:

```python
class EmbeddingProvider(Protocol):
    @property
    def identity(self) -> EmbeddingProviderIdentity: ...

    async def embed_documents(
        self,
        texts: list[str],
        *,
        batch_size: int,
    ) -> list[list[float]]: ...

    async def embed_query(
        self,
        text: str,
    ) -> list[float]: ...
```

Convert the existing `SentenceTransformerEmbeddingProvider` methods to `async def` without thread offloading or model-semantic changes.

### 5.2 Reranker provider

```python
class RerankerProvider(Protocol):
    @property
    def identity(self) -> RerankerProviderIdentity: ...

    @property
    def device(self) -> str: ...

    async def validate_pair_lengths(
        self,
        query: str,
        passages: list[str],
    ) -> None: ...

    async def score(
        self,
        query: str,
        passages: list[str],
    ) -> list[float]: ...
```

Convert the existing local Transformers provider methods to async with the same local inference implementation.

### 5.3 Reranking services

Make both:

```text
RerankingService.rerank(...)
ExternalRerankingService.rerank(...)
```

async because they await the provider.

No other service becomes async merely for consistency.

---

## 6. Modal client/adapters

Add the smallest shared Modal SDK boundary.

Recommended new FastAPI-side files:

```text
backend/app/ai/modal_bge/__init__.py
backend/app/ai/modal_bge/client.py
backend/app/ai/modal_bge/schemas.py

backend/app/ai/embeddings/modal_provider.py
backend/app/ai/reranking/modal_provider.py
```

Do not create a generic multi-vendor inference framework.

### 6.1 ModalBgeClient responsibility

Only:

- resolve the deployed Modal `Cls` by configured App/Class name;
- call the required class method with native async invocation;
- apply a local caller timeout if implemented by existing project convention;
- normalize Modal SDK transport/auth/not-found/timeout/resource/remote failures into a small internal vendor error;
- return primitive response envelopes for provider validation.

It must not know:

- DB/session;
- EmbeddingProfile rows;
- retrieval scope;
- candidate DTO provenance;
- RAG fallback;
- prompt/LLM;
- citations;
- conversation state.

### 6.2 Async invocation invariant

The Modal client must call methods using:

```python
await method.remote.aio(...)
```

Tests must use a fake Modal method whose blocking `.remote()` path raises `AssertionError`.

No production Modal adapter test may pass if `.remote()` is invoked.

### 6.3 Embedding Modal provider identity

Exactly:

```text
provider = MODAL
provider_version = modal-bge-runtime/v1
model_name = BAAI/bge-m3
model_version = 5617a9f61b028005a4858fdac845db406aefb181
dimensions = 1024
embedding_input_version = v1
normalize_embeddings = true
```

The existing retrieval compatibility guard remains authoritative.

Therefore, if runtime config selects Modal while the ACTIVE DB profile is still LOCAL:

```text
identity mismatch
→ existing safe QUERY_EMBEDDING_FAILED path
```

This is expected and must be tested.

Stage A must not create a production MODAL EmbeddingProfile just to make that guard pass.

Test-scoped database profile fixtures with the MODAL identity are allowed.

### 6.4 Reranker Modal provider identity

The reranker has no persisted EmbeddingProfile, but must report honest execution identity:

```text
provider = MODAL
provider_version = modal-bge-runtime/v1
model_name = BAAI/bge-reranker-v2-m3
model_revision = 953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e
reranker_input_version = v1
```

Update both internal and external reranker service identity checks to expect:

```text
settings.reranker_provider == "local" → LOCAL
settings.reranker_provider == "modal" → MODAL
```

For Modal require `provider_version == "modal-bge-runtime/v1"`.

For local preserve the current non-empty local runtime version check.

`ModalRerankerProvider.device` may return a non-network runtime label such as `"modal"` for FastAPI structured logging. Actual CUDA/GPU identity comes from Stage-B remote runtime evidence, not this property.

---

## 7. Remote inference contract

Stage A authors this contract and the runtime code but does not invoke/deploy it.

Use primitive serializable envelopes.

### 7.1 Common success metadata

Every success result contains at least:

```text
ok = true
contract_version = modal-bge-runtime/v1
operation
model_name
model_revision
runtime_versions
device
```

Adapters reject:

- wrong contract version;
- wrong model name;
- wrong model revision;
- wrong operation;
- malformed result.

### 7.2 Structured deterministic failure envelope

For deterministic model/input contract failures, return:

```text
ok = false
contract_version = modal-bge-runtime/v1
error_code
safe_message
```

Do not rely on arbitrary remote traceback strings for:

```text
EMBEDDING_INPUT_TOO_LONG
RERANK_INPUT_TOO_LONG
INVALID_EMBEDDING_OUTPUT
INVALID_RERANKER_OUTPUT
```

Unexpected container/runtime failures may propagate through Modal and are normalized client-side as technical provider failures.

### 7.3 Embedding query

Input:

```text
text: non-empty string
```

Output:

```text
vector: list[float]
len(vector) == 1024
finite
L2 normalized
```

Existing FastAPI retrieval vector validation remains in place.

### 7.4 Embedding documents

Input:

```text
texts: non-empty list[str]
batch_size: positive int
```

The existing FastAPI `EmbeddingInputFormatter/v1` remains authoritative.

Do not send Chunk/ORM/business objects to Modal.

Output:

```text
vectors
count == input count
each vector length == 1024
finite
L2 normalized
```

Existing Step 6.1 output validation remains authoritative before persistence.

### 7.5 Reranker pair-length validation

Input:

```text
query
passages
```

Use the exact frozen tokenizer/revision.

No silent truncation.

### 7.6 Reranker scoring

Input:

```text
query
passages
```

Output:

```text
raw scores
count == passages count
all finite
```

Do not normalize scores.
Do not apply `RAG_MIN_RERANK_SCORE`.
Do not discover/fetch candidates.

---

## 8. Error mapping

Use existing project errors; do not invent public API errors solely because Modal exists.

### 8.1 Embedding

Remote deterministic too-long:

```text
→ existing EMBEDDING_INPUT_TOO_LONG
```

Remote malformed/invalid vector result:

```text
→ existing INVALID_EMBEDDING_OUTPUT / existing Step 6.1 validation path
```

Modal SDK auth/permission/not-found/timeout/resource/remote-execution/transport failure:

```text
→ existing EMBEDDING_PROVIDER_FAILED (or the exact current equivalent in app.ai.embeddings.errors)
```

Semantic retrieval continues to normalize provider failures into the current Step 6.3 retrieval errors.

### 8.2 Reranker

Too long:

```text
→ RERANK_INPUT_TOO_LONG
```

Malformed score count/NaN/Inf:

```text
→ INVALID_RERANKER_OUTPUT
```

Modal lookup/auth/resource problem before usable inference:

```text
→ RERANKER_NOT_AVAILABLE
```

Remote inference/transport failure during scoring:

```text
→ RERANKER_INFERENCE_FAILED
```

No automatic retry.

Technical failure must never become semantic no-evidence or trigger an otherwise invalid evidence-tier transition.

Do not expose Modal exception details, tokens, request texts, vectors, or model tensors in client errors/logs.

---

## 9. Settings / environment changes

Modify:

```text
backend/app/core/config.py
backend/.env.example
```

### 9.1 Provider selectors

```python
embedding_provider: Literal["local", "modal"] = "local"
reranker_provider: Literal["local", "modal"] = "local"
```

Keep all frozen model/revision/input/batch/top-k fields unchanged.

### 9.2 Modal settings

Add only the minimum server-side fields:

```text
MODAL_TOKEN_ID
MODAL_TOKEN_SECRET
MODAL_ENVIRONMENT
MODAL_BGE_APP_NAME
MODAL_BGE_CLASS_NAME
```

Use `SecretStr | None` for token values.

Do not commit real values.

Modal config must be required only when a Modal provider is selected.

### 9.3 Production D-111 guard

When `APP_ENV=production`:

```text
EMBEDDING_PROVIDER must be modal
AND
RERANKER_PROVIDER must be modal
```

This implements D-111 as config validation.

Do not require Modal provider in development/test; local remains the default.

### 9.4 No GPU setting in FastAPI Settings

Do not add a production GPU-tier selector to application Settings in Stage A.

T4 belongs only to the validation runtime definition and is not a frozen production tier.

---

## 10. Modal SDK dependency

Modify:

```text
backend/pyproject.toml
backend/uv.lock
```

Add exact current reviewed SDK:

```text
modal==1.6.1
```

This is a normal runtime dependency because the FastAPI adapters will call Modal in production.

Preserve existing local ML dependencies and the D-004 profiling dev dependency.

Do not remove PyTorch/SentenceTransformers/Transformers in Stage A.

---

## 11. Modal validation runtime definition — author only

Add:

```text
backend/modal_bge/__init__.py
backend/modal_bge/runtime.py
```

This is an inference execution definition only, not a second application/business service.

It must not import or own DB/RAG/business modules.

Conceptual validation App:

```text
Modal App
└── BgeInference
    ├── @modal.enter() load exact embedding model
    ├── @modal.enter() load exact reranker model
    ├── runtime_info()
    ├── embed_query(...)
    ├── embed_documents(...)
    ├── validate_rerank_inputs(...)
    └── score_rerank(...)
```

### 11.1 Validation-only resource configuration

Author the first-evidence runtime with:

```text
gpu = T4
min_containers = 0
max_containers = 2
retries = 0
```

Do not enable:

- dynamic batching;
- in-container `@modal.concurrent`;
- memory snapshots;
- quantization;
- explicit fp16/bf16/autocast optimization.

This does not select the production GPU tier.

### 11.2 Exact model loading

Pin exact revisions.

Use current frozen package versions unless exact checkout proves PM has accepted newer versions:

```text
sentence-transformers==6.1.0
transformers==5.18.0
torch==2.14.1
```

No model substitution.

### 11.3 Model cache definition

Author the Volume/cache path and explicit cache-population function/entrypoint required by Stage B.

Stage A MUST NOT invoke it.

Inference runtime must be designed to run with:

```text
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
```

after the exact revisions are populated later.

Cold-start benchmark must never include initial model download.

---

## 12. Stage-B validation harness/schema — author only

Add:

```text
backend/scripts/validate_modal_bge_runtime.py
```

and focused tests.

Do not create a fake Stage-B result file.

The harness must be able to write later:

```text
docs/ai/evidence/modal-bge-validation/
├── preflight.json
└── t4-validation.json
```

but Stage A must not create `t4-validation.json`.

### 12.1 Real-evidence invariant

A real result requires:

```text
real_modal_runtime = true
```

Only the real Modal client execution path may set it.

Fake/local tests must be unable to generate an artifact accepted as real.

### 12.2 Stage-B target evidence schema

Prepare fields for:

```text
timestamp
git_commit
modal_sdk_version
modal_app_name
modal_class_name
contract_version

gpu_name
gpu_total_vram
torch_version
cuda_version

embedding model/revision
reranker model/revision
runtime package versions

fixture identity

parity results

cold start / model initialization
warm embedding raw samples + p50/p95
warm reranking 20-candidate raw samples + p50/p95
combined embed→rerank samples + p50/p95
concurrency=2 pair samples
VRAM allocated/reserved/max evidence
billing before/after metadata/reference
```

Stage A tests only schema/aggregation/fake rejection.

### 12.3 Real execution gate in the script

Real mode must fail closed unless an explicit Stage-B authorization flag/environment gate is present.

Do not call:

```text
modal token info
modal billing ...
modal run
modal deploy
remote.aio
```

during Stage A test execution.

---

## 13. Stage-B benchmark plan — documentation only

Document, do not run.

### 13.1 Prerequisites

Stage B may run only after:

1. Modal account/workspace exists.
2. Authentication succeeds.
3. Billing/credit status is checked.
4. User explicitly authorizes real-runtime usage.
5. PM approves Stage B.

If available credit/free allowance is insufficient or unclear:

```text
STOP
→ request user approval before paid usage
```

Do not automatically escalate from T4 to another GPU.

### 13.2 Parity gate before performance interpretation

Embedding:

```text
same deterministic fixtures
→ local exact frozen model
vs
→ Modal exact frozen model
→ dimension/norm/finite check
→ record numeric deltas
```

Reranker:

```text
same query/passages
→ local raw scores/order
vs
→ Modal raw scores/order
→ record deltas
→ explicitly check RAG_MIN_RERANK_SCORE decisions
```

If a parity fixture changes the frozen evidence decision:

```text
STOP
→ do not recalibrate threshold automatically
→ specialist/PM review
```

### 13.3 T4 evidence run

Later Stage B measurements:

```text
cold initialization
GPU/VRAM
warm embedding: 5 warmups + 30 samples
warm reranking: 20 candidates, batch 8, 3 warmups + 30 samples
combined embedding→reranking: 3 warmups + 30 samples
concurrency=2: same-arrival, 10 measured pairs
billing before/after
```

No DB/OpenAI/Tavily calls in the performance benchmark.

Do not extrapolate above concurrency=2.

---

## 14. Required test updates — existing tests/fakes

Follow the current test style. Existing async tests commonly use `asyncio.run`; do not add `pytest-asyncio` solely for this task.

### 14.1 Current embedding/retrieval tests

Actual current files include:

```text
backend/tests/step63_test_support.py
backend/tests/test_step63_retrieval_service.py
backend/tests/test_step63_semantic_retrieval_smoke.py
backend/tests/test_config.py
```

Update `FakeProvider.embed_query/embed_documents` to async.

Preserve all existing retrieval/error/profile tests.

Add focused Modal identity tests:

- MODAL provider + matching test-scoped MODAL active profile passes identity gate;
- MODAL provider + LOCAL active profile fails safely;
- exact model/revision/provider_version mismatch fails.

### 14.2 Current reranking tests

Actual current files include:

```text
backend/tests/test_step65_reranker_provider.py
backend/tests/test_step65_reranking_service.py
```

Convert affected provider/service tests to await the async API.

Preserve tests for:

- <=20 candidates;
- batch size 8;
- sequential batches;
- raw scores;
- deterministic tie-break;
- Top 5;
- no threshold;
- empty list avoids provider inference;
- input-too-long;
- invalid count/NaN/Inf;
- no retry;
- technical failures.

### 14.3 Current RAG/external tests

Actual current files include:

```text
backend/tests/test_step68a_rag.py
backend/tests/test_step68b_external_retrieval.py
backend/tests/test_conversation_api.py
backend/tests/test_conversation_concurrency.py
```

Update affected service-level fakes:

```text
FakeReranker.rerank → async
external FakeReranker validate/score → async
```

Preserve:

- CURRENT_LESSON → INTERNAL_KB → TRUSTED_EXTERNAL policy;
- technical failure != no-evidence;
- calibrated threshold equality behavior;
- external trusted allowlist;
- citation/provenance behavior.

### 14.4 D-004 profiler compatibility

Update:

```text
backend/tests/test_profile_bge_runtime.py
backend/scripts/profile_bge_runtime.py
```

for async interfaces.

Focused tests must prove the original benchmark semantics remain intact.

Do not generate new real CPU evidence.

---

## 15. New Stage-A tests

Add focused tests under existing `backend/tests/` convention, for example:

```text
backend/tests/test_step83_modal_bge_client.py
backend/tests/test_step83_modal_embedding_provider.py
backend/tests/test_step83_modal_reranker_provider.py
backend/tests/test_step83_modal_validation.py
```

Use actual repo naming convention if a Step 8.3 test prefix already exists.

Required:

### Modal client

- lookup receives configured app/class/environment;
- async invocation uses `.remote.aio`;
- fake blocking `.remote()` raises if called;
- timeout/auth/not-found/resource/remote failures normalize safely;
- no credential/text/vector leakage in error message.

### Embedding adapter

- D-113 identity exact;
- exact remote model/revision/contract required;
- query result shape accepted only when valid;
- document count/dimension/finite/norm validation preserved;
- too-long maps to existing embedding error;
- unexpected Modal failure maps to technical provider failure;
- no retry.

### Reranker adapter

- MODAL runtime identity exact;
- exact remote model/revision/contract required;
- `device` property does not perform network I/O;
- pair-too-long mapping;
- score count/finite validation;
- no retry;
- blocking `.remote()` prohibited.

### Factories/config

- local remains default;
- local factories still return existing providers;
- modal selection returns Modal adapters;
- missing modal credentials/config fails only when modal selected;
- production rejects local BGE providers per D-111;
- no production profile is created.

### Runtime definition

Static/import-safe tests as practical:

- exact model/revision constants;
- validation GPU = T4;
- min containers 0;
- max containers 2;
- retries 0;
- no dynamic batching/concurrent/memory snapshot/quantization flags;
- import/test does not deploy or authenticate.

### Validation artifact

- fake results cannot set/aggregate as `real_modal_runtime=true`;
- missing required real fields rejected;
- percentile aggregation deterministic;
- parity result includes threshold-decision comparison;
- no real Modal call occurs.

---

## 16. Files/components to change

Existing paths:

```text
backend/app/core/config.py
backend/.env.example

backend/app/ai/embeddings/provider.py
backend/app/ai/embeddings/sentence_transformer_provider.py
backend/app/ai/embeddings/service.py                # verify exact current Step 6.1 service path before patching

backend/app/ai/retrieval/service.py

backend/app/ai/reranking/provider.py
backend/app/ai/reranking/transformers_provider.py
backend/app/ai/reranking/service.py

backend/app/ai/external_retrieval/reranking.py
backend/app/ai/rag/orchestrator.py

backend/scripts/profile_bge_runtime.py
backend/tests/test_profile_bge_runtime.py

backend/tests/step63_test_support.py
backend/tests/test_step63_retrieval_service.py
backend/tests/test_step63_semantic_retrieval_smoke.py
backend/tests/test_step65_reranker_provider.py
backend/tests/test_step65_reranking_service.py
backend/tests/test_step68a_rag.py
backend/tests/test_step68b_external_retrieval.py
backend/tests/test_config.py

backend/pyproject.toml
backend/uv.lock
```

Update any additional current fakes/callers returned by these mandatory searches:

```text
rg "embed_query\(" backend/app backend/tests backend/scripts
rg "embed_documents\(" backend/app backend/tests backend/scripts
rg "validate_pair_lengths\(" backend/app backend/tests backend/scripts
rg "\.score\(" backend/app/ai/reranking backend/app/ai/external_retrieval backend/tests backend/scripts
rg "\.rerank\(" backend/app backend/tests backend/scripts
```

New paths:

```text
backend/app/ai/modal_bge/__init__.py
backend/app/ai/modal_bge/client.py
backend/app/ai/modal_bge/schemas.py
backend/app/ai/embeddings/modal_provider.py
backend/app/ai/reranking/modal_provider.py

backend/modal_bge/__init__.py
backend/modal_bge/runtime.py

backend/scripts/validate_modal_bge_runtime.py

backend/tests/test_step83_modal_bge_client.py
backend/tests/test_step83_modal_embedding_provider.py
backend/tests/test_step83_modal_reranker_provider.py
backend/tests/test_step83_modal_validation.py

docs/ai/step-8.3-modal-bge-runtime-validation.md
```

Do not add a migration.

Do not create production evidence files in Stage A.

---

## 17. Verification

Minimum Stage-A verification:

```text
python/compileall for changed Python
uv lock --check
focused Step 8.3 tests
Step 6.1 embedding regressions
Step 6.3 retrieval regressions
Step 6.5 reranking regressions
Step 6.8-A internal RAG regressions
Step 6.8-B external fallback regressions
conversation/citation regressions affected by RAG
D-004 profiler tests
full backend test suite
```

No network requirement.

No Modal credentials.

No GPU.

Tests must fail if a real Modal SDK call escapes a fake boundary.

---

## 18. Documentation

Create/update:

```text
docs/ai/step-8.3-modal-bge-runtime-validation.md
```

Document:

- D-111/D-112/D-113/D-114;
- current local default;
- async provider mental model;
- data flow;
- Modal inference-only boundary;
- exact identity/model contracts;
- config;
- error mapping;
- Stage A local-only proof;
- Stage B authorization/billing gate;
- T4 evidence plan;
- no production Modal profile/re-embedding;
- D-005 unchanged;
- risks and acceptance criteria.

Do not claim any real Modal latency/VRAM/cost result in Stage A.

---

## 19. Acceptance Criteria — Stage A

- [ ] D-111/D-112/D-113/D-114 are implemented exactly.
- [ ] Embedding provider methods are async.
- [ ] Reranker provider inference methods are async.
- [ ] Existing local providers remain default and preserve behavior.
- [ ] No thread-pool workaround is introduced.
- [ ] Semantic retrieval awaits query embedding outside DB transactions.
- [ ] `RerankingService.rerank()` is async.
- [ ] `ExternalRerankingService.rerank()` is async.
- [ ] RAG orchestrator awaits internal and external reranking.
- [ ] D-004 profiler remains compatible with async local providers without semantic redesign.
- [ ] Modal embedding identity is `MODAL / modal-bge-runtime/v1`.
- [ ] ACTIVE EmbeddingProfile identity guard is unchanged in meaning.
- [ ] Stage A creates/activates no production MODAL EmbeddingProfile.
- [ ] Stage A does not re-embed production data.
- [ ] Modal reranker identity is honest and exact.
- [ ] Local and Modal factory selection is config-driven.
- [ ] Production Settings reject local BGE providers per D-111.
- [ ] Modal SDK invocation path uses `remote.aio`, never blocking `.remote()`.
- [ ] Exact model/revision metadata is verified on every remote result.
- [ ] Existing embedding output validation remains enforced.
- [ ] Existing reranking semantics remain unchanged.
- [ ] Technical Modal failures stay technical.
- [ ] No automatic reranker retry.
- [ ] No public API/schema migration/business logic moved to Modal.
- [ ] Modal runtime definition contains inference only.
- [ ] T4 is only the Stage-B validation candidate, not production GPU selection.
- [ ] Stage-B harness/schema exists but cannot fabricate real evidence.
- [ ] No Modal auth/deploy/GPU usage occurs in Stage A.
- [ ] No paid usage occurs.
- [ ] `RAG_MIN_RERANK_SCORE` unchanged.
- [ ] D-005 unchanged.
- [ ] Relevant regressions and full backend suite pass.
- [ ] Step documentation is complete.

---

## 20. Explicit Stage-A prohibitions

Do NOT:

- run `modal setup`;
- run `modal token ...`;
- run `modal billing ...`;
- run `modal volume create/put/...`;
- run model-cache population;
- run `modal run`;
- run `modal deploy`;
- invoke `.remote()` or `.remote.aio()` against a real workspace;
- allocate T4 or any GPU;
- incur Modal usage;
- create fake `real_modal_runtime=true` evidence;
- choose production GPU tier;
- choose backend hosting;
- choose DB/storage/email vendors;
- create/activate production Modal EmbeddingProfile;
- re-embed production corpus;
- change embedding/reranking models or revisions;
- change `RAG_MIN_RERANK_SCORE`;
- change D-005;
- add Redis/Celery/worker/queue;
- add LangChain/LlamaIndex;
- add quantization;
- add dynamic batching;
- add Modal in-container concurrency;
- redesign public API or RAG behavior.

---

## 21. Required completion handoff

Return:

```text
Step:
Step 8.3 — Modal BGE Runtime Validation — Stage A

Status:
READY_FOR_SPECIALIST_REVIEW
or
BLOCKED / DECISION_NEEDED with exact reason

What was done

PM decisions implemented:
D-111
D-112
D-113
D-114

Files changed

Async interface/call-site changes

Modal adapter/runtime-definition changes

Config/dependency changes

Tests run + exact results

Real Modal authentication performed:
NO

Real Modal deployment performed:
NO

GPU allocated:
NO

Modal usage incurred:
NO

Real Stage-B evidence created:
NO

Production Modal EmbeddingProfile created/activated:
NO

Production data re-embedded:
NO

RAG_MIN_RERANK_SCORE changed:
NO

D-005 changed:
NO

Problems / risks

Decisions needed

Recommended next action:
AI/RAG Specialist independently reviews Stage A implementation.
Only after specialist/PM acceptance may account/billing preflight and separately authorized Stage B begin.
```
