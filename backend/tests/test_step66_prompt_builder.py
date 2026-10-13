import ast
from dataclasses import fields
from pathlib import Path
from uuid import uuid4

import pytest
from app.core.errors import ApplicationError

from app.ai.prompting.builder import PromptContextBuilder
from app.ai.prompting.errors import (
    CONTEXT_BUDGET_EXHAUSTED,
    NO_RETRIEVAL_CONTEXT,
    PROMPT_CONTEXT_BUILD_FAILED,
    TOKEN_COUNT_FAILED,
)
from app.ai.prompting.formatter import ContextBlockFormatter
from app.ai.prompting.instructions import SYSTEM_INSTRUCTIONS
from app.ai.prompting.schemas import LearningContext, PromptBudget
from app.ai.reranking.schemas import RerankedCandidate
from app.ai.retrieval.schemas import RetrievalCandidate


class FakeTokenCounter:
    def __init__(self, counts=None, default=1):
        self.counts = counts or {}
        self.default = default
        self.seen = []

    def count(self, text):
        self.seen.append(text)
        return self.counts.get(text, self.default)


def candidate(rank=1, *, content=None, chunk_id=None, **overrides):
    source_type = overrides.get("source_type", "LESSON")
    values = dict(
        rank=10 - rank,
        chunk_id=chunk_id or uuid4(),
        chunk_index=10 - rank,
        content=content if content is not None else f"evidence-{rank}",
        content_type="GRAMMAR" if source_type == "LESSON" else "DOCUMENT_TEXT",
        knowledge_version_id=uuid4(),
        knowledge_source_id=uuid4(),
        source_type=source_type,
        source_document_id=uuid4() if source_type == "DOCUMENT" else None,
        source_lesson_id=uuid4() if source_type == "LESSON" else None,
        chunk_lesson_id=uuid4() if source_type == "LESSON" else None,
        document_title="Document" if source_type == "DOCUMENT" else None,
        lesson_title="Lesson" if source_type == "LESSON" else None,
        hsk_level_number=1 if source_type == "LESSON" else None,
        page_number=rank,
        section=None,
        locator_metadata={"rank": rank},
        distance=float(rank),
        retrieval_score=1.0 / rank,
        rerank_score=float(100 - rank),
        rerank_rank=rank,
    )
    values.update(overrides)
    retrieval_values = {
        field.name: values[field.name] for field in fields(RetrievalCandidate)
    }
    return RerankedCandidate(
        **retrieval_values,
        rerank_score=values["rerank_score"],
        rerank_rank=values["rerank_rank"],
    )


def roomy_budget(**overrides):
    values = dict(model_input_limit=1000, reserved_output_tokens=25, serialization_overhead_tokens=7)
    values.update(overrides)
    return PromptBudget(**values)


def build(items, counter=None, budget=None, **kwargs):
    counter = counter or FakeTokenCounter()
    builder = PromptContextBuilder(token_counter=counter)
    result = builder.build(
        user_query=kwargs.pop("user_query", "Xin chào"),
        candidates=items,
        prompt_budget=budget or roomy_budget(),
        **kwargs,
    )
    return result, counter


def test_empty_candidates_build_successful_no_retrieval_result():
    result, _ = build([])
    assert result.status == "SUCCEEDED"
    assert result.reason == NO_RETRIEVAL_CONTEXT
    assert result.selected_count == result.omitted_count == 0
    assert result.package.context_blocks == ()
    assert dict(result.package.source_map) == {}
    assert result.package.selected_chunk_ids == ()
    assert result.package.omitted_chunk_ids == ()


@pytest.mark.parametrize("count", [1, 5])
def test_accepts_one_and_five_candidates_preserving_rerank_order(count):
    items = [candidate(rank) for rank in range(1, count + 1)]
    result, _ = build(items)
    assert [block.chunk_id for block in result.package.context_blocks] == [item.chunk_id for item in items]
    assert [block.source_label for block in result.package.context_blocks] == [f"S{i}" for i in range(1, count + 1)]
    assert result.package.omitted_chunk_ids == ()


def test_rejects_more_than_five_candidates():
    with pytest.raises(ApplicationError) as raised:
        build([candidate(rank) for rank in range(1, 7)])
    assert raised.value.code == PROMPT_CONTEXT_BUILD_FAILED


def test_rejects_wrong_candidate_dto():
    with pytest.raises(ApplicationError) as raised:
        build([object()])
    assert raised.value.code == PROMPT_CONTEXT_BUILD_FAILED


def test_rejects_candidate_with_incomplete_source_provenance():
    malformed = candidate(1, source_type="DOCUMENT", source_document_id=None)
    with pytest.raises(ApplicationError) as raised:
        build([malformed])
    assert raised.value.code == PROMPT_CONTEXT_BUILD_FAILED


