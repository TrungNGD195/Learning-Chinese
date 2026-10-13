from app.ai.embeddings.sentence_transformer_provider import SentenceTransformerEmbeddingProvider
from app.core.config import Settings
from app.core.errors import ApplicationError
import pytest


class _Tokenizer:
    def __init__(self): self.kwargs = None
    def __call__(self, texts, **kwargs):
        self.kwargs = kwargs
        return {"input_ids": [[1, 2] for _ in texts]}


class _Model:
    def __init__(self): self.tokenizer = _Tokenizer(); self.max_seq_length = 8; self.calls = []
    def encode(self, texts, **kwargs):
        self.calls.append((texts, kwargs))
        return [[1.0] + [0.0] * 1023 for _ in texts]


def _settings(**values):
    return Settings(_env_file=None, app_env="test", debug=False,
                    test_database_url="postgresql+psycopg://test:test@localhost/test_db",
                    secret_key="test-only-signing-key-not-a-deployment-secret-0123456789", **values)


def test_provider_lazy_model_auto_device_normalization_and_query(monkeypatch):
    from app.ai.embeddings import sentence_transformer_provider as module
    monkeypatch.setattr(module, "version", lambda _: "6.1.0")
    model = _Model(); received = {"factory_calls": 0}
    def factory(name, **kwargs):
        received.update(name=name, kwargs=kwargs)
        received["factory_calls"] += 1
        return model
    provider = SentenceTransformerEmbeddingProvider(_settings(), model_factory=factory)
    assert provider._model is None
    vectors = provider.embed_documents(["one", "two"], batch_size=2)
    assert len(vectors) == 2 and len(vectors[0]) == 1024
    assert received["name"] == "BAAI/bge-m3"
    assert received["kwargs"]["device"] is None
    assert received["kwargs"]["revision"] == "5617a9f61b028005a4858fdac845db406aefb181"
    assert "model_kwargs" not in received["kwargs"]
    assert model.tokenizer.kwargs == {"add_special_tokens": True, "truncation": False}
    assert model.calls[0][1]["normalize_embeddings"] is True
    assert provider.embed_query("query")[0] == 1.0
    assert len(model.calls) == 2
    assert received["factory_calls"] == 1


def test_provider_rejects_overlength_without_calling_encode(monkeypatch):
    from app.ai.embeddings import sentence_transformer_provider as module
    monkeypatch.setattr(module, "version", lambda _: "6.1.0")
    model = _Model(); model.tokenizer = lambda texts, **kwargs: {"input_ids": [[0] * 9]}
    provider = SentenceTransformerEmbeddingProvider(_settings(), model_factory=lambda *_a, **_k: model)
    try:
        provider.embed_documents(["too long"], batch_size=1)
        assert False, "expected input length error"
    except ApplicationError as exc:
        assert exc.code == "EMBEDDING_INPUT_TOO_LONG"
    assert model.calls == []


def test_provider_accepts_exact_max_length_and_rejects_max_plus_one(monkeypatch):
    from app.ai.embeddings import sentence_transformer_provider as module
    monkeypatch.setattr(module, "version", lambda _: "6.1.0")

    accepted_model = _Model()
    accepted_model.max_seq_length = 8
    accepted_model.tokenizer = lambda texts, **kwargs: {"input_ids": [[0] * 8 for _ in texts]}
    accepted = SentenceTransformerEmbeddingProvider(_settings(), model_factory=lambda *_a, **_k: accepted_model)
    assert len(accepted.embed_documents(["exact max"], batch_size=1)) == 1
    assert len(accepted_model.calls) == 1

    rejected_model = _Model()
    rejected_model.max_seq_length = 8
    rejected_model.tokenizer = lambda texts, **kwargs: {"input_ids": [[0] * 9 for _ in texts]}
    rejected = SentenceTransformerEmbeddingProvider(_settings(), model_factory=lambda *_a, **_k: rejected_model)
    with pytest.raises(ApplicationError) as error:
        rejected.embed_documents(["max plus one"], batch_size=1)
    assert error.value.code == "EMBEDDING_INPUT_TOO_LONG"
    assert rejected_model.calls == []


def test_provider_maps_tokenizer_exception_without_leaking_details(monkeypatch):
    from app.ai.embeddings import sentence_transformer_provider as module
    monkeypatch.setattr(module, "version", lambda _: "6.1.0")
    model = _Model()

    def broken_tokenizer(*_args, **_kwargs):
        raise RuntimeError("private tokenizer internals")

    model.tokenizer = broken_tokenizer
    provider = SentenceTransformerEmbeddingProvider(_settings(), model_factory=lambda *_a, **_k: model)
    with pytest.raises(ApplicationError) as error:
        provider.embed_documents(["text"], batch_size=1)
    assert error.value.code == "EMBEDDING_PROVIDER_FAILED"
    assert error.value.message == "Embedding input could not be tokenized."
    assert error.value.details is None
    assert "private tokenizer internals" not in error.value.message
    assert model.calls == []


def test_provider_maps_inference_exception_without_returning_vector_or_details(monkeypatch):
    from app.ai.embeddings import sentence_transformer_provider as module
    monkeypatch.setattr(module, "version", lambda _: "6.1.0")
    model = _Model()

    def broken_encode(texts, **kwargs):
        model.calls.append((texts, kwargs))
        raise RuntimeError("private accelerator failure")

    model.encode = broken_encode
    provider = SentenceTransformerEmbeddingProvider(_settings(), model_factory=lambda *_a, **_k: model)
    with pytest.raises(ApplicationError) as error:
        provider.embed_documents(["text"], batch_size=1)
    assert error.value.code == "EMBEDDING_PROVIDER_FAILED"
    assert error.value.message == "Embedding model inference failed."
    assert error.value.details is None
    assert "private accelerator failure" not in error.value.message
    assert len(model.calls) == 1


def test_provider_rejects_unexpected_installed_version(monkeypatch):
    from app.ai.embeddings import sentence_transformer_provider as module
    from app.core.errors import ApplicationError
    monkeypatch.setattr(module, "version", lambda _: "6.2.0")
    try:
        SentenceTransformerEmbeddingProvider(_settings())
        assert False, "expected provider version error"
    except ApplicationError as exc:
        assert exc.code == "EMBEDDING_PROFILE_INVALID"



@pytest.mark.parametrize("device", ["cpu", "cuda", "mps"])
def test_provider_passes_explicit_device_without_fallback(monkeypatch, device):
    from app.ai.embeddings import sentence_transformer_provider as module
    monkeypatch.setattr(module, "version", lambda _: "6.1.0")
    model = _Model(); received = {}
    provider = SentenceTransformerEmbeddingProvider(
        _settings(embedding_device=device),
        model_factory=lambda name, **kwargs: (received.update(name=name, kwargs=kwargs) or model),
    )
    provider.embed_query("query")
    assert received["kwargs"]["device"] == device


def test_cached_provider_factory_reuses_provider_and_can_reset(monkeypatch):
    from app.ai.embeddings import provider as module

    created = []
    class _SentinelProvider:
        def __init__(self, settings):
            self.settings = settings
            created.append(self)

    monkeypatch.setattr(module, "SentenceTransformerEmbeddingProvider", _SentinelProvider)
    monkeypatch.setattr(module, "get_settings", lambda: object())
    module.get_embedding_provider.cache_clear()
    try:
        first = module.get_embedding_provider()
        assert module.get_embedding_provider() is first
        assert len(created) == 1
        module.get_embedding_provider.cache_clear()
        second = module.get_embedding_provider()
        assert second is not first
        assert len(created) == 2
    finally:
        module.get_embedding_provider.cache_clear()
