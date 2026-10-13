"""Deterministic, stage-level planning and explicit source reprocessing."""
from __future__ import annotations

import hashlib
import json
import logging
from time import perf_counter
from types import SimpleNamespace
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApplicationError
from app.database.models import (
    Chunk, Document, KnowledgeSource, KnowledgeVersion, Lesson, ParsingRun,
    TransformationRun,
)
from app.ingestion import repository
from app.ingestion.cleaning import CLEANING_STRATEGY, CLEANING_VERSION
from app.ingestion.chunking.config import DEFAULT_CHUNKING_CONFIG
from app.ingestion.chunking.models import ChunkMetadata
from app.ingestion.chunking.strategy import content_hash as chunk_content_hash
from app.ingestion.parsing.docx import DocxParser
from app.ingestion.parsing.markdown import MarkdownParser
from app.ingestion.parsing.pdf import PdfParser
from app.ingestion.parsing.text import TxtParser
from app.ingestion.parsing_service import load_parsed_artifact
from app.ingestion.schemas import ParsedArtifactRef, TransformedArtifactRef
from app.ingestion.service import lesson_snapshot_bytes
from app.ingestion.storage import FileStorage
from app.ingestion.transformation.models import ParsedCleanedArtifactInput
from app.ingestion.transformation.service import (
    TRANSFORMATION_STRATEGY, TRANSFORMATION_VERSION, load_transformed_artifact,
)

logger = logging.getLogger(__name__)


class ReprocessingAction(str, Enum):
    NO_OP = "NO_OP"
    FROM_PARSE = "FROM_PARSE"
    FROM_TRANSFORM = "FROM_TRANSFORM"
    FROM_CHUNK = "FROM_CHUNK"
    FROM_EMBED = "FROM_EMBED"


class ReprocessingReason(str, Enum):
    SOURCE_CHANGED = "SOURCE_CHANGED"
    PARSER_CHANGED = "PARSER_CHANGED"
    CLEANING_CHANGED = "CLEANING_CHANGED"
    TRANSFORMATION_CHANGED = "TRANSFORMATION_CHANGED"
    CHUNKING_CHANGED = "CHUNKING_CHANGED"
    ARTIFACT_MISSING = "ARTIFACT_MISSING"
    ARTIFACT_INVALID = "ARTIFACT_INVALID"
    REVIEW_PENDING = "REVIEW_PENDING"
    EMBEDDING_PROFILE_CHANGED = "EMBEDDING_PROFILE_CHANGED"
    EMBEDDING_INPUT_CHANGED = "EMBEDDING_INPUT_CHANGED"


class ReprocessingPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_type: Literal["DOCUMENT", "LESSON"]
    source_id: UUID
    action: ReprocessingAction
    reason: ReprocessingReason | None = None
    source_fingerprint: str
    requires_document_review: bool = False
    reusable_parsed_ref: ParsedArtifactRef | None = None
    reusable_transformed_ref: TransformedArtifactRef | None = None
    baseline_knowledge_version_id: UUID | None = None
    baseline_transformation_run_id: UUID | None = None
    approved_artifact_run_id: UUID | None = None
    review_candidate_run_id: UUID | None = None


def _canonical_hash(value: object) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def derive_parse_fingerprint(
    source_fingerprint: str, parser_name: str, parser_version: str,
    cleaning_strategy: str, cleaning_version: str,
) -> str:
    return _canonical_hash({
        "source_fingerprint": source_fingerprint,
        "parser_name": parser_name,
        "parser_version": parser_version,
        "cleaning_strategy": cleaning_strategy,
        "cleaning_version": cleaning_version,
    })


def derive_transformation_fingerprint(
    parsed_artifact_bytes: bytes, strategy: str, version: str,
) -> str:
    return _canonical_hash({
        "parsed_artifact_sha256": hashlib.sha256(parsed_artifact_bytes).hexdigest(),
        "transformation_strategy": strategy,
        "transformation_version": version,
    })


def derive_chunk_fingerprint(
    transformed_artifact_bytes: bytes, strategy: str, version: str,
    target_chars: int, max_chars: int, overlap_chars: int,
) -> str:
    return _canonical_hash({
        "transformed_artifact_sha256": hashlib.sha256(transformed_artifact_bytes).hexdigest(),
        "chunking_strategy": strategy,
        "chunking_version": version,
        "target_chars": target_chars,
        "max_chars": max_chars,
        "overlap_chars": overlap_chars,
    })


def _desired_parser(source_type: str, file_type: str | None) -> tuple[str, str] | None:
    if source_type == "LESSON":
        return "raw_lesson_snapshot", "v1"
    parsers = {
        "PDF": PdfParser, "DOCX": DocxParser, "TXT": TxtParser, "MD": MarkdownParser,
    }
    parser = parsers.get((file_type or "").upper())
    return (parser.name, parser.version) if parser is not None else None


def _plan(
    source_type: str, source_id: UUID, source_fingerprint: str,
    action: ReprocessingAction, reason: ReprocessingReason | None, **values,
) -> ReprocessingPlan:
    values.pop("raw_storage_reference", None)
    return ReprocessingPlan(
        source_type=source_type, source_id=source_id, source_fingerprint=source_fingerprint,
        action=action, reason=reason, **values,
    )


