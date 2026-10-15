import asyncio
import math

import pytest
from uuid import uuid4

from app.ai.embeddings.modal_provider import ModalEmbeddingProvider
from app.ai.modal_bge.client import ModalBgeError
from app.ai.modal_bge.schemas import CONTRACT_VERSION, EMBEDDING_MODEL, EMBEDDING_REVISION
from app.core.config import Settings
from app.core.errors import ApplicationError


def settings():
    return Settings(
        _env_file=None, app_env="test", debug=False,
        test_database_url="postgresql+psycopg://test:test@localhost/chinese_learning_test",
        secret_key="test-only-secret", embedding_provider="modal",
        modal_token_id="test-id", modal_token_secret="test-secret", modal_environment="test",
        modal_bge_app_name="bge-app", modal_bge_class_name="BgeInference",
    )


def envelope(operation, **kwargs):
    return {
        "ok": True, "contract_version": CONTRACT_VERSION, "operation": operation,
        "model_name": EMBEDDING_MODEL, "model_revision": EMBEDDING_REVISION,
        "runtime_versions": {"torch": "2.14.1"}, "device": "cuda", **kwargs,
    }


class FakeClient:
    def __init__(self, result=None, error=None): self.result, self.error, self.calls = result, error, []
    async def invoke(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if self.error: raise self.error
        return self.result


def vector(): return [1.0] + [0.0] * 1023


def test_modal_identity_and_valid_query_documents_contract():
    client = FakeClient(envelope("embed_query", vector=vector()))
    provider = ModalEmbeddingProvider(settings(), client=client)
    result = asyncio.run(provider.embed_query("你好"))
    assert result == vector()
    assert provider.identity.provider == "MODAL"
    assert provider.identity.provider_version == "modal-bge-runtime/v1"
    assert provider.identity.model_name == EMBEDDING_MODEL
    assert provider.identity.model_version == EMBEDDING_REVISION
    assert provider.identity.dimensions == 1024 and provider.identity.normalize_embeddings is True
    assert provider.device == "modal"
    client.result = envelope("embed_documents", vectors=[vector(), vector()])
    assert asyncio.run(provider.embed_documents(["a", "b"], batch_size=8)) == [vector(), vector()]
    assert client.calls[-1] == (("embed_documents", ["a", "b"]), {"batch_size": 8})


def test_existing_active_profile_identity_guard_accepts_only_matching_modal_identity():
    from app.ai.retrieval.schemas import ActiveEmbeddingProfileSnapshot
    from app.ai.retrieval.service import SemanticRetrievalService

    provider = ModalEmbeddingProvider(settings(), client=FakeClient())
    identity = provider.identity
    active = ActiveEmbeddingProfileSnapshot(
        id=uuid4(), provider=identity.provider, provider_version=identity.provider_version,
        model_name=identity.model_name, model_version=identity.model_version,
        dimensions=identity.dimensions, embedding_input_version=identity.embedding_input_version,
        normalize_embeddings=identity.normalize_embeddings,
    )
    assert SemanticRetrievalService._same_identity(identity, active)
    local_active = ActiveEmbeddingProfileSnapshot(
        id=active.id, provider="LOCAL", provider_version="sentence-transformers/6.1.0",
        model_name=identity.model_name, model_version=identity.model_version,
        dimensions=identity.dimensions, embedding_input_version=identity.embedding_input_version,
        normalize_embeddings=True,
    )
    assert not SemanticRetrievalService._same_identity(identity, local_active)
    incompatible = ActiveEmbeddingProfileSnapshot(
        id=active.id, provider=identity.provider, provider_version="modal-bge-runtime/v0",
        model_name=identity.model_name, model_version=identity.model_version,
        dimensions=identity.dimensions, embedding_input_version=identity.embedding_input_version,
        normalize_embeddings=True,
    )
    assert not SemanticRetrievalService._same_identity(identity, incompatible)


def test_configured_factory_selects_modal_adapter_without_invoking_it(monkeypatch):
    from app.ai.embeddings import provider as module

    sentinel = object()
    monkeypatch.setattr(module, "get_settings", settings)
    monkeypatch.setattr("app.ai.embeddings.modal_provider.ModalEmbeddingProvider", lambda _settings: sentinel)
    module.get_embedding_provider.cache_clear()
    try:
        assert module.get_embedding_provider() is sentinel
    finally:
        module.get_embedding_provider.cache_clear()


@pytest.mark.parametrize("result", [
    {"ok": True, "contract_version": "wrong"},
    envelope("wrong", vector=vector()),
    {**envelope("embed_query", vector=vector()), "model_revision": "wrong"},
    envelope("embed_query", vector=[1.0]),
    envelope("embed_query", vector=[float("nan")] + [0.0] * 1023),
    envelope("embed_query", vector=[0.5] + [0.0] * 1023),
    envelope("embed_documents", vectors=[vector()]),
])
def test_invalid_remote_contracts_rejected(result):
    provider = ModalEmbeddingProvider(settings(), client=FakeClient(result))
    with pytest.raises(ApplicationError) as caught:
        asyncio.run(provider.embed_query("q"))
    assert caught.value.code == "INVALID_EMBEDDING_OUTPUT"


def test_deterministic_too_long_and_technical_failure_mapping_without_retry():
    client = FakeClient({"ok": False, "error_code": "EMBEDDING_INPUT_TOO_LONG", "safe_message": "safe"})
    with pytest.raises(ApplicationError) as caught:
        asyncio.run(ModalEmbeddingProvider(settings(), client=client).embed_query("long"))
    assert caught.value.code == "EMBEDDING_INPUT_TOO_LONG"
    client.error = ModalBgeError("MODAL_INVOCATION_FAILED")
    with pytest.raises(ApplicationError) as caught:
        asyncio.run(ModalEmbeddingProvider(settings(), client=client).embed_query("private"))
    assert caught.value.code == "EMBEDDING_PROVIDER_FAILED"
    assert len(client.calls) == 2
