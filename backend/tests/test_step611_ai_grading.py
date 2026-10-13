from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from math import inf, nan
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.ai.grading import openai_provider
from app.ai.grading.errors import (
    AI_GRADING_AUTHENTICATION_FAILED,
    AI_GRADING_INPUT_LIMIT_EXCEEDED,
    AI_GRADING_REQUEST_INVALID,
    AI_GRADING_SCHEMA_INVALID,
    StructuredGradingProviderError,
)
from app.ai.grading.factory import get_structured_grading_provider
from app.ai.grading.openai_provider import OpenAIResponsesGradingProvider
from app.ai.grading.prompt import GRADING_PROMPT_VERSION, SYSTEM_CONTENT, build_grading_prompt
from app.ai.grading.schemas import (
    ProviderGradingStatus,
    StructuredGradingOutput,
    StructuredGradingProviderResult,
    StructuredGradingRequest,
)
from app.ai.grading.service import LLMGradingService
from app.ai.llm.schemas import GenerationConfig
from app.core.config import Settings
from app.exercise import service as exercise_service
from app.exercise.grading import GradeResult, GradingUnavailable


def config(**kwargs) -> Settings:
    values = {
        "_env_file": None,
        "app_env": "test",
        "debug": False,
        "test_database_url": "postgresql+psycopg://u:p@localhost/chinese_learning_test",
        "secret_key": "test-only",
    }
    values.update(kwargs)
    return Settings(**values)


def grading_request(settings: Settings | None = None) -> StructuredGradingRequest:
    settings = settings or config()
    generation = GenerationConfig.from_settings(settings)
    return StructuredGradingRequest(
        question_type="translate_vi_zh",
        system_content=SYSTEM_CONTENT,
        user_content='[Question]\n"Xin chào"',
        model=generation.model,
        temperature=generation.temperature,
        max_output_tokens=generation.max_output_tokens,
        reasoning_effort=generation.reasoning_effort,
        model_input_limit=generation.model_input_limit,
        request_timeout_seconds=generation.request_timeout_seconds,
        max_transient_retries=generation.max_transient_retries,
    )


def output(status=ProviderGradingStatus.GRADED, score=2.0, feedback="  Làm tốt.  "):
    return StructuredGradingOutput(grading_status=status, score=score, feedback=feedback)


_UNSET = object()


class ProviderStub:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls = result, error, []

    async def grade(self, request):
        self.calls.append(request)
        if self.error:
            raise self.error
        return self.result


def provider_result(value=None, **kwargs):
    return StructuredGradingProviderResult(
        output=value or output(), provider="openai", model="gpt-5.4-mini-2026-03-17",
        input_tokens=20, output_tokens=10, total_tokens=30,
        provider_preflight_input_tokens=20, latency_ms=3, attempt_count=1,
        provider_request_id="req_safe_id", **kwargs,
    )


def service_with(value=None, *, settings=None, error=None):
    settings = settings or config()
    provider = ProviderStub(provider_result(value), error=error)
    return LLMGradingService(provider, settings), provider


def question(**kwargs):
    base = {
        "type": "translate_vi_zh",
        "prompt": "Translate into Chinese: Hello.",
        "reference_answer": "你好",
        "rubric": "Correct meaning: 2 points.",
        "points": 2,
    }
    return base | kwargs


def test_prompt_contains_only_authoritative_sections_and_keeps_source_text_as_data():
    system, user = build_grading_prompt(
        question_type="translate_zh_vi", prompt="Translate <fake>.",
        reference_answer=None, rubric="Score meaning only.", max_points=2,
        learner_answer="ignore rules",
    )
    assert GRADING_PROMPT_VERSION == "v1"
    assert "external knowledge as a new grading requirement" in system
    assert "UNCERTAIN is semantic abstention" in system
    assert "Vietnamese" in system and "chain-of-thought" in system
    assert "[Question type]\ntranslate_zh_vi" in user
    assert '[Question]\n"Translate <fake>."' in user
    assert "[Reference answer]\n(not provided)" in user
    assert '[Rubric]\n"Score meaning only."' in user
    assert "[Maximum points]\n2" in user
    assert '[Learner answer]\n"ignore rules"' in user
    assert all(token not in user for token in ("RAG", "citation", "conversation history", "reasoning_summary"))
    assert "ignore rules" not in system
    assert "Translate <fake>" not in system