def _safe_artifact_reason(exc: ApplicationError) -> ReprocessingReason:
    return (ReprocessingReason.ARTIFACT_MISSING if exc.code == "ARTIFACT_MISSING"
            else ReprocessingReason.ARTIFACT_INVALID)


class ReprocessingPlanner:
    """Inspect current source lineage and select only the earliest stale stage."""

    def __init__(self, session: AsyncSession, storage: FileStorage):
        self.session = session
        self.storage = storage

    async def plan_source(
        self, source_type: Literal["DOCUMENT", "LESSON"], source_id: UUID, *,
        embedding_profile_changed: bool = False,
        embedding_input_changed: bool = False,
    ) -> ReprocessingPlan:
        if source_type == "DOCUMENT":
            return await self._plan_document(
                source_id, embedding_profile_changed=embedding_profile_changed,
                embedding_input_changed=embedding_input_changed,
            )
        if source_type == "LESSON":
            return await self._plan_lesson(
                source_id, embedding_profile_changed=embedding_profile_changed,
                embedding_input_changed=embedding_input_changed,
            )
        raise ApplicationError("INVALID_SOURCE_STATE", "Unsupported reprocessing source.", status_code=409)

    async def _active_version(self, source_type: str, source_id: UUID) -> KnowledgeVersion | None:
        source = await repository.get_knowledge_source(
            self.session, source_type=source_type, source_id=source_id
        )
        if source is None:
            return None
        return await self.session.scalar(select(KnowledgeVersion).where(
            KnowledgeVersion.knowledge_source_id == source.id,
            KnowledgeVersion.status == "ACTIVE",
        ))

    async def _processing_exists(self, source_type: str, source_id: UUID) -> bool:
        source = await repository.get_knowledge_source(
            self.session, source_type=source_type, source_id=source_id
        )
        if source is None:
            return False
        return await repository.find_processing_version(self.session, source.id) is not None

    async def _read_raw(self, key: str, expected_hash: str) -> ReprocessingReason | None:
        try:
            with self.storage.open(key) as handle:
                actual = hashlib.sha256(handle.read()).hexdigest()
        except FileNotFoundError:
            return ReprocessingReason.ARTIFACT_MISSING
        except Exception:
            return ReprocessingReason.ARTIFACT_INVALID
        return None if actual == expected_hash else ReprocessingReason.ARTIFACT_INVALID

    async def _load_exact_parsed(
        self, run: dict, source_type: str, source_id: UUID, expected_hash: str,
    ) -> tuple[ParsedArtifactRef, ParsedCleanedArtifactInput] | ReprocessingReason:
        ref = ParsedArtifactRef(
            parsing_run_id=run["id"], source_type=source_type, source_id=source_id,
            storage_key=run["parsed_storage_reference"], schema_version="parsed_cleaned_artifact/v1",
        )
        try:
            artifact = await load_parsed_artifact(
                ref, session=self.session, storage=self.storage,
                expected_source_fingerprint=expected_hash,
            )
        except ApplicationError as exc:
            return _safe_artifact_reason(exc)
        return ref, artifact

    def _run_snapshot(self, run: ParsingRun | TransformationRun | None, fields: tuple[str, ...]) -> dict | None:
        if run is None:
            return None
        return {field: getattr(run, field) for field in fields}

    async def _plan_document(self, document_id: UUID, *, embedding_profile_changed: bool,
                             embedding_input_changed: bool) -> ReprocessingPlan:
        await self.session.rollback()
        document = await self.session.get(Document, document_id)
        if document is None:
            raise ApplicationError("NOT_FOUND", "Document was not found.", status_code=404)
        if document.processing_status == "PROCESSING" or await self._processing_exists("DOCUMENT", document_id):
            await self.session.rollback()
            raise ApplicationError("PROCESSING_ALREADY_IN_PROGRESS", "Document processing is already in progress.", status_code=409)

        source_fingerprint = document.content_hash or ""
        if document.review_status == "REJECTED" and document.approved_transformation_run_id is None:
            await self.session.rollback()
            raise ApplicationError("INVALID_SOURCE_STATE", "Rejected Document cannot be reprocessed.", status_code=409)
        document_values = {
            "storage_reference": document.storage_reference,
            "file_type": document.file_type,
            "review_status": document.review_status,
            "processing_status": document.processing_status,
            "review_run_id": document.review_transformation_run_id,
            "approved_run_id": document.approved_transformation_run_id,
            "raw_storage_reference": document.storage_reference,
        }
        active = await self._active_version("DOCUMENT", document_id)
        active_values = None if active is None else {
            "id": active.id,
            "transformation_run_id": active.transformation_run_id,
            "chunking_strategy": active.chunking_strategy,
            "chunking_version": active.chunking_version,
            "chunk_size": active.chunk_size,
            "chunk_max_chars": active.chunk_max_chars,
            "chunk_overlap": active.chunk_overlap,
        }

        # A matching candidate awaiting review is already the desired processing result.
        candidate_values = None
        candidate_run_id = document_values["review_run_id"]
        if (document_values["review_status"] == "PENDING"
                and document_values["processing_status"] == "PREVIEW_READY"
                and candidate_run_id is not None):
            candidate = await self.session.get(TransformationRun, candidate_run_id)
            candidate_values = self._run_snapshot(candidate, (
                "id", "source_type", "document_id", "parsing_run_id", "parsed_storage_reference",
                "transformation_strategy", "transformation_version", "status",
                "transformed_storage_reference", "error_code",
            ))

        approved_run_id = document_values["approved_run_id"]
        baseline_run_id = approved_run_id
        if baseline_run_id is None and candidate_values is not None:
            baseline_run_id = candidate_values["id"]
        baseline_run = await self.session.get(TransformationRun, baseline_run_id) if baseline_run_id else None
        baseline_values = self._run_snapshot(baseline_run, (
            "id", "source_type", "document_id", "parsing_run_id", "parsed_storage_reference",
            "transformation_strategy", "transformation_version", "status",
            "transformed_storage_reference", "error_code",
        ))
        parsing_run = await self.session.get(ParsingRun, baseline_values["parsing_run_id"]) if baseline_values else None
        parsing_values = self._run_snapshot(parsing_run, (
            "id", "source_type", "document_id", "raw_storage_reference", "raw_content_hash",
            "parser_name", "parser_version", "cleaning_strategy", "cleaning_version",
            "status", "parsed_storage_reference", "error_code",
        ))
        chunks = []
        if active_values is not None:
            chunks = (await self.session.execute(select(Chunk).where(
                Chunk.knowledge_version_id == active_values["id"]
            ).order_by(Chunk.chunk_index))).scalars().all()
            chunks = [{
                "content": row.content, "chunk_index": row.chunk_index,
                "content_type": row.content_type, "content_hash": row.content_hash,
                "metadata_json": row.metadata_json,
            } for row in chunks]
        await self.session.rollback()

        raw_reason = await self._read_raw(document_values["storage_reference"], source_fingerprint) if source_fingerprint else ReprocessingReason.ARTIFACT_INVALID
        desired_parser = _desired_parser("DOCUMENT", document_values["file_type"])
        needs_review = document_values["review_status"] != "APPROVED" or approved_run_id is None
        base_values = {
            "requires_document_review": needs_review,
            "baseline_knowledge_version_id": active_values["id"] if active_values else None,
            "baseline_transformation_run_id": baseline_run_id,
            "approved_artifact_run_id": approved_run_id,
            "review_candidate_run_id": candidate_run_id,
            "raw_storage_reference": document_values["raw_storage_reference"],
        }
        if candidate_values is not None and raw_reason is None:
            candidate_reason = await self._candidate_matches(
                candidate_values, "DOCUMENT", document_id, source_fingerprint, desired_parser
            )
            if candidate_reason is None:
                pending_plan = None
                if approved_run_id is not None:
                    pending_plan = await self._plan_from_lineage(
                        "DOCUMENT", document_id, source_fingerprint, baseline_values,
                        parsing_values, active_values, chunks, desired_parser,
                        base_values,
                        embedding_profile_changed=embedding_profile_changed,
                        embedding_input_changed=embedding_input_changed,
                    )
                    # Chunk-only drift rebuilds the last approved artifact A,
                    # never the unapproved candidate B.
                    if pending_plan.action is ReprocessingAction.FROM_CHUNK:
                        return pending_plan
                return _plan(
                    "DOCUMENT", document_id, source_fingerprint,
                    ReprocessingAction.NO_OP, ReprocessingReason.REVIEW_PENDING,
                    requires_document_review=True,
                    review_candidate_run_id=candidate_run_id,
                    baseline_knowledge_version_id=active_values["id"] if active_values else None,
                    baseline_transformation_run_id=baseline_run_id,
                    approved_artifact_run_id=approved_run_id,
                )
        if raw_reason is not None:
            return _plan("DOCUMENT", document_id, source_fingerprint,
                         ReprocessingAction.FROM_PARSE, raw_reason, **base_values)
        return await self._plan_from_lineage(
            "DOCUMENT", document_id, source_fingerprint, baseline_values, parsing_values,
            active_values, chunks, desired_parser, base_values,
            embedding_profile_changed=embedding_profile_changed,
            embedding_input_changed=embedding_input_changed,
        )

    async def _candidate_matches(self, run: dict, source_type: str, source_id: UUID,
                                 source_fingerprint: str, desired_parser) -> ReprocessingReason | None:
        if (run["source_type"] != source_type or run["document_id"] != source_id
                or run["status"] != "SUCCEEDED" or run["transformed_storage_reference"] is None
                or run["error_code"] is not None):
            return ReprocessingReason.ARTIFACT_INVALID
        parse_run = await self.session.get(ParsingRun, run["parsing_run_id"])
        parse_values = self._run_snapshot(parse_run, (
            "id", "source_type", "document_id", "parsed_storage_reference", "raw_content_hash",
            "parser_name", "parser_version", "cleaning_strategy", "cleaning_version", "status", "error_code",
        ))
        await self.session.rollback()
        if parse_values is None:
            return ReprocessingReason.ARTIFACT_MISSING
        if (run["parsing_run_id"] != parse_values["id"]
                or run["parsed_storage_reference"] != parse_values["parsed_storage_reference"]):
            return ReprocessingReason.ARTIFACT_INVALID
        if parse_values["raw_content_hash"] != source_fingerprint:
            return ReprocessingReason.SOURCE_CHANGED
        if desired_parser is None or (parse_values["parser_name"], parse_values["parser_version"]) != desired_parser:
            return ReprocessingReason.PARSER_CHANGED
        if (parse_values["cleaning_strategy"], parse_values["cleaning_version"]) != (CLEANING_STRATEGY, CLEANING_VERSION):
            return ReprocessingReason.CLEANING_CHANGED
        parsed = await self._load_exact_parsed(parse_values, source_type, source_id, source_fingerprint)
        if isinstance(parsed, ReprocessingReason):
            return parsed
        try:
            with self.storage.open(run["transformed_storage_reference"]) as handle:
                handle.read()
            ref = TransformedArtifactRef(
                transformation_run_id=run["id"], source_type=source_type, source_id=source_id,
                storage_key=run["transformed_storage_reference"], schema_version="transformed_document/v1",
            )
            load_transformed_artifact(ref, storage=self.storage)
        except FileNotFoundError:
            return ReprocessingReason.ARTIFACT_MISSING
        except Exception:
            return ReprocessingReason.ARTIFACT_INVALID
        from app.ingestion.transformation.service import TRANSFORMATION_STRATEGY, TRANSFORMATION_VERSION
        if (run["transformation_strategy"], run["transformation_version"]) != (TRANSFORMATION_STRATEGY, TRANSFORMATION_VERSION):
            return ReprocessingReason.TRANSFORMATION_CHANGED
        return None

    async def _plan_lesson(self, lesson_id: UUID, *, embedding_profile_changed: bool,
                           embedding_input_changed: bool) -> ReprocessingPlan:
        await self.session.rollback()
        lesson = await self.session.get(Lesson, lesson_id)
        if lesson is None:
            raise ApplicationError("NOT_FOUND", "Lesson was not found.", status_code=404)
        if lesson.status != "PUBLISHED":
            await self.session.rollback()
            raise ApplicationError("INVALID_SOURCE_STATE", "Only published Lessons can be maintained.", status_code=409)
        current_snapshot = await lesson_snapshot_bytes(self.session, lesson_id)
        source_fingerprint = hashlib.sha256(current_snapshot).hexdigest()
        if await self._processing_exists("LESSON", lesson_id):
            await self.session.rollback()
            raise ApplicationError("PROCESSING_ALREADY_IN_PROGRESS", "Lesson processing is already in progress.", status_code=409)

        active = await self._active_version("LESSON", lesson_id)
        active_values = None if active is None else {
            "id": active.id,
            "transformation_run_id": active.transformation_run_id,
            "chunking_strategy": active.chunking_strategy,
            "chunking_version": active.chunking_version,
            "chunk_size": active.chunk_size,
            "chunk_max_chars": active.chunk_max_chars,
            "chunk_overlap": active.chunk_overlap,
        }
        baseline = await self.session.get(
            TransformationRun, active_values["transformation_run_id"]
        ) if active_values and active_values["transformation_run_id"] else None
        baseline_values = self._run_snapshot(baseline, (
            "id", "source_type", "lesson_id", "parsing_run_id", "parsed_storage_reference",
            "transformation_strategy", "transformation_version", "status",
            "transformed_storage_reference", "error_code",
        ))
        parsing = await self.session.get(ParsingRun, baseline_values["parsing_run_id"]) if baseline_values else None
        parsing_values = self._run_snapshot(parsing, (
            "id", "source_type", "lesson_id", "raw_storage_reference", "raw_content_hash",
            "parser_name", "parser_version", "cleaning_strategy", "cleaning_version",
            "status", "parsed_storage_reference", "error_code",
        ))
        chunks = []
        if active_values is not None:
            rows = (await self.session.execute(select(Chunk).where(
                Chunk.knowledge_version_id == active_values["id"]
            ).order_by(Chunk.chunk_index))).scalars().all()
            chunks = [{
                "content": row.content, "chunk_index": row.chunk_index,
                "content_type": row.content_type, "content_hash": row.content_hash,
                "metadata_json": row.metadata_json,
            } for row in rows]
        await self.session.rollback()
        return await self._plan_from_lineage(
            "LESSON", lesson_id, source_fingerprint, baseline_values, parsing_values,
            active_values, chunks, _desired_parser("LESSON", None),
            {"requires_document_review": False,
             "baseline_knowledge_version_id": active_values["id"] if active_values else None,
             "baseline_transformation_run_id": baseline_values["id"] if baseline_values else None},
            embedding_profile_changed=embedding_profile_changed,
            embedding_input_changed=embedding_input_changed,
        )

    async def _plan_from_lineage(
        self, source_type: Literal["DOCUMENT", "LESSON"], source_id: UUID,
        source_fingerprint: str, transform: dict | None, parsing: dict | None,
        active: dict | None, chunks: list[dict], desired_parser,
        base_values: dict, *, embedding_profile_changed: bool,
        embedding_input_changed: bool,
    ) -> ReprocessingPlan:
        def stale(action, reason, *, parsed_ref=None, transformed_ref=None):
            values = dict(base_values)
            if source_type == "DOCUMENT" and action in {
                ReprocessingAction.FROM_PARSE, ReprocessingAction.FROM_TRANSFORM,
            }:
                values["requires_document_review"] = True
            elif source_type == "DOCUMENT":
                values["requires_document_review"] = False
            values["reusable_parsed_ref"] = parsed_ref
            values["reusable_transformed_ref"] = transformed_ref
            return _plan(source_type, source_id, source_fingerprint, action, reason, **values)

        if transform is None or parsing is None:
            return stale(ReprocessingAction.FROM_PARSE, ReprocessingReason.ARTIFACT_MISSING)
        source_field = "document_id" if source_type == "DOCUMENT" else "lesson_id"
        if (transform["source_type"] != source_type or transform[source_field] != source_id
                or parsing["source_type"] != source_type or parsing[source_field] != source_id
                or transform["parsing_run_id"] != parsing["id"]):
            return stale(ReprocessingAction.FROM_PARSE, ReprocessingReason.ARTIFACT_INVALID)
        if parsing["raw_content_hash"] != source_fingerprint:
            return stale(ReprocessingAction.FROM_PARSE, ReprocessingReason.SOURCE_CHANGED)

        if source_type == "DOCUMENT":
            raw_key = base_values.get("raw_storage_reference")
            if parsing["raw_storage_reference"] != raw_key:
                return stale(ReprocessingAction.FROM_PARSE, ReprocessingReason.ARTIFACT_INVALID)
        else:
            raw_key = parsing["raw_storage_reference"]
        raw_reason = await self._read_raw(raw_key, source_fingerprint)
        if raw_reason is not None:
            return stale(ReprocessingAction.FROM_PARSE, raw_reason)
        if desired_parser is None:
            return stale(ReprocessingAction.FROM_PARSE, ReprocessingReason.PARSER_CHANGED)
        desired_parse_fingerprint = derive_parse_fingerprint(
            source_fingerprint, desired_parser[0], desired_parser[1],
            CLEANING_STRATEGY, CLEANING_VERSION,
        )
        baseline_parse_fingerprint = derive_parse_fingerprint(
            parsing["raw_content_hash"], parsing["parser_name"], parsing["parser_version"],
            parsing["cleaning_strategy"], parsing["cleaning_version"],
        )
        if baseline_parse_fingerprint != desired_parse_fingerprint:
            if (parsing["parser_name"], parsing["parser_version"]) != desired_parser:
                return stale(ReprocessingAction.FROM_PARSE, ReprocessingReason.PARSER_CHANGED)
            if (parsing["cleaning_strategy"], parsing["cleaning_version"]) != (CLEANING_STRATEGY, CLEANING_VERSION):
                return stale(ReprocessingAction.FROM_PARSE, ReprocessingReason.CLEANING_CHANGED)
            return stale(ReprocessingAction.FROM_PARSE, ReprocessingReason.SOURCE_CHANGED)
        if parsing["status"] != "SUCCEEDED" or parsing["error_code"] is not None:
            return stale(ReprocessingAction.FROM_PARSE, ReprocessingReason.ARTIFACT_INVALID)
        if parsing["parsed_storage_reference"] is None:
            return stale(ReprocessingAction.FROM_PARSE, ReprocessingReason.ARTIFACT_MISSING)

        parsed_result = await self._load_exact_parsed(
            parsing, source_type, source_id, source_fingerprint
        )
        if isinstance(parsed_result, ReprocessingReason):
            return stale(ReprocessingAction.FROM_PARSE, parsed_result)
        parsed_ref, parsed_artifact = parsed_result
        try:
            with self.storage.open(parsed_ref.storage_key) as handle:
                parsed_bytes = handle.read()
        except FileNotFoundError:
            return stale(ReprocessingAction.FROM_PARSE, ReprocessingReason.ARTIFACT_MISSING)
        except Exception:
            return stale(ReprocessingAction.FROM_PARSE, ReprocessingReason.ARTIFACT_INVALID)
        if (transform["parsed_storage_reference"] != parsed_ref.storage_key
                or transform["parsing_run_id"] != parsed_ref.parsing_run_id):
            return stale(
                ReprocessingAction.FROM_TRANSFORM, ReprocessingReason.ARTIFACT_INVALID,
                parsed_ref=parsed_ref,
            )

        baseline_transform_fingerprint = derive_transformation_fingerprint(
            parsed_bytes, transform["transformation_strategy"], transform["transformation_version"]
        )
        desired_transform_fingerprint = derive_transformation_fingerprint(
            parsed_bytes, TRANSFORMATION_STRATEGY, TRANSFORMATION_VERSION
        )
        if baseline_transform_fingerprint != desired_transform_fingerprint:
            return stale(
                ReprocessingAction.FROM_TRANSFORM,
                ReprocessingReason.TRANSFORMATION_CHANGED,
                parsed_ref=parsed_ref,
            )
        if transform["status"] != "SUCCEEDED" or transform["error_code"] is not None:
            return stale(
                ReprocessingAction.FROM_TRANSFORM, ReprocessingReason.ARTIFACT_INVALID,
                parsed_ref=parsed_ref,
            )
        if transform["transformed_storage_reference"] is None:
            return stale(
                ReprocessingAction.FROM_TRANSFORM, ReprocessingReason.ARTIFACT_MISSING,
                parsed_ref=parsed_ref,
            )
        transformed_ref = TransformedArtifactRef(
            transformation_run_id=transform["id"], source_type=source_type,
            source_id=source_id, storage_key=transform["transformed_storage_reference"],
            schema_version="transformed_document/v1",
        )
        try:
            with self.storage.open(transformed_ref.storage_key) as handle:
                transformed_bytes = handle.read()
        except FileNotFoundError:
            return stale(
                ReprocessingAction.FROM_TRANSFORM, ReprocessingReason.ARTIFACT_MISSING,
                parsed_ref=parsed_ref,
            )
        except Exception:
            return stale(
                ReprocessingAction.FROM_TRANSFORM, ReprocessingReason.ARTIFACT_INVALID,
                parsed_ref=parsed_ref,
            )
        try:
            load_transformed_artifact(transformed_ref, storage=self.storage)
        except ApplicationError:
            return stale(
                ReprocessingAction.FROM_TRANSFORM, ReprocessingReason.ARTIFACT_INVALID,
                parsed_ref=parsed_ref,
            )

        # A valid Chunk set is reusable only when its persisted build points
        # to this exact baseline TransformationRun. Chunk integrity alone
        # cannot prove which approved representation produced those rows.
        if active is not None and active["transformation_run_id"] != transform["id"]:
            return stale(
                ReprocessingAction.FROM_CHUNK, ReprocessingReason.ARTIFACT_INVALID,
                parsed_ref=parsed_ref, transformed_ref=transformed_ref,
            )

        config = DEFAULT_CHUNKING_CONFIG
        expected_config = (
            config.strategy, config.version, config.target_chars,
            config.max_chars, config.overlap_chars,
        )
        if active is None:
            return stale(
                ReprocessingAction.FROM_CHUNK, ReprocessingReason.CHUNKING_CHANGED,
                parsed_ref=parsed_ref, transformed_ref=transformed_ref,
            )
        actual_config = (
            active["chunking_strategy"], active["chunking_version"],
            active["chunk_size"], active["chunk_max_chars"], active["chunk_overlap"],
        )
        if any(value is None for value in actual_config):
            return stale(
                ReprocessingAction.FROM_CHUNK, ReprocessingReason.ARTIFACT_INVALID,
                parsed_ref=parsed_ref, transformed_ref=transformed_ref,
            )
        baseline_chunk_fingerprint = derive_chunk_fingerprint(
            transformed_bytes, actual_config[0], actual_config[1], actual_config[2],
            actual_config[3], actual_config[4],
        )
        desired_chunk_fingerprint = derive_chunk_fingerprint(
            transformed_bytes, expected_config[0], expected_config[1], expected_config[2],
            expected_config[3], expected_config[4],
        )
        if baseline_chunk_fingerprint != desired_chunk_fingerprint:
            return stale(
                ReprocessingAction.FROM_CHUNK, ReprocessingReason.CHUNKING_CHANGED,
                parsed_ref=parsed_ref, transformed_ref=transformed_ref,
            )
        if actual_config != expected_config:
            return stale(
                ReprocessingAction.FROM_CHUNK, ReprocessingReason.CHUNKING_CHANGED,
                parsed_ref=parsed_ref, transformed_ref=transformed_ref,
            )
        chunk_reason = self._validate_chunks(chunks)
        if chunk_reason is not None:
            return stale(
                ReprocessingAction.FROM_CHUNK, chunk_reason,
                parsed_ref=parsed_ref, transformed_ref=transformed_ref,
            )
        if embedding_profile_changed:
            return stale(ReprocessingAction.FROM_EMBED, ReprocessingReason.EMBEDDING_PROFILE_CHANGED,
                         parsed_ref=parsed_ref, transformed_ref=transformed_ref)
        if embedding_input_changed:
            return stale(ReprocessingAction.FROM_EMBED, ReprocessingReason.EMBEDDING_INPUT_CHANGED,
                         parsed_ref=parsed_ref, transformed_ref=transformed_ref)
        values = dict(base_values)
        values["reusable_parsed_ref"] = parsed_ref
        values["reusable_transformed_ref"] = transformed_ref
        return _plan(source_type, source_id, source_fingerprint,
                     ReprocessingAction.NO_OP, None, **values)

    @staticmethod
    def _validate_chunks(chunks: list[dict]) -> ReprocessingReason | None:
        if not chunks:
            return ReprocessingReason.ARTIFACT_MISSING
        try:
            for expected_index, chunk in enumerate(chunks):
                if chunk["chunk_index"] != expected_index or not chunk["content_hash"]:
                    return ReprocessingReason.ARTIFACT_INVALID
                actual_hash = chunk_content_hash(chunk["content"], chunk["content_type"])
                if actual_hash != chunk["content_hash"]:
                    return ReprocessingReason.ARTIFACT_INVALID
                ChunkMetadata.model_validate(chunk["metadata_json"])
        except Exception:
            return ReprocessingReason.ARTIFACT_INVALID
        return None


