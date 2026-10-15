import asyncio
from contextlib import asynccontextmanager
from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy import delete, func, select

from app.ai.citations.schemas import ValidatedCitation
from app.ai.rag.errors import RAG_CONFIGURATION_INVALID
from app.ai.rag.orchestrator import RagOrchestrator
from app.ai.rag.schemas import (
    CalibrationScoreRequest,
    RagInternalTier,
    RagRunStatus,
    RagTierUsed,
)
from app.ai.reranking.schemas import RerankResult, RerankedCandidate
from app.ai.retrieval.schemas import RetrievalCandidate
from app.conversation.processing_lock import advisory_key, assistant_processing_lock
from app.conversation import repository as conversation_repository
from app.conversation.ai_chat import ChatRequest
from app.conversation.service import _finalize_rag_result
from app.core.config import Settings
from app.database.engine import engine
from app.database.models import (
    Chunk, Conversation, KnowledgeSource, KnowledgeVersion, Message,
    MessageCitation, MessageRetrieval,
)
from app.database.session import SessionFactory
from tests import conversation_test_support as support


def settings(**values):
    return Settings(
        _env_file=None,
        app_env="test",
        debug=False,
        test_database_url="postgresql+psycopg://test:test@localhost/chinese_learning_test",
        secret_key="test-only-key",
        rag_memory_max_turns=0,
        **values,
    )


def reranked(score, *, rank=1):
    candidate = RetrievalCandidate(
        rank=rank, chunk_id=uuid4(), chunk_index=rank, content="lesson evidence",
        content_type="GRAMMAR", knowledge_version_id=uuid4(), knowledge_source_id=uuid4(),
        source_type="LESSON", source_document_id=None, source_lesson_id=uuid4(),
        chunk_lesson_id=uuid4(), document_title=None, lesson_title="Lesson title",
        hsk_level_number=2, page_number=None, section=None, locator_metadata=None,
        distance=0.2, retrieval_score=0.8,
    )
    return RerankedCandidate(**candidate.__dict__, rerank_score=score, rerank_rank=rank)


class EmptySessionFactory:
    @asynccontextmanager
    async def __call__(self):
        yield object()


class Retrieval:
    def __init__(self, current_rows, kb_rows, calls):
        self.current_rows, self.kb_rows, self.calls = current_rows, kb_rows, calls

    async def retrieve(self, query, *, retrieval_filter):
        self.calls.append((query, retrieval_filter))
        return self.current_rows if retrieval_filter is not None else self.kb_rows


class Reranker:
    def __init__(self, by_scope):
        self.by_scope = by_scope
        self.calls = []

    async def rerank(self, query, rows):
        result = self.by_scope[len(self.calls)]
        self.calls.append(rows)
        return result


def package_for(candidate):
    from app.ai.prompting.schemas import BudgetUsage, PromptPackage, SourceMapEntry

    return PromptPackage(
        system_instructions="System", learning_context=None, context_blocks=(), user_query="why?",
        selected_chunk_ids=(candidate.chunk_id,), omitted_chunk_ids=(),
        source_map={"S1": SourceMapEntry(
            source_label="S1", chunk_id=candidate.chunk_id,
            knowledge_source_id=candidate.knowledge_source_id, source_type="LESSON",
            source_document_id=None, source_lesson_id=candidate.source_lesson_id,
            title="Lesson title", page_number=None, section=None, locator_metadata=None,
        )},
        budget_usage=BudgetUsage(1, 0, 1, 0, 1, 2, 10, 1, 2, 100),
    )


class PromptBuilder:
    def __init__(self, candidate=None):
        self.calls = []
        self.packages = []
        self.candidate = candidate

    def build(self, *, user_query, candidates, prompt_budget, learning_context):
        self.calls.append(tuple(candidates))
        package = package_for(candidates[0])
        self.packages.append(package)
        return SimpleNamespace(status="SUCCEEDED", package=package, selected_count=1)


