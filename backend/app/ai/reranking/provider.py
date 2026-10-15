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

    async def validate_pair_lengths(self, query: str, passages: list[str]) -> None: ...

    async def score(self, query: str, passages: list[str]) -> list[float]: ...


@lru_cache(maxsize=1)
def get_reranker_provider() -> RerankerProvider:
    settings = get_settings()
    if settings.reranker_provider == "modal":
        from app.ai.reranking.modal_provider import ModalRerankerProvider

        return ModalRerankerProvider(settings)
    return TransformersRerankerProvider(settings)