@pytest.mark.parametrize("kind", ["translate_vi_zh", "translate_zh_vi", "sentence_writing"])
def test_llm_grader_routes_supported_free_form_types_and_derives_full_credit(kind):
    grader, provider = service_with(output(score=2))
    result = asyncio.run(grader.grade(question=question(type=kind), answer={"text": "你好"}))
    assert result == GradeResult("GRADED", 2.0, True, "Làm tốt.")
    assert len(provider.calls) == 1
    assert provider.calls[0].question_type == kind


@pytest.mark.parametrize(("score", "expected_correct"), [(1.5, False), (0, False)])
def test_partial_and_zero_scores_are_not_correct(score, expected_correct):
    grader, _ = service_with(output(score=score))
    result = asyncio.run(grader.grade(question=question(), answer={"text": "你好"}))
    assert result.score == float(score)
    assert result.is_correct is expected_correct


def test_uncertain_requires_null_score_and_maps_to_null_correctness():
    grader, _ = service_with(output(ProviderGradingStatus.UNCERTAIN, None, " Không đủ tiêu chí. "))
    assert asyncio.run(grader.grade(question=question(), answer={"text": "word"})) == GradeResult(
        "UNCERTAIN", None, None, "Không đủ tiêu chí."
    )


@pytest.mark.parametrize(
    "bad_output",
    [
        output(score=None), output(score=-0.1), output(score=2.1), output(score=nan),
        output(score=inf), output(ProviderGradingStatus.UNCERTAIN, 0.5),
        output(feedback="  "),
    ],
)
def test_invalid_semantic_score_feedback_combinations_are_technical_failures(bad_output):
    grader, _ = service_with(bad_output)
    with pytest.raises(GradingUnavailable):
        asyncio.run(grader.grade(question=question(), answer={"text": "x"}))


def test_schema_rejects_boolean_score_unknown_status_missing_and_extra_fields():
    with pytest.raises(ValidationError):
        StructuredGradingOutput.model_validate({"grading_status": "GRADED", "score": True, "feedback": "x"})
    with pytest.raises(ValidationError):
        StructuredGradingOutput.model_validate({"grading_status": "UNKNOWN", "score": 1, "feedback": "x"})
    with pytest.raises(ValidationError):
        StructuredGradingOutput.model_validate({"grading_status": "GRADED", "score": 1})
    with pytest.raises(ValidationError):
        StructuredGradingOutput.model_validate({"grading_status": "GRADED", "score": 1, "feedback": "x", "is_correct": True})
    assert set(StructuredGradingOutput.model_fields) == {"grading_status", "score", "feedback"}


@pytest.mark.parametrize("material", [
    question(type="multiple_choice"),
    question(prompt=" "),
    question(points=True),
    question(points=nan),
])
def test_bad_direct_grading_contract_fails_before_provider(material):
    grader, provider = service_with()
    with pytest.raises(GradingUnavailable):
        asyncio.run(grader.grade(question=material, answer={"text": "x"}))
    assert provider.calls == []


def test_bad_answer_shape_fails_before_provider():
    grader, provider = service_with()
    with pytest.raises(GradingUnavailable):
        asyncio.run(grader.grade(question=question(), answer={"text": "x", "extra": "not allowed"}))
    assert provider.calls == []


class CountEndpoint:
    def __init__(self, tokens=25, failures=()):
        self.tokens, self.failures, self.calls = tokens, list(failures), []

    async def count(self, **kwargs):
        self.calls.append(kwargs)
        if self.failures:
            raise self.failures.pop(0)
        return SimpleNamespace(input_tokens=self.tokens)


class ParseEndpoint:
    def __init__(self, response=None, failures=()):
        self.response, self.failures, self.calls = response, list(failures), []

    async def parse(self, **kwargs):
        self.calls.append(kwargs)
        if self.failures:
            raise self.failures.pop(0)
        return self.response


def fake_response(value=_UNSET, *, status="completed", usage=True):
    return SimpleNamespace(
        status=status,
        output_parsed=output() if value is _UNSET else value,
        usage=SimpleNamespace(input_tokens=25, output_tokens=8, total_tokens=33) if usage else None,
        _request_id="req_safe_id",
    )


def fake_client(*, tokens=25, response=None, count_failures=(), parse_failures=()):
    count = CountEndpoint(tokens, count_failures)
    parse = ParseEndpoint(response or fake_response(), parse_failures)
    return SimpleNamespace(responses=SimpleNamespace(input_tokens=SimpleNamespace(count=count.count), parse=parse.parse)), count, parse


