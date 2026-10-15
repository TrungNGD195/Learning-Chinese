from __future__ import annotations

import logging
import math
from dataclasses import fields
from time import perf_counter
from typing import Sequence
from uuid import UUID

from app.ai.reranking.errors import reranking_error
from app.ai.reranking.formatter import RerankPassageFormatter
from app.ai.reranking.provider import RerankerProvider, get_reranker_provider
from app.ai.reranking.schemas import RerankResult, RerankedCandidate, RerankerProviderIdentity
from app.ai.retrieval.query_preprocessor import QueryPreprocessor
from app.ai.retrieval.schemas import RetrievalCandidate
from app.core.config import Settings, get_settings
from app.core.errors import ApplicationError

logger = logging.getLogger(__name__)
_CANDIDATE_POOL_SIZE = 20


class RerankingService:
    """Score and order only the already-hydrated semantic candidate set."""

    def __init__(
        self,
        *,
        provider: RerankerProvider | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.provider = provider
        self.settings = settings or get_settings()

    def _provider(self) -> RerankerProvider:
        provider = self.provider or get_reranker_provider()
        identity = provider.identity
        expected = (
            "MODAL" if self.settings.reranker_provider == "modal" else "LOCAL",
            self.settings.reranker_model_name,
            self.settings.reranker_model_revision,
            self.settings.reranker_input_version,
        )
        actual = (
            identity.provider,
            identity.model_name,
            identity.model_revision,
            identity.reranker_input_version,
        )
        expected_version = "modal-bge-runtime/v1" if self.settings.reranker_provider == "modal" else None
        if actual != expected or not identity.provider_version or (expected_version and identity.provider_version != expected_version):
            raise reranking_error(
                "RERANKER_NOT_AVAILABLE", "Configured reranker identity is invalid.", 503
            )
        return provider

    @staticmethod
    def _validate_candidates(candidates: object) -> list[RetrievalCandidate]:
        if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes, bytearray)):
            raise reranking_error("INVALID_RERANK_INPUT", "Reranker candidates are invalid.", 422)
        items = list(candidates)
        seen: set[UUID] = set()
        for candidate in items:
            if not isinstance(candidate, RetrievalCandidate):
                raise reranking_error("INVALID_RERANK_INPUT", "Reranker candidate is invalid.", 422)
            if not isinstance(candidate.chunk_id, UUID) or candidate.chunk_id in seen:
                raise reranking_error("INVALID_RERANK_INPUT", "Reranker candidate identity is invalid.", 422)
            seen.add(candidate.chunk_id)
            if (
                not isinstance(candidate.rank, int)
                or isinstance(candidate.rank, bool)
                or candidate.rank < 1
                or not isinstance(candidate.content, str)
                or not candidate.content.strip()
            ):
                raise reranking_error("INVALID_RERANK_INPUT", "Reranker candidate content is invalid.", 422)
        return items

    @staticmethod
    def _with_scores(
        candidate: RetrievalCandidate,
        *,
        score: float,
        rerank_rank: int,
    ) -> RerankedCandidate:
        original_fields = {field.name: getattr(candidate, field.name) for field in fields(RetrievalCandidate)}
        return RerankedCandidate(**original_fields, rerank_score=score, rerank_rank=rerank_rank)

    def _log_fields(
        self,
        *,
        provider: RerankerProvider | None,
        candidate_count: int,
        scored_count: int,
        batch_count: int,
        started: float,
        top_retrieval_score: float | None,
        top_rerank_score: float | None,
        status: str,
        error_code: str | None,
    ) -> dict:
        try:
            identity: RerankerProviderIdentity | None = provider.identity if provider is not None else None
        except Exception:
            identity = None
        try:
            device = provider.device if provider is not None else self.settings.reranker_device
        except Exception:
            device = "unavailable"
        return {
            "provider": identity.provider if identity else "LOCAL",
            "provider_version": identity.provider_version if identity else None,
            "model_name": identity.model_name if identity else self.settings.reranker_model_name,
            "model_revision": identity.model_revision if identity else self.settings.reranker_model_revision,
            "reranker_input_version": identity.reranker_input_version if identity else self.settings.reranker_input_version,
            "candidate_count": candidate_count,
            "scored_count": scored_count,
            "rerank_top_k": self.settings.reranker_top_k,
            "batch_size": self.settings.reranker_batch_size,
            "batch_count": batch_count,
            "device": device,
            "rerank_duration_ms": round((perf_counter() - started) * 1000, 2),
            "top_retrieval_score": top_retrieval_score,
            "top_rerank_score": top_rerank_score,
            "status": status,
            "error_code": error_code,
        }

    async def rerank(
        self,
        query_text: str,
        candidates: Sequence[RetrievalCandidate],
    ) -> RerankResult:
        started = perf_counter()
        original_count = 0
        selected_count = 0
        scored_count = 0
        batch_count = 0
        active_provider: RerankerProvider | None = None
        try:
            validated = self._validate_candidates(candidates)
            original_count = len(validated)
            if not validated:
                logger.info(
                    "reranking_completed",
                    extra=self._log_fields(
                        provider=None,
                        candidate_count=0,
                        scored_count=0,
                        batch_count=0,
                        started=started,
                        top_retrieval_score=None,
                        top_rerank_score=None,
                        status="SUCCEEDED",
                        error_code=None,
                    ),
                )
                return RerankResult((), ())

            normalized_query = QueryPreprocessor.preprocess(query_text)
            pool = validated[:_CANDIDATE_POOL_SIZE]
            selected_count = len(pool)
            passages = [RerankPassageFormatter.format(candidate) for candidate in pool]
            active_provider = self._provider()
            await active_provider.validate_pair_lengths(normalized_query, passages)

            batch_scores: list[float] = []
            batch_size = self.settings.reranker_batch_size
            batch_count = math.ceil(len(passages) / batch_size)
            for start in range(0, len(passages), batch_size):
                passage_batch = passages[start : start + batch_size]
                scores = await active_provider.score(normalized_query, passage_batch)
                if not isinstance(scores, Sequence) or isinstance(scores, (str, bytes)):
                    raise reranking_error("INVALID_RERANKER_OUTPUT", "Reranker returned invalid scores.")
                if len(scores) != len(passage_batch):
                    raise reranking_error("INVALID_RERANKER_OUTPUT", "Reranker returned an invalid score count.")
                try:
                    converted_scores = [float(score) for score in scores]
                except (TypeError, ValueError, OverflowError):
                    raise reranking_error("INVALID_RERANKER_OUTPUT", "Reranker returned invalid scores.") from None
                if not all(math.isfinite(score) for score in converted_scores):
                    raise reranking_error("INVALID_RERANKER_OUTPUT", "Reranker returned invalid scores.")
                batch_scores.extend(converted_scores)
                scored_count += len(converted_scores)

            if len(batch_scores) != len(pool):
                raise reranking_error("INVALID_RERANKER_OUTPUT", "Reranker returned an invalid score count.")

            scored = list(zip(pool, batch_scores, strict=True))
            scored.sort(key=lambda item: (-item[1], item[0].rank, str(item[0].chunk_id)))
            reranked = [
                self._with_scores(candidate, score=score, rerank_rank=rank)
                for rank, (candidate, score) in enumerate(scored, start=1)
            ]
            result = RerankResult(
                scored_candidates=tuple(reranked),
                top_candidates=tuple(reranked[: self.settings.reranker_top_k]),
            )
            logger.info(
                "reranking_completed",
                extra=self._log_fields(
                    provider=active_provider,
                    candidate_count=original_count,
                    scored_count=selected_count,
                    batch_count=batch_count,
                    started=started,
                    top_retrieval_score=result.top_candidates[0].retrieval_score if result.top_candidates else None,
                    top_rerank_score=result.top_candidates[0].rerank_score if result.top_candidates else None,
                    status="SUCCEEDED",
                    error_code=None,
                ),
            )
            return result
        except ApplicationError as exc:
            logger.warning(
                "reranking_failed",
                extra=self._log_fields(
                    provider=active_provider,
                    candidate_count=original_count,
                    scored_count=scored_count,
                    batch_count=batch_count,
                    started=started,
                    top_retrieval_score=None,
                    top_rerank_score=None,
                    status="FAILED",
                    error_code=exc.code,
                ),
            )
            raise
        except Exception:
            error = reranking_error(
                "RERANKER_INFERENCE_FAILED", "Local reranker inference failed."
            )
            logger.warning(
                "reranking_failed",
                extra=self._log_fields(
                    provider=active_provider,
                    candidate_count=original_count,
                    scored_count=scored_count,
                    batch_count=batch_count,
                    started=started,
                    top_retrieval_score=None,
                    top_rerank_score=None,
                    status="FAILED",
                    error_code=error.code,
                ),
            )
            raise error from None
