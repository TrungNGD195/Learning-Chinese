from typing import Protocol

from app.ai.external_retrieval.schemas import ExternalCandidate


class ExternalRetrievalProvider(Protocol):
    async def search(self, query: str, limit: int) -> tuple[ExternalCandidate, ...]: ...