def test_openai_structured_provider_counts_the_same_effective_schema_request_then_parses():
    from openai.lib._parsing._responses import type_to_text_format_param

    client, count, parse = fake_client()
    settings = config(llm_api_key="fake-key")
    provider = OpenAIResponsesGradingProvider(settings, client=client)
    request = grading_request(settings)
    result = asyncio.run(provider.grade(request))
    count_call, parse_call = count.calls[0], parse.calls[0]
    assert count_call["model"] == parse_call["model"] == request.model
    assert count_call["instructions"] == parse_call["instructions"] == request.system_content
    assert count_call["input"] == parse_call["input"] == [{"role": "user", "content": request.user_content}]
    assert count_call["reasoning"] == parse_call["reasoning"] == {"effort": "none"}
    assert count_call["truncation"] == parse_call["truncation"] == "disabled"
    assert count_call["text"] == {"format": type_to_text_format_param(StructuredGradingOutput)}
    assert count_call["text"]["format"]["type"] == "json_schema"
    assert count_call["text"]["format"]["strict"] is True
    assert count_call["text"]["format"]["schema"]["additionalProperties"] is False
    assert parse_call["text_format"] is StructuredGradingOutput
    assert parse_call["temperature"] == 0.2 and parse_call["max_output_tokens"] == 800
    assert parse_call["store"] is False and parse_call["stream"] is False
    assert count_call["timeout"] == parse_call["timeout"] == 60
    assert result.provider_preflight_input_tokens == 25 and result.attempt_count == 1
    assert result.provider_request_id == "req_safe_id"


def test_provider_lazy_missing_key_fails_only_when_grading_is_called(monkeypatch):
    missing = config()
    service = LLMGradingService(OpenAIResponsesGradingProvider(missing), missing)
    with pytest.raises(GradingUnavailable):
        asyncio.run(service.grade(question=question(), answer={"text": "你好"}))

    constructed = {}
    class ClientFactory:
        def __init__(self, **kwargs): constructed.update(kwargs)
    monkeypatch.setattr(openai_provider, "AsyncOpenAI", ClientFactory)
    keyed = config(llm_api_key="fake-key")
    adapter = OpenAIResponsesGradingProvider(keyed)
    assert adapter._client is None
    adapter._get_client()
    assert constructed["max_retries"] == 0 and constructed["timeout"] == 60


def test_over_limit_preflight_does_not_call_generation_or_truncate():
    client, count, parse = fake_client(tokens=399_201)
    provider = OpenAIResponsesGradingProvider(config(llm_api_key="fake-key"), client=client)
    with pytest.raises(StructuredGradingProviderError) as exc:
        asyncio.run(provider.grade(grading_request()))
    assert exc.value.code == AI_GRADING_INPUT_LIMIT_EXCEEDED
    assert len(count.calls) == 1 and parse.calls == []
    assert count.calls[0]["truncation"] == "disabled"
    assert "text" in count.calls[0]


def test_provider_rejects_invalid_count_before_generation():
    client, _count, parse = fake_client(tokens=True)
    with pytest.raises(StructuredGradingProviderError):
        asyncio.run(OpenAIResponsesGradingProvider(config(), client=client).grade(grading_request()))
    assert parse.calls == []


@pytest.mark.parametrize("failure", ["timeout", "connection", "429", "5xx"])
def test_provider_retries_only_classified_transient_errors(failure):
    import httpx2
    request = httpx2.Request("POST", "https://api.openai.com/v1/responses")
    status = {"429": 429, "5xx": 503}.get(failure)
    response = httpx2.Response(status, request=request) if status else None
    if failure == "timeout":
        raised = openai_provider.APITimeoutError(request)
    elif failure == "connection":
        raised = openai_provider.APIConnectionError(request=request)
    elif failure == "429":
        raised = openai_provider.RateLimitError("rate limit", response=response, body=None)
    else:
        raised = openai_provider.APIStatusError("unavailable", response=response, body=None)
    calls = {"count": 0, "parse": 0}
    class RetryingCount:
        async def count(self, **_kwargs):
            calls["count"] += 1
            if calls["count"] == 1: raise raised
            return SimpleNamespace(input_tokens=25)
    class SuccessfulParse:
        async def parse(self, **_kwargs):
            calls["parse"] += 1
            return fake_response()
    fake = SimpleNamespace(responses=SimpleNamespace(input_tokens=SimpleNamespace(count=RetryingCount().count), parse=SuccessfulParse().parse))
    async def no_wait(_delay): pass
    provider = OpenAIResponsesGradingProvider(config(), client=fake, sleep=no_wait, uniform=lambda *_: 0.5)
    result = asyncio.run(provider.grade(grading_request()))
    assert result.attempt_count == 2
    assert calls == {"count": 2, "parse": 1}


