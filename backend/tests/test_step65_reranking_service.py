from dataclasses import fields
from uuid import UUID, uuid4

import pytest

from app.ai.reranking.schemas import RerankerProviderIdentity
from app.ai.reranking.service import RerankingService
from app.ai.retrieval.schemas import RetrievalCandidate
from app.core.config import Settings


REVISION = "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"


def settings(**kwargs):
    return Settings(
        _env_file=None,
        app_env="test",
        debug=False,
        test_database_url="postgresql+psycopg://test:test@localhost/chinese_learning_test",
        secret_key="test-only-key",
        **kwargs,
    )


def candidate(rank: int, *, chunk_id=None, content=None, **overrides):
    values = dict(
        rank=rank,
        chunk_id=chunk_id or uuid4(),
        chunk_index=rank,
        content=content if content is not None else f"passage-{rank}",
        content_type="VOCABULARY",
        knowledge_version_id=uuid4(),
        knowledge_source_id=uuid4(),
        source_type="LESSON",
        source_document_id=None,
        source_lesson_id=uuid4(),
        chunk_lesson_id=uuid4(),
        document_title=None,
        lesson_title="Lesson one",
        hsk_level_number=1,
        page_number=None,
        section=None,
        locator_metadata={"source": "preserve"},
        distance=0.25,
        retrieval_score=0.75,
    )
    values.update(overrides)
    return RetrievalCandidate(**values)


class FakeProvider:
    def __init__(self, score_fn=None):
        self.identity = RerankerProviderIdentity(
            provider="LOCAL",
            provider_version="test-transformers/5.18.0;torch/2.14.1",
            model_name="BAAI/bge-reranker-v2-m3",
            model_revision=REVISION,
            reranker_input_version="v1",
        )
        self.device = "cpu"
        self.score_fn = score_fn or (lambda query, passages: [float(p.rsplit("passage-", 1)[-1]) for p in passages])
        self.validation_calls = []
        self.score_calls = []

    def validate_pair_lengths(self, query, passages):
        self.validation_calls.append((query, list(passages)))

    def score(self, query, passages):
        batch = list(passages)
        self.score_calls.append((query, batch))
        return self.score_fn(query, batch)


def passage_number(passage: str) -> int:
    return int(passage.rsplit("passage-", 1)[-1])


def provider_for_numbered_content():
    return FakeProvider(lambda _query, passages: [float(passage_number(p)) for p in passages])


def test_candidate_pool_is_exactly_first_twenty_all_scored_sequentially_then_top_five():
    candidates = [candidate(i) for i in range(1, 26)]
    provider = provider_for_numbered_content()

    result = RerankingService(provider=provider, settings=settings()).rerank("  q\t text ", candidates)

    assert sum(len(batch) for _, batch in provider.score_calls) == 20
    assert [len(batch) for _, batch in provider.score_calls] == [8, 8, 4]
    assert all(query == "q text" for query, _ in provider.score_calls)
    assert [item.rank for item in result.top_candidates] == [20, 19, 18, 17, 16]
    assert all(item.chunk_id in {c.chunk_id for c in candidates[:20]} for item in result.top_candidates)
    assert not ({c.chunk_id for c in candidates[20:]} & {item.chunk_id for item in result.scored_candidates})
    assert len(result.scored_candidates) == 20
    assert result.top_candidates == result.scored_candidates[:5]
    assert [item.retrieval_score for item in result.top_candidates] == [0.75] * 5
    assert [item.rerank_rank for item in result.scored_candidates] == list(range(1, 21))


@pytest.mark.parametrize("count", [1, 5, 19, 20])
def test_every_candidate_below_or_at_twenty_is_scored_count_times(count):
    candidates = [candidate(i) for i in range(1, count + 1)]
    provider = provider_for_numbered_content()

    result = RerankingService(provider=provider, settings=settings()).rerank("query", candidates)

    assert sum(len(batch) for _, batch in provider.score_calls) == count
    assert len(result.top_candidates) == min(count, 5)
    assert len(result.scored_candidates) == count


