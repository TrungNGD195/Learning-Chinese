import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from unittest.mock import AsyncMock

from app.ai.citations.schemas import ExternalCitationSource
from app.ai.citations.validator import CitationValidator, TrustedExternalDomains, sources_from_prompt_package
from app.ai.external_retrieval.errors import (
    EXTERNAL_RETRIEVAL_AUTH_FAILED,
    EXTERNAL_RETRIEVAL_FAILED,
    EXTERNAL_RETRIEVAL_NOT_CONFIGURED,
    EXTERNAL_RETRIEVAL_TIMEOUT,
)
from app.ai.external_retrieval.reranking import ExternalRerankingService
from app.ai.external_retrieval.schemas import ExternalCandidate, ExternalRerankResult, RerankedExternalCandidate
from app.ai.external_retrieval.service import ExternalRetrievalService
from app.ai.external_retrieval.tavily_provider import TavilyExternalRetrievalProvider
from app.ai.prompting.builder import PromptContextBuilder
from app.ai.prompting.evidence import ExternalContextEvidence
from app.ai.prompting.schemas import PromptBudget
from app.ai.rag.orchestrator import RagOrchestrator
from app.ai.rag.schemas import NO_EVIDENCE_CONTENT, RagRunResult, RagRunStatus, RagTierUsed
from app.ai.memory.schemas import empty_memory
from app.ai.reranking.schemas import RerankerProviderIdentity, RerankResult
from app.ai.reranking.service import RerankingService
from app.ai.retrieval.schemas import RetrievalCandidate
from app.conversation.ai_chat import ChatRequest
from app.core.config import Settings, TRUSTED_EXTERNAL_DOMAINS
from app.core.errors import ApplicationError


def settings(**kwargs):
    values = {
        "_env_file": None, "app_env": "test", "debug": False,
        "test_database_url": "postgresql+psycopg://x:x@localhost/chinese_learning_test",
        "secret_key": "test", "rag_min_rerank_score": -1.0815147161483765,
        "rag_memory_max_turns": 0,
    }
    values.update(kwargs)
    return Settings(**values)


def candidate(url="https://www.open.edu/example", *, rank=1, domain="fake.invalid"):
    return ExternalCandidate("A trusted page", url, domain, "Reviewable reference content", rank, 0.98)


def test_settings_freezes_provider_k_domains_and_allows_missing_key():
    config = settings(external_retrieval_allowed_domains=" WWW.OPEN.EDU.,en.wiktionary.org,www.chinesetest.cn,www.open.edu ")
    assert config.external_retrieval_provider == "tavily"
    assert config.external_retrieval_k == 10
    assert config.external_retrieval_api_key is None
    assert config.rag_min_rerank_score == -1.0815147161483765
    assert config.external_retrieval_allowed_domains == TRUSTED_EXTERNAL_DOMAINS
    with pytest.raises(ValueError):
        settings(external_retrieval_allowed_domains="www.open.edu,evil.example,en.wiktionary.org,www.chinesetest.cn")
    with pytest.raises(ValueError):
        settings(external_retrieval_k=9)
    with pytest.raises(ValueError):
        settings(external_retrieval_provider="another-provider")


def test_tavily_missing_key_is_typed_failure():
    with pytest.raises(ApplicationError) as exc:
        asyncio.run(TavilyExternalRetrievalProvider(settings()).search("normalized query", 10))
    assert exc.value.code == EXTERNAL_RETRIEVAL_NOT_CONFIGURED


def test_tavily_request_and_mapping_are_exact():
    captured = {}
    async def handler(request):
        captured["url"] = str(request.url)
        captured["headers"] = request.headers
        captured["body"] = __import__("json").loads(request.content)
        return httpx.Response(200, json={"results": [{
            "title": "Title", "url": "https://www.open.edu/a", "content": "Snippet", "score": 0.7,
            "raw_content": "ignored", "favicon": "ignored",
        }]})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await TavilyExternalRetrievalProvider(
                settings(external_retrieval_api_key="secret-test-only"), client=client
            ).search("normalized current query", 10)
    rows = asyncio.run(run())
    assert captured["url"] == "https://api.tavily.com/search"
    assert captured["headers"]["authorization"] == "Bearer secret-test-only"
    assert captured["body"] == {
        "query": "normalized current query", "search_depth": "basic", "topic": "general", "max_results": 10,
        "include_answer": False, "include_raw_content": False, "include_images": False,
        "include_image_descriptions": False, "include_favicon": False,
        "include_domains": list(TRUSTED_EXTERNAL_DOMAINS), "auto_parameters": False,
    }
    assert rows[0].title == "Title" and rows[0].content == "Snippet"
    assert rows[0].provider_rank == 1 and rows[0].provider_score == 0.7