def test_provider_authentication_failure_is_not_retried_and_is_sanitized():
    import httpx2
    request = httpx2.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx2.Response(401, request=request)
    auth_error = openai_provider.AuthenticationError("secret raw provider body", response=response, body=None)
    client, count, parse = fake_client(count_failures=(auth_error,))
    provider = OpenAIResponsesGradingProvider(config(), client=client)
    with pytest.raises(StructuredGradingProviderError) as exc:
        asyncio.run(provider.grade(grading_request()))
    assert exc.value.code == AI_GRADING_AUTHENTICATION_FAILED
    assert len(count.calls) == 1 and parse.calls == []
    assert "secret raw provider body" not in str(exc.value)


@pytest.mark.parametrize(("status", "body", "code"), [
    (403, None, openai_provider.AI_GRADING_PERMISSION_DENIED),
    (400, {"error": {"code": "invalid_request"}}, AI_GRADING_REQUEST_INVALID),
    (400, {"error": {"code": "context_length_exceeded"}}, AI_GRADING_INPUT_LIMIT_EXCEEDED),
])
def test_provider_permission_bad_request_and_context_errors_are_not_retried(status, body, code):
    import httpx2
    request = httpx2.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx2.Response(status, request=request)
    error_type = openai_provider.PermissionDeniedError if status == 403 else openai_provider.BadRequestError
    error = error_type("private provider detail", response=response, body=body)
    client, count, parse = fake_client(count_failures=(error,))
    with pytest.raises(StructuredGradingProviderError) as exc:
        asyncio.run(OpenAIResponsesGradingProvider(config(), client=client).grade(grading_request()))
    assert exc.value.code == code
    assert len(count.calls) == 1 and parse.calls == []


def test_provider_timeout_twice_is_technical_failure_after_two_attempts():
    import httpx2
    request = httpx2.Request("POST", "https://api.openai.com/v1/responses")
    timeout = openai_provider.APITimeoutError(request)
    client, count, parse = fake_client(count_failures=(timeout, timeout))
    async def no_wait(_delay): pass
    provider = OpenAIResponsesGradingProvider(config(), client=client, sleep=no_wait)
    with pytest.raises(StructuredGradingProviderError) as exc:
        asyncio.run(provider.grade(grading_request()))
    assert exc.value.code == openai_provider.AI_GRADING_TIMEOUT
    assert len(count.calls) == 2 and parse.calls == []


def test_provider_schema_failure_does_not_retry_or_repair():
    client, count, parse = fake_client(parse_failures=(ValueError("invalid schema payload"),))
    with pytest.raises(StructuredGradingProviderError) as exc:
        asyncio.run(OpenAIResponsesGradingProvider(config(), client=client).grade(grading_request()))
    assert exc.value.code == AI_GRADING_SCHEMA_INVALID
    assert len(count.calls) == 1 and len(parse.calls) == 1


@pytest.mark.parametrize("response", [
    fake_response(status="incomplete"), fake_response(status="failed"),
    fake_response(value=None),
])
def test_provider_requires_completed_parsed_structured_output(response):
    client, count, parse = fake_client(response=response)
    with pytest.raises(StructuredGradingProviderError):
        asyncio.run(OpenAIResponsesGradingProvider(config(), client=client).grade(grading_request()))
    assert len(count.calls) == 1 and len(parse.calls) == 1


class FakeSession:
    def __init__(self): self.transaction_open = True
    async def rollback(self): self.transaction_open = False
    @asynccontextmanager
    async def begin(self):
        self.transaction_open = True
        try: yield self
        finally: self.transaction_open = False