class Generation:
    def __init__(self):
        self.calls = 0

    async def generate_with_attempt_preparer(self, package, config, prepare):
        from app.ai.llm.schemas import LLMGenerationResult

        self.calls += 1
        await prepare(1)
        return LLMGenerationResult(
            text="Answer [S1]", provider="fake", model=config.model, input_tokens=1,
            output_tokens=1, total_tokens=2, provider_preflight_input_tokens=1,
            latency_ms=1, attempt_count=1, provider_request_id=None,
        )


def request():
    from app.conversation.ai_chat import ChatRequest

    return ChatRequest(uuid4(), uuid4(), uuid4(), uuid4(), uuid4(), "why?")


def make_orchestrator(*, config, candidates, scores, prompt=None, generation=None):
    calls = []
    reranker = Reranker([
        RerankResult(tuple(reranked(score, rank=index + 1) for index, score in enumerate(tier_scores)),
                     tuple(reranked(score, rank=index + 1) for index, score in enumerate(tier_scores[:5])))
        for tier_scores in scores
    ])
    # The reranker returns the prepared rows directly; retrieval is selected by scope.
    current_rows, kb_rows = candidates
    def retrieval_factory(_session):
        return Retrieval(current_rows, kb_rows, calls)
    prompt = prompt or PromptBuilder()
    generation = generation or Generation()
    class EmptyExternal:
        async def search(self, _query): return ()
    return RagOrchestrator(
        settings=config, session_factory=EmptySessionFactory(), retrieval_factory=retrieval_factory,
        reranker=reranker, prompt_builder=prompt, token_counter=SimpleNamespace(count=len),
        generation_service=generation, external_retrieval_service=EmptyExternal(),
    ), calls, reranker, prompt, generation


def test_learner_rag_blocks_before_retrieval_when_calibrating_or_threshold_missing():
    for config in (settings(rag_evidence_calibration_mode=True), settings(rag_min_rerank_score=None)):
        orchestrator, calls, _, _, _ = make_orchestrator(
            config=config, candidates=([], []), scores=([], []),
        )
        with pytest.raises(Exception) as error:
            asyncio.run(orchestrator.run(request()))
        assert error.value.code == RAG_CONFIGURATION_INVALID
        assert calls == []


def test_calibration_collects_both_internal_tiers_without_generation_or_prompt():
    current, internal = [reranked(0.2)], [reranked(0.9)]
    prompt, generation = PromptBuilder(), Generation()
    orchestrator, calls, _, _, _ = make_orchestrator(
        config=settings(rag_evidence_calibration_mode=True, rag_min_rerank_score=0.7),
        candidates=(current, internal), scores=([0.2], [0.9]), prompt=prompt, generation=generation,
    )
    trace = asyncio.run(orchestrator.collect_calibration_scores(CalibrationScoreRequest("why?", uuid4())))
    assert [call[1] is not None for call in calls] == [True, False]
    assert trace.current_lesson.status == "SCORED" and trace.internal_kb.status == "SCORED"
    assert trace.current_lesson.candidates[0].rerank_score == 0.2
    assert trace.internal_kb.candidates[0].rerank_score == 0.9
    assert prompt.calls == [] and generation.calls == 0


def test_threshold_equality_selects_current_lesson_without_running_internal_kb():
    current = [reranked(0.5)]
    orchestrator, calls, reranker, prompt, generation = make_orchestrator(
        config=settings(rag_min_rerank_score=0.5), candidates=(current, []), scores=([0.5],),
    )
    result = asyncio.run(orchestrator.run(request()))
    assert result.status is RagRunStatus.GROUNDED_ANSWER
    assert result.tier_used is RagTierUsed.CURRENT_LESSON
    assert result.tiers_attempted == (RagInternalTier.CURRENT_LESSON,)
    assert len(calls) == 1 and len(reranker.calls) == 1
    assert len(prompt.calls) == 1 and generation.calls == 1