@pytest.mark.parametrize(("status", "expected"), [(401, EXTERNAL_RETRIEVAL_AUTH_FAILED), (429, EXTERNAL_RETRIEVAL_FAILED), (503, EXTERNAL_RETRIEVAL_FAILED)])
def test_tavily_http_errors_are_normalized(status, expected):
    async def handler(_request):
        return httpx.Response(status, json={"error": "private provider details"})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await TavilyExternalRetrievalProvider(settings(external_retrieval_api_key="k"), client=client).search("q", 10)
    with pytest.raises(ApplicationError) as exc:
        asyncio.run(run())
    assert exc.value.code == expected


def test_malformed_success_body_is_provider_failure():
    async def handler(_request):
        return httpx.Response(200, json={"results": [{"title": "Title"}]})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await TavilyExternalRetrievalProvider(settings(external_retrieval_api_key="k"), client=client).search("q", 10)
    with pytest.raises(ApplicationError) as exc:
        asyncio.run(run())
    assert exc.value.code == EXTERNAL_RETRIEVAL_FAILED


def test_tavily_timeout_is_normalized():
    async def handler(_request):
        raise httpx.ReadTimeout("private transport detail")
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await TavilyExternalRetrievalProvider(settings(external_retrieval_api_key="k"), client=client).search("q", 10)
    with pytest.raises(ApplicationError) as exc:
        asyncio.run(run())
    assert exc.value.code == EXTERNAL_RETRIEVAL_TIMEOUT


def test_tavily_connection_failure_is_normalized_without_transport_details():
    async def handler(_request):
        raise httpx.ConnectError("private raw network detail")
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await TavilyExternalRetrievalProvider(settings(external_retrieval_api_key="k"), client=client).search("q", 10)
    with pytest.raises(ApplicationError) as exc:
        asyncio.run(run())
    assert exc.value.code == EXTERNAL_RETRIEVAL_FAILED
    assert "private raw network detail" not in exc.value.message
    assert not isinstance(exc.value, httpx.HTTPError)


def test_exact_host_filter_ignores_provider_domain_label():
    class Provider:
        async def search(self, _query, _limit):
            urls = [
                "https://www.open.edu/a", "https://en.wiktionary.org/a", "https://www.chinesetest.cn/a",
                "https://open.edu/a", "https://learn.open.edu/a", "https://foo.en.wiktionary.org/a",
                "https://www.open.edu.evil.example/a", "http://www.open.edu/a",
                "https://user:pass@www.open.edu/a",
            ]
            return tuple(candidate(url, rank=i) for i, url in enumerate(urls, 1))
    trusted = asyncio.run(ExternalRetrievalService(Provider(), settings()).search("q"))
    assert [row.domain for row in trusted] == list(TRUSTED_EXTERNAL_DOMAINS)


class FakeReranker:
    def __init__(self, scores):
        self.scores = scores
        self.calls = []
        self.score_calls = []
    @property
    def identity(self):
        return RerankerProviderIdentity("LOCAL", "v", "BAAI/bge-reranker-v2-m3", "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e", "v1")
    @property
    def device(self): return "cpu"
    async def validate_pair_lengths(self, query, passages):
        self.calls.append((query, tuple(passages)))
    async def score(self, query, passages):
        self.score_calls.append((query, tuple(passages)))
        return self.scores[:len(passages)]


