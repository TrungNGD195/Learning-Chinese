from __future__ import annotations

import json
from pathlib import Path

from app.ai.external_retrieval.schemas import ExternalCandidate


ROOT = Path(__file__).resolve().parents[4]
FIXTURE = ROOT / "evaluation/fixtures/lesson_chat_rag/trusted_external/v0.1.0/reviewed-sources.json"


class ReviewedExternalFixtureProvider:
    """Evaluation-only provider; matches normalized query text to reviewed claims."""

    def __init__(self, fixture_path: Path = FIXTURE):
        data = json.loads(fixture_path.read_text(encoding="utf-8"))
        if data.get("status") != "ACCEPTED_FOR_EVALUATION_FIXTURE":
            raise ValueError("EXTERNAL_FIXTURE_NOT_ACCEPTED")
        self._sources = data["sources"]

    def provenance_for_url(self, url: str) -> dict | None:
        """Retain fixture-only identity in trace metadata without changing provider DTOs."""
        import hashlib
        for source in self._sources:
            if source.get("url") == url:
                return {"source_id": source.get("source_id"), "url": source.get("url"),
                        "domain": source.get("domain"), "title": source.get("title"),
                        "reviewed_claims_sha256": hashlib.sha256(
                            "\n".join(source.get("reviewed_claims", [])).encode("utf-8")).hexdigest()}
        return None

    async def search(self, query: str, limit: int) -> tuple[ExternalCandidate, ...]:
        if not isinstance(query, str) or not query.strip() or type(limit) is not int or limit < 1:
            raise ValueError("EXTERNAL_FIXTURE_QUERY_INVALID")
        terms = {part.casefold() for part in query.split() if len(part) > 1}
        ranked = []
        for source in self._sources:
            corpus = " ".join([source["title"], *source.get("reviewed_claims", [])]).casefold()
            overlap = sum(term in corpus for term in terms)
            if overlap:
                ranked.append((overlap, source))
        ranked.sort(key=lambda row: (-row[0], row[1]["source_id"]))
        return tuple(ExternalCandidate(
            title=source["title"], url=source["url"], domain=source["domain"],
            content="\n".join(source.get("reviewed_claims", [])), provider_rank=index,
            provider_score=None,
        ) for index, (_, source) in enumerate(ranked[:limit], start=1))