def test_empty_candidate_list_does_not_load_or_call_provider_even_for_empty_query():
    class ForbiddenProvider:
        @property
        def identity(self):
            raise AssertionError("provider must not be loaded for empty input")

        @property
        def device(self):
            raise AssertionError("provider must not be loaded for empty input")

    assert RerankingService(provider=ForbiddenProvider(), settings=settings()).rerank("", []).scored_candidates == ()


def test_configured_top_k_is_applied_after_all_selected_candidates_are_scored():
    items = [candidate(i) for i in range(1, 9)]
    provider = provider_for_numbered_content()

    result = RerankingService(
        provider=provider, settings=settings(reranker_top_k=1)
    ).rerank("query", items)

    assert sum(len(batch) for _, batch in provider.score_calls) == 8
    assert len(result.top_candidates) == 1
    assert result.top_candidates[0].rerank_score == 8.0
    assert result.top_candidates[0].rerank_rank == 1
    assert len(result.scored_candidates) == 8


def test_output_preserves_every_semantic_field_and_does_not_mutate_candidate():
    original = candidate(1)
    original_snapshot = tuple(getattr(original, f.name) for f in fields(RetrievalCandidate))
    provider = FakeProvider(lambda _query, _passages: [-2.375])

    result = RerankingService(provider=provider, settings=settings()).rerank("query", [original])

    ranked = result.scored_candidates[0]
    assert tuple(getattr(ranked, f.name) for f in fields(RetrievalCandidate)) == original_snapshot
    assert ranked.rank == original.rank
    assert ranked.retrieval_score == original.retrieval_score
    assert ranked.rerank_score == -2.375
    assert ranked.rerank_rank == 1
    assert original.content == "passage-1"
    assert not hasattr(ranked, "vector")


def test_raw_positive_negative_scores_are_not_fused_and_ties_are_deterministic():
    low_id, high_id = UUID(int=1), UUID(int=2)
    inputs = [candidate(2, chunk_id=high_id), candidate(1, chunk_id=low_id), candidate(3)]
    provider = FakeProvider(lambda _query, _passages: [-1.5, -1.5, 2.0])

    result = RerankingService(provider=provider, settings=settings()).rerank("query", inputs)

    assert [item.chunk_id for item in result.scored_candidates] == [inputs[2].chunk_id, low_id, high_id]
    assert [item.rerank_score for item in result.scored_candidates] == [2.0, -1.5, -1.5]
    assert [item.rank for item in result.scored_candidates] == [3, 1, 2]


def test_equal_rerank_and_semantic_ranks_use_stable_chunk_id_key():
    higher_id, lower_id = UUID(int=9), UUID(int=3)
    items = [candidate(1, chunk_id=higher_id), candidate(1, chunk_id=lower_id)]
    provider = FakeProvider(lambda _query, _passages: [0.4, 0.4])

    result = RerankingService(provider=provider, settings=settings()).rerank("query", items)

    assert [item.chunk_id for item in result.scored_candidates] == [lower_id, higher_id]


@pytest.mark.parametrize("scores", [[0.1], [float("nan"), 0.0], [float("inf"), 0.0]])
def test_mismatch_nan_and_infinity_fail_the_whole_operation(scores):
    provider = FakeProvider(lambda _query, _passages: scores)
    items = [candidate(1), candidate(2)]

    with pytest.raises(Exception) as caught:
        RerankingService(provider=provider, settings=settings()).rerank("query", items)

    assert getattr(caught.value, "code", None) == "INVALID_RERANKER_OUTPUT"


def test_later_batch_failure_discards_prior_batch_results_and_does_not_retry():
    class PartialFailure(FakeProvider):
        def score(self, query, passages):
            self.score_calls.append((query, list(passages)))
            if len(self.score_calls) == 1:
                return [0.9] * len(passages)
            raise RuntimeError("sensitive passage text must not escape")

    provider = PartialFailure()
    items = [candidate(i) for i in range(1, 10)]

    with pytest.raises(Exception) as caught:
        RerankingService(provider=provider, settings=settings()).rerank("private query", items)

    assert getattr(caught.value, "code", None) == "RERANKER_INFERENCE_FAILED"
    assert len(provider.score_calls) == 2


