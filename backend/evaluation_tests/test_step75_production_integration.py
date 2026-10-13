"""Opt-in local PostgreSQL + pinned-model tests through the real learner path.

These tests intentionally skip when the dedicated database or exact local model
snapshots are unavailable. The only replaced seam is generation: paid API calls
are prohibited in this offline task. Retrieval, reranking, prompt assembly,
memory, citation validation, learner application service, and persistence remain
the repository production implementations.
"""
from __future__ import annotations

import asyncio
import copy
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import pytest
from sqlalchemy import select, text


BUCKETS = (
    "CURRENT_LESSON_ANSWERABLE", "INTERNAL_KB_FALLBACK",
    "TRUSTED_EXTERNAL_FALLBACK", "NO_EVIDENCE_REFUSAL",
    "OUT_OF_DOMAIN_REFUSAL", "MULTI_TURN_CONTEXT",
)


def _settings_or_skip(monkeypatch):
    # Match the backend test harness's non-secret environment semantics without
    # weakening its requirement for an explicitly configured dedicated DB URL.
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DEBUG", "false")
    from app.core.config import get_settings
    get_settings.cache_clear()
    try:
        settings = get_settings()
    except Exception:
        get_settings.cache_clear()
        pytest.skip("DEDICATED_TEST_DATABASE_URL_OR_REQUIRED_TEST_SETTINGS_UNAVAILABLE")
    if settings.app_env != "test" or not settings.test_database_url:
        pytest.skip("DEDICATED_TEST_DATABASE_URL_UNAVAILABLE; no test database access attempted")
    return settings


def _pinned_model_cache_or_skip(settings):
    try:
        from huggingface_hub import try_to_load_from_cache
        def snapshot_available(repo, revision):
            config = try_to_load_from_cache(repo, "config.json", revision=revision)
            weights = [try_to_load_from_cache(repo, name, revision=revision) for name in
                       ("model.safetensors", "pytorch_model.bin", "model.safetensors.index.json",
                        "pytorch_model.bin.index.json")]
            return isinstance(config, str) and any(isinstance(path, str) for path in weights)
        embedding = snapshot_available(settings.embedding_model_name, settings.embedding_model_revision)
        reranker = snapshot_available(settings.reranker_model_name, settings.reranker_model_revision)
    except Exception:
        pytest.skip("PINNED_LOCAL_MODEL_CACHE_CHECK_UNAVAILABLE; network use prohibited")
    if not embedding or not reranker:
        pytest.skip("EXACT_PINNED_EMBEDDING_OR_RERANKER_SNAPSHOT_UNAVAILABLE; network use prohibited")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"


class _OfflineGenerationProvider:
    """Deterministic no-network provider below the real LLMGenerationService."""
    def __init__(self, model):
        self.requests = []
        self.provider = type("ProviderIdentity", (), {
            "provider_name": "OFFLINE_TEST_FIXTURE", "model_name": model})()

    async def generate(self, request):
        from app.ai.llm.schemas import LLMGenerationResult
        self.requests.append(request)
        return LLMGenerationResult(
            text="Câu trả lời dựa trên nguồn [S1].", provider="OFFLINE_TEST_FIXTURE",
            model=request.model, input_tokens=40, output_tokens=10, total_tokens=50,
            provider_preflight_input_tokens=0, latency_ms=0, attempt_count=1,
            provider_request_id=None, provider_preflight_count=0,
            memory_selected_turn_count=len(request.historical_messages) // 2,
        )


class _OfflineSemanticJudge:
    """Deterministic judge implementing the production Step-7.5 protocol/schema."""
    def __init__(self):
        self.payloads = []

    async def evaluate(self, payload, *, case_id, repeat_index,
                       current_citation_labels, source_map_labels):
        from app.evaluation.step75.contracts import DIMENSIONS, E2EJudgeResult
        self.payloads.append(payload)
        memory = payload.get("sanitized_conversation_memory")
        if memory is not None:
            assert memory["evidence_authority"] is False
            assert all("[S" not in turn["assistant_text"] for turn in memory["turns"])
        return E2EJudgeResult.model_validate({
            "schema_version": "1.0.0", "case_id": case_id, "repeat_index": repeat_index,
            "generation_dimension_scores": {key: {"score": 1, "rationale": "offline test"}
                                            for key in DIMENSIONS},
            "claims": [], "context_adherence": {"material_violation": False,
                "memory_used_as_evidence": False, "historical_citation_label_leak": False,
                "current_evidence_overridden_by_history": False, "concise_rationale": "offline test"},
            "semantic_critical_failures": [], "concise_overall_rationale": "offline test",
        })


