from __future__ import annotations

from typing import Any, Awaitable, Callable

from sqlalchemy import select

from app.ai.rag.schemas import NO_EVIDENCE_CONTENT, RagRunStatus

from .contracts import ActualBehavior


async def invoke_learner_application_path(
    submit: Callable[..., Awaitable[Any]], *, user_id: Any, conversation_id: Any,
    current_question: str,
):
    """Invoke the existing learner application-service boundary with user input only.

    Expected bucket/tier/behavior labels intentionally are not accepted by this API.
    The caller must compare the returned production trace after this function ends.
    """
    if not isinstance(current_question, str) or not current_question.strip():
        raise ValueError("E2E_CURRENT_QUESTION_REQUIRED")
    return await submit(user_id=user_id, conversation_id=conversation_id,
                        content=current_question)


async def submit_through_learner_service(*, session, user_id, conversation_id,
                                         current_question: str, ai_chat_service):
    """Concrete production entry point used by local Step-7.5 integration tests."""
    from app.conversation.service import send_message

    if not isinstance(current_question, str) or not current_question.strip():
        raise ValueError("E2E_CURRENT_QUESTION_REQUIRED")
    return await send_message(session, user_id, conversation_id, current_question, ai_chat_service)


class RecordingAIChatService:
    """Observe results while delegating to the real RAG AI service unchanged."""

    def __init__(self, delegate):
        self.delegate = delegate
        self.results: dict[str, Any] = {}

    async def generate_reply(self, request):
        result = await self.delegate.generate_reply(request)
        self.results[str(request.assistant_message_id)] = result
        return result