def test_external_reranking_uses_frozen_passage_gate_and_deterministic_order():
    provider = FakeReranker([0.1, -1.0815147161483765, 0.8])
    service = ExternalRerankingService(settings(reranker_top_k=1), provider=provider)
    rows = (candidate(rank=2), candidate("https://en.wiktionary.org/b", rank=1), candidate("https://www.chinesetest.cn/c", rank=3))
    result = asyncio.run(service.rerank("normalized q", rows))
    assert len(provider.calls) == 1
    assert provider.calls[0][0] == "normalized q"
    assert provider.calls[0][1][0] == "Title: A trusted page\nDomain: fake.invalid\n\nReviewable reference content"
    assert [x.rerank_score for x in result.scored_candidates] == [0.8, 0.1, -1.0815147161483765]
    assert result.eligible_top_candidates[0].rerank_score == 0.8
    assert result.eligible_top_candidates[0].rerank_rank == 1


def test_external_threshold_equality_passes_and_empty_skips_provider():
    provider = FakeReranker([-1.0815147161483765])
    service = ExternalRerankingService(settings(), provider=provider)
    assert len(asyncio.run(service.rerank("q", (candidate(),))).eligible_top_candidates) == 1
    calls = len(provider.calls)
    assert asyncio.run(service.rerank("q", ())).scored_candidates == ()
    assert len(provider.calls) == calls


def test_external_reranking_keeps_all_scores_then_selects_top_five():
    rows = tuple(candidate(f"https://www.open.edu/{i}", rank=i) for i in range(1, 8))
    provider = FakeReranker([float(i) for i in range(7)])
    result = asyncio.run(ExternalRerankingService(settings(rag_min_rerank_score=-1.0815147161483765), provider=provider).rerank("q", rows))
    assert len(result.scored_candidates) == 7
    assert len(result.eligible_top_candidates) == 5
    assert [row.rerank_rank for row in result.scored_candidates] == list(range(1, 8))


def test_external_reranking_discards_partial_or_nonfinite_scores():
    rows = (candidate(rank=1), candidate("https://en.wiktionary.org/a", rank=2))
    for values in ([0.1], [0.1, float("nan")]):
        with pytest.raises(ApplicationError):
            asyncio.run(ExternalRerankingService(settings(), provider=FakeReranker(values)).rerank("q", rows))


def test_external_prompt_keeps_url_backend_only_and_citations_resolve_trusted_source():
    evidence = tuple(ExternalContextEvidence(i, f"Title {i}", f"https://www.open.edu/{i}", "www.open.edu", "snippet", 0.1) for i in (1, 2))
    built = PromptContextBuilder(token_counter=type("Counter", (), {"count": staticmethod(len)})()).build_from_evidence(
        user_query="q", evidence=evidence, prompt_budget=PromptBudget(4000, 50, 0),
    )
    assert len(built.package.context_blocks) == 2
    assert "www.open.edu/1" not in built.package.context_blocks[0].text
    assert built.package.context_blocks[0].text.startswith("Source: S1\nTitle: Title 1\nDomain: www.open.edu")
    sources = sources_from_prompt_package(built.package)
    assert isinstance(sources["S1"], ExternalCitationSource)
    validated = CitationValidator(TrustedExternalDomains(frozenset(TRUSTED_EXTERNAL_DOMAINS))).validate(
        text="Grounded [S1]", sources=sources, citation_required=True,
    )
    assert validated.citations[0].source_kind == "EXTERNAL_URL"
    assert validated.citations[0].url == "https://www.open.edu/1"


def test_terminal_dns_dot_is_canonicalized_through_candidate_validation_and_persistence():
    class Provider:
        async def search(self, _query, _limit):
            return (candidate("https://www.open.edu./source", domain="untrusted-provider-label"),)

    async def run():
        filtered = await ExternalRetrievalService(Provider(), settings()).search("q")
        assert len(filtered) == 1
        assert filtered[0].domain == "www.open.edu"
        built = PromptContextBuilder(token_counter=type("Counter", (), {"count": staticmethod(len)})()).build_from_evidence(
            user_query="q",
            evidence=(ExternalContextEvidence(1, filtered[0].title, filtered[0].url, filtered[0].domain, filtered[0].content, 0.2),),
            prompt_budget=PromptBudget(4000, 50, 0),
        )
        sources = sources_from_prompt_package(built.package)
        class RecordingTrustPolicy:
            def __init__(self):
                self.hostnames = []
                self.delegate = TrustedExternalDomains(frozenset(TRUSTED_EXTERNAL_DOMAINS))
            def is_trusted_hostname(self, hostname):
                self.hostnames.append(hostname)
                return self.delegate.is_trusted_hostname(hostname)
        trust_policy = RecordingTrustPolicy()
        validated = CitationValidator(trust_policy).validate(
            text="Grounded [S1]", sources=sources, citation_required=True,
        )
        citation = validated.citations[0]
        assert trust_policy.hostnames == ["www.open.edu"]
        assert citation.domain == "www.open.edu"

        # Exercise the repository mapper used by Transaction B and inspect the row's stored domain.
        from app.conversation import repository
        class Session:
            def __init__(self): self.rows = []
            def add_all(self, rows): self.rows.extend(rows)
            async def flush(self): pass
        session = Session()
        await repository.add_message_citations(session, uuid4(), validated.citations)
        assert session.rows[0].domain == "www.open.edu"

    asyncio.run(run())


