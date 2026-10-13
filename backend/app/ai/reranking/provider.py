from functools import lru_cache
from typing import Protocol

from app.ai.reranking.schemas import RerankerProviderIdentity
from app.ai.reranking.transformers_provider import TransformersRerankerProvider
from app.core.config import get_settings


class RerankerProvider(Protocol):
    @property
    def identity(self) -> RerankerProviderIdentity: ...

    @property
    def device(self) -> str: ...

    def validate_pair_lengths(self, query: str, passages: list[str]) -> None: ...

    def score(self, query: str, passages: list[str]) -> list[float]: ...


@lru_cache(maxsize=1)
def get_reranker_provider() -> RerankerProvider:
    return TransformersRerankerProvider(get_settings())