def trace_actual_rag_result(result, *, execution_id: str, case_id: str,
                            repeat_index: int, assistant_status: str,
                            current_question: str,
                            conversation_id: str | None = None,
                            current_user_message_id: str | None = None,
                            current_user_sequence_number: int | None = None,
                            evidence_metadata_by_chunk_id: dict[str, dict] | None = None,
                            observer=None, persisted: dict | None = None,
                            lesson_id: str | None = None) -> dict:
    """Join actual observed production seams and committed DB state into a trace."""
    from .observer import citation_validation_snapshot
    if observer is None or persisted is None:
        raise ValueError("E2E_FULL_PRODUCTION_TRACE_OBSERVER_AND_PERSISTENCE_REQUIRED")
    if result.status is RagRunStatus.NO_EVIDENCE:
        behavior = ActualBehavior.REFUSE_NO_EVIDENCE
        generation = {"called": False, "answer": result.assistant_content}
        selected_tier = "NONE"
        selected = []
        no_evidence = True
    else:
        selected_tier = result.tier_used.value
        behavior = {"CURRENT_LESSON": ActualBehavior.ANSWER,
                    "INTERNAL_KB": ActualBehavior.FALLBACK_INTERNAL,
                    "TRUSTED_EXTERNAL": ActualBehavior.FALLBACK_EXTERNAL}.get(selected_tier)
        if behavior is None:
            raise ValueError("E2E_PRODUCTION_RAG_RESULT_HAS_UNKNOWN_TIER")
        generation = {"called": True, "answer": result.assistant_content}
        selected = observer.actual_evidence(result)
        no_evidence = False
    citation_records = [{
        "label": citation.label, "source_kind": citation.source_kind,
        "title": citation.title,
        "chunk_id": str(citation.chunk_id) if citation.chunk_id else None,
        "url": citation.url, "domain": citation.domain, "source_type": citation.source_type,
        "locator": dict(citation.locator) if citation.locator is not None else None,
        "metadata": dict(citation.metadata) if citation.metadata is not None else None,
    } for citation in result.validated_citations]
    source_map = observer.source_map_snapshot if observer.prompt_package else {}
    context_blocks = observer.context_blocks_snapshot if observer.prompt_package else []
    observer.finalize_tier_policy(selected_tier)
    trace = {
        "schema_version": "1.0.0", "execution_id": execution_id, "case_id": case_id,
        "repeat_index": repeat_index,
        "conversation": {"conversation_id": conversation_id,
                          "current_user_message_id": current_user_message_id,
                          "assistant_message_id": str(result.assistant_message_id),
                          "lesson_id": str(lesson_id) if lesson_id else None,
                          "current_user_sequence_number": current_user_sequence_number,
                          "current_question": current_question},
        "domain_guard": {"status": "NOT_PRESENT", "out_of_domain_detected": False,
                         "error_code": None},
        "tiers_attempted": observer.tier_trace(result.tiers_attempted),
        "selected_tier": selected_tier, "selected_evidence": selected,
        "prompt": {"built": bool(observer.prompt_package),
                   "selected_context_count": result.selected_context_count,
                   "omitted_context_count": (len(observer.prompt_package.omitted_chunk_ids)
                                             if observer.prompt_package else 0),
                   "source_map_snapshot": source_map,
                   "source_map_sha256": observer.sha256(source_map),
                   "context_blocks": context_blocks,
                   "prompt_package_sha256": observer.prompt_package_sha256,
                   "context_build_duration_ms": observer.context_build_duration_ms},
        "memory": {"applied": observer.memory_applied_to_generation,
                   "production_path_ran": observer.memory_builder_invocation_count > 0,
                   "builder_invocation_count": observer.memory_builder_invocation_count,
                   "composition_applied": observer.memory_composition_applied,
                   "generation_selected_turn_count": observer.generated_memory_selected_turn_count,
                   "dropped_after_preflight": observer.memory_dropped_after_preflight,
                   "selected_turn_count": result.memory_selected_turn_count,
                   "omitted_turn_count": getattr(observer.memory, "omitted_turn_count", 0),
                   "token_count": getattr(observer.memory, "token_count", 0),
                   "historical_citation_markers_removed": observer.memory_markers_removed,
                   "historical_citation_labels": observer.memory_historical_citation_labels,
                   "sanitized_context": observer.sanitized_memory_snapshot,
                   "sanitized_context_sha256": observer.sha256(observer.sanitized_memory_snapshot)},
        "generation": {**generation,
                       "provider": getattr(observer, "provider", None),
                       "model": getattr(observer, "model", None),
                       "answer_sha256": observer.sha256(result.assistant_content),
                       "latency_ms": observer.generated_latency_ms,
                       "token_usage": observer.token_usage,
                       "error_code": observer.generation_error_code},
        "citation_validation": citation_validation_snapshot(observer, citation_records, valid=True),
        "persistence": persisted,
        "actual_behavior": behavior, "semantic_no_evidence": no_evidence,
        "frozen_no_evidence_content": NO_EVIDENCE_CONTENT,
        "selected_evidence_gate_passed": (selected_tier == "NONE" or any(
            row.get("tier") == selected_tier and row.get("evidence_gate_passed") is True
            for row in observer.tiers)),
        "all_applicable_tiers_semantically_exhausted": (no_evidence and bool(observer.tiers)
            and all(row.get("retrieval_status") == "SUCCESS"
                    and row.get("rerank_status") in {"SUCCESS", "NOT_APPLICABLE"}
                    and row.get("evidence_gate_passed") is False for row in observer.tiers)),
        "timings": {"total_latency_ms": observer.total_latency_ms,
                    "retrieval_latency_ms": sum(row.get("retrieval_latency_ms") or 0 for row in observer.tiers),
                    "rerank_latency_ms": sum(row.get("rerank_latency_ms") or 0 for row in observer.tiers),
                    "context_build_duration_ms": observer.context_build_duration_ms,
                    "llm_latency_ms": observer.generated_latency_ms,
                    "citation_validation_latency_ms": observer.citation_validation_latency_ms,
                    "citation_finalization_latency_ms": observer.citation_finalization_latency_ms,
                    "evaluation_only_persistence_readback_latency_ms": observer.persistence_readback_latency_ms,
                    "evaluation_only_citation_finalization_diagnostic_latency_ms": (
                        observer.citation_validation_latency_ms
                        + observer.citation_finalization_latency_ms
                        + observer.persistence_readback_latency_ms)},
    }
    from .contracts import E2EExecutionTrace
    return E2EExecutionTrace.model_validate(trace).model_dump(mode="json")


