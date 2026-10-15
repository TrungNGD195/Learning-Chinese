import ast
import asyncio
from pathlib import Path
from datetime import UTC, datetime

import pytest

from app.ai.modal_bge.schemas import CONTRACT_VERSION, EMBEDDING_MODEL, EMBEDDING_REVISION, RERANKER_MODEL, RERANKER_REVISION
from scripts import validate_modal_bge_runtime as harness

BACKEND = Path(__file__).resolve().parents[1]


def _valid_pending_result():
    captured = datetime.now(UTC).isoformat()
    samples = [float(index + 1) for index in range(30)]
    summary = {
        "raw_samples_ms": samples,
        "p50_ms": harness.nearest_rank(samples, 0.5),
        "p95_ms": harness.nearest_rank(samples, 0.95),
        "warmups": 5,
        "sample_count": 30,
    }
    rerank_summary = {**summary, "warmups": 3}
    requests = [
        {"latency_ms": 200.0, "execution_ms": 100.0},
        {"latency_ms": 300.0, "execution_ms": 150.0},
    ]
    return {
        "status": harness.PENDING_STATUS,
        "real_modal_runtime": True,
        "timestamp_utc": "2026-10-14T00:00:00Z",
        "git_commit": "a" * 40,
        "modal_sdk_version": "1.6.1",
        "modal_app_name": "review-validation-app",
        "modal_class_name": "BgeInference",
        "contract_version": CONTRACT_VERSION,
        "gpu_name": "NVIDIA T4",
        "gpu_total_vram_bytes": 16_384,
        "runtime_provenance_verified": True,
        "torch_version": "2.14.1",
        "cuda_version": "12.8",
        "runtime_versions": {"sentence-transformers": "6.1.0", "transformers": "5.18.0", "torch": "2.14.1"},
        "embedding": {"model_name": EMBEDDING_MODEL, "model_revision": EMBEDDING_REVISION,
                      "raw_samples_ms": samples},
        "reranker": {"model_name": RERANKER_MODEL, "model_revision": RERANKER_REVISION,
                     "raw_samples_ms": samples},
        "fixture_identity": {"name": "fixture-v1", "query": "query", "passages": [f"passage-{i}" for i in range(20)]},
        "parity": {
            "embedding": {"max_absolute_delta": 0.0, "dimension": 1024, "finite": True, "unit_norm": True},
            "reranker": {
                "max_absolute_delta": 0.0,
                "local_raw_scores": [0.5] * 20, "modal_raw_scores": [0.5] * 20,
                "local_order": list(range(20)), "modal_order": list(range(20)),
                "order_equal": True,
                "local_threshold_decisions": [True] * 20, "modal_threshold_decisions": [True] * 20,
                "candidate_count": 20, "batch_size": 8, "batch_count": 3,
                "threshold_decisions_equal": True,
                "threshold": 0.4,
            },
        },
        "cold_initialization": {"runtime_info_ms": 25.0},
        "warm_embedding_ms": summary,
        "warm_reranking_ms": {**rerank_summary, "candidate_count": 20, "batch_size": 8, "batch_count": 3},
        "combined_ms": {**rerank_summary, "candidate_count": 20, "batch_size": 8, "batch_count": 3},
        "concurrency_2_ms": [
            {"requests": requests, "pair_makespan_ms": 300.0}
            for _ in range(10)
        ],
        "vram": {
            "allocated_bytes": 1000,
            "reserved_bytes": 2000,
            "max_allocated_bytes": 1500,
            "max_reserved_bytes": 2500,
        },
        "billing": {
            "before_reference": "billing-before-123", "before_captured_at_utc": captured,
            "after_reference": None, "after_captured_at_utc": None,
        },
        "billing_reference": {"before": "billing-before-123", "after": "billing-after-456"},
    }


