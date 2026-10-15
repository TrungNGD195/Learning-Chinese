from __future__ import annotations

import math

from app.ai.embeddings.errors import embedding_error
from app.ai.embeddings.schemas import EmbeddingProviderIdentity
from app.ai.modal_bge import ModalBgeClient, ModalBgeError
from app.ai.modal_bge.schemas import (
    CONTRACT_VERSION, EMBEDDING_MODEL, EMBEDDING_REVISION,
)
from app.core.config import Settings


class ModalEmbeddingProvider:
    def __init__(self, settings: Settings, *, client: ModalBgeClient | None = None):
        self.settings = settings
        self.client = client or ModalBgeClient(settings)
        self.identity = EmbeddingProviderIdentity(
            provider="MODAL", provider_version=CONTRACT_VERSION,
            model_name=EMBEDDING_MODEL, model_version=EMBEDDING_REVISION,
            dimensions=1024, embedding_input_version="v1", normalize_embeddings=True,
        )

    @property
    def device(self) -> str:
        return "modal"

    @staticmethod
    def _error(code: str, message: str, status: int = 500):
        return embedding_error(code, message, status)

    def _vectors(self, result, *, operation: str, count: int) -> list[list[float]]:
        if not isinstance(result, dict) or result.get("ok") is not True:
            code = result.get("error_code") if isinstance(result, dict) else None
            if code == "EMBEDDING_INPUT_TOO_LONG":
                raise self._error(code, "Embedding input exceeds the model token limit.", 422)
            raise self._error("INVALID_EMBEDDING_OUTPUT", "Embedding provider returned invalid output.")
        if (result.get("contract_version"), result.get("operation"), result.get("model_name"), result.get("model_revision")) != (
            CONTRACT_VERSION, operation, EMBEDDING_MODEL, EMBEDDING_REVISION
        ):
            raise self._error("INVALID_EMBEDDING_OUTPUT", "Embedding provider returned invalid output.")
        if not isinstance(result.get("runtime_versions"), dict) or not isinstance(result.get("device"), str):
            raise self._error("INVALID_EMBEDDING_OUTPUT", "Embedding provider returned invalid output.")
        raw = result.get("vector") if operation == "embed_query" else result.get("vectors")
        if operation == "embed_query":
            raw = [raw] if isinstance(raw, list) else None
        if not isinstance(raw, list) or len(raw) != count:
            raise self._error("INVALID_EMBEDDING_OUTPUT", "Embedding provider returned an invalid vector count.")
        vectors: list[list[float]] = []
        for vector in raw:
            if not isinstance(vector, list) or len(vector) != 1024:
                raise self._error("INVALID_EMBEDDING_OUTPUT", "Embedding provider returned an invalid vector.")
            try:
                converted = [float(value) for value in vector]
            except (TypeError, ValueError, OverflowError):
                raise self._error("INVALID_EMBEDDING_OUTPUT", "Embedding provider returned an invalid vector.") from None
            norm = math.sqrt(sum(value * value for value in converted))
            if not all(math.isfinite(value) for value in converted) or abs(norm - 1.0) > 1e-3:
                raise self._error("INVALID_EMBEDDING_OUTPUT", "Embedding provider returned an invalid vector.")
            vectors.append(converted)
        return vectors

    async def embed_documents(self, texts: list[str], *, batch_size: int) -> list[list[float]]:
        if not texts or any(not isinstance(text, str) or not text.strip() for text in texts) or batch_size <= 0:
            raise self._error("INVALID_EMBEDDING_OUTPUT", "Embedding input is invalid.", 422)
        try:
            result = await self.client.invoke("embed_documents", texts, batch_size=batch_size)
        except ModalBgeError:
            raise self._error("EMBEDDING_PROVIDER_FAILED", "Embedding provider is unavailable.") from None
        return self._vectors(result, operation="embed_documents", count=len(texts))

    async def embed_query(self, text: str) -> list[float]:
        if not isinstance(text, str) or not text.strip():
            raise self._error("INVALID_EMBEDDING_OUTPUT", "Embedding input is invalid.", 422)
        try:
            result = await self.client.invoke("embed_query", text)
        except ModalBgeError:
            raise self._error("EMBEDDING_PROVIDER_FAILED", "Embedding provider is unavailable.") from None
        return self._vectors(result, operation="embed_query", count=1)[0]