def test_internal_and_external_passages_never_share_one_reranker_invocation():
    provider = FakeReranker([0.4, 0.5])
    internal = RetrievalCandidate(
        rank=1, chunk_id=uuid4(), chunk_index=0, content="Internal lesson passage",
        content_type="LESSON_GENERAL", knowledge_version_id=uuid4(), knowledge_source_id=uuid4(),
        source_type="LESSON", source_document_id=None, source_lesson_id=uuid4(), chunk_lesson_id=uuid4(),
        document_title=None, lesson_title="Lesson A", hsk_level_number=1, page_number=None, section=None,
        locator_metadata=None, distance=0.1, retrieval_score=0.9,
    )
    asyncio.run(RerankingService(provider=provider, settings=settings()).rerank("q", (internal,)))
    external = ExternalCandidate("A trusted page", "https://www.open.edu/example", "fake.invalid", "External web passage", 1, 0.98)
    asyncio.run(ExternalRerankingService(settings(), provider=provider).rerank("q", (external,)))
    assert len(provider.score_calls) == 2
    internal_batch, external_batch = (batch for _query, batch in provider.score_calls)
    assert len(internal_batch) == len(external_batch) == 1
    assert "Lesson: Lesson A" in internal_batch[0]
    assert "Domain: fake.invalid" in external_batch[0]
    for _query, batch in provider.score_calls:
        has_internal = any("Lesson: Lesson A" in passage for passage in batch)
        has_external = any("Domain: fake.invalid" in passage for passage in batch)
        assert not (has_internal and has_external)


def test_external_source_trust_policy_rejects_lookalike_citation_host():
    with pytest.raises(ApplicationError):
        CitationValidator(TrustedExternalDomains(frozenset(TRUSTED_EXTERNAL_DOMAINS))).validate(
            text="[S1]", sources={"S1": ExternalCitationSource("S1", "Title", "https://foo.open.edu/a")}, citation_required=True,
        )


class EmptySession:
    @asynccontextmanager
    async def __call__(self):
        yield object()


class EmptyInternalRetrieval:
    async def retrieve(self, _query, *, retrieval_filter):
        return []


class InternalReranker:
    def __init__(self, fail=False): self.calls, self.fail = 0, fail
    async def rerank(self, _query, _rows):
        self.calls += 1
        if self.fail: raise ApplicationError("RERANKER_NOT_AVAILABLE", "failed", status_code=503)
        return RerankResult((), ())


class ExternalService:
    def __init__(self, rows): self.rows, self.calls = rows, []
    async def search(self, query): self.calls.append(query); return self.rows


class Generation:
    def __init__(self): self.calls = 0
    async def generate_with_attempt_preparer(self, package, config, prepare):
        from app.ai.llm.schemas import LLMGenerationResult
        self.calls += 1
        await prepare(1)
        return LLMGenerationResult("Answer [S1]", "fake", config.model, 1, 1, 2, 1, 1, 1, None)


def request():
    return ChatRequest(uuid4(), uuid4(), uuid4(), uuid4(), uuid4(), "  Chinese   question? ")


