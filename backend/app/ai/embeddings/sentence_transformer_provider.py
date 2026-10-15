from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import Any

from app.ai.embeddings.errors import embedding_error
from app.ai.embeddings.schemas import EmbeddingProviderIdentity
from app.core.config import Settings


class SentenceTransformerEmbeddingProvider:
    def __init__(self, settings: Settings, *, model_factory=None):
        self.settings = settings
        self._model_factory = model_factory
        self._model = None
        try:
            package_version = version("sentence-transformers")
        except PackageNotFoundError as exc:
            raise embedding_error("EMBEDDING_PROVIDER_FAILED", "Embedding provider is unavailable.", 500) from exc
        if package_version != "6.1.0":
            raise embedding_error("EMBEDDING_PROFILE_INVALID", "Installed embedding provider version does not match the configured profile.", 409)
        self.identity = EmbeddingProviderIdentity(
            provider="LOCAL", provider_version="sentence-transformers/6.1.0",
            model_name=settings.embedding_model_name, model_version=settings.embedding_model_revision,
            dimensions=1024, embedding_input_version=settings.embedding_input_version,
            normalize_embeddings=settings.embedding_normalize,
        )

    @property
    def device(self) -> str:
        if self._model is not None:
            return str(getattr(self._model, "device", self.settings.embedding_device))
        return self.settings.embedding_device

    def _load_model(self):
        if self._model is None:
            factory = self._model_factory
            if factory is None:
                try:
                    from sentence_transformers import SentenceTransformer
                except Exception as exc:
                    raise embedding_error("EMBEDDING_PROVIDER_FAILED", "Embedding provider could not be loaded.", 500) from exc
                factory = SentenceTransformer
            # Pin the SentenceTransformer snapshot itself. Passing this only via
            # model_kwargs does not select the Hub revision for every loader path.
            kwargs: dict[str, Any] = {"revision": self.settings.embedding_model_revision}
            if self.settings.embedding_device != "auto":
                kwargs["device"] = self.settings.embedding_device
            else:
                kwargs["device"] = None
            try:
                self._model = factory(self.settings.embedding_model_name, **kwargs)
            except Exception as exc:
                raise embedding_error("EMBEDDING_PROVIDER_FAILED", "Embedding provider could not be loaded.", 500) from exc
        return self._model

    def _validate_lengths(self, texts: list[str]) -> None:
        model = self._load_model()
        try:
            tokenized = model.tokenizer(texts, add_special_tokens=True, truncation=False)
            max_length = int(model.max_seq_length)
            input_ids = tokenized["input_ids"]
            if any(len(ids) > max_length for ids in input_ids):
                raise embedding_error("EMBEDDING_INPUT_TOO_LONG", "Embedding input exceeds the model token limit.", 422)
        except Exception as exc:
            if getattr(exc, "code", None) == "EMBEDDING_INPUT_TOO_LONG":
                raise
            raise embedding_error("EMBEDDING_PROVIDER_FAILED", "Embedding input could not be tokenized.", 500) from exc

    async def embed_documents(self, texts: list[str], *, batch_size: int) -> list[list[float]]:
        model = self._load_model()
        self._validate_lengths(texts)
        try:
            vectors = model.encode(texts, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=False)
            return [[float(value) for value in vector] for vector in vectors]
        except Exception as exc:
            if getattr(exc, "code", None) == "EMBEDDING_INPUT_TOO_LONG":
                raise
            raise embedding_error("EMBEDDING_PROVIDER_FAILED", "Embedding model inference failed.", 500) from exc

    async def embed_query(self, text: str) -> list[float]:
        vectors = await self.embed_documents([text], batch_size=1)
        return vectors[0]
