import asyncio
import math

import pytest

from app.ai.modal_bge.schemas import CONTRACT_VERSION, RERANKER_MODEL, RERANKER_REVISION
from app.ai.modal_bge.client import ModalBgeError
from app.ai.reranking.modal_provider import ModalRerankerProvider
from app.core.config import Settings
from app.core.errors import ApplicationError


def settings():
    return Settings(
        _env_file=None, app_env="test", debug=False,
        test_database_url="postgresql+psycopg://test:test@localhost/chinese_learning_test",
        secret_key="test-only-secret", reranker_provider="modal",
        modal_token_id="test-id", modal_token_secret="test-secret", modal_environment="test",
        modal_bge_app_name="bge-app", modal_bge_class_name="BgeInference",
    )


def envelope(operation, **kwargs):
    return {"ok": True, "contract_version": CONTRACT_VERSION, "operation": operation,
            "model_name": RERANKER_MODEL, "model_revision": RERANKER_REVISION,
            "runtime_versions": {"torch": "2.14.1"}, "device": "cuda", **kwargs}


class FakeClient:
    def __init__(self, responses): self.responses, self.calls = list(responses), []
    async def invoke(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        result = self.responses.pop(0)
        if isinstance(result, Exception): raise result
        return result


def test_honest_modal_identity_pair_validation_and_raw_scores():
    client = FakeClient([envelope("validate_rerank_inputs"), envelope("score_rerank", scores=[-0.8, 0.3])])
    provider = ModalRerankerProvider(settings(), client=client)
    assert provider.identity.provider == "MODAL"
    assert provider.identity.provider_version == "modal-bge-runtime/v1"
    assert provider.identity.model_name == RERANKER_MODEL
    assert provider.identity.model_revision == RERANKER_REVISION
    assert provider.device == "modal"
    asyncio.run(provider.validate_pair_lengths("q", ["a", "b"]))
    assert asyncio.run(provider.score("q", ["a", "b"])) == [-0.8, 0.3]
    assert client.calls == [(("validate_rerank_inputs", "q", ["a", "b"]), {}), (("score_rerank", "q", ["a", "b"]), {})]


@pytest.mark.parametrize("result", [
    {"ok": True, "contract_version": "wrong"},
    envelope("wrong", scores=[0.1]),
    {**envelope("score_rerank", scores=[0.1]), "model_revision": "wrong"},
    envelope("score_rerank", scores=[0.1, 0.2]),
    envelope("score_rerank", scores=[float("inf")]),
])
def test_invalid_remote_rerank_contracts_fail(result):
    provider = ModalRerankerProvider(settings(), client=FakeClient([result]))
    with pytest.raises(ApplicationError) as caught:
        asyncio.run(provider.score("q", ["p"]))
    assert caught.value.code == "INVALID_RERANKER_OUTPUT"


def test_pair_and_batch_bounds_and_safe_technical_mapping():
    client = FakeClient([envelope("score_rerank", scores=[0.1])])
    provider = ModalRerankerProvider(settings(), client=client)
    with pytest.raises(ApplicationError): asyncio.run(provider.validate_pair_lengths("q", ["p"] * 21))
    with pytest.raises(ApplicationError): asyncio.run(provider.score("q", ["p"] * 9))
    assert client.calls == []
    client.responses = [ModalBgeError("MODAL_INVOCATION_FAILED")]
    with pytest.raises(ApplicationError) as caught: asyncio.run(provider.score("private", ["passage"]))
    assert caught.value.code == "RERANKER_INFERENCE_FAILED"
    assert len(client.calls) == 1


def test_service_identity_policy_accepts_modal_only_when_selected():
    from app.ai.reranking.service import RerankingService
    provider = ModalRerankerProvider(settings(), client=FakeClient([]))
    assert RerankingService(provider=provider, settings=settings())._provider() is provider
    local_settings = Settings(
        _env_file=None, app_env="test", debug=False,
        test_database_url="postgresql+psycopg://test:test@localhost/chinese_learning_test",
        secret_key="test-only-secret",
    )
    with pytest.raises(ApplicationError) as caught:
        RerankingService(provider=provider, settings=local_settings)._provider()
    assert caught.value.code == "RERANKER_NOT_AVAILABLE"


def test_configured_reranker_factory_selects_modal_adapter_without_remote_call(monkeypatch):
    from app.ai.reranking import provider as module
    sentinel = object()
    monkeypatch.setattr(module, "get_settings", settings)
    monkeypatch.setattr("app.ai.reranking.modal_provider.ModalRerankerProvider", lambda _settings: sentinel)
    module.get_reranker_provider.cache_clear()
    try:
        assert module.get_reranker_provider() is sentinel
    finally:
        module.get_reranker_provider.cache_clear()