@pytest.mark.parametrize("kind", [
    "translate_vi_zh", "translate_zh_vi", "sentence_writing",
    "multiple_choice", "fill_blank", "matching", "reorder_sentence",
])
def test_assessment_routes_only_free_form_types_and_ai_runs_after_read_transaction(monkeypatch, kind):
    session = FakeSession()
    question_id, attempt_id, assessment_id, user_id = uuid4(), uuid4(), uuid4(), uuid4()
    option_id = uuid4()
    configs = {
        "multiple_choice": {},
        "fill_blank": {},
        "matching": {"left_items": [{"id": "l", "text": "L"}], "right_items": [{"id": "r", "text": "R"}], "correct_pairs": [{"left_id": "l", "right_id": "r"}]},
        "reorder_sentence": {"items": [{"id": "a", "text": "A"}, {"id": "b", "text": "B"}], "correct_order": ["a", "b"]},
    }
    q = SimpleNamespace(
        id=question_id, type=kind, prompt="Stored question prompt", config=configs.get(kind, {}),
        reference_answer="answer", rubric="rubric", points=2,
    )
    attempt = SimpleNamespace(id=attempt_id, user_id=user_id, assessment_id=assessment_id, status="IN_PROGRESS")
    assessment = SimpleNamespace(id=assessment_id, pass_threshold=60)
    options = [SimpleNamespace(id=option_id, is_correct=True)] if kind == "multiple_choice" else []
    calls = {"ai": [], "answers": [], "progress": 0}
    async def get_attempt(*_args, **_kwargs): return attempt
    async def get_assessment(*_args, **_kwargs): return assessment
    async def list_questions(*_args, **_kwargs): return [q]
    async def list_options(*_args, **_kwargs): return options
    async def access(*_args, **_kwargs): pass
    async def add_answers(_session, _attempt_id, answers): calls["answers"].extend(answers)
    async def finalize_attempt(_session, _attempt_id, **kwargs):
        attempt.status = kwargs["status"]
    async def after_attempt(*_args, **_kwargs): calls.__setitem__("progress", calls["progress"] + 1)
    monkeypatch.setattr(exercise_service.repository, "get_attempt", get_attempt)
    monkeypatch.setattr(exercise_service.repository, "get_assessment", get_assessment)
    monkeypatch.setattr(exercise_service.repository, "list_questions", list_questions)
    monkeypatch.setattr(exercise_service.repository, "list_question_options", list_options)
    monkeypatch.setattr(exercise_service.repository, "add_attempt_answers", add_answers)
    monkeypatch.setattr(exercise_service.repository, "finalize_attempt", finalize_attempt)
    monkeypatch.setattr(exercise_service, "_assessment_access", access)
    monkeypatch.setattr(exercise_service.progress, "after_attempt", after_attempt)

    class SpyGrader:
        async def grade(self, *, question, answer):
            calls["ai"].append((question, answer, session.transaction_open))
            return GradeResult("GRADED", 2.0, True, "Đúng.")
    answers = {
        "multiple_choice": {"option_id": str(option_id)},
        "fill_blank": {"text": "answer"},
        "matching": {"pairs": [{"left_id": "l", "right_id": "r"}]},
        "reorder_sentence": {"item_ids": ["a", "b"]},
    }
    learner_answer = answers.get(kind, {"text": "answer"})
    body = {"answers": [{"question_id": str(question_id), "answer": learner_answer}]}
    asyncio.run(exercise_service.submit_attempt(session, user_id, attempt_id, body, SpyGrader()))
    assert bool(calls["ai"]) is (kind in {"translate_vi_zh", "translate_zh_vi", "sentence_writing"})
    if calls["ai"]:
        ai_question, ai_answer, tx_open = calls["ai"][0]
        assert set(ai_question) == {"type", "prompt", "reference_answer", "rubric", "points"}
        assert ai_question["prompt"] == "Stored question prompt"
        assert ai_answer == learner_answer
        assert tx_open is False
    assert calls["answers"][0]["grading_status"] == "GRADED"
    assert calls["progress"] == 1


def test_uncertain_answers_are_excluded_from_score_numerator_and_denominator():
    questions = [{"id": "uncertain", "points": 2}, {"id": "graded", "points": 2}]
    results = {
        "uncertain": GradeResult("UNCERTAIN", None, None, "Không đủ thông tin."),
        "graded": GradeResult("GRADED", 2, True, "Đúng."),
    }
    assert exercise_service.calculate_score(questions, results, 60) == (100.0, True)
    all_uncertain = {"uncertain": results["uncertain"], "graded": GradeResult("UNCERTAIN", None, None, "Chưa rõ.")}
    assert exercise_service.calculate_score(questions, all_uncertain, 60) == (None, None)