@pytest.mark.parametrize("ranks", [(1, 3), (2,), (True,)])
def test_rejects_non_contiguous_or_bool_rerank_order(ranks):
    items = [candidate(rank, rerank_rank=rank) for rank in ranks]
    with pytest.raises(ApplicationError) as raised:
        build(items)
    assert raised.value.code == PROMPT_CONTEXT_BUILD_FAILED


def test_rejects_duplicate_chunk_identity_but_keeps_distinct_identical_content():
    repeated_id = uuid4()
    with pytest.raises(ApplicationError) as raised:
        build([candidate(1, chunk_id=repeated_id), candidate(2, chunk_id=repeated_id)])
    assert raised.value.code == PROMPT_CONTEXT_BUILD_FAILED

    result, _ = build([candidate(1, content="same", chunk_id=uuid4()), candidate(2, content="same", chunk_id=uuid4())])
    assert [block.text.rsplit("\n\n", 1)[-1] for block in result.package.context_blocks] == ["same", "same"]


def test_base_token_accounting_includes_system_learning_query_overhead_and_reserve():
    learning = LearningContext(hsk_level=2, lesson_title="lesson")
    learning_text = "Current learning context:\nHSK 2\nLesson: lesson"
    counter = FakeTokenCounter({SYSTEM_INSTRUCTIONS: 11, learning_text: 5, "query": 3})
    result, _ = build(
        [],
        counter,
        PromptBudget(50, 7, 4),
        user_query="query",
        learning_context=learning,
    )
    usage = result.package.budget_usage
    assert usage.system_tokens == 11
    assert usage.learning_context_tokens == 5
    assert usage.user_query_tokens == 3
    assert usage.serialization_overhead_tokens == 4
    assert usage.reserved_output_tokens == 7
    assert usage.base_input_tokens == 23
    assert usage.estimated_input_tokens + usage.reserved_output_tokens <= 50


def test_d1_base_fits_empty_candidates_yields_no_retrieval_context():
    counter = FakeTokenCounter({SYSTEM_INSTRUCTIONS: 4, "q": 2})
    result, _ = build([], counter, PromptBudget(20, 3, 2), user_query="q")
    assert result.reason == NO_RETRIEVAL_CONTEXT
    assert result.package.budget_usage.estimated_input_tokens + 3 <= 20


def test_d1_equality_base_total_equals_limit_is_valid_fit_with_empty_candidates():
    counter = FakeTokenCounter({SYSTEM_INSTRUCTIONS: 4, "q": 2})
    result, _ = build([], counter, PromptBudget(11, 3, 2), user_query="q")
    assert result.reason == NO_RETRIEVAL_CONTEXT
    assert result.package.budget_usage.estimated_input_tokens + 3 == 11


def test_d1_one_token_base_overflow_with_empty_candidates_is_exhausted():
    counter = FakeTokenCounter({SYSTEM_INSTRUCTIONS: 4, "q": 3})
    with pytest.raises(ApplicationError) as raised:
        build([], counter, PromptBudget(11, 3, 2), user_query="q")
    assert raised.value.code == CONTEXT_BUDGET_EXHAUSTED


def test_d1_structurally_valid_reserve_sum_can_be_runtime_infeasible():
    counter = FakeTokenCounter({SYSTEM_INSTRUCTIONS: 4, "q": 2})
    budget = PromptBudget(
        model_input_limit=10,
        reserved_output_tokens=5,
        serialization_overhead_tokens=5,
    )
    with pytest.raises(ApplicationError) as raised:
        build([], counter, budget, user_query="q")
    assert raised.value.code == CONTEXT_BUDGET_EXHAUSTED


