import asyncio
import logging
from types import SimpleNamespace

import pytest

from app.ai.llm.errors import (
    EMPTY_LLM_RESPONSE,
    INVALID_LLM_RESPONSE,
    LLM_CONTEXT_LIMIT_EXCEEDED,
    LLM_PROVIDER_NOT_CONFIGURED,
)
from app.ai.llm.openai_provider import OpenAILLMProvider
from app.ai.llm.schemas import GenerationConfig
from app.ai.llm.serializer import LLMRequestSerializer
from app.core.config import Settings
from step67_fixtures import prompt_package


class FakeEndpoint:
    def __init__(self, values):
        self.values = list(values)
        self.calls = []

    async def count(self, **kwargs):
        self.calls.append(kwargs)
        value = self.values.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        value = self.values.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


class FakeClient:
    def __init__(self, counts, generations):
        self.count_endpoint = FakeEndpoint(counts)
        self.create_endpoint = FakeEndpoint(generations)
        self.responses = SimpleNamespace(
            input_tokens=SimpleNamespace(count=self.count_endpoint.count),
            create=self.create_endpoint.create,
        )


def request():
    return LLMRequestSerializer().serialize(prompt_package(), GenerationConfig())


def settings(**overrides):
    values = dict(
        _env_file=None, app_env="test", debug=False,
        test_database_url="postgresql+psycopg://t:t@localhost/chinese_learning_test",
        secret_key="test-only-signing-key-not-a-deployment-secret-0123456789",
    )
    values.update(overrides)
    return Settings(**values)


def count(tokens=1200):
    return SimpleNamespace(input_tokens=tokens)


def response(status="completed", text="A clear answer", **kwargs):
    return SimpleNamespace(
        id="resp-resource-id", status=status, output_text=text, usage=SimpleNamespace(
            input_tokens=1200, output_tokens=12, total_tokens=1212
        ), _request_id="req-safe-id", **kwargs,
    )


def sdk_status_error(error_type, status, body=None):
    import openai._base_client as base_client
    request = base_client.httpx2.Request("POST", "https://api.openai.com/v1/responses")
    response_obj = base_client.httpx2.Response(status, request=request)
    return error_type("provider error", response=response_obj, body=body)


def test_provider_preflights_then_sends_stateless_frozen_request() -> None:
    client = FakeClient([count()], [response()])
    result = asyncio.run(OpenAILLMProvider(settings(), client=client).generate(request()))
    assert result.text == "A clear answer"
    assert result.provider_preflight_input_tokens == 1200
    assert result.provider_request_id == "req-safe-id"
    assert result.provider_request_id != "resp-resource-id"
    assert result.attempt_count == 1
    assert client.count_endpoint.calls[0]["model"] == "gpt-5.4-mini-2026-03-17"
    sent = client.create_endpoint.calls[0]
    assert sent["reasoning"] == {"effort": "none"}
    assert sent["temperature"] == 0.2 and sent["max_output_tokens"] == 800
    assert sent["truncation"] == "disabled" and sent["store"] is False
    assert sent["stream"] is False and "previous_response_id" not in sent


def test_provider_context_overflow_never_generates_or_retries() -> None:
    client = FakeClient([count(400_000)], [])
    with pytest.raises(Exception) as caught:
        asyncio.run(OpenAILLMProvider(settings(), client=client).generate(request()))
    assert caught.value.code == LLM_CONTEXT_LIMIT_EXCEEDED
    assert len(client.count_endpoint.calls) == 1 and not client.create_endpoint.calls


@pytest.mark.parametrize(
    ("provider_response", "expected"),
    [
        (response(text="  \n"), EMPTY_LLM_RESPONSE),
        (response(status="incomplete", text="partial", incomplete_details=SimpleNamespace(reason="max_output_tokens")), INVALID_LLM_RESPONSE),
        (response(status="queued"), INVALID_LLM_RESPONSE),
        (response(status=None), INVALID_LLM_RESPONSE),
        (response(status="completed", text=None), INVALID_LLM_RESPONSE),
        (response(status="failed"), "LLM_GENERATION_FAILED"),
        (None, INVALID_LLM_RESPONSE),
    ],
)
def test_non_success_statuses_fail_closed_without_second_call(provider_response, expected) -> None:
    client = FakeClient([count()], [provider_response])
    with pytest.raises(Exception) as caught:
        asyncio.run(OpenAILLMProvider(settings(), client=client).generate(request()))
    assert caught.value.code == expected
    assert len(client.create_endpoint.calls) == 1