def orchestrator(*, rows, ext_score=0.2, internal_fail=False, citation_validator=None):
    config = settings()
    internal = InternalReranker(internal_fail)
    external = ExternalService(rows)
    external_ranker = ExternalRerankingService(config, provider=FakeReranker([ext_score] * len(rows)))
    generation = Generation()
    def retrieval(_session): return EmptyInternalRetrieval()
    rag = RagOrchestrator(
        settings=config, session_factory=EmptySession(), retrieval_factory=retrieval,
        reranker=internal, token_counter=type("Counter", (), {"count": staticmethod(len)})(),
        generation_service=generation, external_retrieval_service=external,
        external_reranking_service=external_ranker, citation_validator=citation_validator,
    )
    return rag, external, internal, generation


def test_orchestrator_uses_external_only_after_both_internal_tiers_and_same_normalized_query():
    rag, external, internal, generation = orchestrator(rows=(candidate(),))
    result = asyncio.run(rag.run(request()))
    assert internal.calls == 2
    assert external.calls == ["Chinese question?"]
    assert result.tiers_attempted == (RagTierUsed.CURRENT_LESSON, RagTierUsed.INTERNAL_KB, RagTierUsed.TRUSTED_EXTERNAL)
    assert result.tier_used == RagTierUsed.TRUSTED_EXTERNAL
    assert result.retrieval_trace == ()
    assert result.external_candidate_count == result.external_scored_count == 1
    assert result.validated_citations[0].source_kind == "EXTERNAL_URL"
    assert generation.calls == 1


def test_external_semantic_empty_returns_exact_refusal_without_generation():
    class CitationSpy:
        def __init__(self): self.calls = 0
        def validate(self, **_kwargs): self.calls += 1; raise AssertionError("no-evidence must not validate citations")
    citation_spy = CitationSpy()
    rag, _external, _internal, generation = orchestrator(rows=(), ext_score=0.2, citation_validator=citation_spy)
    result = asyncio.run(rag.run(request()))
    assert result.status is RagRunStatus.NO_EVIDENCE
    assert result.assistant_content == NO_EVIDENCE_CONTENT
    assert result.tiers_attempted[-1] is RagTierUsed.TRUSTED_EXTERNAL
    assert generation.calls == 0 and result.validated_citations == ()
    assert citation_spy.calls == 0


def test_below_threshold_is_semantic_no_evidence_not_provider_order_success():
    rag, _external, _internal, generation = orchestrator(rows=(candidate(),), ext_score=-2.0)
    result = asyncio.run(rag.run(request()))
    assert result.status is RagRunStatus.NO_EVIDENCE
    assert result.external_candidate_count == 1 and result.external_scored_count == 1
    assert generation.calls == 0


def test_missing_tavily_key_fails_before_prompt_or_llm():
    from app.ai.external_retrieval.tavily_provider import TavilyExternalRetrievalProvider

    config = settings()
    generation = Generation()
    rag = RagOrchestrator(
        settings=config, session_factory=EmptySession(), retrieval_factory=lambda _session: EmptyInternalRetrieval(),
        reranker=InternalReranker(), token_counter=type("Counter", (), {"count": staticmethod(len)})(),
        generation_service=generation,
        external_retrieval_service=ExternalRetrievalService(TavilyExternalRetrievalProvider(config), config),
        external_reranking_service=ExternalRerankingService(config, provider=FakeReranker([])),
    )
    with pytest.raises(ApplicationError) as exc:
        asyncio.run(rag.run(request()))
    assert exc.value.code == EXTERNAL_RETRIEVAL_NOT_CONFIGURED
    assert generation.calls == 0


def test_internal_technical_failure_does_not_call_external():
    rag, external, _internal, generation = orchestrator(rows=(candidate(),), internal_fail=True)
    with pytest.raises(ApplicationError):
        asyncio.run(rag.run(request()))
    assert external.calls == [] and generation.calls == 0