def test_runtime_definition_is_validation_only_and_exposes_vram_counters():
    source = (BACKEND / "modal_bge/runtime.py").read_text(encoding="utf-8")
    schema_source = (BACKEND / "app/ai/modal_bge/schemas.py").read_text(encoding="utf-8")
    for value in ("gpu=\"T4\"", "min_containers=0", "max_containers=2", "retries=0",
                  "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "memory_allocated()",
                  "memory_reserved()", "max_memory_allocated()", "max_memory_reserved()"):
        assert value in source
    for forbidden in ("@modal.concurrent", "memory_snapshot", "quantization", "autocast"):
        assert forbidden not in source
    ast.parse(source)
    assert EMBEDDING_REVISION in schema_source and RERANKER_REVISION in schema_source


def test_old_complete_looking_fake_payload_is_rejected_for_semantic_incompleteness():
    fake = _valid_pending_result()
    fake["status"] = harness.COMPLETE_STATUS
    fake["gpu_name"] = "fabricated GPU identity"
    fake["billing"]["after_reference"] = "fabricated-after-reference"
    fake["vram"] = None
    with pytest.raises(ValueError, match="VRAM evidence"):
        harness.validate_real_result(fake)


@pytest.mark.parametrize("field", ["allocated_bytes", "reserved_bytes", "max_allocated_bytes", "max_reserved_bytes"])
def test_missing_or_null_vram_counter_is_rejected(field):
    evidence = _valid_pending_result()
    evidence["vram"][field] = None
    with pytest.raises(ValueError, match="vram|VRAM"):
        harness.validate_pending_measurement(evidence)


def test_runtime_package_versions_are_preserved_and_required():
    evidence = _valid_pending_result()
    harness.validate_pending_measurement(evidence)
    assert evidence["runtime_versions"] == {
        "sentence-transformers": "6.1.0", "transformers": "5.18.0", "torch": "2.14.1",
    }
    del evidence["runtime_versions"]["torch"]
    with pytest.raises(ValueError, match="runtime_versions.torch"):
        harness.validate_pending_measurement(evidence)


def test_concurrency_uses_common_arrival_and_records_execution_and_pair_makespan():
    ticks = iter([10.0, 10.005, 10.010, 10.105, 10.210])
    lock = asyncio.Lock()

    async def serialized_fake_request():
        async with lock:
            await asyncio.sleep(0)

    result = asyncio.run(harness.measure_concurrency_pair(serialized_fake_request, clock=lambda: next(ticks)))
    left, right = result["requests"]
    assert left == {"latency_ms": pytest.approx(105.0), "execution_ms": pytest.approx(100.0)}
    assert right == {"latency_ms": pytest.approx(210.0), "execution_ms": pytest.approx(200.0)}
    assert result["pair_makespan_ms"] == pytest.approx(210.0)
    assert left["latency_ms"] != left["execution_ms"]