def test_missing_key_fails_before_any_provider_call() -> None:
    with pytest.raises(Exception) as caught:
        asyncio.run(OpenAILLMProvider(settings(), client=None).generate(request()))
    assert caught.value.code == LLM_PROVIDER_NOT_CONFIGURED


def transient_error(kind):
    import openai._base_client as base_client
    from openai import APIConnectionError, APITimeoutError, InternalServerError, RateLimitError

    request_obj = base_client.httpx2.Request("POST", "https://api.openai.com/v1/responses")
    if kind == "timeout":
        return APITimeoutError(request=request_obj)
    if kind == "connection":
        return APIConnectionError(request=request_obj)
    if kind == "rate_limit":
        return sdk_status_error(RateLimitError, 429)
    return sdk_status_error(InternalServerError, 503)


@pytest.mark.parametrize("kind", ["timeout", "connection", "rate_limit", "server_error"])
def test_transient_retry_performs_new_preflight_and_does_not_sleep_in_test(kind) -> None:
    failure = transient_error(kind)
    client = FakeClient([count(), count()], [failure, response()])
    sleeps = []
    async def no_sleep(value):
        sleeps.append(value)
    provider = OpenAILLMProvider(settings(), client=client, sleep=no_sleep, uniform=lambda a, b: 0.75)
    result = asyncio.run(provider.generate(request()))
    assert result.attempt_count == 2
    assert len(client.count_endpoint.calls) == 2
    assert len(client.create_endpoint.calls) == 2
    assert sleeps == [0.75]


@pytest.mark.parametrize("kind", ["timeout", "connection", "rate_limit", "server_error"])
def test_second_transient_failure_stops_after_two_logical_attempts(kind) -> None:
    client = FakeClient([count(), count()], [transient_error(kind), transient_error(kind)])
    sleeps = []
    async def no_sleep(value):
        sleeps.append(value)
    provider = OpenAILLMProvider(settings(), client=client, sleep=no_sleep, uniform=lambda a, b: 0.75)
    with pytest.raises(Exception) as caught:
        asyncio.run(provider.generate(request()))
    assert caught.value.code in {
        "LLM_TIMEOUT", "LLM_PROVIDER_UNAVAILABLE", "LLM_RATE_LIMITED"
    }
    assert len(client.count_endpoint.calls) == 2
    assert len(client.create_endpoint.calls) == 2
    assert sleeps == [0.75]


def test_transient_preflight_failure_gets_new_preflight_before_generation() -> None:
    failure = transient_error("timeout")
    client = FakeClient([failure, count()], [response()])
    sleeps = []
    async def no_sleep(value):
        sleeps.append(value)
    provider = OpenAILLMProvider(settings(), client=client, sleep=no_sleep, uniform=lambda a, b: 0.5)
    result = asyncio.run(provider.generate(request()))
    assert result.attempt_count == 2
    assert len(client.count_endpoint.calls) == 2
    assert len(client.create_endpoint.calls) == 1
    assert sleeps == [0.5]


@pytest.mark.parametrize("error_type,status", [("auth", 401), ("permission", 403), ("bad_request", 400)])
def test_permanent_provider_failures_do_not_retry(error_type, status) -> None:
    from openai import AuthenticationError, BadRequestError, PermissionDeniedError
    error_class = {"auth": AuthenticationError, "permission": PermissionDeniedError, "bad_request": BadRequestError}[error_type]
    client = FakeClient([count()], [sdk_status_error(error_class, status)])
    with pytest.raises(Exception):
        asyncio.run(OpenAILLMProvider(settings(), client=client).generate(request()))
    assert len(client.count_endpoint.calls) == 1
    assert len(client.create_endpoint.calls) == 1


