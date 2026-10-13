from __future__ import annotations

import logging
import math
from time import perf_counter
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.retrieval.filters import RetrievalFilter
from app.ai.vector_storage import repository
from app.ai.vector_storage.errors import vector_storage_error
from app.ai.vector_storage.schemas import VectorReadinessResult
from app.core.errors import ApplicationError
from app.database.models import EmbeddingProfile

logger = logging.getLogger(__name__)


class VectorStorageService:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _profile_complete(profile) -> bool:
        return bool(
            profile is not None
            and isinstance(profile.provider, str) and profile.provider.strip()
            and isinstance(profile.provider_version, str) and profile.provider_version.strip()
            and isinstance(profile.model_name, str) and profile.model_name.strip()
            and isinstance(profile.model_version, str) and profile.model_version.strip()
            and isinstance(profile.embedding_input_version, str) and profile.embedding_input_version.strip()
            and isinstance(profile.dimensions, int) and profile.dimensions > 0
            and profile.normalize_embeddings is not None
            and profile.status in {"ACTIVE", "INACTIVE"}
        )

    @staticmethod
    def _failure(version_id, profile_id, code, *, chunks=0, embeddings=0,
                 dimensions=0, invalid=0, probe=None):
        return VectorReadinessResult(version_id, profile_id, False, chunks, embeddings,
                                     dimensions, invalid, probe, code)

    @staticmethod
    def _log_failure(action: str, exc: ApplicationError, *, profile_id=None,
                     version_id=None, source_count=None, version_count=None):
        fields = {
            "embedding_profile_id": str(profile_id) if profile_id else None,
            "knowledge_version_id": str(version_id) if version_id else None,
            "distance_metric": "cosine", "activation_action": action,
            "readiness_status": "FAILED", "status": "FAILED", "error_code": exc.code,
        }
        if source_count is not None:
            fields["source_count"] = source_count
        if version_count is not None:
            fields["version_count"] = version_count
        logger.warning("vector_storage_operation_failed", extra=fields)

    async def check_vector_pair_readiness(self, knowledge_version_id: UUID,
                                          embedding_profile_id: UUID) -> VectorReadinessResult:
        required_count = embedding_count = dimensions = invalid_count = 0
        try:
            version = await repository.get_version(self.session, knowledge_version_id)
            if version is None:
                return self._failure(knowledge_version_id, embedding_profile_id,
                                     "KNOWLEDGE_VERSION_NOT_VECTOR_READY")
            profile = await repository.get_profile(self.session, embedding_profile_id)
            if not self._profile_complete(profile):
                return self._failure(knowledge_version_id, embedding_profile_id,
                                     "EMBEDDING_PROFILE_NOT_READY",
                                     dimensions=getattr(profile, "dimensions", 0) or 0)
            dimensions = profile.dimensions
            required_count = await repository.count_required_chunks(self.session, knowledge_version_id)
            embedding_count = await repository.count_embeddings_for_version_profile(
                self.session, knowledge_version_id, embedding_profile_id
            )
            invalid_count = await repository.count_invalid_vector_dimensions(
                self.session, knowledge_version_id, embedding_profile_id, dimensions
            )
            if required_count <= 0 or embedding_count != required_count:
                return self._failure(knowledge_version_id, embedding_profile_id,
                                     "KNOWLEDGE_VERSION_NOT_VECTOR_READY",
                                     chunks=required_count, embeddings=embedding_count,
                                     dimensions=dimensions, invalid=invalid_count)
            if invalid_count:
                return self._failure(knowledge_version_id, embedding_profile_id,
                                     "VECTOR_DIMENSION_MISMATCH", chunks=required_count,
                                     embeddings=embedding_count, dimensions=dimensions,
                                     invalid=invalid_count)
            first = await repository.select_probe_embedding(self.session, knowledge_version_id,
                                                            embedding_profile_id)
            if first is None:
                return self._failure(knowledge_version_id, embedding_profile_id,
                                     "KNOWLEDGE_VERSION_NOT_VECTOR_READY",
                                     chunks=required_count, embeddings=embedding_count,
                                     dimensions=dimensions)
            probe_vector = first.vector
            if probe_vector is None or len(probe_vector) != dimensions:
                return self._failure(knowledge_version_id, embedding_profile_id,
                                     "VECTOR_DIMENSION_MISMATCH", chunks=required_count,
                                     embeddings=embedding_count, dimensions=dimensions, invalid=1)
            started = perf_counter()
            result = await repository.run_candidate_probe(
                self.session, knowledge_version_id, embedding_profile_id, probe_vector
            )
            duration_ms = round((perf_counter() - started) * 1000, 3)
            if result is None:
                return self._failure(knowledge_version_id, embedding_profile_id,
                                     "KNOWLEDGE_VERSION_NOT_VECTOR_READY",
                                     chunks=required_count, embeddings=embedding_count,
                                     dimensions=dimensions)
            distance = float(result.distance) if result.distance is not None else math.nan
            if (result.embedding_profile_id != embedding_profile_id
                    or result.knowledge_version_id != knowledge_version_id
                    or result.vector is None or len(result.vector) != dimensions
                    or not math.isfinite(distance) or abs(distance) > 1e-6):
                return self._failure(knowledge_version_id, embedding_profile_id,
                                     "KNOWLEDGE_VERSION_NOT_VECTOR_READY",
                                     chunks=required_count, embeddings=embedding_count,
                                     dimensions=dimensions,
                                     probe=distance if math.isfinite(distance) else None)
            logger.info("vector_pair_readiness_checked", extra={
                "embedding_profile_id": str(embedding_profile_id),
                "knowledge_version_id": str(knowledge_version_id),
                "vector_count": embedding_count, "dimensions": dimensions,
                "distance_metric": "cosine", "readiness_status": "READY",
                "query_probe_duration_ms": duration_ms, "status": "SUCCEEDED",
            })
            return VectorReadinessResult(knowledge_version_id, embedding_profile_id, True,
                                         required_count, embedding_count, dimensions,
                                         0, distance, None)
        except Exception:
            logger.error("vector_pair_readiness_query_failed", extra={
                "embedding_profile_id": str(embedding_profile_id),
                "knowledge_version_id": str(knowledge_version_id),
                "vector_count": embedding_count, "dimensions": dimensions,
                "distance_metric": "cosine", "readiness_status": "FAILED",
                "error_code": "VECTOR_QUERY_FAILED",
            })
            return self._failure(knowledge_version_id, embedding_profile_id, "VECTOR_QUERY_FAILED",
                                 chunks=required_count, embeddings=embedding_count,
                                 dimensions=dimensions, invalid=invalid_count)

    @staticmethod
    def _active_profile(profiles):
        active = [profile for profile in profiles if profile.status == "ACTIVE"]
        if not active:
            raise vector_storage_error("ACTIVE_EMBEDDING_PROFILE_NOT_FOUND", "No active embedding profile is configured.")
        if len(active) > 1:
            raise vector_storage_error("MULTIPLE_ACTIVE_EMBEDDING_PROFILES", "Multiple active embedding profiles were found.")
        return active[0]

    async def resolve_active_profile(self):
        try:
            return self._active_profile(await repository.list_profiles(self.session))
        except ApplicationError:
            raise
        except Exception as exc:
            raise vector_storage_error("VECTOR_QUERY_FAILED", "Active embedding profile lookup failed.") from exc

    @staticmethod
    def _require_complete_profile(profile):
        if not VectorStorageService._profile_complete(profile):
            raise vector_storage_error("EMBEDDING_PROFILE_NOT_READY", "Embedding profile is incomplete or unavailable.")

    async def _locked_profiles(self):
        profiles = await repository.lock_all_profiles(self.session)
        active = [profile for profile in profiles if profile.status == "ACTIVE"]
        if len(active) > 1:
            raise vector_storage_error("MULTIPLE_ACTIVE_EMBEDDING_PROFILES", "Multiple active embedding profiles were found.")
        return profiles, active[0] if active else None

    async def _readiness_or_raise(self, version_id, profile_id):
        result = await self.check_vector_pair_readiness(version_id, profile_id)
        if result.ready:
            return result
        code = result.failure_code or "KNOWLEDGE_VERSION_NOT_VECTOR_READY"
        if code not in {"KNOWLEDGE_VERSION_NOT_VECTOR_READY", "EMBEDDING_PROFILE_NOT_READY",
                        "VECTOR_DIMENSION_MISMATCH", "VECTOR_QUERY_FAILED"}:
            code = "KNOWLEDGE_VERSION_NOT_VECTOR_READY"
        messages = {
            "KNOWLEDGE_VERSION_NOT_VECTOR_READY": "Knowledge version does not have technically ready vectors.",
            "EMBEDDING_PROFILE_NOT_READY": "Embedding profile is incomplete or unavailable.",
            "VECTOR_DIMENSION_MISMATCH": "Stored vectors do not match the embedding profile dimensions.",
            "VECTOR_QUERY_FAILED": "Vector storage readiness query failed.",
        }
        raise vector_storage_error(code, messages[code])

    async def bootstrap_profile(self, target_profile_id: UUID) -> None:
        action = "bootstrap_profile"
        source_count = version_count = 0
        try:
            await self.session.rollback()
            async with self.session.begin():
                profiles, active = await self._locked_profiles()
                target = next((profile for profile in profiles if profile.id == target_profile_id), None)
                self._require_complete_profile(target)
                if active is not None:
                    raise vector_storage_error("ACTIVATION_CONFLICT", "An embedding profile is already active.")
                if target.status != "INACTIVE":
                    raise vector_storage_error("EMBEDDING_PROFILE_NOT_READY", "Bootstrap target profile must be inactive.")
                sources = await repository.lock_sources(self.session)
                source_count = len(sources)
                if not sources:
                    raise vector_storage_error("ACTIVATION_CONFLICT", "Cannot bootstrap an empty knowledge corpus.")
                versions = await repository.lock_versions_for_sources(
                    self.session, [source.id for source in sources], ["PROCESSING", "ACTIVE"]
                )
                if any(version.status == "ACTIVE" for version in versions):
                    raise vector_storage_error("ACTIVATION_CONFLICT", "Knowledge is already active before profile bootstrap.")
                by_source = {}
                for version in versions:
                    if version.status == "PROCESSING":
                        by_source.setdefault(version.knowledge_source_id, []).append(version)
                candidates = []
                for source in sources:
                    source_candidates = by_source.get(source.id, [])
                    if len(source_candidates) != 1:
                        raise vector_storage_error("KNOWLEDGE_VERSION_NOT_PROCESSING", "Every bootstrap source must have one processing knowledge version.")
                    candidates.append(source_candidates[0])
                version_count = len(candidates)
                for candidate in candidates:
                    await self._readiness_or_raise(candidate.id, target.id)
                transaction_timestamp = await self.session.scalar(select(func.now()))
                target.status = "ACTIVE"
                for candidate in candidates:
                    candidate.status = "ACTIVE"
                    candidate.activated_at = transaction_timestamp
                await self.session.flush()
        except ApplicationError as exc:
            self._log_failure(action, exc, profile_id=target_profile_id,
                              source_count=source_count, version_count=version_count)
            raise
        logger.info("vector_storage_activation_completed", extra={
            "embedding_profile_id": str(target_profile_id), "source_count": source_count,
            "version_count": version_count, "activation_action": action,
            "distance_metric": "cosine", "status": "SUCCEEDED",
        })

    async def activate_version(self, version_id: UUID) -> None:
        action = "activate_version"
        active_profile_id = None
        try:
            await self.session.rollback()
            async with self.session.begin():
                _, active_profile = await self._locked_profiles()
                if active_profile is None:
                    raise vector_storage_error("ACTIVE_EMBEDDING_PROFILE_NOT_FOUND", "No active embedding profile is configured.")
                active_profile_id = active_profile.id
                source_id = await repository.get_version_source_id(self.session, version_id)
                if source_id is None:
                    raise vector_storage_error("KNOWLEDGE_VERSION_NOT_PROCESSING", "Knowledge version is not available for activation.")
                source = await repository.lock_source(self.session, source_id)
                if source is None:
                    raise vector_storage_error("KNOWLEDGE_VERSION_NOT_PROCESSING", "Knowledge version is not available for activation.")
                versions = await repository.lock_versions_for_sources(
                    self.session, [source_id], ["PROCESSING", "ACTIVE"]
                )
                target = next((version for version in versions if version.id == version_id), None)
                if target is None:
                    state = await repository.get_version(self.session, version_id)
                    if state is not None and state.status == "ACTIVE":
                        raise vector_storage_error("ACTIVATION_CONFLICT", "Active knowledge version is not coherent with the active profile.")
                    raise vector_storage_error("KNOWLEDGE_VERSION_NOT_PROCESSING", "Knowledge version is not available for activation.")
                active_versions = [version for version in versions if version.status == "ACTIVE"]
                if len(active_versions) > 1:
                    raise vector_storage_error("ACTIVATION_CONFLICT", "Source has multiple active knowledge versions.")
                previous = active_versions[0] if active_versions else None
                no_op = target.status == "ACTIVE"
                if no_op:
                    try:
                        await self._readiness_or_raise(target.id, active_profile.id)
                    except ApplicationError as exc:
                        if exc.code == "VECTOR_QUERY_FAILED":
                            raise
                        raise vector_storage_error("ACTIVATION_CONFLICT", "Active knowledge version is not coherent with the active profile.") from exc
                elif target.status == "PROCESSING":
                    await self._readiness_or_raise(target.id, active_profile.id)
                    if previous is not None and previous.id != target.id:
                        previous.status = "SUPERSEDED"
                        # The old state remains externally visible until this transaction commits.
                        # Flush it only after candidate readiness has passed so the partial unique
                        # index permits the new ACTIVE row in the same atomic transaction.
                        await self.session.flush()
                    target.status = "ACTIVE"
                    target.activated_at = await self.session.scalar(select(func.now()))
                else:
                    raise vector_storage_error("KNOWLEDGE_VERSION_NOT_PROCESSING", "Knowledge version is not available for activation.")
                await self.session.flush()
        except ApplicationError as exc:
            self._log_failure(action, exc, profile_id=active_profile_id, version_id=version_id)
            raise
        logger.info("knowledge_version_activation_completed", extra={
            "embedding_profile_id": str(active_profile_id), "knowledge_version_id": str(version_id),
            "activation_action": action, "distance_metric": "cosine",
            "status": "NO_OP" if no_op else "SUCCEEDED",
        })

    async def migrate_active_profile(self, target_profile_id: UUID) -> None:
        action = "migrate_active_profile"
        active_profile_id = None
        source_count = version_count = 0
        try:
            await self.session.rollback()
            async with self.session.begin():
                profiles, active_profile = await self._locked_profiles()
                if active_profile is None:
                    raise vector_storage_error("ACTIVE_EMBEDDING_PROFILE_NOT_FOUND", "No active embedding profile is configured.")
                active_profile_id = active_profile.id
                target = next((profile for profile in profiles if profile.id == target_profile_id), None)
                self._require_complete_profile(target)
                sources, versions = await repository.lock_active_sources_and_versions(self.session)
                source_count, version_count = len(sources), len(versions)
                no_op = target.id == active_profile.id
                if no_op:
                    for version in versions:
                        try:
                            await self._readiness_or_raise(version.id, active_profile.id)
                        except ApplicationError as exc:
                            if exc.code == "VECTOR_QUERY_FAILED":
                                raise
                            raise vector_storage_error("ACTIVATION_CONFLICT", "Active knowledge is not coherent with the active profile.") from exc
                else:
                    if target.status != "INACTIVE":
                        raise vector_storage_error("EMBEDDING_PROFILE_NOT_READY", "Profile migration target must be inactive.")
                    if not versions:
                        raise vector_storage_error("ACTIVATION_CONFLICT", "Active knowledge cohort is empty.")
                    for version in versions:
                        await self._readiness_or_raise(version.id, target.id)
                    active_profile.status = "INACTIVE"
                    # Keep the global partial unique index valid at each SQL statement;
                    # both profile updates remain in this single transaction.
                    await self.session.flush()
                    target.status = "ACTIVE"
                    await self.session.flush()
        except ApplicationError as exc:
            self._log_failure(action, exc, profile_id=target_profile_id,
                              source_count=source_count, version_count=version_count)
            raise
        logger.info("vector_profile_activation_completed", extra={
            "embedding_profile_id": str(target_profile_id), "source_count": source_count,
            "version_count": version_count, "activation_action": action,
            "distance_metric": "cosine", "status": "NO_OP" if no_op else "SUCCEEDED",
        })

    async def nearest_vectors(self, query_vector: list[float], embedding_profile_id: UUID,
                              limit: int, *,
                              retrieval_filter: RetrievalFilter | None = None):
        if retrieval_filter is not None:
            retrieval_filter.validate()
        if limit <= 0:
            raise ValueError("limit must be positive")
        profile = await self.resolve_active_profile()
        if profile.id != embedding_profile_id:
            raise vector_storage_error("EMBEDDING_PROFILE_NOT_READY", "Requested profile is not the globally active profile.")
        if len(query_vector) != profile.dimensions:
            raise vector_storage_error("VECTOR_DIMENSION_MISMATCH", "Query vector dimensions do not match the active profile.")
        try:
            return await repository.nearest_vectors(
                self.session, query_vector, profile.id, limit,
                retrieval_filter=retrieval_filter,
            )
        except Exception as exc:
            raise vector_storage_error("VECTOR_QUERY_FAILED", "Vector nearest-neighbor query failed.") from exc