def test_parity_threshold_mismatch_stops_all_performance_calls(monkeypatch):
    monkeypatch.setenv(harness.STAGE_B_ENV, "true")
    settings = type("Settings", (), {
        "rag_min_rerank_score": 0.5,
        "modal_bge_app_name": "app",
        "modal_bge_class_name": "BgeInference",
        "model_copy": lambda self, update: self,
    })()
    monkeypatch.setattr(harness, "get_settings", lambda: settings)
    calls = []
    remote_score_batch_sizes = []
    local_score_batch_sizes = []
    runtime = {
        "contract_version": CONTRACT_VERSION,
        "embedding_model_name": EMBEDDING_MODEL, "embedding_model_revision": EMBEDDING_REVISION,
        "reranker_model_name": RERANKER_MODEL, "reranker_model_revision": RERANKER_REVISION,
        "device": "cuda",
        "gpu_name": "T4", "gpu_total_vram_bytes": 16_000,
        "torch_version": "2.14.1", "cuda_version": "12.8",
        "runtime_versions": {"sentence-transformers": "6.1.0", "transformers": "5.18.0", "torch": "2.14.1"},
        "vram_allocated_bytes": 100, "vram_reserved_bytes": 200,
        "vram_max_allocated_bytes": 150, "vram_max_reserved_bytes": 250,
    }

    class FakeClient:
        real_modal_runtime = False
        def __init__(self, _settings): pass
        async def invoke(self, operation, *args):
            calls.append(operation)
            if operation == "runtime_info": return runtime
            if operation == "embed_query": return {"vector": [1.0] + [0.0] * 1023}
            if operation == "validate_rerank_inputs": return {"ok": True}
            if operation == "score_rerank":
                batch = args[1]
                remote_score_batch_sizes.append(len(batch))
                start = sum(remote_score_batch_sizes[:-1])
                scores = [0.9] * len(batch)
                if start <= 11 < start + len(batch):
                    scores[11 - start] = 0.1
                return {"ok": True, "scores": scores}
            raise AssertionError(operation)

    class FakeEmbedding:
        def __init__(self, _settings): pass
        async def embed_query(self, _query): return [1.0] + [0.0] * 1023

    class FakeReranker:
        def __init__(self, _settings): pass
        async def score(self, _query, passages):
            local_score_batch_sizes.append(len(passages))
            return [0.9] * len(passages)

    monkeypatch.setattr(harness, "ModalBgeClient", FakeClient)
    from app.ai.embeddings import sentence_transformer_provider
    from app.ai.reranking import transformers_provider
    monkeypatch.setattr(sentence_transformer_provider, "SentenceTransformerEmbeddingProvider", FakeEmbedding)
    monkeypatch.setattr(transformers_provider, "TransformersRerankerProvider", FakeReranker)

    result = asyncio.run(harness.run_real_validation(billing_before_reference="before-123"))
    assert result["status"] == harness.PARITY_FAILED_STATUS
    assert result["parity"]["reranker"]["threshold_decisions_equal"] is False
    assert result["parity"]["reranker"]["candidate_count"] == 20
    assert len(result["parity"]["reranker"]["local_raw_scores"]) == 20
    assert len(result["parity"]["reranker"]["modal_raw_scores"]) == 20
    assert remote_score_batch_sizes == local_score_batch_sizes == [8, 8, 4]
    assert "warm_embedding_ms" not in result
    assert "concurrency_2_ms" not in result
    assert calls == ["runtime_info", "embed_query", "validate_rerank_inputs",
                     "score_rerank", "score_rerank", "score_rerank"]
    with pytest.raises(ValueError, match="COMPLETE_REAL_MEASUREMENTS"):
        harness.validate_real_result(result)


def test_pending_billing_artifact_is_not_canonical_complete_evidence():
    pending = _valid_pending_result()
    harness.validate_pending_measurement(pending)
    with pytest.raises(ValueError, match="COMPLETE_REAL_MEASUREMENTS"):
        harness.validate_real_result(pending)


def test_finalize_requires_billing_after_reference():
    with pytest.raises(ValueError, match="billing_after_reference"):
        harness.finalize_real_result(_valid_pending_result(), billing_after_reference=" ")


def test_finalize_accepts_only_complete_valid_evidence():
    pending = _valid_pending_result()
    before_time = pending["billing"]["before_captured_at_utc"]
    complete = harness.finalize_real_result(
        pending, billing_after_reference="billing-after-456",
    )
    harness.validate_real_result(complete)
    assert complete["status"] == harness.COMPLETE_STATUS
    assert complete["billing"]["before_reference"] == "billing-before-123"
    assert complete["billing"]["after_reference"] == "billing-after-456"
    assert datetime.fromisoformat(complete["billing"]["after_captured_at_utc"]) >= datetime.fromisoformat(before_time)
    broken = _valid_pending_result()
    broken["vram"]["max_reserved_bytes"] = None
    with pytest.raises(ValueError, match="vram|VRAM"):
        harness.finalize_real_result(broken, billing_after_reference="billing-after-456")