class ReprocessingService:
    """Explicit internal maintenance boundary; execution always replans first."""

    def __init__(self, session: AsyncSession, storage: FileStorage):
        self.session = session
        self.storage = storage
        self.planner = ReprocessingPlanner(session, storage)

    async def plan_source(
        self, source_type: Literal["DOCUMENT", "LESSON"], source_id: UUID, *,
        embedding_profile_changed: bool = False,
        embedding_input_changed: bool = False,
    ) -> ReprocessingPlan:
        return await self.planner.plan_source(
            source_type, source_id,
            embedding_profile_changed=embedding_profile_changed,
            embedding_input_changed=embedding_input_changed,
        )

    async def reprocess_source(
        self, source_type: Literal["DOCUMENT", "LESSON"], source_id: UUID,
    ) -> ReprocessingPlan | dict:
        plan = await self.plan_source(source_type, source_id)
        logger.info("reprocessing_plan", extra={
            "source_id": str(source_id), "source_type": source_type,
            "action": plan.action.value,
            "reason": plan.reason.value if plan.reason else None,
        })
        if plan.action in {ReprocessingAction.NO_OP, ReprocessingAction.FROM_EMBED}:
            return plan
        if source_type == "DOCUMENT":
            if plan.action is ReprocessingAction.FROM_CHUNK:
                return await self._rebuild_document_chunks(plan)
            return await self._build_document_candidate(plan)
        return await self._rebuild_lesson(plan)

    async def _claim_document_candidate(self, plan: ReprocessingPlan) -> Document:
        await self.session.rollback()
        async with self.session.begin():
            document = await repository.get_document_for_update(self.session, plan.source_id)
            if document is None:
                raise ApplicationError("NOT_FOUND", "Document was not found.", status_code=404)
            if document.processing_status == "PROCESSING":
                raise ApplicationError("PROCESSING_ALREADY_IN_PROGRESS", "Document processing is already in progress.", status_code=409)
            if (document.content_hash or "") != plan.source_fingerprint:
                raise ApplicationError("REPROCESSING_STATE_CHANGED", "Document source changed during planning.", status_code=409)
            if (document.approved_transformation_run_id != plan.approved_artifact_run_id
                    or document.review_transformation_run_id != plan.review_candidate_run_id):
                raise ApplicationError("REPROCESSING_STATE_CHANGED", "Document review identity changed during planning.", status_code=409)
            if document.review_status == "REJECTED" and document.approved_transformation_run_id is None:
                raise ApplicationError("INVALID_SOURCE_STATE", "Rejected Document cannot be reprocessed.", status_code=409)
            if document.review_status not in {"PENDING", "APPROVED"}:
                raise ApplicationError("INVALID_SOURCE_STATE", "Document cannot be reprocessed in its current state.", status_code=409)
            # Any previous approval remains authoritative while a new candidate is generated.
            document.review_status = "PENDING"
            document.processing_status = "PROCESSING"
            document.review_transformation_run_id = None
        await self.session.refresh(document)
        raw_values = {
            "id": document.id, "storage_reference": document.storage_reference,
            "file_type": document.file_type, "mime_type": document.mime_type,
            "file_size_bytes": document.file_size_bytes,
            "content_hash": document.content_hash,
        }
        await self.session.rollback()
        return SimpleNamespace(**raw_values)

    async def _build_document_candidate(self, plan: ReprocessingPlan) -> dict:
        from app.ingestion import orchestrator as orchestration
        try:
            document = await self._claim_document_candidate(plan)
            if plan.action is ReprocessingAction.FROM_PARSE:
                try:
                    raw_started = perf_counter()
                    raw = orchestration.raw_service.document_raw_artifact_ref(document)
                except Exception as exc:
                    await orchestration._mark_document_failed(self.session, plan.source_id)
                    orchestration._log(
                        plan.source_id, "DOCUMENT", "raw", "FAILED", raw_started,
                        error_code="INGESTION_PROCESSING_FAILED",
                    )
                    raise ApplicationError(
                        "INGESTION_PROCESSING_FAILED", "Document processing could not be completed.",
                        status_code=500,
                    ) from exc
                parsed = await orchestration._stage(
                    orchestration.parse_raw_artifact(
                        raw, session=self.session, storage=self.storage
                    ),
                    source_id=plan.source_id, source_type="DOCUMENT", stage="parse",
                )
            else:
                if plan.reusable_parsed_ref is None:
                    raise ApplicationError("ARTIFACT_INVALID", "Parsed artifact lineage is unavailable.", status_code=409)
                parsed = plan.reusable_parsed_ref
                await load_parsed_artifact(
                    parsed, session=self.session, storage=self.storage,
                    expected_source_fingerprint=plan.source_fingerprint,
                )
            transformed = await orchestration._stage(
                orchestration.transform_parsed_artifact(
                    parsed, session=self.session, storage=self.storage
                ),
                source_id=plan.source_id, source_type="DOCUMENT", stage="transform",
            )
            await self.session.rollback()
            async with self.session.begin():
                current = await repository.get_document(self.session, plan.source_id)
                if (current is None or current.review_status != "PENDING"
                        or current.processing_status != "PREVIEW_READY"
                        or current.review_transformation_run_id != transformed.transformation_run_id
                        or current.approved_transformation_run_id != plan.approved_artifact_run_id):
                    raise ApplicationError("INGESTION_PROCESSING_FAILED", "Document processing could not be completed.", status_code=500)
            return {
                "source_id": plan.source_id, "action": plan.action.value,
                "review_status": "PENDING", "processing_status": "PREVIEW_READY",
                "review_candidate_run_id": transformed.transformation_run_id,
                "approved_transformation_run_id": plan.approved_artifact_run_id,
            }
        except ApplicationError as exc:
            if exc.code not in {"NOT_FOUND", "PROCESSING_ALREADY_IN_PROGRESS", "REPROCESSING_STATE_CHANGED", "INVALID_SOURCE_STATE"}:
                await orchestration._mark_document_failed(self.session, plan.source_id)
                if exc.code not in {"INGESTION_PROCESSING_FAILED"}:
                    raise ApplicationError(
                        "INGESTION_PROCESSING_FAILED", "Document processing could not be completed.", status_code=500
                    ) from exc
            raise
        except Exception as exc:
            await orchestration._mark_document_failed(self.session, plan.source_id)
            raise ApplicationError(
                "INGESTION_PROCESSING_FAILED", "Document processing could not be completed.", status_code=500
            ) from exc

    async def _rebuild_document_chunks(self, plan: ReprocessingPlan) -> dict:
        from app.ingestion import orchestrator as orchestration
        ref = plan.reusable_transformed_ref
        if ref is None or ref.transformation_run_id != plan.approved_artifact_run_id:
            raise ApplicationError("ARTIFACT_INVALID", "Approved transformed artifact is unavailable.", status_code=409)
        version_id = await orchestration._allocate_document_version(
            self.session, plan.source_id, transformation_run_id=ref.transformation_run_id,
            expected_source_fingerprint=plan.source_fingerprint,
        )
        await orchestration._build_knowledge(
            self.session, self.storage, source_id=plan.source_id, source_type="DOCUMENT",
            version_id=version_id, artifact=ref,
        )
        return {"source_id": plan.source_id, "action": plan.action.value,
                "knowledge_version_id": version_id, "transformation_run_id": ref.transformation_run_id}

    async def _rebuild_lesson(self, plan: ReprocessingPlan) -> dict:
        from app.ingestion import orchestrator as orchestration
        transform_id = (plan.reusable_transformed_ref.transformation_run_id
                        if plan.action is ReprocessingAction.FROM_CHUNK
                        and plan.reusable_transformed_ref is not None else None)
        version_id = await orchestration._allocate_lesson_version(
            self.session, plan.source_id,
            expected_source_fingerprint=plan.source_fingerprint,
            expected_active_version_id=plan.baseline_knowledge_version_id,
            expected_transformation_run_id=plan.baseline_transformation_run_id,
            revalidate_baseline=True,
            transformation_run_id=transform_id,
        )
        try:
            if plan.action is ReprocessingAction.FROM_PARSE:
                raw = await orchestration._stage(
                    orchestration.create_lesson_snapshot(self.session, plan.source_id, self.storage),
                    source_id=plan.source_id, source_type="LESSON", stage="raw", version_id=version_id,
                )
                if raw.content_hash != plan.source_fingerprint:
                    raise ApplicationError("REPROCESSING_STATE_CHANGED", "Lesson content changed during execution.", status_code=409)
                parsed = await orchestration._stage(
                    orchestration.parse_raw_artifact(raw, session=self.session, storage=self.storage),
                    source_id=plan.source_id, source_type="LESSON", stage="parse", version_id=version_id,
                )
            elif plan.action is ReprocessingAction.FROM_TRANSFORM:
                if plan.reusable_parsed_ref is None:
                    raise ApplicationError("ARTIFACT_INVALID", "Parsed artifact lineage is unavailable.", status_code=409)
                parsed = plan.reusable_parsed_ref
                await load_parsed_artifact(
                    parsed, session=self.session, storage=self.storage,
                    expected_source_fingerprint=plan.source_fingerprint,
                )
            else:
                ref = plan.reusable_transformed_ref
                if ref is None:
                    raise ApplicationError("ARTIFACT_INVALID", "Transformed artifact lineage is unavailable.", status_code=409)
                if transform_id != ref.transformation_run_id:
                    raise ApplicationError("REPROCESSING_STATE_CHANGED", "Lesson transform lineage changed during planning.", status_code=409)
                await orchestration._build_knowledge(
                    self.session, self.storage, source_id=plan.source_id, source_type="LESSON",
                    version_id=version_id, artifact=ref,
                )
                return {"source_id": plan.source_id, "action": plan.action.value,
                        "knowledge_version_id": version_id, "transformation_run_id": transform_id}

            transformed = await orchestration._stage(
                orchestration.transform_parsed_artifact(
                    parsed, session=self.session, storage=self.storage
                ), source_id=plan.source_id, source_type="LESSON", stage="transform",
                version_id=version_id,
            )
            await self.session.rollback()
            async with self.session.begin():
                await repository.set_knowledge_version_transformation_run(
                    self.session, version_id, transformed.transformation_run_id
                )
            await orchestration._build_knowledge(
                self.session, self.storage, source_id=plan.source_id, source_type="LESSON",
                version_id=version_id, artifact=transformed,
            )
            return {"source_id": plan.source_id, "action": plan.action.value,
                    "knowledge_version_id": version_id,
                    "transformation_run_id": transformed.transformation_run_id}
        except ApplicationError as exc:
            await orchestration._mark_version_failed(
                self.session, version_id, source_id=plan.source_id, source_type="LESSON"
            )
            if exc.code == "KNOWLEDGE_BUILD_FAILED":
                raise
            if exc.code == "REPROCESSING_STATE_CHANGED":
                raise
            raise ApplicationError("KNOWLEDGE_BUILD_FAILED", "Knowledge build could not be completed.", status_code=500) from exc
        except Exception as exc:
            await orchestration._mark_version_failed(
                self.session, version_id, source_id=plan.source_id, source_type="LESSON"
            )
            raise ApplicationError("KNOWLEDGE_BUILD_FAILED", "Knowledge build could not be completed.", status_code=500) from exc