def test_transaction_b_external_success_persists_citations_without_internal_retrieval(monkeypatch):
    from app.conversation import service as conversation_service
    from app.ai.citations.schemas import ValidatedCitation

    assistant_id, conversation_id, user_message_id = uuid4(), uuid4(), uuid4()
    assistant = SimpleNamespace(
        id=assistant_id, role="ASSISTANT", status="PENDING", conversation_id=conversation_id,
        reply_to_message_id=user_message_id, sequence_number=2, content=None, created_at=None,
    )
    session = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock())
    calls = []
    async def get_message(_session, _id, *, for_update): return assistant
    async def add_retrievals(*_args): raise AssertionError("external answers must not persist MessageRetrieval")
    async def add_citations(_session, _id, citations): calls.append(tuple(citations))
    async def finalize(_session, row, *, status, content): row.status, row.content = status, content
    async def list_citations(_session, _ids): return {assistant_id: []}
    monkeypatch.setattr(conversation_service.repository, "get_message", get_message)
    monkeypatch.setattr(conversation_service.repository, "add_message_retrievals", add_retrievals)
    monkeypatch.setattr(conversation_service.repository, "add_message_citations", add_citations)
    monkeypatch.setattr(conversation_service.repository, "finalize_message", finalize)
    monkeypatch.setattr(conversation_service.repository, "list_message_citations", list_citations)
    citation = ValidatedCitation("S1", "EXTERNAL_URL", "Trusted title", url="https://www.open.edu/a", domain="www.open.edu")
    result = RagRunResult(
        assistant_message_id=assistant_id, status=RagRunStatus.GROUNDED_ANSWER,
        assistant_content="Answer [S1]", tiers_attempted=(RagTierUsed.CURRENT_LESSON, RagTierUsed.INTERNAL_KB, RagTierUsed.TRUSTED_EXTERNAL),
        tier_used=RagTierUsed.TRUSTED_EXTERNAL, current_lesson_candidate_count=0,
        current_lesson_scored_count=0, internal_kb_candidate_count=0, internal_kb_scored_count=0,
        selected_context_count=1, memory_selected_turn_count=0, retrieval_trace=(),
        validated_citations=(citation,), external_candidate_count=1, external_scored_count=1,
    )
    request_value = ChatRequest(uuid4(), conversation_id, uuid4(), user_message_id, assistant_id, "question")
    payload = asyncio.run(conversation_service._finalize_rag_result(session, request_value, result))
    assert assistant.status == "COMPLETED" and assistant.content == "Answer [S1]"
    assert len(calls) == 1 and session.commit.await_count == 1
    assert payload["status"] == "COMPLETED"


def test_transaction_b_external_citation_persistence_failure_rolls_back_without_partial_rows(monkeypatch):
    from app.conversation import service as conversation_service
    from app.ai.citations.schemas import ValidatedCitation

    assistant_id, conversation_id, user_message_id = uuid4(), uuid4(), uuid4()
    assistant = SimpleNamespace(
        id=assistant_id, role="ASSISTANT", status="PENDING", conversation_id=conversation_id,
        reply_to_message_id=user_message_id, sequence_number=2, content=None, created_at=None,
    )
    class TransactionSession:
        def __init__(self):
            self.commit = AsyncMock()
            self.rollback = AsyncMock(side_effect=self._rollback)
            self.staged_citations = []
            self.persisted_citations = []
        async def _rollback(self): self.staged_citations.clear()
    session = TransactionSession()
    retrieval_count = 0
    finalize_count = 0
    async def get_message(_session, _id, *, for_update): return assistant
    async def add_retrievals(*_args):
        nonlocal retrieval_count
        retrieval_count += 1
    async def add_citations(_session, _id, citations):
        _session.staged_citations.extend(citations)
        raise RuntimeError("forced citation persistence failure")
    async def finalize(_session, row, *, status, content):
        nonlocal finalize_count
        finalize_count += 1
        row.status, row.content = status, content
    async def list_citations(_session, _ids): return {assistant_id: []}
    monkeypatch.setattr(conversation_service.repository, "get_message", get_message)
    monkeypatch.setattr(conversation_service.repository, "add_message_retrievals", add_retrievals)
    monkeypatch.setattr(conversation_service.repository, "add_message_citations", add_citations)
    monkeypatch.setattr(conversation_service.repository, "finalize_message", finalize)
    monkeypatch.setattr(conversation_service.repository, "list_message_citations", list_citations)
    citation = ValidatedCitation("S1", "EXTERNAL_URL", "Trusted title", url="https://www.open.edu/a", domain="www.open.edu")
    result = RagRunResult(
        assistant_message_id=assistant_id, status=RagRunStatus.GROUNDED_ANSWER,
        assistant_content="Answer [S1]", tiers_attempted=(RagTierUsed.CURRENT_LESSON, RagTierUsed.INTERNAL_KB, RagTierUsed.TRUSTED_EXTERNAL),
        tier_used=RagTierUsed.TRUSTED_EXTERNAL, current_lesson_candidate_count=0,
        current_lesson_scored_count=0, internal_kb_candidate_count=0, internal_kb_scored_count=0,
        selected_context_count=1, memory_selected_turn_count=0, retrieval_trace=(),
        validated_citations=(citation,), external_candidate_count=1, external_scored_count=1,
    )
    request_value = ChatRequest(uuid4(), conversation_id, uuid4(), user_message_id, assistant_id, "question")
    with pytest.raises(RuntimeError, match="forced citation persistence failure"):
        asyncio.run(conversation_service._finalize_rag_result(session, request_value, result))
    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()
    assert assistant.status == "PENDING" and assistant.content is None
    assert finalize_count == 0
    assert retrieval_count == 0
    assert session.staged_citations == [] and session.persisted_citations == []