def test_d1_base_overflow_precedes_candidate_formatting_and_packing(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("candidate formatting must not run before base budget validation")

    monkeypatch.setattr(ContextBlockFormatter, "format", forbidden)
    counter = FakeTokenCounter({SYSTEM_INSTRUCTIONS: 10, "q": 4})
    with pytest.raises(ApplicationError) as raised:
        build([candidate(1)], counter, PromptBudget(20, 3, 4), user_query="q")
    assert raised.value.code == CONTEXT_BUDGET_EXHAUSTED
    assert len(counter.seen) == 2


def test_candidates_present_but_no_whole_block_fits_is_budget_exhausted():
    item = candidate(1)
    counter = FakeTokenCounter({SYSTEM_INSTRUCTIONS: 2, "q": 1}, default=999)
    with pytest.raises(ApplicationError) as raised:
        build([item], counter, PromptBudget(30, 5, 2))
    assert raised.value.code == CONTEXT_BUDGET_EXHAUSTED


def test_whole_block_greedy_packing_skips_oversized_middle_and_reuses_label():
    items = [candidate(1, content="A"), candidate(2, content="B"), candidate(3, content="C")]
    rendered_counts = {
        "Source: S1\nHSK: 1\nLesson: Lesson\nType: GRAMMAR\n\nA": 200,
        "Source: S2\nHSK: 1\nLesson: Lesson\nType: GRAMMAR\n\nB": 700,
        "Source: S2\nHSK: 1\nLesson: Lesson\nType: GRAMMAR\n\nC": 250,
    }
    counter = FakeTokenCounter({SYSTEM_INSTRUCTIONS: 3, "q": 2, **rendered_counts})
    result, _ = build(items, counter, PromptBudget(520, 10, 5), user_query="q")
    assert [block.text.rsplit("\n\n", 1)[-1] for block in result.package.context_blocks] == ["A", "C"]
    assert [block.source_label for block in result.package.context_blocks] == ["S1", "S2"]
    assert result.package.selected_chunk_ids == (items[0].chunk_id, items[2].chunk_id)
    assert result.package.omitted_chunk_ids == (items[1].chunk_id,)
    assert set(result.package.source_map) == {"S1", "S2"}
    assert result.package.budget_usage.selected_context_tokens == 450


def test_whole_block_omission_never_returns_truncated_evidence():
    item = candidate(1, content="NO_PARTIAL_COPY")
    counter = FakeTokenCounter({SYSTEM_INSTRUCTIONS: 2, "q": 1}, default=500)
    with pytest.raises(ApplicationError) as raised:
        build([item], counter, PromptBudget(50, 5, 2))
    assert raised.value.code == CONTEXT_BUDGET_EXHAUSTED


def test_source_map_contains_selected_trusted_provenance_only():
    items = [candidate(1), candidate(2)]
    counter = FakeTokenCounter({SYSTEM_INSTRUCTIONS: 2, "q": 1}, default=1)
    result, _ = build(items, counter)
    assert result.package.source_map["S1"].chunk_id == items[0].chunk_id
    assert result.package.source_map["S1"].knowledge_source_id == items[0].knowledge_source_id
    assert result.package.source_map["S1"].source_lesson_id == items[0].source_lesson_id
    assert result.package.source_map["S1"].page_number == items[0].page_number
    assert result.package.source_map["S1"].locator_metadata == items[0].locator_metadata


def test_package_keeps_system_learning_evidence_and_query_separate_without_future_fields():
    result, _ = build([candidate(1)], learning_context=LearningContext(current_module="Grammar"))
    package = result.package
    assert package.system_instructions == SYSTEM_INSTRUCTIONS
    assert package.learning_context == "Current learning context:\nModule: Grammar"
    assert package.context_blocks[0].text.endswith("evidence-1")
    assert package.user_query == "Xin chào"
    names = {field.name for field in fields(package)}
    assert not {"messages", "history", "citations", "provider_request"} & names
    assert package.conversation_memory is None
    assert "[S1]" not in package.system_instructions


@pytest.mark.parametrize("bad_count", [-1, 1.5, True, "1"])
def test_token_counter_contract_failures_are_normalized(bad_count):
    counter = FakeTokenCounter({SYSTEM_INSTRUCTIONS: bad_count})
    with pytest.raises(ApplicationError) as raised:
        build([], counter)
    assert raised.value.code == TOKEN_COUNT_FAILED
    assert "bad_count" not in raised.value.message


def test_token_counter_exception_does_not_leak_raw_exception_or_query_in_logs(caplog):
    class ExplodingCounter:
        def count(self, _text):
            raise RuntimeError("SENTINEL_RAW_COUNTER_EXCEPTION")

    with pytest.raises(ApplicationError) as raised:
        build([], ExplodingCounter(), user_query="SENTINEL_QUERY")
    assert raised.value.code == TOKEN_COUNT_FAILED
    assert "SENTINEL_RAW_COUNTER_EXCEPTION" not in str(raised.value)
    assert "SENTINEL_QUERY" not in caplog.text
    assert "SENTINEL_RAW_COUNTER_EXCEPTION" not in caplog.text
    assert any(getattr(record, "error_code", None) == TOKEN_COUNT_FAILED for record in caplog.records)


def test_success_and_failure_logs_do_not_contain_query_or_evidence(caplog):
    item = candidate(1, content="SENTINEL_EVIDENCE")
    with caplog.at_level("INFO", logger="app.ai.prompting.builder"):
        build([item], user_query="SENTINEL_QUERY")
    assert "SENTINEL_QUERY" not in caplog.text
    assert "SENTINEL_EVIDENCE" not in caplog.text
    assert any(record.message == "prompt_context_build_completed" for record in caplog.records)
    success = next(record for record in caplog.records if record.message == "prompt_context_build_completed")
    assert success.input_candidate_count == 1


def test_prompting_package_has_no_database_network_provider_orchestration_imports():
    package = Path(__file__).parents[1] / "app" / "ai" / "prompting"
    forbidden_roots = {
        "sqlalchemy",
        "psycopg",
        "httpx",
        "requests",
        "openai",
        "anthropic",
        "transformers",
        "sentence_transformers",
    }
    for path in package.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                imported = [node.module or ""]
            else:
                continue
            assert not any(name.split(".", 1)[0] in forbidden_roots for name in imported)
