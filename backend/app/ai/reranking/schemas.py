from dataclasses import dataclass

from app.ai.retrieval.schemas import RetrievalCandidate


@dataclass(frozen=True)
class RerankerProviderIdentity:
    provider: str
    provider_version: str
    model_name: str
    model_revision: str
    reranker_input_version: str


@dataclass(frozen=True)
class RerankedCandidate(RetrievalCandidate):
    """A semantic candidate with separate, runtime-only rerank fields."""

    rerank_score: float
    rerank_rank: int


@dataclass(frozen=True)
class RerankResult:
    """Both runtime views of one full, scored reranker ordering."""

    scored_candidates: tuple[RerankedCandidate, ...]
    top_candidates: tuple[RerankedCandidate, ...]