async def execute_case_through_application_service(*, session, user_id, conversation_id,
                                                  lesson_id, case: dict, execution: dict,
                                                  ai_chat_service: RecordingAIChatService,
                                                  judge=None,
                                                  evidence_metadata_by_chunk_id: dict[str, dict] | None = None) -> dict:
    """Run real user submission first; inspect expected labels only after persistence."""
    from .observer import ProductionTraceObserver, load_persisted_state
    delegate = getattr(ai_chat_service, "delegate", None)
    orchestrator = getattr(delegate, "orchestrator", None)
    if orchestrator is None:
        raise ValueError("STEP75_REQUIRES_EXISTING_PRODUCTION_RAG_ORCHESTRATOR")
    observer = ProductionTraceObserver(orchestrator,
        evidence_metadata_by_chunk_id=evidence_metadata_by_chunk_id)
    from app.conversation import service as conversation_service
    original_finalizer = conversation_service._finalize_rag_result
    from time import perf_counter
    async def observed_finalizer(*args, **kwargs):
        started = perf_counter()
        try:
            return await original_finalizer(*args, **kwargs)
        finally:
            observer.citation_finalization_latency_ms += max(0, round((perf_counter() - started) * 1000))
    conversation_service._finalize_rag_result = observed_finalizer
    try:
        observer.start_production_request()
        response = await submit_through_learner_service(
            session=session, user_id=user_id, conversation_id=conversation_id,
            current_question=case["question"], ai_chat_service=ai_chat_service,
        )
        observer.finish_production_request()
    except Exception as exc:
        observer.finish_production_request()
        from app.conversation import repository
        from app.database.models import Message

        await session.rollback()
        user_message = await session.scalar(select(Message).where(
            Message.conversation_id == conversation_id, Message.role == "USER"
        ).order_by(Message.sequence_number.desc()).limit(1))
        assistant = (await repository.latest_assistant_attempt(session, user_message.id)
                     if user_message is not None else None)
        user_message_id = str(user_message.id) if user_message is not None else None
        if assistant is not None:
            persisted = await load_persisted_state(session, assistant.id)
        else:
            persisted = {"final_message_status": None, "message_retrieval_count": 0,
                         "message_citation_count": 0, "persisted_retrievals": [],
                         "persisted_citations": [], "error_code": "APPLICATION_SERVICE_FAILED"}
        trace = observer.failure_trace(execution, conversation_id, lesson_id,
                                       user_message_id, assistant, persisted,
                                       current_question=case["question"],
                                       error_code=getattr(exc, "code", "LEARNER_MESSAGE_FAILED"))
        from .evaluator import evaluate_case
        observer.restore()
        conversation_service._finalize_rag_result = original_finalizer
        return evaluate_case(case, trace)
    except BaseException:
        observer.finish_production_request()
        observer.restore()
        conversation_service._finalize_rag_result = original_finalizer
        raise
    assistant = response["assistant_message"]
    run_result = ai_chat_service.results.get(assistant["id"])
    if run_result is None:
        # The application boundary returned a final response without an observable RAG result.
        trace = {"execution_id": execution["execution_id"], "case_id": case["case_id"],
                 "repeat_index": execution["repeat_index"],
                 "selected_tier": "NONE", "selected_evidence": [],
                 "generation": {"called": False, "answer": None},
                 "persistence": {"final_message_status": assistant.get("status"),
                                 "error_code": None},
                 "technical_error": {"stage": "RAG_TRACE", "code": "RAG_RESULT_NOT_CAPTURED"}}
        persisted = await load_persisted_state(session, assistant["id"])
        trace = observer.failure_trace(execution, conversation_id, lesson_id,
                                       response["user_message"].get("id"), None, persisted,
                                       current_question=case["question"],
                                       error_code="RAG_RESULT_NOT_CAPTURED")
    else:
        from time import perf_counter
        persisted_started = perf_counter()
        persisted = await load_persisted_state(session, assistant["id"])
        observer.persistence_readback_latency_ms += max(0, round((perf_counter() - persisted_started) * 1000))
        trace = trace_actual_rag_result(
            run_result, execution_id=execution["execution_id"], case_id=case["case_id"],
            repeat_index=execution["repeat_index"], assistant_status=assistant.get("status"),
            current_question=case["question"],
            conversation_id=str(conversation_id),
            current_user_message_id=response["user_message"].get("id"),
            current_user_sequence_number=response["user_message"].get("sequence_number"),
            evidence_metadata_by_chunk_id=evidence_metadata_by_chunk_id,
            observer=observer, persisted=persisted, lesson_id=str(lesson_id),
        )
    judge_completed = False
    if run_result is not None and run_result.status is RagRunStatus.GROUNDED_ANSWER and judge is not None:
        from .judge import build_judge_payload
        payload = build_judge_payload(case, trace)
        try:
            judge_result = await judge.evaluate(
                payload, case_id=case["case_id"], repeat_index=execution["repeat_index"],
                current_citation_labels=set(trace["citation_validation"].get("cited_labels", [])),
                source_map_labels=set(trace["prompt"].get("source_map_snapshot", {})),
            )
            trace["judge_result"] = judge_result.model_dump(mode="json")
            judge_completed = True
        except Exception as exc:
            trace["judge_error_code"] = getattr(exc, "code", "JUDGE_INVALID_RESPONSE")
    # This is intentionally the first use of case expected labels in the execution flow.
    from .evaluator import evaluate_case
    observer.restore()
    conversation_service._finalize_rag_result = original_finalizer
    return evaluate_case(case, trace, judge_completed=judge_completed)
