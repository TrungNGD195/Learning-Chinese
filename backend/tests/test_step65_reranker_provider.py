import asyncio
from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from app.ai.reranking.transformers_provider import TransformersRerankerProvider
from app.core.config import Settings


def settings(**kwargs):
    return Settings(
        _env_file=None,
        app_env="test",
        debug=False,
        test_database_url="postgresql+psycopg://test:test@localhost/chinese_learning_test",
        secret_key="test-only-key",
        **kwargs,
    )


class FakeTensor:
    def __init__(self, values):
        self.values = values

    def to(self, _device):
        return self

    def reshape(self, *_shape):
        return self

    def numel(self):
        return len(self.values)

    def detach(self):
        return self

    def cpu(self):
        return self

    def tolist(self):
        return self.values


class FakeTokenizer:
    model_max_length = 4

    def __init__(self):
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if len(args) == 2 and isinstance(args[0], str):
            return {"input_ids": list(range(len(args[0].split()) + len(args[1].split())))}
        passages = args[1]
        return {"input_ids": FakeTensor([0] * len(passages)), "attention_mask": FakeTensor([1] * len(passages))}


class FakeModel:
    config = SimpleNamespace(max_position_embeddings=4)
    device = "cpu"

    def __init__(self):
        self.to_calls = []
        self.eval_calls = 0
        self.inference_batches = []

    def to(self, device):
        self.device = device
        self.to_calls.append(device)
        return self

    def eval(self):
        self.eval_calls += 1

    def __call__(self, **values):
        count = values["input_ids"].numel()
        self.inference_batches.append(count)
        return SimpleNamespace(logits=FakeTensor([-0.75] * count))


class FakeTorch:
    class cuda:
        @staticmethod
        def is_available():
            return False

    class backends:
        class mps:
            @staticmethod
            def is_available():
                return False

    @staticmethod
    def inference_mode():
        return nullcontext()


