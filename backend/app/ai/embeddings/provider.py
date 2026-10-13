from functools import lru_cache
from typing import Protocol

from app.ai.embeddings.schemas import EmbeddingProviderIdentity
from app.ai.embeddings.sentence_transformer_provider import SentenceTransformerEmbeddingProvider
from app.core.config import get_settings


class EmbeddingProvider(Protocol):
    @property
    def identity(self) -> EmbeddingProviderIdentity: ...
    @property
    def device(self) -> str: ...
    def embed_documents(self, texts: list[str], *, batch_size: int) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...


@lru_cache(maxsize=1)
def get_embedding_provider() -> EmbeddingProvider:
    return SentenceTransformerEmbeddingProvider(get_settings())
