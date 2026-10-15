from __future__ import annotations

import logging
import math
from time import perf_counter
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings.provider import EmbeddingProvider, get_embedding_provider
from app.ai.embeddings.schemas import EmbeddingProviderIdentity
from app.ai.retrieval import repository
from app.ai.retrieval.errors import retrieval_error
from app.ai.retrieval.filters import RetrievalFilter
from app.ai.retrieval.query_preprocessor import QueryPreprocessor
from app.ai.retrieval.schemas import (
    ActiveEmbeddingProfileSnapshot,
    CandidateMetadata,
    RetrievalCandidate,
)
from app.ai.vector_storage.service import VectorStorageService
from app.core.config import Settings, get_settings
from app.core.errors import ApplicationError
from app.database.models import EmbeddingProfile

logger = logging.getLogger(__name__)


class SemanticRetrievalService:
    """Turn query text into ranked candidates from the ACTIVE internal corpus."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        provider: EmbeddingProvider | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.provider = provider
        self.settings = settings or get_settings()

    @staticmethod
    def _snapshot(profile) -> ActiveEmbeddingProfileSnapshot:
        return ActiveEmbeddingProfileSnapshot(
            id=profile.id,
            provider=profile.provider,
            provider_version=profile.provider_version,
            model_name=profile.model_name,
            model_version=profile.model_version,
            dimensions=profile.dimensions,
            embedding_input_version=profile.embedding_input_version,
            normalize_embeddings=profile.normalize_embeddings,
        )

    def _expire_profile_state(self) -> None:
        # Step 6.2 re-resolves the ACTIVE profile through the same request
        # session. Expire only those ORM identities so a concurrent activation
        # is visible without invalidating unrelated caller-loaded objects.
        for instance in self.session.identity_map.values():
            if isinstance(instance, EmbeddingProfile):
                self.session.expire(instance)

    @staticmethod
    def _same_identity(
        provider_identity: EmbeddingProviderIdentity,
        profile: ActiveEmbeddingProfileSnapshot,
    ) -> bool:
        return (
            provider_identity.provider,
            provider_identity.provider_version,
            provider_identity.model_name,
            provider_identity.model_version,
            provider_identity.dimensions,
            provider_identity.embedding_input_version,
            provider_identity.normalize_embeddings,
        ) == (
            profile.provider,
            profile.provider_version,
            profile.model_name,
            profile.model_version,
            profile.dimensions,
            profile.embedding_input_version,
            profile.normalize_embeddings,
        )

    @staticmethod
    def _validate_query_vector(vector, profile: ActiveEmbeddingProfileSnapshot) -> list[float]:
        try:
            values = list(vector)
            valid = len(values) == profile.dimensions and all(math.isfinite(value) for value in values)
            if valid and profile.normalize_embeddings:
                norm = math.sqrt(sum(value * value for value in values))
                valid = abs(norm - 1.0) <= 1e-3
        except (TypeError, ValueError, OverflowError):
            valid = False
            values = []
        if not valid:
            raise retrieval_error(
                "INVALID_QUERY_EMBEDDING",
                "The embedding provider returned an invalid query vector.",
            )
        return values

    @staticmethod
    def _safe_profile_error(exc: ApplicationError) -> ApplicationError:
        if exc.code in {
            "ACTIVE_EMBEDDING_PROFILE_NOT_FOUND",
            "MULTIPLE_ACTIVE_EMBEDDING_PROFILES",
            "SEMANTIC_RETRIEVAL_FAILED",
        }:
            return exc
        return retrieval_error(
            "VECTOR_RETRIEVAL_FAILED",
            "Semantic vector retrieval failed.",
        )

    def _log_failure(
        self,
        *,
        started: float,
        query_length: int,
        candidate_k: int,
        profile_id: UUID | None,
        code: str,
        retrieval_filter: RetrievalFilter | None = None,
        embedding_ms: float = 0,
        vector_ms: float = 0,
        hydration_ms: float = 0,
    ) -> None:
        logger.warning(
            "semantic_retrieval_failed",
            extra={
                **SemanticRetrievalService._filter_log_fields(retrieval_filter),
                "embedding_profile_id": str(profile_id) if profile_id else None,
                "query_length_chars": query_length,
                "candidate_k": candidate_k,
                "returned_count": 0,
                "embedding_duration_ms": round(embedding_ms, 2),
                "vector_query_duration_ms": round(vector_ms, 2),
                "metadata_hydration_duration_ms": round(hydration_ms, 2),
                "total_retrieval_duration_ms": round((perf_counter() - started) * 1000, 2),
                "status": "FAILED",
                "error_code": code,
            },
        )

    @staticmethod
    def _filter_log_fields(retrieval_filter: RetrievalFilter | None) -> dict:
        return {
            "lesson_filter_count": len(retrieval_filter.lesson_ids) if retrieval_filter and retrieval_filter.lesson_ids is not None else 0,
            "hsk_filter_count": len(retrieval_filter.hsk_levels) if retrieval_filter and retrieval_filter.hsk_levels is not None else 0,
            "content_types": sorted(retrieval_filter.content_types) if retrieval_filter and retrieval_filter.content_types is not None else [],
            "source_types": sorted(retrieval_filter.source_types) if retrieval_filter and retrieval_filter.source_types is not None else [],
            "source_categories": sorted(retrieval_filter.source_categories) if retrieval_filter and retrieval_filter.source_categories is not None else [],
            "source_languages": sorted(retrieval_filter.source_languages) if retrieval_filter and retrieval_filter.source_languages is not None else [],
        }

    async def retrieve(
        self,
        query_text: str,
        *,
        retrieval_filter: RetrievalFilter | None = None,
    ) -> list[RetrievalCandidate]:
        started = perf_counter()
        candidate_k = self.settings.rag_retrieval_candidate_k
        profile_id: UUID | None = None
        embedding_ms = vector_ms = hydration_ms = 0.0
        try:
            if retrieval_filter is not None:
                if not isinstance(retrieval_filter, RetrievalFilter):
                    raise retrieval_error(
                        "INVALID_RETRIEVAL_FILTER",
                        "Retrieval filter has an invalid type.",
                        422,
                    )
                retrieval_filter.validate()
        except ApplicationError as exc:
            self._log_failure(
                started=started, query_length=0, candidate_k=candidate_k,
                profile_id=None, code=exc.code,
            )
            raise
        try:
            normalized_query = QueryPreprocessor.preprocess(query_text)
        except ApplicationError as exc:
            self._log_failure(
                started=started, query_length=0, candidate_k=candidate_k,
                profile_id=None, code=exc.code,
                retrieval_filter=retrieval_filter,
            )
            raise

        query_length = len(normalized_query)

        # Finish the profile read before provider/model inference. This service
        # is deliberately called outside any caller-owned write transaction.
        try:
            async with self.session.begin():
                profile = await VectorStorageService(self.session).resolve_active_profile()
                snapshot = self._snapshot(profile)
            profile_id = snapshot.id
        except ApplicationError as exc:
            safe_error = self._safe_profile_error(exc)
            self._log_failure(
                started=started, query_length=query_length, candidate_k=candidate_k,
                profile_id=None, code=safe_error.code,
                retrieval_filter=retrieval_filter,
            )
            if safe_error is exc:
                raise
            raise safe_error from None
        except Exception:
            error = retrieval_error(
                "VECTOR_RETRIEVAL_FAILED", "Semantic vector retrieval failed."
            )
            self._log_failure(
                started=started, query_length=query_length, candidate_k=candidate_k,
                profile_id=None, code=error.code,
                retrieval_filter=retrieval_filter,
            )
            raise error from None

        try:
            if self.session.in_transaction():
                raise retrieval_error(
                    "QUERY_EMBEDDING_FAILED",
                    "Query embedding cannot run inside a database transaction.",
                )
            provider = self.provider or get_embedding_provider()
            if not self._same_identity(provider.identity, snapshot):
                raise retrieval_error(
                    "QUERY_EMBEDDING_FAILED",
                    "Configured query embedding identity does not match the active profile.",
                )
            embedding_started = perf_counter()
            vector = await provider.embed_query(normalized_query)
            embedding_ms = (perf_counter() - embedding_started) * 1000
        except ApplicationError as exc:
            code = (
                "RETRIEVAL_QUERY_TOO_LONG"
                if exc.code == "EMBEDDING_INPUT_TOO_LONG"
                else "QUERY_EMBEDDING_FAILED"
            )
            status = 422 if code == "RETRIEVAL_QUERY_TOO_LONG" else 500
            error = retrieval_error(
                code,
                "The retrieval query is too long."
                if status == 422
                else "Query embedding failed.",
                status,
            )
            self._log_failure(
                started=started, query_length=query_length, candidate_k=candidate_k,
                profile_id=profile_id, code=code, retrieval_filter=retrieval_filter,
                embedding_ms=embedding_ms,
            )
            raise error from None
        except Exception:
            code = "QUERY_EMBEDDING_FAILED"
            error = retrieval_error(code, "Query embedding failed.")
            self._log_failure(
                started=started, query_length=query_length, candidate_k=candidate_k,
                profile_id=profile_id, code=code, retrieval_filter=retrieval_filter,
                embedding_ms=embedding_ms,
            )
            raise error from None

        try:
            query_vector = self._validate_query_vector(vector, snapshot)
        except ApplicationError as exc:
            self._log_failure(
                started=started, query_length=query_length, candidate_k=candidate_k,
                profile_id=profile_id, code=exc.code, retrieval_filter=retrieval_filter,
                embedding_ms=embedding_ms,
            )
            raise

        # The second read starts only after inference. Expiring profile ORM
        # identities ensures Step 6.2 re-reads lifecycle state if activation
        # changed while the query was being embedded.
        try:
            self._expire_profile_state()
            async with self.session.begin():
                vector_started = perf_counter()
                vector_rows = await VectorStorageService(self.session).nearest_vectors(
                    query_vector, snapshot.id, candidate_k,
                    retrieval_filter=retrieval_filter,
                )
                vector_ms = (perf_counter() - vector_started) * 1000
                if not vector_rows:
                    metadata_rows: list[CandidateMetadata] = []
                else:
                    hydration_started = perf_counter()
                    try:
                        metadata_rows = await repository.load_candidate_metadata(
                            self.session, [row.chunk_id for row in vector_rows]
                        )
                    except ApplicationError:
                        raise
                    except Exception:
                        raise retrieval_error(
                            "SEMANTIC_RETRIEVAL_FAILED",
                            "Retrieved knowledge metadata could not be resolved.",
                        ) from None
                    hydration_ms = (perf_counter() - hydration_started) * 1000
        except ApplicationError as exc:
            safe_error = self._safe_profile_error(exc)
            self._log_failure(
                started=started, query_length=query_length, candidate_k=candidate_k,
                profile_id=profile_id, code=safe_error.code,
                retrieval_filter=retrieval_filter,
                embedding_ms=embedding_ms, vector_ms=vector_ms,
                hydration_ms=hydration_ms,
            )
            if safe_error is exc:
                raise
            raise safe_error from None
        except Exception:
            error = retrieval_error(
                "VECTOR_RETRIEVAL_FAILED", "Semantic vector retrieval failed."
            )
            self._log_failure(
                started=started, query_length=query_length, candidate_k=candidate_k,
                profile_id=profile_id, code=error.code,
                retrieval_filter=retrieval_filter,
                embedding_ms=embedding_ms, vector_ms=vector_ms,
                hydration_ms=hydration_ms,
            )
            raise error from None

        if not vector_rows:
            self._log_success(
                started, query_length, candidate_k, profile_id, 0,
                embedding_ms, vector_ms, hydration_ms, None, None, retrieval_filter,
            )
            return []

        metadata_by_id = {item.chunk_id: item for item in metadata_rows}
        if len(metadata_by_id) != len(metadata_rows) or any(
            row.chunk_id not in metadata_by_id for row in vector_rows
        ):
            error = retrieval_error(
                "SEMANTIC_RETRIEVAL_FAILED",
                "Retrieved knowledge metadata could not be resolved.",
            )
            self._log_failure(
                started=started, query_length=query_length, candidate_k=candidate_k,
                profile_id=profile_id, code=error.code,
                retrieval_filter=retrieval_filter,
                embedding_ms=embedding_ms, vector_ms=vector_ms,
                hydration_ms=hydration_ms,
            )
            raise error

        candidates: list[RetrievalCandidate] = []
        for rank, vector_row in enumerate(vector_rows, start=1):
            try:
                distance = float(vector_row.distance)
                if not math.isfinite(distance):
                    raise ValueError
                metadata = metadata_by_id[vector_row.chunk_id]
                candidates.append(self._candidate(rank, metadata, distance))
            except (KeyError, TypeError, ValueError, OverflowError):
                error = retrieval_error(
                    "SEMANTIC_RETRIEVAL_FAILED",
                    "Retrieved knowledge metadata could not be resolved.",
                )
                self._log_failure(
                    started=started, query_length=query_length, candidate_k=candidate_k,
                    profile_id=profile_id, code=error.code,
                    retrieval_filter=retrieval_filter,
                    embedding_ms=embedding_ms, vector_ms=vector_ms,
                    hydration_ms=hydration_ms,
                )
                raise error from None

        first = candidates[0]
        self._log_success(
            started, query_length, candidate_k, profile_id, len(candidates),
            embedding_ms, vector_ms, hydration_ms, first.distance,
            first.retrieval_score, retrieval_filter,
        )
        return candidates

    @staticmethod
    def _candidate(rank: int, metadata: CandidateMetadata, distance: float) -> RetrievalCandidate:
        return RetrievalCandidate(
            rank=rank,
            chunk_id=metadata.chunk_id,
            chunk_index=metadata.chunk_index,
            content=metadata.content,
            content_type=metadata.content_type,
            knowledge_version_id=metadata.knowledge_version_id,
            knowledge_source_id=metadata.knowledge_source_id,
            source_type=metadata.source_type,
            source_document_id=metadata.source_document_id,
            source_lesson_id=metadata.source_lesson_id,
            chunk_lesson_id=metadata.chunk_lesson_id,
            document_title=metadata.document_title,
            lesson_title=metadata.lesson_title,
            hsk_level_number=metadata.hsk_level_number,
            page_number=metadata.page_number,
            section=metadata.section,
            locator_metadata=metadata.locator_metadata,
            distance=distance,
            retrieval_score=1.0 - distance,
        )

    @staticmethod
    def _log_success(
        started: float,
        query_length: int,
        candidate_k: int,
        profile_id: UUID,
        returned_count: int,
        embedding_ms: float,
        vector_ms: float,
        hydration_ms: float,
        top_distance: float | None,
        top_score: float | None,
        retrieval_filter: RetrievalFilter | None,
    ) -> None:
        logger.info(
            "semantic_retrieval_completed",
            extra={
                **SemanticRetrievalService._filter_log_fields(retrieval_filter),
                "embedding_profile_id": str(profile_id),
                "query_length_chars": query_length,
                "candidate_k": candidate_k,
                "returned_count": returned_count,
                "top_distance": top_distance,
                "top_retrieval_score": top_score,
                "embedding_duration_ms": round(embedding_ms, 2),
                "vector_query_duration_ms": round(vector_ms, 2),
                "metadata_hydration_duration_ms": round(hydration_ms, 2),
                "total_retrieval_duration_ms": round((perf_counter() - started) * 1000, 2),
                "status": "SUCCEEDED",
                "error_code": None,
            },
        )