def test_structured_context_rejection_at_preflight_is_terminal() -> None:
    from openai import BadRequestError
    client = FakeClient(
        [sdk_status_error(BadRequestError, 400, {"error": {"code": "context_length_exceeded"}})],
        [],
    )
    with pytest.raises(Exception) as caught:
        asyncio.run(OpenAILLMProvider(settings(), client=client).generate(request()))
    assert caught.value.code == LLM_CONTEXT_LIMIT_EXCEEDED
    assert len(client.count_endpoint.calls) == 1
    assert not client.create_endpoint.calls


def test_provider_client_uses_backend_secret_timeout_and_disables_sdk_retries() -> None:
    captured = {}
    import app.ai.llm.openai_provider as module
    class Client:
        max_retries = 0
        timeout = 60
    def build_client(**kwargs):
        captured.update(kwargs)
        return Client()
    previous = module.AsyncOpenAI
    module.AsyncOpenAI = build_client
    try:
        configured = settings(llm_api_key="test-only-openai-secret")
        provider = OpenAILLMProvider(configured)
        provider._get_client()
        provider._get_client()
        assert captured == {
            "api_key": "test-only-openai-secret", "timeout": 60, "max_retries": 0
        }
        assert provider._client.max_retries == 0
    finally:
        module.AsyncOpenAI = previous


def test_structured_logs_omit_prompts_queries_and_generated_text(caplog) -> None:
    client = FakeClient([count()], [response(text="private generated answer")])
    with caplog.at_level(logging.INFO, logger="app.ai.llm.openai_provider"):
        asyncio.run(OpenAILLMProvider(settings(), client=client).generate(request()))
    assert "private generated answer" not in caplog.text
    assert "Explain 你好" not in caplog.text
    assert "Chinese reference" not in caplog.text
    assert "llm_generation_completed" in caplog.text


def test_openai_exception_mapping_matches_frozen_retry_policy() -> None:
    from openai import (
        APIConnectionError, APITimeoutError, AuthenticationError, BadRequestError,
        InternalServerError, PermissionDeniedError, RateLimitError,
    )
    from app.ai.llm.openai_provider import _provider_error
    import openai._base_client as base_client

    request_obj = base_client.httpx2.Request("POST", "https://api.openai.com/v1/responses")
    assert _provider_error(APITimeoutError(request=request_obj)) == ("LLM_TIMEOUT", True)
    assert _provider_error(APIConnectionError(request=request_obj)) == ("LLM_PROVIDER_UNAVAILABLE", True)
    for error_type, status, expected in (
        (RateLimitError, 429, ("LLM_RATE_LIMITED", True)),
        (AuthenticationError, 401, ("LLM_AUTHENTICATION_FAILED", False)),
        (PermissionDeniedError, 403, ("LLM_PERMISSION_DENIED", False)),
        (BadRequestError, 400, ("LLM_REQUEST_INVALID", False)),
        (InternalServerError, 503, ("LLM_PROVIDER_UNAVAILABLE", True)),
    ):
        assert _provider_error(sdk_status_error(error_type, status)) == expected
    ordinary = sdk_status_error(
        BadRequestError, 400,
        {"type": "invalid_request_error", "code": "invalid_parameter"},
    )
    assert _provider_error(ordinary) == ("LLM_REQUEST_INVALID", False)
    for code in (
        "context_length_exceeded",
        "input_tokens_exceeded",
        "max_input_tokens_exceeded",
    ):
        context = sdk_status_error(BadRequestError, 400, {"code": code})
        assert _provider_error(context) == (LLM_CONTEXT_LIMIT_EXCEEDED, False)

    # Keep raw-envelope support only as a defensive compatibility path.
    nested = sdk_status_error(
        BadRequestError, 400, {"error": {"code": "context_length_exceeded"}}
    )
    assert _provider_error(nested) == (LLM_CONTEXT_LIMIT_EXCEEDED, False)
    assert _provider_error(RuntimeError("secret or raw provider details")) == ("LLM_GENERATION_FAILED", False)