def test_internal_kb_prompt_and_trace_exclude_rejected_current_lesson():
    current, internal = [reranked(0.2)], [reranked(0.8)]
    prompt, generation = PromptBuilder(), Generation()
    orchestrator, calls, _, _, _ = make_orchestrator(
        config=settings(rag_min_rerank_score=0.5),
        candidates=(current, internal), scores=([0.2], [0.8]), prompt=prompt, generation=generation,
    )
    result = asyncio.run(orchestrator.run(request()))
    assert [call[1] is not None for call in calls] == [True, False]
    assert prompt.calls == [(orchestrator.reranker.by_scope[1].top_candidates[0],)]
    assert result.tier_used is RagTierUsed.INTERNAL_KB
    assert result.tiers_attempted == (RagInternalTier.CURRENT_LESSON, RagInternalTier.INTERNAL_KB)
    assert {row.chunk_id for row in result.retrieval_trace} == {
        item.chunk_id for item in orchestrator.reranker.by_scope[1].scored_candidates
    }
    assert all(row.chunk_id != current[0].chunk_id for row in result.retrieval_trace)


def test_semantic_no_evidence_stops_before_prompt_generation_and_citations():
    prompt, generation = PromptBuilder(), Generation()
    orchestrator, calls, _, _, _ = make_orchestrator(
        config=settings(rag_min_rerank_score=0.9),
        candidates=([reranked(0.2)], [reranked(0.4)]), scores=([0.2], [0.4]),
        prompt=prompt, generation=generation,
    )
    result = asyncio.run(orchestrator.run(request()))
    assert result.status is RagRunStatus.NO_EVIDENCE
    assert result.tier_used is RagTierUsed.NONE
    assert len(calls) == 2 and prompt.calls == [] and generation.calls == 0
    assert result.retrieval_trace == () and result.validated_citations == ()


def test_technical_current_lesson_rerank_error_does_not_fall_through_to_internal_kb():
    class FailingReranker:
        def __init__(self):
            self.calls = 0

        async def rerank(self, query, rows):
            self.calls += 1
            raise RuntimeError("private reranker failure")

    reranker = FailingReranker()
    orchestrator, calls, _, prompt, generation = make_orchestrator(
        config=settings(rag_min_rerank_score=0.5),
        candidates=([reranked(0.1)], [reranked(0.9)]), scores=([0.1], [0.9]),
    )
    orchestrator.reranker = reranker
    with pytest.raises(RuntimeError):
        asyncio.run(orchestrator.run(request()))
    assert reranker.calls == 1 and len(calls) == 1
    assert prompt.calls == [] and generation.calls == 0


def test_settings_reject_nan_infinity_and_boolean_threshold():
    for value in (float("nan"), float("inf"), float("-inf"), True):
        with pytest.raises(Exception):
            settings(rag_min_rerank_score=value)


def test_attempt_preparer_rebuilds_memory_after_retry_and_recovers_after_prior_zero_memory_fallback():
    from app.ai.llm.openai_provider import OpenAILLMProvider
    from app.ai.llm.schemas import LLMRoleMessage
    from test_step67_llm_provider import FakeClient, count, request as llm_request, response, settings as llm_settings, transient_error

    client = FakeClient(
        [count(400_000), count(100), count(100)],
        [transient_error("connection"), response()],
    )
    calls = []
    base = llm_request()

    async def prepare(attempt):
        calls.append(attempt)
        memory = (
            LLMRoleMessage("user", f"fresh question {attempt}"),
            LLMRoleMessage("assistant", f"fresh answer {attempt}"),
        )
        return replace(
            base,
            historical_messages=memory,
            memory_input_tokens=2,
            estimated_input_tokens=base.estimated_input_tokens + 2,
        )

    provider = OpenAILLMProvider(llm_settings(), client=client, sleep=lambda _: asyncio.sleep(0), uniform=lambda a, b: 0)
    result = asyncio.run(provider.generate_with_attempt_preparer(base, prepare))
    assert calls == [1, 2]
    assert result.attempt_count == 2
    assert result.memory_selected_turn_count == 1
    assert len(client.count_endpoint.calls) == 3
    assert client.create_endpoint.calls[0]["input"][-1]["role"] == "user"
    assert client.create_endpoint.calls[0]["input"][0]["content"] == base.user_content
    assert [entry["content"] for entry in client.create_endpoint.calls[1]["input"][:-1]] == [
        "fresh question 2", "fresh answer 2",
    ]


