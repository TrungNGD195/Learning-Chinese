import asyncio
from types import SimpleNamespace
from uuid import uuid4

from app.ai.llm.openai_provider import OpenAILLMProvider
from app.ai.llm.schemas import GenerationConfig
from app.ai.llm.serializer import LLMRequestSerializer
from app.ai.memory.schemas import ConversationMemory, MemoryTurn
from step67_fixtures import prompt_package
from app.core.config import Settings


class Endpoint:
    def __init__(self, values):
        self.values = list(values)
        self.calls = []

    async def call(self, **kwargs):
        self.calls.append(kwargs)
        value = self.values.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


class FakeClient:
    def __init__(self, counts, generations):
        count_endpoint, create_endpoint = Endpoint(counts), Endpoint(generations)
        self.count_endpoint = count_endpoint
        self.create_endpoint = create_endpoint
        self.responses = SimpleNamespace(
            input_tokens=SimpleNamespace(count=count_endpoint.call), create=create_endpoint.call,
        )


def settings():
    return Settings(
        _env_file=None, app_env="test", debug=False,
        test_database_url="postgresql+psycopg://t:t@localhost/chinese_learning_test",
        secret_key="test-only-signing-key-not-a-deployment-secret-0123456789",
    )


def count(tokens=1200):
    return SimpleNamespace(input_tokens=tokens)


def response():
    return SimpleNamespace(
        status="completed", output_text="A clear answer",
        usage=SimpleNamespace(input_tokens=1200, output_tokens=12, total_tokens=1212),
        _request_id="safe-test-request-id",
    )


def transient_error(kind):
    from openai import APITimeoutError, InternalServerError
    import openai._base_client as base_client

    request = base_client.httpx2.Request("POST", "https://api.openai.com/v1/responses")
    if kind == "timeout":
        return APITimeoutError(request=request)
    response_obj = base_client.httpx2.Response(503, request=request)
    return InternalServerError("provider error", response=response_obj, body=None)


def request_with_memory():
    package = prompt_package()
    package = __import__("dataclasses").replace(
        package,
        conversation_memory=ConversationMemory(
            (MemoryTurn("prior question", "prior answer", uuid4(), uuid4(), 1, 2),),
            1, 0, 4, "APPLIED",
        ),
    )
    return LLMRequestSerializer().serialize(package, GenerationConfig())


def test_exact_memory_overflow_drops_all_memory_for_one_final_preflight():
    client = FakeClient([count(400_000), count(1200)], [response()])
    result = asyncio.run(OpenAILLMProvider(settings(), client=client).generate(request_with_memory()))
    assert result.provider_preflight_count == 2
    assert result.memory_dropped_after_exact_preflight is True
    first_input = client.count_endpoint.calls[0]["input"]
    second_input = client.count_endpoint.calls[1]["input"]
    generated_input = client.create_endpoint.calls[0]["input"]
    assert [item["role"] for item in first_input] == ["user", "assistant", "user"]
    assert second_input == generated_input and len(second_input) == 1
    assert client.create_endpoint.calls[0]["input"] is second_input


def test_memory_that_fits_uses_one_identical_role_input_for_preflight_and_generation():
    client = FakeClient([count(1200)], [response()])
    result = asyncio.run(OpenAILLMProvider(settings(), client=client).generate(request_with_memory()))
    assert result.provider_preflight_count == 1
    assert result.memory_dropped_after_exact_preflight is False
    assert client.count_endpoint.calls[0]["input"] == client.create_endpoint.calls[0]["input"]
    assert [item["role"] for item in client.create_endpoint.calls[0]["input"]] == ["user", "assistant", "user"]


def test_zero_memory_final_preflight_overflow_fails_without_generation():
    client = FakeClient([count(400_000), count(400_000)], [])
    try:
        asyncio.run(OpenAILLMProvider(settings(), client=client).generate(request_with_memory()))
    except Exception as exc:
        assert exc.code == "LLM_CONTEXT_LIMIT_EXCEEDED"
    else:
        raise AssertionError("Expected zero-memory context overflow")
    assert len(client.count_endpoint.calls) == 2
    assert not client.create_endpoint.calls
    assert len(client.count_endpoint.calls[0]["input"]) == 3
    assert len(client.count_endpoint.calls[1]["input"]) == 1


def test_exact_preflight_failure_is_not_misclassified_as_memory_overflow():
    client = FakeClient([transient_error("timeout"), count(1200)], [response()])
    result = asyncio.run(OpenAILLMProvider(settings(), client=client).generate(request_with_memory()))
    assert result.provider_preflight_count == 2
    assert result.memory_dropped_after_exact_preflight is False
    assert [len(call["input"]) for call in client.count_endpoint.calls] == [3, 3]


def test_fallback_preflights_are_per_attempt_and_total_can_reach_four():
    client = FakeClient(
        [count(400_000), count(1200), count(400_000), count(1200)],
        [transient_error("server_error"), response()],
    )
    result = asyncio.run(OpenAILLMProvider(settings(), client=client).generate(request_with_memory()))
    assert result.attempt_count == 2
    assert result.provider_preflight_count == 4
    assert result.memory_dropped_after_exact_preflight is True


def test_exact_overflow_without_memory_fails_without_generation_or_retry():
    client = FakeClient([count(400_000)], [])
    try:
        asyncio.run(OpenAILLMProvider(settings(), client=client).generate(
            LLMRequestSerializer().serialize(prompt_package(), GenerationConfig())
        ))
    except Exception as exc:
        assert exc.code == "LLM_CONTEXT_LIMIT_EXCEEDED"
    else:
        raise AssertionError("Expected exact context overflow")
    assert len(client.count_endpoint.calls) == 1 and not client.create_endpoint.calls


def test_transient_retry_reconstructs_memory_for_new_attempt_after_first_fallback():
    client = FakeClient(
        [count(400_000), count(1200), count(1200)],
        [transient_error("server_error"), response()],
    )
    result = asyncio.run(OpenAILLMProvider(settings(), client=client).generate(request_with_memory()))
    assert result.attempt_count == 2
    assert result.provider_preflight_count == 3
    assert result.memory_dropped_after_exact_preflight is True
    assert [len(call["input"]) for call in client.count_endpoint.calls] == [3, 1, 3]
    assert [len(call["input"]) for call in client.create_endpoint.calls] == [1, 3]
    assert client.create_endpoint.calls[1]["input"][-1]["role"] == "user"