class Loader:
    def __init__(self, value):
        self.value = value
        self.calls = []

    def from_pretrained(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.value


def provider(monkeypatch, *, max_length=4):
    tokenizer = FakeTokenizer()
    tokenizer.model_max_length = max_length
    model = FakeModel()
    model.config.max_position_embeddings = max_length
    tokenizer_loader = Loader(tokenizer)
    model_loader = Loader(model)
    monkeypatch.setattr("app.ai.reranking.transformers_provider.version", lambda name: {
        "transformers": "5.18.0", "torch": "2.14.1"
    }[name])
    instance = TransformersRerankerProvider(
        settings(),
        loader=(tokenizer_loader, model_loader),
        torch_module=FakeTorch(),
    )
    return instance, tokenizer, model, tokenizer_loader, model_loader


def test_pinned_model_identity_passed_to_both_loaders_and_loaded_once(monkeypatch):
    instance, _tokenizer, model, tokenizer_loader, model_loader = provider(monkeypatch)

    asyncio.run(instance.validate_pair_lengths("one", ["two"]))
    asyncio.run(instance.score("one", ["two"]))
    asyncio.run(instance.validate_pair_lengths("one", ["three"]))

    revision = "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"
    assert tokenizer_loader.calls == [(("BAAI/bge-reranker-v2-m3",), {"revision": revision})]
    assert model_loader.calls == [(("BAAI/bge-reranker-v2-m3",), {"revision": revision})]
    assert instance.identity.provider == "LOCAL"
    assert instance.identity.model_name == "BAAI/bge-reranker-v2-m3"
    assert instance.identity.model_revision == revision
    assert instance.identity.provider_version == "transformers/5.18.0;torch/2.14.1"
    assert instance.identity.reranker_input_version == "v1"
    assert model.to_calls == ["cpu"]
    assert model.eval_calls == 1


def test_pair_length_validation_disables_truncation_and_accepts_exact_limit(monkeypatch):
    instance, tokenizer, _model, *_ = provider(monkeypatch, max_length=4)

    asyncio.run(instance.validate_pair_lengths("one two", ["three four"]))

    assert tokenizer.calls[0][1]["truncation"] is False


def test_overlong_pair_fails_without_truncation(monkeypatch):
    instance, tokenizer, _model, *_ = provider(monkeypatch, max_length=3)

    with pytest.raises(Exception) as caught:
        asyncio.run(instance.validate_pair_lengths("one two", ["three four"]))

    assert getattr(caught.value, "code", None) == "RERANK_INPUT_TOO_LONG"
    assert tokenizer.calls[0][1]["truncation"] is False


def test_provider_returns_raw_negative_logits_without_assuming_fp16(monkeypatch):
    instance, tokenizer, _model, *_ = provider(monkeypatch)

    assert asyncio.run(instance.score("query", ["passage"])) == [-0.75]
    kwargs = tokenizer.calls[-1][1]
    assert kwargs["truncation"] is False
    assert "torch_dtype" not in kwargs


def test_explicit_reranker_device_is_independent_from_embedding_device(monkeypatch):
    tokenizer = FakeTokenizer()
    model = FakeModel()
    tokenizer_loader, model_loader = Loader(tokenizer), Loader(model)
    monkeypatch.setattr("app.ai.reranking.transformers_provider.version", lambda name: {
        "transformers": "5.18.0", "torch": "2.14.1"
    }[name])
    instance = TransformersRerankerProvider(
        settings(reranker_device="cpu", embedding_device="auto"),
        loader=(tokenizer_loader, model_loader),
        torch_module=FakeTorch(),
    )

    asyncio.run(instance.validate_pair_lengths("q", ["p"]))

    assert instance.device == "cpu"
    assert model.to_calls == ["cpu"]


def test_model_initialization_failure_is_normalized(monkeypatch):
    class BrokenLoader:
        @staticmethod
        def from_pretrained(*_args, **_kwargs):
            raise RuntimeError("model download detail")

    monkeypatch.setattr("app.ai.reranking.transformers_provider.version", lambda _name: "5.18.0")
    instance = TransformersRerankerProvider(
        settings(), loader=(BrokenLoader, Loader(FakeModel())), torch_module=FakeTorch()
    )

    with pytest.raises(Exception) as caught:
        asyncio.run(instance.validate_pair_lengths("query", ["passage"]))

    assert getattr(caught.value, "code", None) == "RERANKER_NOT_AVAILABLE"
    assert "model download detail" not in str(caught.value)


def test_model_inference_failure_is_normalized(monkeypatch):
    class BrokenModel(FakeModel):
        def __call__(self, **_values):
            raise RuntimeError("private model input")

    instance, *_ = provider(monkeypatch)
    instance._model = BrokenModel()
    instance._tokenizer = FakeTokenizer()

    with pytest.raises(Exception) as caught:
        asyncio.run(instance.score("query", ["passage"]))

    assert getattr(caught.value, "code", None) == "RERANKER_INFERENCE_FAILED"
    assert "private model input" not in str(caught.value)


@pytest.mark.parametrize("field,value", [("reranker_batch_size", 1), ("reranker_batch_size", 8), ("reranker_batch_size", 20), ("reranker_top_k", 1), ("reranker_top_k", 5)])
def test_frozen_config_bounds_accept_boundary_and_default_values(field, value):
    settings_obj = settings(**{field: value})
    assert getattr(settings_obj, field) == value


def test_reranker_configuration_defaults_and_immutable_identity():
    settings_obj = settings()

    assert settings_obj.reranker_provider == "local"
    assert settings_obj.reranker_model_name == "BAAI/bge-reranker-v2-m3"
    assert settings_obj.reranker_model_revision == "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"
    assert settings_obj.reranker_device == "auto"
    assert settings_obj.reranker_batch_size == 8
    assert settings_obj.reranker_top_k == 5
    assert settings_obj.reranker_input_version == "v1"


@pytest.mark.parametrize("field,value", [("reranker_batch_size", 0), ("reranker_batch_size", -1), ("reranker_batch_size", 21), ("reranker_top_k", 0), ("reranker_top_k", -1), ("reranker_top_k", 6)])
def test_frozen_config_bounds_reject_out_of_range_values(field, value):
    with pytest.raises(ValueError):
        settings(**{field: value})
