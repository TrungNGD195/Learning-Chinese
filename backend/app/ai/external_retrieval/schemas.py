from dataclasses import dataclass


@dataclass(frozen=True)
class ExternalCandidate:
    title: str
    url: str
    domain: str
    content: str
    provider_rank: int
    provider_score: float | None = None

    def __post_init__(self) -> None:
        if not all(isinstance(v, str) and v.strip() for v in (self.title, self.url, self.domain, self.content)):
            raise ValueError("External candidate fields must be nonblank")
        if type(self.provider_rank) is not int or self.provider_rank < 1:
            raise ValueError("External provider rank must be positive")


@dataclass(frozen=True, kw_only=True)
class RerankedExternalCandidate(ExternalCandidate):
    rerank_score: float
    rerank_rank: int


@dataclass(frozen=True)
class ExternalRerankResult:
    scored_candidates: tuple[RerankedExternalCandidate, ...]
    eligible_top_candidates: tuple[RerankedExternalCandidate, ...]
