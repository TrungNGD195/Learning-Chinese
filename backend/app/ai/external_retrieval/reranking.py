from __future__ import annotations

import logging
import math
from time import perf_counter

from app.ai.external_retrieval.schemas import ExternalCandidate, ExternalRerankResult, RerankedExternalCandidate
from app.ai.reranking.errors import reranking_error
from app.ai.reranking.provider import RerankerProvider, get_reranker_provider
from app.core.config import Settings

logger = logging.getLogger("app.ai.external_retrieval")


class ExternalRerankingService:
    def __init__(self, settings: Settings, *, provider: RerankerProvider | None = None) -> None:
        self.settings = settings
        self.provider = provider

    @staticmethod
    def _log_failure(count: int, started: float, code: str) -> None:
        logger.warning("external_reranking_failed", extra={
            "external_provider": "tavily", "external_candidate_count": count,
            "external_scored_count": 0,
            "external_rerank_duration_ms": round((perf_counter() - started) * 1000, 2),
            "status": "FAILED", "error_stage": "RERANK", "error_code": code,
        })

    async def rerank(self, query: str, candidates: tuple[ExternalCandidate, ...]) -> ExternalRerankResult:
        started = perf_counter()
        if not candidates:
            return ExternalRerankResult((), ())
        if len(candidates) > 10:
            candidates = candidates[:10]
        provider = self.provider or get_reranker_provider()
        identity = provider.identity
        expected = (
            "MODAL" if self.settings.reranker_provider == "modal" else "LOCAL",
            self.settings.reranker_model_name, self.settings.reranker_model_revision,
            self.settings.reranker_input_version,
        )
        actual = (identity.provider, identity.model_name, identity.model_revision, identity.reranker_input_version)
        expected_version = "modal-bge-runtime/v1" if self.settings.reranker_provider == "modal" else None
        if actual != expected or not identity.provider_version or (expected_version and identity.provider_version != expected_version):
            self._log_failure(len(candidates), started, "RERANKER_NOT_AVAILABLE")
            raise reranking_error("RERANKER_NOT_AVAILABLE", "Configured reranker identity is invalid.", 503)
        passages = [f"Title: {item.title}\nDomain: {item.domain}\n\n{item.content}" for item in candidates]
        try:
            await provider.validate_pair_lengths(query, passages)
        except Exception as exc:
            code = getattr(exc, "code", "RERANK_INPUT_TOO_LONG")
            self._log_failure(len(candidates), started, code)
            if getattr(exc, "code", None):
                raise
            raise reranking_error("RERANK_INPUT_TOO_LONG", "External reranker input is invalid.") from None
        scores: list[float] = []
        for start in range(0, len(passages), self.settings.reranker_batch_size):
            batch = passages[start:start + self.settings.reranker_batch_size]
            try:
                batch_scores = await provider.score(query, batch)
            except Exception as exc:
                code = getattr(exc, "code", "RERANKER_INFERENCE_FAILED")
                self._log_failure(len(candidates), started, code)
                if getattr(exc, "code", None):
                    raise
                raise reranking_error("RERANKER_INFERENCE_FAILED", "External reranker inference failed.") from None
            if not isinstance(batch_scores, (list, tuple)) or len(batch_scores) != len(batch):
                self._log_failure(len(candidates), started, "INVALID_RERANKER_OUTPUT")
                raise reranking_error("INVALID_RERANKER_OUTPUT", "Reranker returned invalid scores.")
            try:
                values = [float(value) for value in batch_scores]
            except (TypeError, ValueError, OverflowError):
                self._log_failure(len(candidates), started, "INVALID_RERANKER_OUTPUT")
                raise reranking_error("INVALID_RERANKER_OUTPUT", "Reranker returned invalid scores.") from None
            if not all(math.isfinite(value) for value in values):
                self._log_failure(len(candidates), started, "INVALID_RERANKER_OUTPUT")
                raise reranking_error("INVALID_RERANKER_OUTPUT", "Reranker returned invalid scores.")
            scores.extend(values)
        if len(scores) != len(candidates):
            self._log_failure(len(candidates), started, "INVALID_RERANKER_OUTPUT")
            raise reranking_error("INVALID_RERANKER_OUTPUT", "Reranker returned invalid scores.")
        ordered = sorted(zip(candidates, scores, strict=True), key=lambda pair: (-pair[1], pair[0].provider_rank, pair[0].url))
        scored = tuple(RerankedExternalCandidate(
            title=c.title, url=c.url, domain=c.domain, content=c.content,
            provider_rank=c.provider_rank, provider_score=c.provider_score,
            rerank_score=score, rerank_rank=index,
        ) for index, (c, score) in enumerate(ordered, start=1))
        threshold = self.settings.rag_min_rerank_score
        if threshold is None:
            self._log_failure(len(candidates), started, "RAG_CONFIGURATION_INVALID")
            raise reranking_error("RAG_CONFIGURATION_INVALID", "The calibrated evidence threshold is unavailable.", 503)
        eligible = tuple(item for item in scored if item.rerank_score >= threshold)[:self.settings.reranker_top_k]
        logger.info("external_reranking_completed", extra={
            "external_provider": "tavily", "external_scored_count": len(scored),
            "external_eligible_count": sum(item.rerank_score >= threshold for item in scored),
            "external_rerank_duration_ms": round((perf_counter() - started) * 1000, 2),
            "status": "SUCCEEDED", "error_stage": "RERANK", "error_code": None,
        })
        return ExternalRerankResult(scored, eligible)