@pytest.mark.parametrize("scenario", ["A", "F", "G"], ids=[
    "A-first-attempt-success",
    "F-retry-citation-only-for-final-response",
    "G-retry-preserves-evidence-and-memory-boundaries",
])
def test_d084_d085_rag_attempt_lifecycle_preserves_evidence_and_validates_final_citation_once(scenario):
    from app.ai.citations.validator import CitationValidator
    from app.ai.llm.openai_provider import OpenAILLMProvider
    from app.ai.llm.service import LLMGenerationService
    from app.ai.memory.schemas import ConversationMemory, MemoryTurn
    from test_step67_llm_provider import FakeClient, count, response as provider_response
    from test_step67_llm_provider import settings as provider_settings, transient_error

    candidate = reranked(0.8)
    current = [candidate]
    prompt = PromptBuilder()
    config = settings().model_copy(update={
        "rag_min_rerank_score": 0.5,
        "rag_memory_max_turns": 2,
    })
    orchestrator, retrieval_calls, reranker, prompt, _ = make_orchestrator(
        config=config, candidates=(current, []), scores=([0.8],), prompt=prompt,
    )

    class MemoryBuilder:
        calls = 0

        async def build(self, **_kwargs):
            self.calls += 1
            return ConversationMemory(
                turns=(MemoryTurn(
                    user_text="earlier question", assistant_text="earlier answer",
                    user_message_id=uuid4(), assistant_message_id=uuid4(),
                    user_sequence_number=1, assistant_sequence_number=2,
                ),),
                selected_turn_count=1, omitted_turn_count=0, token_count=2, status="APPLIED",
            )

    memory_builder = MemoryBuilder()
    orchestrator.memory_builder_factory = lambda _session: memory_builder

    async def current_sequence(_request):
        return 3

    orchestrator._current_user_sequence = current_sequence

    class CitationSpy:
        calls = []

        def validate(self, **kwargs):
            self.calls.append(kwargs)
            return CitationValidator().validate(**kwargs)

    citation_spy = CitationSpy()
    orchestrator.citation_validator = citation_spy
    evidence_checks = []
    original_evidence_check = orchestrator._has_usable_evidence

    def count_evidence_check(result):
        evidence_checks.append(tuple(item.chunk_id for item in result.scored_candidates))
        return original_evidence_check(result)

    orchestrator._has_usable_evidence = count_evidence_check

    retry = scenario in {"F", "G"}
    if retry:
        client = FakeClient(
            [count(), count()],
            [transient_error("connection"), provider_response(text=f"Answer for {scenario} [S1]")],
        )
        expected_text = f"Answer for {scenario} [S1]"
        expected_attempts = 2
    else:
        client = FakeClient([count()], [provider_response(text="Answer on first attempt [S1]")])
        expected_text = "Answer on first attempt [S1]"
        expected_attempts = 1

    provider = OpenAILLMProvider(
        provider_settings(llm_max_transient_retries=1), client=client,
        sleep=lambda _delay: asyncio.sleep(0), uniform=lambda _low, _high: 0,
    )
    generation = LLMGenerationService(provider)
    orchestrator.generation_service = generation
    result = asyncio.run(orchestrator.run(request()))

    assert result.status is RagRunStatus.GROUNDED_ANSWER
    assert result.assistant_content == expected_text
    assert result.memory_selected_turn_count == 1
    assert result.tier_used is RagTierUsed.CURRENT_LESSON
    selected_candidate = reranker.by_scope[0].scored_candidates[0]
    assert tuple(item.chunk_id for item in result.retrieval_trace) == (selected_candidate.chunk_id,)
    assert len(retrieval_calls) == len(reranker.calls) == len(prompt.calls) == 1
    assert len(evidence_checks) == 1
    assert memory_builder.calls == expected_attempts
    assert len(client.count_endpoint.calls) == expected_attempts
    assert len(client.create_endpoint.calls) == expected_attempts
    assert len(citation_spy.calls) == 1
    assert citation_spy.calls[0]["text"] == expected_text
    assert tuple(prompt.packages[0].source_map) == ("S1",)
    assert prompt.packages[0].selected_chunk_ids == (
        prompt.packages[0].source_map["S1"].chunk_id,
    )
    provider_inputs = [sent["input"] for sent in client.create_endpoint.calls]
    assert all(
        payload[-1]["content"] == "[Question]\nwhy?"
        and payload[-1]["role"] == "user"
        for payload in provider_inputs
    )
    assert all(
        [message["content"] for message in payload[:-1]]
        == ["earlier question", "earlier answer"]
        for payload in provider_inputs
    )
    assert prompt.packages[0].source_map["S1"].source_label == "S1"


