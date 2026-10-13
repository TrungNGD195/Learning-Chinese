from dataclasses import dataclass

from app.ai.reranking.schemas import RerankedCandidate


@dataclass(frozen=True)
class InternalContextEvidence:
    final_order: int
    candidate: RerankedCandidate


@dataclass(frozen=True)
class ExternalContextEvidence:
    final_order: int
    title: str
    url: str
    domain: str
    content: str
    rerank_score: float


ContextEvidence = InternalContextEvidence | ExternalContextEvidence