@pytest.mark.parametrize("target", ["fixture", "warm", "combined"])
def test_evidence_requires_all_20_rerank_candidates_in_8_8_4_batches(target):
    evidence = _valid_pending_result()
    if target == "fixture":
        evidence["fixture_identity"]["passages"].pop()
    elif target == "warm":
        evidence["warm_reranking_ms"]["candidate_count"] = 8
    else:
        evidence["combined_ms"]["batch_count"] = 1
    with pytest.raises(ValueError, match="20|8/8/4"):
        harness.validate_pending_measurement(evidence)


def test_complete_fake_client_run_cannot_create_finalizable_real_evidence(monkeypatch):
    monkeypatch.setenv(harness.STAGE_B_ENV, "true")
    settings = type("Settings", (), {
        "rag_min_rerank_score": 0.5,
        "modal_bge_app_name": "app",
        "modal_bge_class_name": "BgeInference",
        "model_copy": lambda self, update: self,
    })()
    runtime = {
        "contract_version": CONTRACT_VERSION,
        "embedding_model_name": EMBEDDING_MODEL, "embedding_model_revision": EMBEDDING_REVISION,
        "reranker_model_name": RERANKER_MODEL, "reranker_model_revision": RERANKER_REVISION,
        "device": "cuda", "gpu_name": "NVIDIA T4", "gpu_total_vram_bytes": 16_000,
        "torch_version": "2.14.1", "cuda_version": "12.8",
        "runtime_versions": {"sentence-transformers": "6.1.0", "transformers": "5.18.0", "torch": "2.14.1"},
        "vram_allocated_bytes": 100, "vram_reserved_bytes": 200,
        "vram_max_allocated_bytes": 150, "vram_max_reserved_bytes": 250,
    }

    class FakeClient:
        real_modal_runtime = False
        def __init__(self, _settings): pass
        async def invoke(self, operation, *args):
            if operation == "runtime_info": return runtime
            if operation == "embed_query": return {"ok": True, "vector": [1.0] + [0.0] * 1023}
            if operation == "validate_rerank_inputs": return {"ok": True}
            if operation == "score_rerank": return {"ok": True, "scores": [0.8] * len(args[1])}
            raise AssertionError(operation)

    class FakeEmbedding:
        def __init__(self, _settings): pass
        async def embed_query(self, _query): return [1.0] + [0.0] * 1023

    class FakeReranker:
        def __init__(self, _settings): pass
        async def score(self, _query, passages): return [0.8] * len(passages)

    monkeypatch.setattr(harness, "get_settings", lambda: settings)
    monkeypatch.setattr(harness, "ModalBgeClient", FakeClient)
    monkeypatch.setattr(harness, "_package_version", lambda _package: "1.6.1")
    monkeypatch.setattr(harness, "_git_commit", lambda: "a" * 40)
    from app.ai.embeddings import sentence_transformer_provider
    from app.ai.reranking import transformers_provider
    monkeypatch.setattr(sentence_transformer_provider, "SentenceTransformerEmbeddingProvider", FakeEmbedding)
    monkeypatch.setattr(transformers_provider, "TransformersRerankerProvider", FakeReranker)

    result = asyncio.run(harness.run_real_validation(billing_before_reference="before-123"))
    assert result["status"] == harness.PENDING_STATUS
    assert result["runtime_provenance_verified"] is True
    assert result["real_modal_runtime"] is False
    assert len(result["parity"]["reranker"]["local_raw_scores"]) == 20
    with pytest.raises(ValueError, match="real Modal execution path"):
        harness.validate_pending_measurement(result)
    with pytest.raises(ValueError, match="real Modal execution path"):
        harness.finalize_real_result(result, billing_after_reference="after-456")


def test_stage_b_main_fails_closed_without_two_authorization_gates(monkeypatch):
    monkeypatch.delenv(harness.STAGE_B_ENV, raising=False)
    monkeypatch.setattr("sys.argv", ["validate_modal_bge_runtime.py", "run", "--stage-b-authorized",
                                     "--billing-before-reference", "before"])
    with pytest.raises(SystemExit):
        harness.main()