def test_external_transient_llm_retry_reuses_retrieval_reranking_and_prompt_but_rebuilds_memory():
    class SearchProvider:
        def __init__(self): self.calls = 0
        async def search(self, _query, _limit):
            self.calls += 1
            return (candidate(),)
    class CountingTrustFilter(ExternalRetrievalService):
        def __init__(self, provider, config): super().__init__(provider, config); self.calls = 0
        async def search(self, query):
            self.calls += 1
            return await super().search(query)
    class PromptSpy:
        def __init__(self):
            self.calls = 0
            self.delegate = PromptContextBuilder(token_counter=type("Counter", (), {"count": staticmethod(len)})())
        def build_from_evidence(self, **kwargs):
            self.calls += 1
            return self.delegate.build_from_evidence(**kwargs)
    class MemoryFactory:
        def __init__(self): self.build_calls = 0
        def __call__(self, _session): return self
        async def build(self, **_kwargs):
            self.build_calls += 1
            return empty_memory()
    class QueryResult:
        def one_or_none(self): return SimpleNamespace(sequence_number=1, role="USER", status="COMPLETED")
    class MemorySession:
        async def execute(self, _query): return QueryResult()
        def begin(self):
            @asynccontextmanager
            async def transaction(): yield self
            return transaction()
    class MemorySessionFactory:
        @asynccontextmanager
        async def __call__(self): yield MemorySession()
    class TransientRetryGeneration:
        def __init__(self): self.attempts = 0
        async def generate_with_attempt_preparer(self, _package, config, prepare):
            from app.ai.llm.schemas import LLMGenerationResult
            self.attempts += 1
            try:
                await prepare(1)
                raise httpx.ReadTimeout("simulated transient LLM transport failure")
            except httpx.TimeoutException:
                pass
            self.attempts += 1
            await prepare(2)
            return LLMGenerationResult("Answer [S1]", "fake", config.model, 1, 1, 2, 1, 1, 1, None)

    config = settings(rag_memory_max_turns=2)
    provider = SearchProvider()
    trust_filter = CountingTrustFilter(provider, config)
    reranker = FakeReranker([0.2])
    prompt = PromptSpy()
    memory = MemoryFactory()
    generation = TransientRetryGeneration()
    rag = RagOrchestrator(
        settings=config, session_factory=MemorySessionFactory(), retrieval_factory=lambda _session: EmptyInternalRetrieval(),
        reranker=InternalReranker(), prompt_builder=prompt,
        token_counter=type("Counter", (), {"count": staticmethod(len)})(),
        generation_service=generation, external_retrieval_service=trust_filter,
        external_reranking_service=ExternalRerankingService(config, provider=reranker),
        memory_builder_factory=memory,
    )
    result = asyncio.run(rag.run(request()))
    assert result.status is RagRunStatus.GROUNDED_ANSWER
    assert provider.calls == 1  # Tavily search
    assert trust_filter.calls == 1  # local trust filtering
    assert len(reranker.score_calls) == 1  # external reranking
    assert prompt.calls == 1  # PromptContextBuilder
    assert generation.attempts == 2 and memory.build_calls == 2
