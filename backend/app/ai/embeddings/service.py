from __future__ import annotations

import logging
import math
from hashlib import sha256
from time import perf_counter
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings import repository
from app.ai.embeddings.errors import embedding_error
from app.ai.embeddings.formatter import EmbeddingInputFormatter
from app.ai.embeddings.provider import EmbeddingProvider, get_embedding_provider
from app.ai.embeddings.schemas import (
    EmbeddingBuildResult, EmbeddingProfileIdentity,
)
from app.core.config import Settings, get_settings
from app.core.errors import ApplicationError
from app.database.models import Chunk, Document, Lesson, ParsingRun, TransformationRun
from app.ingestion.chunking.strategy import content_hash as chunk_content_hash

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self, session: AsyncSession, *, provider: EmbeddingProvider | None = None,
                 settings: Settings | None = None, formatter: EmbeddingInputFormatter | None = None):
        self.session = session
        self.provider = provider or get_embedding_provider()
        self.settings = settings or get_settings()
        self.formatter = formatter or EmbeddingInputFormatter()

    def _desired_identity(self) -> EmbeddingProfileIdentity:
        provider_identity = self.provider.identity
        if (
            provider_identity.provider != ("MODAL" if self.settings.embedding_provider == "modal" else "LOCAL")
            or provider_identity.provider_version != (
                "modal-bge-runtime/v1" if self.settings.embedding_provider == "modal"
                else "sentence-transformers/6.1.0"
            )
            or provider_identity.model_name != self.settings.embedding_model_name
            or provider_identity.model_version != self.settings.embedding_model_revision
            or provider_identity.dimensions != 1024
            or not provider_identity.normalize_embeddings
            or not self.settings.embedding_normalize
        ):
            raise embedding_error("EMBEDDING_PROFILE_INVALID", "Embedding provider identity does not match the frozen V0 profile.", 409)
        return EmbeddingProfileIdentity(
            provider=provider_identity.provider,
            provider_version=provider_identity.provider_version,
            model_name=self.settings.embedding_model_name,
            model_version=self.settings.embedding_model_revision,
            dimensions=provider_identity.dimensions,
            embedding_input_version=self.settings.embedding_input_version,
            normalize_embeddings=self.settings.embedding_normalize,
        )

    @staticmethod
    def _validate_profile(profile, identity: EmbeddingProfileIdentity) -> None:
        values = (
            profile.provider, profile.provider_version, profile.model_name, profile.model_version,
            profile.dimensions, profile.embedding_input_version, profile.normalize_embeddings,
        )
        expected = (
            identity.provider, identity.provider_version, identity.model_name, identity.model_version,
            identity.dimensions, identity.embedding_input_version, identity.normalize_embeddings,
        )
        if any(value is None for value in values) or values != expected or profile.status not in {"ACTIVE", "INACTIVE"}:
            raise embedding_error("EMBEDDING_PROFILE_INVALID", "Embedding profile identity is incomplete or incompatible.", 409)

    async def _read_eligibility(self, version_id: UUID):
        row = await repository.get_version_and_source(self.session, version_id)
        if row is None:
            await self.session.rollback()
            raise embedding_error("KNOWLEDGE_VERSION_NOT_PROCESSING", "Knowledge version is not available for embedding.", 409)
        version, source = row
        source_id = source.id
        required = await repository.count_required_chunks(self.session, version_id)
        status = version.status
        await self.session.rollback()
        if status != "PROCESSING":
            raise embedding_error("KNOWLEDGE_VERSION_NOT_PROCESSING", "Knowledge version is not available for embedding.", 409)
        return source_id, required

    async def _resolve_profile(self, identity: EmbeddingProfileIdentity):
        await self.session.rollback()
        async with self.session.begin():
            profile = await repository.get_or_create_embedding_profile(self.session, identity)
            self._validate_profile(profile, identity)
            profile_id = profile.id
        return profile_id

    async def _fail_version(self, version_id: UUID) -> None:
        await self.session.rollback()
        async with self.session.begin():
            await repository.mark_version_failed(self.session, version_id)

    @staticmethod
    def _validate_vectors(vectors: list[list[float]], expected_count: int, dimensions: int) -> None:
        if len(vectors) != expected_count:
            raise embedding_error("INVALID_EMBEDDING_OUTPUT", "Embedding provider returned an invalid vector count.", 500)
        for vector in vectors:
            if len(vector) != dimensions or not all(math.isfinite(value) for value in vector):
                raise embedding_error("INVALID_EMBEDDING_OUTPUT", "Embedding provider returned an invalid vector.", 500)
            norm = math.sqrt(sum(value * value for value in vector))
            if abs(norm - 1.0) > 1e-3:
                raise embedding_error("INVALID_EMBEDDING_OUTPUT", "Embedding provider returned a non-normalized vector.", 500)

    async def embed_processing_version(self, knowledge_version_id: UUID) -> EmbeddingBuildResult:
        _, required_count = await self._read_eligibility(knowledge_version_id)
        if required_count == 0:
            await self._fail_version(knowledge_version_id)
            logger.error("embedding_build_failed", extra={
                "knowledge_version_id": str(knowledge_version_id), "embedding_profile_id": None,
                "model_name": self.settings.embedding_model_name, "model_version": self.settings.embedding_model_revision,
                "batch_index": 0, "batch_size": 0, "duration_ms": 0, "embedded_count": 0,
                "skipped_count": 0, "device": self.provider.device, "status": "FAILED",
                "error_code": "EMBEDDING_BUILD_FAILED",
            })
            raise embedding_error("EMBEDDING_BUILD_FAILED", "Knowledge version has no chunks to embed.", 409, reason="ZERO_REQUIRED_CHUNKS")

        identity = None
        profile_id = None
        batch_index = 0
        embedded_this_run = 0
        skipped_count = 0
        try:
            identity = self._desired_identity()
            profile_id = await self._resolve_profile(identity)
            await self.session.rollback()
            skipped_count = await repository.count_embeddings_for_version_profile(
                self.session, knowledge_version_id, profile_id
            )
            await self.session.rollback()
            while True:
                await self.session.rollback()
                contexts = await repository.list_missing_chunk_contexts_for_profile(
                    self.session, knowledge_version_id, profile_id, self.settings.embedding_batch_size
                )
                await self.session.rollback()
                if not contexts:
                    break
                chunk_ids = [item.chunk_id for item in contexts]
                already = await repository.list_existing_embedding_chunk_ids(self.session, profile_id, chunk_ids)
                await self.session.rollback()
                skipped_count += len(already)
                to_encode = [item for item in contexts if item.chunk_id not in already]
                if not to_encode:
                    batch_index += 1
                    continue
                texts = [self.formatter.format(item) for item in to_encode]
                started = perf_counter()
                try:
                    vectors = await self.provider.embed_documents(texts, batch_size=self.settings.embedding_batch_size)
                except ApplicationError:
                    raise
                except Exception as exc:
                    raise embedding_error("EMBEDDING_PROVIDER_FAILED", "Embedding model inference failed.", 500) from exc
                self._validate_vectors(vectors, len(texts), identity.dimensions)
                duration_ms = round((perf_counter() - started) * 1000, 2)
                rows = [
                    {"chunk_id": item.chunk_id, "embedding_profile_id": profile_id, "vector": vector}
                    for item, vector in zip(to_encode, vectors, strict=True)
                ]
                await self.session.rollback()
                async with self.session.begin():
                    version = await repository.lock_version(self.session, knowledge_version_id)
                    if version is None or version.status != "PROCESSING":
                        raise embedding_error("KNOWLEDGE_VERSION_NOT_PROCESSING", "Knowledge version is not available for embedding.", 409)
                    profile = await repository.get_profile(self.session, profile_id)
                    self._validate_profile(profile, identity)
                    existing = await repository.list_existing_embedding_chunk_ids(self.session, profile_id, chunk_ids)
                    pending_rows = [row for row in rows if row["chunk_id"] not in existing]
                    skipped_count += len(existing)
                    inserted = await repository.insert_embeddings_conflict_safe(self.session, pending_rows)
                    embedded_this_run += inserted
                    skipped_count += len(pending_rows) - inserted
                logger.info("embedding_batch_completed", extra={
                    "knowledge_version_id": str(knowledge_version_id), "embedding_profile_id": str(profile_id),
                    "model_name": identity.model_name, "model_version": identity.model_version,
                    "batch_index": batch_index, "batch_size": len(to_encode), "duration_ms": duration_ms,
                    "embedded_count": inserted, "skipped_count": len(pending_rows) - inserted,
                    "device": self.provider.device, "status": "SUCCEEDED",
                })
                batch_index += 1

            await self.session.rollback()
            required_count = await repository.count_required_chunks(self.session, knowledge_version_id)
            embedded_count = await repository.count_embeddings_for_version_profile(self.session, knowledge_version_id, profile_id)
            version = await repository.lock_version(self.session, knowledge_version_id)
            status = version.status if version else None
            await self.session.rollback()
            if required_count <= 0 or embedded_count != required_count:
                raise embedding_error("EMBEDDING_BUILD_FAILED", "Embedding completeness verification failed.", 500)
            if status != "PROCESSING":
                raise embedding_error("KNOWLEDGE_VERSION_NOT_PROCESSING", "Knowledge version is not available for embedding.", 409)
            logger.info("embedding_build_completed", extra={
                "knowledge_version_id": str(knowledge_version_id), "embedding_profile_id": str(profile_id),
                "model_name": identity.model_name, "model_version": identity.model_version,
                "batch_index": batch_index, "batch_size": self.settings.embedding_batch_size,
                "duration_ms": 0, "embedded_count": embedded_count,
                "skipped_count": skipped_count, "device": self.provider.device, "status": "SUCCEEDED",
            })
            return EmbeddingBuildResult(knowledge_version_id, profile_id, required_count,
                                        embedded_count, embedded_this_run, skipped_count)
        except Exception as exc:
            await self._fail_version(knowledge_version_id)
            if isinstance(exc, ApplicationError):
                logger.error("embedding_build_failed", extra={
                    "knowledge_version_id": str(knowledge_version_id),
                    "embedding_profile_id": str(profile_id) if profile_id else None,
                    "model_name": identity.model_name if identity else self.settings.embedding_model_name,
                    "model_version": identity.model_version if identity else self.settings.embedding_model_revision,
                    "batch_index": batch_index, "batch_size": self.settings.embedding_batch_size,
                    "duration_ms": 0, "embedded_count": embedded_this_run,
                    "skipped_count": skipped_count, "device": self.provider.device,
                    "status": "FAILED", "error_code": exc.code,
                })
                raise
            logger.exception("embedding_build_failed", extra={
                "knowledge_version_id": str(knowledge_version_id),
                "embedding_profile_id": str(profile_id) if profile_id else None,
                "model_name": identity.model_name if identity else self.settings.embedding_model_name,
                "model_version": identity.model_version if identity else self.settings.embedding_model_revision,
                "batch_index": batch_index, "batch_size": self.settings.embedding_batch_size,
                "duration_ms": 0, "embedded_count": embedded_this_run,
                "skipped_count": skipped_count, "device": self.provider.device,
                "status": "FAILED", "error_code": "EMBEDDING_BUILD_FAILED",
            })
            raise embedding_error("EMBEDDING_BUILD_FAILED", "Embedding build failed.", 500) from exc

    async def retry_failed_version(self, knowledge_version_id: UUID, *, reprocessing_planner) -> EmbeddingBuildResult:
        # Compatibility proof and durable retry claim are serialized using the existing source lock.
        await self.session.rollback()
        mismatch: tuple[bool, bool, str] | None = None
        async with self.session.begin():
            row = await repository.get_version_and_source(self.session, knowledge_version_id)
            if row is None:
                raise embedding_error("KNOWLEDGE_VERSION_NOT_PROCESSING", "Knowledge version is not available for embedding.", 409)
            version, source = row
            await repository.lock_source(self.session, source.id)
            version = await repository.lock_version(self.session, version.id)
            if await repository.find_processing_version(self.session, source.id):
                raise embedding_error("PROCESSING_ALREADY_IN_PROGRESS", "Knowledge source processing is already in progress.", 409)
            if version is None or version.status != "FAILED":
                raise embedding_error("KNOWLEDGE_VERSION_NOT_PROCESSING", "Knowledge version is not failed and retryable.", 409)
            # Retry compatibility is established in lineage order. A stale upstream
            # artifact takes precedence over any missing or old embedding evidence.
            source_run_id = version.transformation_run_id
            run = await self.session.get(TransformationRun, source_run_id) if source_run_id else None
            parsing = await self.session.get(ParsingRun, run.parsing_run_id) if run else None
            from app.ingestion.cleaning import CLEANING_STRATEGY, CLEANING_VERSION
            from app.ingestion.reprocessing import _desired_parser
            from app.ingestion.transformation.service import TRANSFORMATION_STRATEGY, TRANSFORMATION_VERSION
            from app.ingestion.chunking.models import ChunkMetadata

            valid_source = False
            if run and parsing and run.status == "SUCCEEDED" and run.error_code is None and run.transformed_storage_reference:
                valid_target = (
                    run.source_type == source.source_type
                    and run.document_id == source.document_id
                    and run.lesson_id == source.lesson_id
                    and parsing.source_type == source.source_type
                    and parsing.document_id == source.document_id
                    and parsing.lesson_id == source.lesson_id
                    and parsing.status == "SUCCEEDED"
                    and parsing.error_code is None
                    and run.parsing_run_id == parsing.id
                    and run.parsed_storage_reference == parsing.parsed_storage_reference
                    and (run.transformation_strategy, run.transformation_version)
                    == (TRANSFORMATION_STRATEGY, TRANSFORMATION_VERSION)
                    and (parsing.cleaning_strategy, parsing.cleaning_version)
                    == (CLEANING_STRATEGY, CLEANING_VERSION)
                )
                if source.source_type == "DOCUMENT" and valid_target:
                    document = await self.session.get(Document, source.document_id)
                    expected_parser = _desired_parser("DOCUMENT", document.file_type if document else None)
                    valid_source = bool(
                        document and document.content_hash == parsing.raw_content_hash
                        and document.approved_transformation_run_id == run.id
                        and expected_parser == (parsing.parser_name, parsing.parser_version)
                    )
                elif source.source_type == "LESSON" and valid_target:
                    lesson = await self.session.get(Lesson, source.lesson_id)
                    expected_parser = _desired_parser("LESSON", None)
                    if lesson and lesson.status == "PUBLISHED" and expected_parser == (parsing.parser_name, parsing.parser_version):
                        from app.ingestion.service import lesson_snapshot_bytes
                        valid_source = sha256(await lesson_snapshot_bytes(self.session, lesson.id)).hexdigest() == parsing.raw_content_hash
            if not valid_source:
                mismatch = (False, False, "source")

            from app.ingestion.chunking.config import DEFAULT_CHUNKING_CONFIG
            if mismatch is None and (
                version.chunking_strategy != DEFAULT_CHUNKING_CONFIG.strategy
                or version.chunking_version != DEFAULT_CHUNKING_CONFIG.version
                or version.chunk_size != DEFAULT_CHUNKING_CONFIG.target_chars
                or version.chunk_max_chars != DEFAULT_CHUNKING_CONFIG.max_chars
                or version.chunk_overlap != DEFAULT_CHUNKING_CONFIG.overlap_chars
            ):
                mismatch = (False, False, "chunking")

            candidate_chunks = []
            if mismatch is None:
                candidate_chunks = list((await self.session.scalars(
                    select(Chunk).where(Chunk.knowledge_version_id == version.id).order_by(Chunk.chunk_index.asc())
                )).all())
                valid_chunks = bool(candidate_chunks) and all(
                    chunk.chunk_index == index
                    and chunk.content_hash is not None
                    and chunk.content_hash == chunk_content_hash(chunk.content, chunk.content_type)
                    for index, chunk in enumerate(candidate_chunks)
                )
                if valid_chunks:
                    try:
                        for chunk in candidate_chunks:
                            ChunkMetadata.model_validate(chunk.metadata_json or {})
                    except Exception:
                        valid_chunks = False
                if not valid_chunks:
                    mismatch = (False, False, "chunks")

            chunks = await repository.list_chunk_contexts_for_version(self.session, version.id) if mismatch is None else []
            if mismatch is None and not chunks:
                mismatch = (False, False, "chunks")

            # Only a fully current source → parse/clean/transform → chunk lineage
            # may be classified from prior embedding profile evidence.
            if mismatch is None:
                profile_ids = await repository.list_existing_embedding_profile_ids_for_version(self.session, version.id)
                identity = self._desired_identity()
                compatible = False
                mismatch_profile = len(profile_ids) != 1
                mismatch_input = False
                if len(profile_ids) == 1:
                    profile = await repository.get_profile(self.session, next(iter(profile_ids)))
                    fields = ("provider", "provider_version", "model_name", "model_version", "dimensions",
                              "embedding_input_version", "normalize_embeddings")
                    previous = tuple(getattr(profile, field) for field in fields) if profile is not None else ()
                    desired = tuple(getattr(identity, field) for field in fields)
                    compatible = profile is not None and previous == desired
                    if not compatible and profile is not None:
                        non_input = ("provider", "provider_version", "model_name", "model_version", "dimensions", "normalize_embeddings")
                        mismatch_profile = any(getattr(profile, field) != getattr(identity, field) for field in non_input)
                        mismatch_input = not mismatch_profile and profile.embedding_input_version != identity.embedding_input_version
                if not compatible:
                    mismatch = (mismatch_profile, mismatch_input, "profile")
            if mismatch is None:
                version.status = "PROCESSING"
                await self.session.flush()
        if mismatch is not None:
            profile_changed, input_changed, _ = mismatch
            try:
                plan = await reprocessing_planner.plan_source(
                    source.source_type,
                    source.document_id if source.source_type == "DOCUMENT" else source.lesson_id,
                    embedding_profile_changed=profile_changed,
                    embedding_input_changed=input_changed,
                )
            except ApplicationError as exc:
                logger.info("embedding_retry_reprocessing_handoff", extra={
                    "knowledge_version_id": str(knowledge_version_id),
                    "embedding_profile_id": None, "model_name": self.settings.embedding_model_name,
                    "model_version": self.settings.embedding_model_revision, "batch_index": 0,
                    "batch_size": 0, "duration_ms": 0, "embedded_count": 0,
                    "skipped_count": 0, "device": self.provider.device, "status": "FAILED",
                    "error_code": "EMBEDDING_FINGERPRINT_MISMATCH",
                    "reprocessing_action": None, "reprocessing_reason": None,
                })
                raise embedding_error("EMBEDDING_FINGERPRINT_MISMATCH", "Failed embedding attempt is not compatible with current source and profile identity.", 409) from exc
            logger.info("embedding_retry_reprocessing_handoff", extra={
                "knowledge_version_id": str(knowledge_version_id),
                "embedding_profile_id": None, "model_name": self.settings.embedding_model_name,
                "model_version": self.settings.embedding_model_revision, "batch_index": 0,
                "batch_size": 0, "duration_ms": 0, "embedded_count": 0,
                "skipped_count": 0, "device": self.provider.device, "status": "FAILED",
                "error_code": "EMBEDDING_FINGERPRINT_MISMATCH",
                "reprocessing_action": plan.action.value,
                "reprocessing_reason": plan.reason.value if plan.reason else None,
            })
            raise embedding_error("EMBEDDING_FINGERPRINT_MISMATCH", "Failed embedding attempt is not compatible with current source and profile identity.", 409,
                                  reprocessing_action=plan.action.value,
                                  reprocessing_reason=plan.reason.value if plan.reason else None)
        return await self.embed_processing_version(knowledge_version_id)