def test_memory_database_read_transaction_ends_before_token_packing():
    from app.ai.memory.builder import ConversationMemoryBuilder
    from app.conversation.repository import MemoryTurnRow

    conversation_id = uuid4()
    user_id, assistant_id = uuid4(), uuid4()

    class Session:
        active = False

        @asynccontextmanager
        async def begin(self):
            self.active = True
            try:
                yield self
            finally:
                self.active = False

    session = Session()

    class Repository:
        async def list_recent_completed_turn_pairs_for_memory(self, _session, **kwargs):
            assert session.active is True
            return (MemoryTurnRow(
                user_message_id=user_id, assistant_message_id=assistant_id,
                user_text="older question", assistant_text="older answer",
                user_sequence_number=1, assistant_sequence_number=2,
                conversation_id=conversation_id,
            ),)

    class Counter:
        def count(self, _text):
            assert session.active is False
            return 1

    memory = asyncio.run(ConversationMemoryBuilder(
        session, token_counter=Counter(), repository=Repository(),
    ).build(
        conversation_id=conversation_id, current_user_sequence_number=3,
        memory_token_budget=10, max_turns=2,
    ))
    assert memory.selected_turn_count == 1


def test_transaction_b_commits_grounded_trace_atomically_and_rolls_back_partial_failure(monkeypatch):
    user_id, lesson_id = asyncio.run(support.seed_user_lesson())
    conversation_id, user_message_id, good_id, failed_id = uuid4(), uuid4(), uuid4(), uuid4()
    source_id, version_id, chunk_id = uuid4(), uuid4(), uuid4()

    async def seed():
        async with SessionFactory.begin() as session:
            session.add(Conversation(id=conversation_id, user_id=user_id, lesson_id=lesson_id))
            session.add(Message(
                id=user_message_id, conversation_id=conversation_id, sequence_number=1,
                role="USER", content="question", status="COMPLETED",
            ))
            session.add_all([
                Message(id=good_id, conversation_id=conversation_id, sequence_number=2,
                        role="ASSISTANT", content=None, status="PENDING", reply_to_message_id=user_message_id),
                Message(id=failed_id, conversation_id=conversation_id, sequence_number=3,
                        role="ASSISTANT", content=None, status="PENDING", reply_to_message_id=user_message_id),
            ])
            session.add(KnowledgeSource(id=source_id, source_type="LESSON", lesson_id=lesson_id))
            session.add(KnowledgeVersion(
                id=version_id, knowledge_source_id=source_id, version_number=1,
                status="ACTIVE", chunking_strategy="test", chunk_size=100,
                chunk_overlap=0, chunking_version="test", chunk_max_chars=100,
            ))
            await session.flush()
            session.add(Chunk(
                id=chunk_id, knowledge_version_id=version_id, content="evidence",
                content_type="GRAMMAR", chunk_index=0, lesson_id=lesson_id,
            ))

    async def cleanup():
        async with SessionFactory.begin() as session:
            await session.execute(delete(MessageRetrieval).where(MessageRetrieval.message_id.in_([good_id, failed_id])))
            await session.execute(delete(MessageCitation).where(MessageCitation.message_id.in_([good_id, failed_id])))
            await session.execute(delete(Message).where(Message.id.in_([user_message_id, good_id, failed_id])))
            await session.execute(delete(Conversation).where(Conversation.id == conversation_id))
            await session.execute(delete(Chunk).where(Chunk.id == chunk_id))
            await session.execute(delete(KnowledgeVersion).where(KnowledgeVersion.id == version_id))
            await session.execute(delete(KnowledgeSource).where(KnowledgeSource.id == source_id))

    asyncio.run(seed())
    request_value = ChatRequest(user_id, conversation_id, lesson_id, user_message_id, good_id, "question")
    citation = ValidatedCitation(
        label="S1", source_kind="INTERNAL_CHUNK", title="Lesson evidence",
        chunk_id=chunk_id, source_type="LESSON",
    )
    good_result = SimpleNamespace(
        assistant_message_id=good_id, status=RagRunStatus.GROUNDED_ANSWER,
        assistant_content="Answer [S1]", tier_used=RagTierUsed.CURRENT_LESSON,
        retrieval_trace=(SimpleNamespace(chunk_id=chunk_id, rank=1, retrieval_score=0.8, rerank_score=0.7),),
        validated_citations=(citation,),
    )
    try:
        async def finalize_good():
            async with SessionFactory() as session:
                return await _finalize_rag_result(session, request_value, good_result)
        response = asyncio.run(finalize_good())
        assert response["status"] == "COMPLETED" and response["citations"][0]["label"] == "S1"

        async def fail_citation_insert(*_args, **_kwargs):
            raise RuntimeError("test transaction failure")
        monkeypatch.setattr(conversation_repository, "add_message_citations", fail_citation_insert)
        failed_request = ChatRequest(user_id, conversation_id, lesson_id, user_message_id, failed_id, "question")
        failed_result = SimpleNamespace(**{**good_result.__dict__, "assistant_message_id": failed_id})
        async def finalize_failed():
            async with SessionFactory() as session:
                await _finalize_rag_result(session, failed_request, failed_result)
        with pytest.raises(RuntimeError):
            asyncio.run(finalize_failed())

        async def inspect():
            async with SessionFactory() as session:
                good = await session.get(Message, good_id)
                failed = await session.get(Message, failed_id)
                retrieval_count = await session.scalar(select(func.count()).select_from(MessageRetrieval).where(
                    MessageRetrieval.message_id == good_id,
                ))
                failed_retrieval_count = await session.scalar(select(func.count()).select_from(MessageRetrieval).where(
                    MessageRetrieval.message_id == failed_id,
                ))
                return good.status, failed.status, retrieval_count, failed_retrieval_count
        assert asyncio.run(inspect()) == ("COMPLETED", "PENDING", 1, 0)
    finally:
        asyncio.run(cleanup())
        support.scenario_cleanup(user_id, lesson_id)


def test_real_postgres_session_lock_is_nonblocking_and_released_on_same_connection():
    from app.core.errors import ApplicationError

    async def run():
        attempt = uuid4()
        key = advisory_key(attempt)
        async with assistant_processing_lock(attempt) as held:
            assert held.in_transaction() is False
            with pytest.raises(ApplicationError) as duplicate:
                async with assistant_processing_lock(attempt):
                    pytest.fail("duplicate attempt must not enter AI work")
            assert duplicate.value.code == "DUPLICATE_RAG_GENERATION"
            async with engine.connect() as second:
                unavailable = await second.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": key})
                assert unavailable.scalar_one() is False
                await second.commit()
        async with engine.connect() as second:
            available = await second.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": key})
            assert available.scalar_one() is True
            await second.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
            await second.commit()
        other = advisory_key(uuid4())
        assert other != key
        async with assistant_processing_lock(uuid4()):
            async with assistant_processing_lock(uuid4()):
                pass
        cancelled_attempt = uuid4()
        with pytest.raises(asyncio.CancelledError):
            async with assistant_processing_lock(cancelled_attempt):
                raise asyncio.CancelledError
        async with assistant_processing_lock(cancelled_attempt):
            pass
    asyncio.run(run())