def _case_for_bucket(bucket):
    root = Path(__file__).resolve().parents[2]
    rows = []
    dataset = root / "evaluation/datasets/lesson_chat_rag/v0"
    for filename in ("development.jsonl", "holdout.jsonl"):
        rows.extend(json.loads(line) for line in (dataset / filename).read_text(encoding="utf-8").splitlines() if line)
    return next(row for row in rows if row["bucket"] == bucket and row["review_status"] == "APPROVED")


@pytest.mark.parametrize("bucket", BUCKETS)
def test_real_db_model_application_path_for_each_bucket(bucket, monkeypatch):
    settings = _settings_or_skip(monkeypatch)
    _pinned_model_cache_or_skip(settings)

    from app.ai.external_retrieval.reranking import ExternalRerankingService
    from app.ai.external_retrieval.service import ExternalRetrievalService
    from app.ai.llm.service import LLMGenerationService
    from app.ai.rag.orchestrator import RagOrchestrator
    from app.conversation.ai_chat import RAGAIChatService
    from app.database.models import Message
    from app.database.session import SessionFactory
    from app.evaluation.step73.fixtures import bootstrap
    from app.evaluation.step75.database import (
        create_isolated_conversation, delete_isolated_conversation,
        fixture_metadata_by_chunk_id,
    )
    from app.evaluation.step75.execution import (
        RecordingAIChatService, execute_case_through_application_service,
    )
    from app.evaluation.step75.external_fixture import ReviewedExternalFixtureProvider
    from app.ingestion.storage import LocalFileStorage

    async def run_case():
        case = copy.deepcopy(_case_for_bucket(bucket))
        if bucket == "MULTI_TURN_CONTEXT" and case.get("conversation_context"):
            case["conversation_context"].insert(0, {
                "user_text": "I am practicing Mandarin conversation.",
                "assistant_text": "We can continue with the lesson topic.",
            })
            case["conversation_context"][-1]["assistant_text"] += " [S1]"
        async with SessionFactory() as session:
            actual_database = await session.scalar(text("select current_database()"))
            root = Path(__file__).resolve().parents[2]
            storage = LocalFileStorage(root / "tmp" / "step75-integration-fixture-storage")
            staged = await bootstrap(session, storage, settings=settings, actual_database=actual_database)
            lesson_locator = (case.get("lesson_context") or {}).get("lesson_locator")
            if lesson_locator not in staged["lesson_runtime_ids"]:
                lesson_locator = next(iter(staged["lesson_runtime_ids"]))
            lesson_id = staged["lesson_runtime_ids"][lesson_locator]
            isolated = await create_isolated_conversation(
                session, settings=settings, actual_database=actual_database,
                lesson_id=lesson_id, case=case, run_id="step75-offline", execution_id=uuid4().hex)

        provider = _OfflineGenerationProvider(settings.llm_model)
        external_provider = ReviewedExternalFixtureProvider()
        external_search_calls = []
        original_external_search = external_provider.search
        async def observed_external_search(query, limit):
            external_search_calls.append((query, limit))
            return await original_external_search(query, limit)
        external_provider.search = observed_external_search
        orchestrator = RagOrchestrator(
            settings=settings,
            generation_service=LLMGenerationService(provider),
            external_retrieval_service=ExternalRetrievalService(
                external_provider, settings),
            external_reranking_service=ExternalRerankingService(settings),
        )
        application_ai = RecordingAIChatService(RAGAIChatService(orchestrator))
        judge = _OfflineSemanticJudge()
        try:
            async with SessionFactory() as session:
                result = await execute_case_through_application_service(
                    session=session, user_id=isolated["user_id"],
                    conversation_id=isolated["conversation_id"], lesson_id=lesson_id,
                    case=case, execution={"execution_id": uuid4().hex,
                                          "case_id": case["case_id"], "repeat_index": 1},
                    ai_chat_service=application_ai,
                    judge=judge,
                    evidence_metadata_by_chunk_id=fixture_metadata_by_chunk_id(staged),
                )
                messages = list((await session.scalars(select(Message).where(
                    Message.conversation_id == isolated["conversation_id"]
                ).order_by(Message.sequence_number))).all())
                assert [row.role for row in messages[-2:]] == ["USER", "ASSISTANT"]
                assert messages[-2].status == "COMPLETED"
                assert messages[-1].status in {"COMPLETED", "FAILED"}
                assert result["trace"]["persistence"]["final_message_status"] == messages[-1].status
                assert "persisted_retrievals" in result["trace"]["persistence"]
                assert "persisted_citations" in result["trace"]["persistence"]
                trace = result["trace"]
                attempted = [row["tier"] for row in trace["tiers_attempted"]]
                if bucket == "CURRENT_LESSON_ANSWERABLE":
                    assert attempted == ["CURRENT_LESSON"]
                    assert trace["selected_tier"] == "CURRENT_LESSON"
                    assert trace["tiers_attempted"][0]["evidence_gate_passed"] is True
                    assert messages[-1].status == "COMPLETED"
                elif bucket == "INTERNAL_KB_FALLBACK":
                    assert attempted == ["CURRENT_LESSON", "INTERNAL_KB"]
                    assert trace["tiers_attempted"][0]["evidence_gate_passed"] is False
                    assert trace["selected_tier"] == "INTERNAL_KB"
                    assert trace["tiers_attempted"][1]["evidence_gate_passed"] is True
                elif bucket == "TRUSTED_EXTERNAL_FALLBACK":
                    assert attempted == ["CURRENT_LESSON", "INTERNAL_KB", "TRUSTED_EXTERNAL"]
                    assert not trace["tiers_attempted"][0]["evidence_gate_passed"]
                    assert not trace["tiers_attempted"][1]["evidence_gate_passed"]
                    assert trace["tiers_attempted"][2]["candidate_count"] > 0
                    assert trace["selected_tier"] == "TRUSTED_EXTERNAL"
                    assert len(external_search_calls) == 1
                    persisted_citations = trace["persistence"]["persisted_citations"]
                    assert persisted_citations
                    assert all(row["source_kind"] == "EXTERNAL_URL" for row in persisted_citations)
                    assert all(row.get("url") and row.get("domain") for row in persisted_citations)
                elif bucket == "NO_EVIDENCE_REFUSAL":
                    assert trace["all_applicable_tiers_semantically_exhausted"] is True
                    assert trace["generation"]["called"] is False
                    assert trace["generation"]["answer"] == trace["frozen_no_evidence_content"]
                    assert messages[-1].status == "COMPLETED"
                    assert trace["persistence"]["message_citation_count"] == 0
                elif bucket == "OUT_OF_DOMAIN_REFUSAL":
                    assert trace["actual_behavior"] != "REFUSE_OUT_OF_DOMAIN"
                    if trace["generation"]["called"]:
                        assert "OUT_OF_DOMAIN_ANSWER" in result["critical_failures"]
                    else:
                        assert trace["actual_behavior"] == "REFUSE_NO_EVIDENCE"
                elif bucket == "MULTI_TURN_CONTEXT":
                    pairings = isolated["history_pairings"]
                    assert len(pairings) == 2
                    for pair in pairings:
                        assert pair["reply_to_message_id"] == pair["user_message_id"]
                        assert pair["user_sequence_number"] < pair["assistant_sequence_number"]
                    assert trace["memory"]["production_path_ran"] is True
                    assert trace["memory"]["composition_applied"] is True
                    assert trace["memory"]["applied"] is True
                    assert trace["memory"]["selected_turn_count"] == len(pairings)
                    assert trace["memory"]["generation_selected_turn_count"] == len(pairings)
                    snapshot = trace["memory"]["sanitized_context"]
                    assert [turn["user_message_id"] for turn in snapshot["turns"]] == [
                        str(pair["user_message_id"]) for pair in pairings[-len(snapshot["turns"]):]]
                    assert [turn["assistant_message_id"] for turn in snapshot["turns"]] == [
                        str(pair["assistant_message_id"]) for pair in pairings[-len(snapshot["turns"]):]]
                    assert [turn["assistant_message_id"] for turn in snapshot["turns"]] == [
                        str(pair["assistant_message_id"]) for pair in pairings[-len(snapshot["turns"]):]]
                    assert [turn["user_sequence_number"] for turn in snapshot["turns"]] == sorted(
                        turn["user_sequence_number"] for turn in snapshot["turns"])
                    assert trace["memory"]["historical_citation_markers_removed"] is True
                    assert trace["memory"]["historical_citation_labels"] == ["[S1]"]
                    assert all("[S1]" not in turn["assistant_text"] for turn in snapshot["turns"])
                    assert judge.payloads[-1]["sanitized_conversation_memory"] == snapshot
                    assert provider.requests and all("[S1]" not in message.content
                                                     for message in provider.requests[-1].historical_messages)
                    assert [(message.role, message.content) for message in provider.requests[-1].historical_messages] == [
                        (message["role"], message["content"]) for message in snapshot["messages"]]
                    assert not ({label.strip("[]") for label in trace["memory"][
                        "historical_citation_labels"]} & set(trace["prompt"]["source_map_snapshot"]))
                if trace["generation"]["called"]:
                    assert trace["generation"]["token_usage"] == {
                        "input_tokens": 40, "output_tokens": 10, "total_tokens": 50}
                    assert result["generation_dimension_scores"] is not None
                    assert result["generation_ok"] is True
                    timings = trace["timings"]
                    assert timings["evaluation_only_citation_finalization_diagnostic_latency_ms"] == sum(
                        timings[field] for field in ("citation_validation_latency_ms",
                            "citation_finalization_latency_ms",
                            "evaluation_only_persistence_readback_latency_ms"))
                    assert timings["citation_finalization_latency_ms"] >= 0
                return result
        finally:
            async with SessionFactory() as session:
                await delete_isolated_conversation(
                    session, settings=settings, actual_database=actual_database,
                    conversation_id=isolated["conversation_id"], user_id=isolated["user_id"])

    result = asyncio.run(run_case())
    assert result["trace"]["case_id"] == _case_for_bucket(bucket)["case_id"]
    assert result["trace"]["actual_behavior"] in {
        "ANSWER", "FALLBACK_INTERNAL", "FALLBACK_EXTERNAL", "REFUSE_NO_EVIDENCE", "TECHNICAL_FAILURE"
    }