def test_duplicate_ids_and_malformed_candidates_fail_closed():
    duplicate_id = uuid4()
    duplicate = [candidate(1, chunk_id=duplicate_id), candidate(2, chunk_id=duplicate_id)]
    for inputs in (duplicate, [candidate(1, content=" \t ")], [object()]):
        with pytest.raises(Exception) as caught:
            RerankingService(provider=provider_for_numbered_content(), settings=settings()).rerank("query", inputs)
        assert getattr(caught.value, "code", None) == "INVALID_RERANK_INPUT"


def test_duplicate_passage_text_with_distinct_ids_stays_distinct():
    items = [candidate(1, content="same passage"), candidate(2, content="same passage")]
    provider = FakeProvider(lambda _query, passages: [0.0] * len(passages))

    result = RerankingService(provider=provider, settings=settings()).rerank("query", items)

    assert [item.chunk_id for item in result.scored_candidates] == [item.chunk_id for item in items]


def test_provider_identity_mismatch_fails_closed():
    provider = provider_for_numbered_content()
    provider.identity = RerankerProviderIdentity("LOCAL", "x", "unexpected", REVISION, "v1")

    with pytest.raises(Exception) as caught:
        RerankingService(provider=provider, settings=settings()).rerank("query", [candidate(1)])

    assert getattr(caught.value, "code", None) == "RERANKER_NOT_AVAILABLE"


def test_overlong_input_error_is_not_replaced_with_empty_or_semantic_success():
    class TooLong(FakeProvider):
        def validate_pair_lengths(self, _query, _passages):
            from app.ai.reranking.errors import reranking_error
            raise reranking_error("RERANK_INPUT_TOO_LONG", "too long", 422)

    with pytest.raises(Exception) as caught:
        RerankingService(provider=TooLong(), settings=settings()).rerank("query", [candidate(1)])

    assert getattr(caught.value, "code", None) == "RERANK_INPUT_TOO_LONG"


def test_structured_logs_exclude_query_passage_and_uuid(caplog):
    item = candidate(1, content="private passage secret")
    provider = FakeProvider(lambda _query, _passages: [0.5])

    with caplog.at_level("INFO", logger="app.ai.reranking.service"):
        RerankingService(provider=provider, settings=settings()).rerank("private query", [item])

    serialized = " ".join(record.getMessage() + repr(record.__dict__) for record in caplog.records)
    assert "private query" not in serialized
    assert "private passage secret" not in serialized
    assert str(item.chunk_id) not in serialized
    record = next(record for record in caplog.records if record.message == "reranking_completed")
    assert record.candidate_count == 1
    assert record.scored_count == 1
    assert record.rerank_top_k == 5


def test_failure_log_uses_safe_error_code_without_raw_inference_exception(caplog):
    class UnsafeFailure(FakeProvider):
        def score(self, _query, _passages):
            raise RuntimeError("private passage text must never appear")

    with caplog.at_level("WARNING", logger="app.ai.reranking.service"):
        with pytest.raises(Exception) as caught:
            RerankingService(provider=UnsafeFailure(), settings=settings()).rerank(
                "private learner query", [candidate(1, content="private passage text")]
            )

    serialized = " ".join(record.getMessage() + repr(record.__dict__) for record in caplog.records)
    assert getattr(caught.value, "code", None) == "RERANKER_INFERENCE_FAILED"
    assert "private learner query" not in serialized
    assert "private passage text" not in serialized
    assert "private passage text must never appear" not in serialized
    record = next(record for record in caplog.records if record.message == "reranking_failed")
    assert record.error_code == "RERANKER_INFERENCE_FAILED"


def test_service_has_no_db_or_per_request_configuration_parameters():
    parameters = RerankingService.rerank.__annotations__
    assert "session" not in parameters
    assert "batch_size" not in parameters
    assert "top_k" not in parameters
