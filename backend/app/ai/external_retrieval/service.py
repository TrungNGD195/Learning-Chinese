from __future__ import annotations

import logging
from time import perf_counter
from urllib.parse import urlsplit

from app.ai.external_retrieval.provider import ExternalRetrievalProvider
from app.ai.external_retrieval.schemas import ExternalCandidate
from app.core.config import Settings

logger = logging.getLogger("app.ai.external_retrieval")


class ExternalRetrievalService:
    def __init__(self, provider: ExternalRetrievalProvider, settings: Settings) -> None:
        self.provider = provider
        self.settings = settings

    async def search(self, normalized_query: str) -> tuple[ExternalCandidate, ...]:
        started = perf_counter()
        rows = await self.provider.search(normalized_query, self.settings.external_retrieval_k)
        trusted = []
        allowed = frozenset(self.settings.external_retrieval_allowed_domains)
        for row in rows:
            try:
                parsed = urlsplit(row.url)
                host = parsed.hostname
                hostname = host.lower().removesuffix(".") if host else ""
                safe = parsed.scheme.lower() == "https" and host and parsed.username is None and parsed.password is None and hostname in allowed
            except Exception:
                safe = False
                hostname = ""
            if safe:
                trusted.append(ExternalCandidate(
                    title=row.title, url=row.url, domain=hostname, content=row.content,
                    provider_rank=row.provider_rank, provider_score=row.provider_score,
                ))
        logger.info("external_trust_filter_completed", extra={
            "external_provider": "tavily", "external_returned_count": len(rows),
            "external_trusted_count": len(trusted),
            "external_duration_ms": round((perf_counter() - started) * 1000, 2),
            "status": "SUCCEEDED", "error_stage": "TRUST_FILTER", "error_code": None,
        })
        return tuple(trusted)