@pytest.mark.parametrize("failure", [
    "retrieval", "reranker", "context_budget", "llm_provider", "citation_validator", "finalization",
])
def test_real_application_path_narrow_technical_failures(failure, monkeypatch):
    """Inject one failing production seam; all other local seams remain real/offline."""
    settings = _settings_or_skip(monkeypatch)
    _pinned_model_cache_or_skip(settings)
    from app.ai.external_retrieval.reranking import ExternalRerankingService
    from app.ai.external_retrieval.service import ExternalRetrievalService
    from app.ai.llm.service import LLMGenerationService
    from app.ai.rag.orchestrator import RagOrchestrator
    from app.conversation.ai_chat import RAGAIChatService
    from app.conversation import service as conversation_service
    from app.database.session import SessionFactory
    from app.evaluation.step73.fixtures import bootstrap
    from app.evaluation.step75.database import create_isolated_conversation, delete_isolated_conversation
    from app.evaluation.step75.execution import RecordingAIChatService, execute_case_through_application_service
    from app.evaluation.step75.external_fixture import ReviewedExternalFixtureProvider
    from app.ingestion.storage import LocalFileStorage

    async def run_case():
        case = _case_for_bucket("CURRENT_LESSON_ANSWERABLE")
        async with SessionFactory() as session:
            actual_database = await session.scalar(text("select current_database()"))
            root = Path(__file__).resolve().parents[2]
            staged = await bootstrap(session, LocalFileStorage(root / "tmp" / "step75-failure-fixture"),
                                     settings=settings, actual_database=actual_database)
            lesson_locator = case["lesson_context"]["lesson_locator"]
            lesson_id = staged["lesson_runtime_ids"][lesson_locator]
            isolated = await create_isolated_conversation(
                session, settings=settings, actual_database=actual_database, lesson_id=lesson_id,
                case=case, run_id="step75-failure", execution_id=uuid4().hex)
        provider = _OfflineGenerationProvider(settings.llm_model)
        orchestrator = RagOrchestrator(
            settings=settings, generation_service=LLMGenerationService(provider),
            external_retrieval_service=ExternalRetrievalService(ReviewedExternalFixtureProvider(), settings),
            external_reranking_service=ExternalRerankingService(settings),
        )
        if failure == "retrieval":
            class BrokenRetrieval:
                async def retrieve(self, *args, **kwargs): raise RuntimeError("injected retrieval fault")
            original_factory = orchestrator.retrieval_factory
            orchestrator.retrieval_factory = lambda session: BrokenRetrieval()
        elif failure == "reranker":
            orchestrator.reranker.rerank = lambda *args, **kwargs: (_ for _ in ()).throw(
                RuntimeError("injected reranker fault"))
        elif failure == "context_budget":
            orchestrator.prompt_builder.build = lambda *args, **kwargs: (_ for _ in ()).throw(
                RuntimeError("injected context budget exhaustion"))
        elif failure == "llm_provider":
            async def broken_generate(request): raise RuntimeError("injected provider fault")
            provider.generate = broken_generate
        elif failure == "citation_validator":
            orchestrator.citation_validator.validate = lambda *args, **kwargs: (_ for _ in ()).throw(
                RuntimeError("injected citation validation fault"))
        application_ai = RecordingAIChatService(RAGAIChatService(orchestrator))
        original_finalizer = conversation_service._finalize_rag_result
        if failure == "finalization":
            async def broken_finalize(*args, **kwargs): raise RuntimeError("injected finalization fault")
            conversation_service._finalize_rag_result = broken_finalize
        try:
            async with SessionFactory() as session:
                result = await execute_case_through_application_service(
                    session=session, user_id=isolated["user_id"],
                    conversation_id=isolated["conversation_id"], lesson_id=lesson_id,
                    case=case, execution={"execution_id": uuid4().hex,
                                         "case_id": case["case_id"], "repeat_index": 1},
                    ai_chat_service=application_ai,
                    evidence_metadata_by_chunk_id={},
                )
            trace = result["trace"]
            assert result["actual"]["behavior"] == "TECHNICAL_FAILURE"
            assert result["technical_ok"] is False
            assert result["e2e_case_pass"] is False
            if failure in {"retrieval", "reranker", "context_budget"}:
                assert [row["tier"] for row in trace["tiers_attempted"]] == ["CURRENT_LESSON"]
                assert trace["generation"]["called"] is False
            if failure in {"llm_provider", "citation_validator", "finalization"}:
                assert trace["selected_evidence"]
                assert trace["persistence"]["final_message_status"] == "FAILED"
                assert result["generation_dimension_scores"] is None
            if failure == "llm_provider":
                assert trace["generation"]["error_code"]
            if failure == "citation_validator":
                assert trace["generation"]["token_usage"] == {
                    "input_tokens": 40, "output_tokens": 10, "total_tokens": 50}
            if failure == "finalization":
                assert trace["persistence"].get("message_citation_count", 0) == 0
            return result
        finally:
            conversation_service._finalize_rag_result = original_finalizer
            async with SessionFactory() as session:
                await delete_isolated_conversation(session, settings=settings,
                    actual_database=actual_database, conversation_id=isolated["conversation_id"],
                    user_id=isolated["user_id"])

    result = asyncio.run(run_case())
    assert result["actual"]["behavior"] == "TECHNICAL_FAILURE"