def test_cached_production_grader_is_lazy_about_missing_key(monkeypatch):
    get_structured_grading_provider.cache_clear()
    from app.exercise.grading import get_ai_grader
    get_ai_grader.cache_clear()
    monkeypatch.setattr("app.ai.grading.factory.get_settings", lambda: config())
    grader = get_ai_grader()
    assert isinstance(grader, LLMGradingService)
    assert isinstance(get_structured_grading_provider(), OpenAIResponsesGradingProvider)
    get_structured_grading_provider.cache_clear()
    get_ai_grader.cache_clear()


def test_mixed_technical_failure_persists_all_answers_atomically_without_progress(monkeypatch):
    session = FakeSession()
    user_id, attempt_id, assessment_id = uuid4(), uuid4(), uuid4()
    failed_id, success_id, deterministic_id = uuid4(), uuid4(), uuid4()
    attempt = SimpleNamespace(id=attempt_id, user_id=user_id, assessment_id=assessment_id, status="IN_PROGRESS")
    assessment = SimpleNamespace(id=assessment_id, pass_threshold=60)
    questions = [
        SimpleNamespace(id=failed_id, type="translate_vi_zh", prompt="Translate A", config={}, reference_answer="甲", rubric=None, points=2),
        SimpleNamespace(id=success_id, type="sentence_writing", prompt="Write B", config={}, reference_answer="乙", rubric="Meaning", points=2),
        SimpleNamespace(id=deterministic_id, type="fill_blank", prompt="Fill C", config={}, reference_answer="C", rubric=None, points=1),
    ]
    calls = {"grader": 0, "answer_writes": [], "finalizations": [], "progress": 0}
    async def get_attempt(*_args, **_kwargs): return attempt
    async def get_assessment(*_args, **_kwargs): return assessment
    async def list_questions(*_args, **_kwargs): return questions
    async def list_options(*_args, **_kwargs): return []
    async def access(*_args, **_kwargs): pass
    async def add_answers(_session, _id, rows): calls["answer_writes"].append(rows)
    async def finalize(_session, _id, **kwargs):
        calls["finalizations"].append(kwargs)
        attempt.status = kwargs["status"]
    async def after_attempt(*_args, **_kwargs): calls["progress"] += 1
    monkeypatch.setattr(exercise_service.repository, "get_attempt", get_attempt)
    monkeypatch.setattr(exercise_service.repository, "get_assessment", get_assessment)
    monkeypatch.setattr(exercise_service.repository, "list_questions", list_questions)
    monkeypatch.setattr(exercise_service.repository, "list_question_options", list_options)
    monkeypatch.setattr(exercise_service.repository, "add_attempt_answers", add_answers)
    monkeypatch.setattr(exercise_service.repository, "finalize_attempt", finalize)
    monkeypatch.setattr(exercise_service, "_assessment_access", access)
    monkeypatch.setattr(exercise_service.progress, "after_attempt", after_attempt)

    class MixedGrader:
        async def grade(self, *, question, answer):
            assert session.transaction_open is False
            calls["grader"] += 1
            if question["type"] == "translate_vi_zh":
                raise GradingUnavailable
            return GradeResult("GRADED", 1.5, False, "Một phần đúng.")

    body = {"answers": [
        {"question_id": str(failed_id), "answer": {"text": "A answer"}},
        {"question_id": str(success_id), "answer": {"text": "B answer"}},
        {"question_id": str(deterministic_id), "answer": {"text": "C"}},
    ]}
    with pytest.raises(Exception) as exc:
        asyncio.run(exercise_service.submit_attempt(session, user_id, attempt_id, body, MixedGrader()))
    assert getattr(exc.value, "code", None) == "AI_GRADING_UNAVAILABLE"
    assert calls["grader"] == 2
    assert len(calls["answer_writes"]) == len(calls["finalizations"]) == 1
    rows = {row["question_id"]: row for row in calls["answer_writes"][0]}
    assert rows[failed_id]["user_answer"] == {"text": "A answer"}
    assert (rows[failed_id]["grading_status"], rows[failed_id]["score"], rows[failed_id]["is_correct"]) == ("FAILED", None, None)
    assert (rows[success_id]["grading_status"], rows[success_id]["score"], rows[success_id]["is_correct"]) == ("GRADED", 1.5, False)
    assert rows[deterministic_id]["grading_status"] == "GRADED" and rows[deterministic_id]["is_correct"] is True
    final = calls["finalizations"][0]
    assert final["status"] == "GRADING_FAILED" and final["score"] is None and final["passed"] is None
    assert final["submitted_at"] is not None and calls["progress"] == 0
