from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings.service import EmbeddingService
from app.ai.vector_storage.service import VectorStorageService
from app.core.config import Settings
from app.database.models import (
    Chunk, Document, Embedding, EmbeddingProfile, Grammar, HSKLevel,
    KnowledgeSource, KnowledgeVersion, Lesson, LessonGrammar, LessonVocabulary,
    ParsingRun, TransformationRun, User, Vocabulary,
)
from app.ingestion.orchestrator import IngestionOrchestrator
from app.ingestion.storage import LocalFileStorage
from app.ingestion.orchestrator import IngestionOrchestrator
from app.ingestion.transformation.models import (
    CanonicalBlock, DocumentProvenance, TextBlockLocator, TransformedDocument,
)


FIXTURE_ROOT = Path(__file__).resolve().parents[4] / "evaluation/fixtures/lesson_chat_rag/v0.1.0"
EXPECTED_HASHES = {
    "manifest.json": "6a02b5c6d43063dcaa381586628cf9b7b3e68945025872039947f02c848b3276",
    "sources/internal-kb-beginner-notes.json": "cef9b36e2f4a426ee49146eccae1f1df503f7494ae791144b5c01e7b1c610c0f",
    "sources/lesson-01-greetings.json": "64bc5a7252d14b28e72ea34934df0411f48584ab2c65b3b2c5eaf049aad6bf3f",
    "sources/lesson-02-numbers-age.json": "765d0ab8c7a05b010fc917538bb690add88622800e58f0aad6b437f052b31a6d",
    "sources/lesson-03-family.json": "797a912041b0f36417eb6c140d5869b1029205e9b3e6987825ca7808dfab94c0",
}
LESSON_IDS = (
    "fixture.lesson.hsk1.01.greetings",
    "fixture.lesson.hsk1.02.numbers-age",
    "fixture.lesson.hsk1.03.family",
)
INTERNAL_ID = "fixture.internal-kb.hsk1.beginner-notes"
FIXTURE_MARKER = "step73-fixture-pack=lesson_chat_rag/0.1.0;source_id="
EVALUATION_LESSON_NUMBER_BASE = 970000


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_fixture_pack(root: Path = FIXTURE_ROOT) -> tuple[dict, list[dict], dict]:
    manifest_bytes = (root / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    if (manifest.get("fixture_pack"), manifest.get("fixture_pack_version"), manifest.get("status")) != (
        "lesson_chat_rag", "0.1.0", "ACCEPTED_FOR_EVALUATION_FIXTURE",
    ):
        raise ValueError("Fixture pack identity/status is not accepted")
    if (manifest.get("source_count"), manifest.get("lesson_source_count"),
            manifest.get("internal_kb_source_count"), manifest.get("educational_block_count"),
            manifest.get("trusted_external_source_count")) != (4, 3, 1, 26, 0):
        raise ValueError("Fixture pack source/block counts do not match the frozen contract")
    source_rows, blocks, per_source_hash = [], [], {}
    seen: set[str] = set()
    for item in manifest["sources"]:
        path = item["path"]
        raw = (root / path).read_bytes()
        digest = _sha(raw)
        if path in EXPECTED_HASHES and EXPECTED_HASHES[path] != digest:
            raise ValueError(f"Accepted fixture semantic file drifted: {path}")
        source = json.loads(raw)
        if source.get("source_id") != item["source_id"] or source.get("status") != "ACCEPTED_FOR_EVALUATION_FIXTURE":
            raise ValueError(f"Fixture source identity/status mismatch: {path}")
        if len(source.get("blocks", [])) != item["block_count"]:
            raise ValueError(f"Fixture block count mismatch: {path}")
        for block in source["blocks"]:
            if block.get("source_id") != item["source_id"] or not all(
                isinstance(block.get(key), str) and block[key] for key in
                ("block_id", "stable_locator", "source_locator", "content_type")
            ):
                raise ValueError(f"Malformed fixture block in {path}")
            if block["stable_locator"] in seen:
                raise ValueError("Fixture stable locators are not unique")
            seen.add(block["stable_locator"])
            blocks.append({**block, "source_kind": item["kind"], "source_path": path,
                           "lesson_locator": source.get("lesson_locator"),
                           "source_title": source.get("lesson_title") or source.get("source_title") or "Beginner notes"})
        source_rows.append(source)
        per_source_hash[item["source_id"]] = digest
    if len(seen) != 26 or {source["source_id"] for source in source_rows} != {*LESSON_IDS, INTERNAL_ID}:
        raise ValueError("Fixture locator/source identity set differs from the approved pack")
    aggregate = hashlib.sha256()
    for relative, digest in sorted({"manifest.json": _sha(manifest_bytes), **{
        item["path"]: per_source_hash[item["source_id"]] for item in manifest["sources"]
    }}.items()):
        aggregate.update(relative.encode("utf-8") + b"\0" + digest.encode("ascii") + b"\n")
    hashes = {"fixture_manifest_sha256": _sha(manifest_bytes), "per_source_sha256": per_source_hash,
              "aggregate_fixture_content_sha256": aggregate.hexdigest()}
    return manifest, blocks, hashes


def assert_evaluation_database(settings: Settings, actual_database: str) -> dict:
    if settings.app_env != "test":
        raise RuntimeError("Fixture bootstrap requires APP_ENV=test")
    target = settings.effective_database_url
    from sqlalchemy.engine import make_url
    target_url = make_url(target)
    if not target_url.database or not any(token in target_url.database.lower() for token in ("test", "eval")):
        raise RuntimeError("Fixture bootstrap target name is not explicitly test/evaluation isolated")
    if settings.database_url and settings._database_identity(settings.database_url) == settings._database_identity(target):
        raise RuntimeError("Fixture bootstrap target matches normal DATABASE_URL")
    if actual_database != target_url.database:
        raise RuntimeError("Connected database identity differs from the configured test/evaluation target")
    return {"environment": settings.app_env, "database_name": actual_database,
            "database_isolation": "DEDICATED_TEST_EVALUATION", "normal_database_configured": bool(settings.database_url)}


def _json_bytes(value: dict) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _block_text(block: dict) -> str:
    content = block["content"]
    if not isinstance(content, dict):
        return str(content)
    return "\n".join(f"{key}: {value}" for key, value in content.items() if value is not None)


def _fixture_locator_metadata(chunk_metadata: dict, source_id: str, kind: str,
                               fixture_blocks: list[dict]) -> list[str]:
    found: list[str] = []
    ranges = chunk_metadata.get("source_ranges") or []
    by_order = {}
    if kind == "LESSON":
        by_order = _lesson_locator_by_order(fixture_blocks)
        for source_range in ranges:
            locator = source_range.get("source_locator", {})
            key = (locator.get("section"), locator.get("order_index"))
            if key in by_order:
                found.append(by_order[key]["stable_locator"])
    else:
        for source_range in ranges:
            locator = source_range.get("source_locator", {})
            if locator.get("kind") == "TEXT_BLOCK":
                index = locator.get("block_index")
                if isinstance(index, int) and 0 <= index < len(fixture_blocks):
                    found.append(fixture_blocks[index]["stable_locator"])
    return sorted(set(found))


def _fixture_provenance_records(chunk_metadata: dict, kind: str, fixture_blocks: list[dict]) -> list[dict]:
    selected = []
    by_order = {}
    if kind == "LESSON":
        by_order = _lesson_locator_by_order(fixture_blocks)
        for source_range in chunk_metadata.get("source_ranges") or []:
            locator = source_range.get("source_locator", {})
            block = by_order.get((locator.get("section"), locator.get("order_index")))
            if block:
                selected.append(block)
    else:
        by_index = {i: block for i, block in enumerate(fixture_blocks)}
        for source_range in chunk_metadata.get("source_ranges") or []:
            locator = source_range.get("source_locator", {})
            block = by_index.get(locator.get("block_index")) if locator.get("kind") == "TEXT_BLOCK" else None
            if block:
                selected.append(block)
    by_stable = {item["stable_locator"]: item for item in selected}
    return [by_stable[key] for key in sorted(by_stable)]


def _lesson_locator_by_order(fixture_blocks: list[dict]) -> dict[tuple[str, int], dict]:
    result = {}
    vocabulary_order = 0
    for block in (row for row in fixture_blocks if row["content_type"] == "VOCABULARY"):
        count = len(block["content"].get("items", [])) or 1
        for _ in range(count):
            result[("VOCABULARY", vocabulary_order)] = block
            vocabulary_order += 1
    for order, block in enumerate(row for row in fixture_blocks if row["content_type"] == "GRAMMAR"):
        result[("GRAMMAR", order)] = block
    general = [row for row in fixture_blocks if row["content_type"] == "LESSON_GENERAL"]
    if general:
        result[("LESSON", None)] = general[0]
    return result


def _lesson_description(source: dict) -> str | None:
    general = next((block for block in source["blocks"] if block["content_type"] == "LESSON_GENERAL"), None)
    if general is None:
        return None
    content = general["content"]
    examples = content.get("examples", []) if isinstance(content, dict) else []
    if not examples or not all(isinstance(item, dict) and all(
        isinstance(item.get(key), str) and item[key].strip() for key in ("chinese", "pinyin", "vietnamese")
    ) for item in examples):
        raise ValueError("LESSON_GENERAL fixture block has no valid source-derived examples")
    return "\n\n".join("Chinese: {chinese}\nPinyin: {pinyin}\nVietnamese: {vietnamese}".format(**item)
                         for item in examples)


def _bootstrap_identity(hashes: dict, settings: Settings) -> tuple[str, dict]:
    identity = {
        "fixture_pack": "lesson_chat_rag", "fixture_pack_version": "0.1.0",
        "aggregate_fixture_content_sha256": hashes["aggregate_fixture_content_sha256"],
        "source_adapter": "step73_accepted_fixture_adapter/v1",
        "transformation_identity": "canonical_document/v1;raw_lesson_snapshot/v1",
        "chunking_identity": "structure_aware/v1;target=1200;max=1800;overlap=150",
        "embedding_identity": {
            "provider": "LOCAL", "provider_version": "sentence-transformers/6.1.0",
            "model": settings.embedding_model_name, "revision": settings.embedding_model_revision,
            "dimensions": 1024, "input_version": settings.embedding_input_version,
            "normalize_embeddings": settings.embedding_normalize,
        },
    }
    encoded = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest(), identity


async def _ensure_hsk(session: AsyncSession) -> HSKLevel:
    row = await session.scalar(select(HSKLevel).where(HSKLevel.level_number == 1))
    if row is None:
        row = HSKLevel(level_number=1, title="HSK 1 (synthetic evaluation identity)",
                       description="Evaluation fixture identity only; not official syllabus certification.", order_index=1)
        session.add(row)
        await session.flush()
    return row


async def _lesson_identities(session: AsyncSession, sources: list[dict]) -> dict[str, UUID]:
    hsk = await _ensure_hsk(session)
    result = {}
    for source in sources:
        if source.get("source_kind") != "LESSON":
            continue
        identity = source["source_id"]
        locator = source["lesson_locator"]
        number = EVALUATION_LESSON_NUMBER_BASE + int(locator.split(":")[3])
        title = source["lesson_title"]
        description = _lesson_description(source)
        lesson = await session.scalar(select(Lesson).where(
            Lesson.hsk_level_id == hsk.id, Lesson.lesson_number == number,
        ))
        marker = FIXTURE_MARKER + identity
        if lesson is None:
            lesson = Lesson(hsk_level_id=hsk.id, lesson_number=number, title=title,
                            description=description, status="PUBLISHED", published_at=datetime.now(UTC))
            session.add(lesson)
            await session.flush()
        elif (lesson.title != title or lesson.status != "PUBLISHED"
              or lesson.lesson_number != number or lesson.description != description):
            raise RuntimeError(f"Conflicting non-fixture Lesson identity at {locator}")
        result[identity] = lesson.id
    return result


async def _materialize_lesson(session: AsyncSession, source: dict, lesson_id: UUID) -> None:
    blocks = source["blocks"]
    order = 0
    for block in (b for b in blocks if b["content_type"] == "VOCABULARY"):
        content = block["content"]
        rows = content.get("items") or [content]
        for data in rows:
            row = await session.scalar(select(Vocabulary).where(
                Vocabulary.hanzi == data["chinese"], Vocabulary.pinyin == data["pinyin"],
                Vocabulary.vietnamese_meaning == data["vietnamese"],
            ))
            if row is None:
                row = Vocabulary(hanzi=data["chinese"], pinyin=data["pinyin"],
                                 vietnamese_meaning=data["vietnamese"], part_of_speech=None)
                session.add(row)
                await session.flush()
            link = await session.scalar(select(LessonVocabulary).where(
                LessonVocabulary.lesson_id == lesson_id, LessonVocabulary.order_index == order,
            ))
            note = " | ".join(x for x in (content.get("example_pinyin"), content.get("example_vietnamese")) if x)
            if link is None:
                session.add(LessonVocabulary(lesson_id=lesson_id, vocabulary_id=row.id,
                                             order_index=order, note=note or None, example=content.get("example")))
            elif link.vocabulary_id != row.id:
                raise RuntimeError("Fixture Lesson vocabulary identity conflicts with an existing row")
            order += 1
    for order, block in enumerate(b for b in blocks if b["content_type"] == "GRAMMAR"):
        data = block["content"]
        grammar_name = data["pattern"]
        grammar = await session.scalar(select(Grammar).where(Grammar.name == grammar_name))
        if grammar is None:
            grammar = Grammar(name=grammar_name, structure=data.get("pattern"),
                              explanation=data.get("vietnamese_explanation", ""),
                              usage=data.get("pinyin"))
            session.add(grammar)
            await session.flush()
        link = await session.scalar(select(LessonGrammar).where(
            LessonGrammar.lesson_id == lesson_id, LessonGrammar.order_index == order,
        ))
        extra_note = " | ".join(x for x in (data.get("example_pinyin"), data.get("example_vietnamese")) if x)
        if link is None:
            session.add(LessonGrammar(lesson_id=lesson_id, grammar_id=grammar.id,
                                      order_index=order, note=extra_note or None,
                                      example=data.get("example")))
        elif link.grammar_id != grammar.id:
            raise RuntimeError("Fixture Lesson grammar identity conflicts with an existing row")
    await session.flush()


def _internal_document_artifact(source: dict, document_id: UUID) -> TransformedDocument:
    blocks = []
    for index, block in enumerate(source["blocks"]):
        blocks.append(CanonicalBlock(
            order=index, content_type="DOCUMENT_TEXT", block_kind="PARAGRAPH",
            text=_block_text(block), section_path=["Accepted evaluation fixture"],
            source_locator=TextBlockLocator(kind="TEXT_BLOCK", block_index=index),
        ))
    return TransformedDocument(
        schema_version="transformed_document/v1", source_type="DOCUMENT", source_id=document_id,
        title=source.get("source_title", "HSK1 Beginner Notes"), source_language="vi",
        source_category="INTERNAL_AUTHORED", transformation_strategy="canonical_document",
        transformation_version="v1",
        provenance=DocumentProvenance(source_origin=FIXTURE_MARKER + INTERNAL_ID,
                                      usage_rights_note="Synthetic accepted evaluation fixture content."),
        blocks=blocks,
    )


async def _materialize_internal_document(session: AsyncSession, storage: LocalFileStorage,
                                         source: dict, admin_id: UUID) -> UUID:
    content = _json_bytes(source)
    content_hash = _sha(content)
    document = await session.scalar(select(Document).where(Document.content_hash == content_hash))
    if document is None:
        raw_key = "evaluation-fixtures/step73/internal-kb-source.json"
        storage.write_bytes(raw_key, content)
        document = Document(
            original_filename="accepted-internal-kb-fixture.json", file_type="json",
            storage_reference=raw_key, mime_type="application/json", file_size_bytes=len(content),
            content_hash=content_hash, processing_status="PREVIEW_READY", review_status="PENDING",
            uploaded_by=admin_id, title=source.get("source_title", "HSK1 Beginner Notes"),
            source_category="INTERNAL_AUTHORED", source_origin=FIXTURE_MARKER + INTERNAL_ID,
            source_language="vi", usage_rights_note="Synthetic accepted evaluation fixture content.",
        )
        session.add(document)
        await session.flush()
    elif document.source_origin != FIXTURE_MARKER + INTERNAL_ID:
        raise RuntimeError("Fixture Document content hash collides with a non-fixture Document")
    existing = await session.get(TransformationRun, document.review_transformation_run_id) if document.review_transformation_run_id else None
    if existing and existing.status == "SUCCEEDED" and existing.transformed_storage_reference:
        return document.id
    parsed_id, transform_id = uuid4(), uuid4()
    parsed_key = f"evaluation-fixtures/step73/{document.id}/parsed.json"
    transformed_key = f"evaluation-fixtures/step73/{document.id}/transformed.json"
    storage.write_bytes(parsed_key, _json_bytes({"source_id": str(document.id), "fixture_source_id": INTERNAL_ID}))
    transformed = _internal_document_artifact(source, document.id)
    storage.write_bytes(transformed_key, _json_bytes(transformed.model_dump(mode="json")))
    session.add(ParsingRun(
        id=parsed_id, source_type="DOCUMENT", document_id=document.id, lesson_id=None,
        raw_storage_reference=document.storage_reference, raw_content_hash=content_hash,
        parser_name="step73_accepted_fixture_adapter", parser_version="v1",
        cleaning_strategy="identity", cleaning_version="v1", status="SUCCEEDED",
        parsed_storage_reference=parsed_key,
    ))
    await session.flush()
    session.add(TransformationRun(
        id=transform_id, source_type="DOCUMENT", document_id=document.id, lesson_id=None,
        parsing_run_id=parsed_id, parsed_storage_reference=parsed_key,
        transformation_strategy="canonical_document", transformation_version="v1",
        status="SUCCEEDED", transformed_storage_reference=transformed_key,
        source_metadata_snapshot={"source_type": "DOCUMENT", "source_id": str(document.id),
                                  "title": document.title, "source_language": "vi",
                                  "source_category": "INTERNAL_AUTHORED", "source_origin": document.source_origin,
                                  "usage_rights_note": document.usage_rights_note,
                                  "original_filename": document.original_filename},
    ))
    await session.flush()
    document.processing_status = "PREVIEW_READY"
    document.review_status = "PENDING"
    document.review_transformation_run_id = transform_id
    document.approved_transformation_run_id = None
    document.approved_by = None
    document.approved_at = None
    await session.flush()
    return document.id


async def _ensure_eval_admin(session: AsyncSession) -> UUID:
    email = "step73-evaluation-bootstrap@invalid.local"
    user = await session.scalar(select(User).where(User.email == email))
    if user is None:
        from argon2 import PasswordHasher
        import secrets
        unusable_random_password = secrets.token_urlsafe(48)
        user = User(email=email, password_hash=PasswordHasher().hash(unusable_random_password),
                    full_name="Step 7.3 Evaluation Bootstrap", role="ADMIN", is_active=False)
        session.add(user)
        await session.flush()
    if user.role != "ADMIN":
        raise RuntimeError("Evaluation bootstrap principal has conflicting role")
    return user.id


async def reset_fixture_state(session: AsyncSession, storage: LocalFileStorage, *, settings: Settings,
                              actual_database: str) -> None:
    assert_evaluation_database(settings, actual_database)
    # Reset is permitted only when every source/version in this dedicated database is fixture-owned.
    sources = list((await session.scalars(select(KnowledgeSource))).all())
    if len(sources) > 4:
        raise RuntimeError("Refusing reset: non-fixture knowledge source contamination detected")
    versions = list((await session.scalars(select(KnowledgeVersion))).all())
    for version in versions:
        chunks = list((await session.scalars(select(Chunk).where(Chunk.knowledge_version_id == version.id))).all())
        for chunk in chunks:
            await session.execute(delete(Embedding).where(Embedding.chunk_id == chunk.id))
        await session.execute(delete(Chunk).where(Chunk.knowledge_version_id == version.id))
        await session.execute(delete(KnowledgeVersion).where(KnowledgeVersion.id == version.id))
    for source in sources:
        await session.execute(delete(KnowledgeSource).where(KnowledgeSource.id == source.id))
    documents = list((await session.scalars(select(Document).where(Document.source_origin.like(FIXTURE_MARKER + "%")))).all())
    for doc in documents:
        await session.execute(delete(TransformationRun).where(TransformationRun.document_id == doc.id))
        await session.execute(delete(ParsingRun).where(ParsingRun.document_id == doc.id))
        await session.execute(delete(Document).where(Document.id == doc.id))
    lesson_names = {row["source_id"]: row["source_title"] for row in load_fixture_pack()[1]
                    if row.get("source_kind") == "LESSON"}
    # Include marker-owned rows from earlier interrupted bootstrap attempts as well as
    # the reserved evaluation-only lesson-number range used by the current adapter.
    lessons = list((await session.scalars(select(Lesson).where(
        Lesson.description.like(FIXTURE_MARKER + "%") |
        ((Lesson.lesson_number > EVALUATION_LESSON_NUMBER_BASE)
         & (Lesson.lesson_number <= EVALUATION_LESSON_NUMBER_BASE + 3))
    ))).all())
    lessons = [lesson for lesson in lessons if lesson.description and lesson.description.startswith(FIXTURE_MARKER)
               or lesson.title in lesson_names.values()]
    for lesson in lessons:
        await session.execute(delete(TransformationRun).where(TransformationRun.lesson_id == lesson.id))
        await session.execute(delete(ParsingRun).where(ParsingRun.lesson_id == lesson.id))
        await session.execute(delete(LessonVocabulary).where(LessonVocabulary.lesson_id == lesson.id))
        await session.execute(delete(LessonGrammar).where(LessonGrammar.lesson_id == lesson.id))
        await session.execute(delete(Lesson).where(Lesson.id == lesson.id))
    await session.commit()
    # Local files are immutable run artifacts; leave them intact for audit/reproducibility.


async def bootstrap(session: AsyncSession, storage: LocalFileStorage, *, settings: Settings,
                    actual_database: str, reset: bool = False) -> dict:
    db = assert_evaluation_database(settings, actual_database)
    manifest, blocks, hashes = load_fixture_pack()
    bootstrap_id, bootstrap_identity = _bootstrap_identity(hashes, settings)
    sources = []
    for item in manifest["sources"]:
        source = json.loads((FIXTURE_ROOT / item["path"]).read_text(encoding="utf-8"))
        source["source_kind"] = item["kind"]
        source["source_title"] = source.get("lesson_title") or "HSK1 Beginner Notes"
        sources.append(source)
    if reset:
        await reset_fixture_state(session, storage, settings=settings, actual_database=actual_database)
    dbname_sources = list((await session.scalars(select(KnowledgeSource))).all())
    if dbname_sources:
        active_fixture = await _existing_bootstrap(session, db, hashes, manifest, blocks,
                                                   settings=settings, bootstrap_id=bootstrap_id,
                                                   bootstrap_identity=bootstrap_identity)
        if active_fixture:
            return active_fixture
        raise RuntimeError("Evaluation database contains unrecognized knowledge; refusing fixture contamination")
    await session.rollback()

    lesson_ids: dict[str, UUID] = {}
    async with session.begin():
        lesson_ids = await _lesson_identities(session, sources)
        for source in sources:
            if source["source_id"] in lesson_ids:
                await _materialize_lesson(session, source, lesson_ids[source["source_id"]])
        admin_id = await _ensure_eval_admin(session)
        internal_source = next(s for s in sources if s["source_id"] == INTERNAL_ID)
        document_id = await _materialize_internal_document(session, storage, internal_source, admin_id)
    for lesson_id in lesson_ids.values():
        await IngestionOrchestrator(session, storage).process_published_lesson(lesson_id)
    doc_result = await IngestionOrchestrator(session, storage).approve_document(document_id, admin_id)

    # Existing ingestion boundaries create source/version/chunk records. Retain each
    # accepted stable locator in the existing JSONB Chunk metadata for deterministic resolution.
    source_versions: dict[str, UUID] = {}
    async with session.begin():
        for source in sources:
            source_id = lesson_ids[source["source_id"]] if source["source_id"] in lesson_ids else document_id
            kind = source["source_kind"]
            source_row = await session.scalar(select(KnowledgeSource).where(
                (KnowledgeSource.lesson_id == source_id) if kind == "LESSON" else
                (KnowledgeSource.document_id == source_id)
            ))
            version = await session.scalar(select(KnowledgeVersion).where(
                KnowledgeVersion.knowledge_source_id == source_row.id, KnowledgeVersion.status == "PROCESSING",
            ))
            if version is None:
                version_id = doc_result["knowledge_version_id"] if kind == "INTERNAL_KB" else None
                if version_id is None:
                    raise RuntimeError("Fixture source has no PROCESSING KnowledgeVersion")
                version = await session.get(KnowledgeVersion, version_id)
            source_versions[source["source_id"]] = version.id
            fixture_blocks = [b for b in blocks if b["source_id"] == source["source_id"]]
            chunks = list((await session.scalars(select(Chunk).where(
                Chunk.knowledge_version_id == version.id,
            ).order_by(Chunk.chunk_index))).all())
            if not chunks:
                raise RuntimeError("Fixture source produced no runtime Chunks")
            for chunk in chunks:
                metadata = dict(chunk.metadata_json or {})
                locators = _fixture_locator_metadata(metadata, source["source_id"], kind, fixture_blocks)
                if not locators:
                    raise RuntimeError("Chunk provenance could not resolve to fixture stable locators")
                provenance_records = _fixture_provenance_records(metadata, kind, fixture_blocks)
                metadata.update({"fixture_pack": "lesson_chat_rag", "fixture_pack_version": "0.1.0",
                                 "fixture_source_id": source["source_id"],
                                 "fixture_stable_locators": locators,
                                 "fixture_provenance": [{key: record[key] for key in
                                     ("block_id", "stable_locator", "source_locator")} for record in provenance_records],
                                 "fixture_bootstrap_id": bootstrap_id,
                                 "fixture_content_sha256": hashes["aggregate_fixture_content_sha256"],
                                 "fixture_chunking_identity": bootstrap_identity["chunking_identity"]})
                chunk.metadata_json = metadata
    embedding_service = EmbeddingService(session, settings=settings)
    profile_id = None
    for version_id in source_versions.values():
        result = await embedding_service.embed_processing_version(version_id)
        profile_id = result.embedding_profile_id
    if profile_id is None:
        raise RuntimeError("Embedding pipeline did not resolve a profile")
    active_profile = await session.scalar(select(EmbeddingProfile).where(EmbeddingProfile.status == "ACTIVE"))
    if active_profile is None:
        await VectorStorageService(session).bootstrap_profile(profile_id)
    else:
        if (active_profile.model_name, active_profile.model_version) != (
            settings.embedding_model_name, settings.embedding_model_revision,
        ):
            raise RuntimeError("Existing active embedding profile does not match the pinned evaluation model")
        for version_id in source_versions.values():
            await VectorStorageService(session).activate_version(version_id)
    mapping = await _resolve_runtime_map(session, blocks, source_versions)
    if len(mapping) != 26 or any(not items for items in mapping.values()):
        raise RuntimeError("Not every accepted stable locator resolved to ACTIVE runtime chunks")
    return {
        "fixture_bootstrap_id": bootstrap_id, "fixture_bootstrap_identity": bootstrap_identity,
        "created_at": datetime.now(UTC).isoformat(), "fixture_pack": "lesson_chat_rag",
        "fixture_pack_version": "0.1.0", "fixture_pack_status": manifest["status"],
        "fixture_source_count": 4, "lesson_source_count": 3, "internal_kb_source_count": 1,
        "fixture_block_count": 26, "fixture_hashes": hashes, "database_isolation": db,
        "source_runtime_ids": {source_id: str(version_id) for source_id, version_id in source_versions.items()},
        "lesson_runtime_ids": {
            source["lesson_locator"]: str(lesson_ids[source["source_id"]])
            for source in sources if source["source_id"] in lesson_ids
        },
        "lesson_runtime_ids_by_source_id": {source_id: str(value) for source_id, value in lesson_ids.items()},
        "internal_document_id": str(document_id), "embedding_profile_id": str(profile_id),
        "active_source_version_count": 4, "stable_locator_count": len(mapping),
        "runtime_map": mapping,
    }


async def _existing_bootstrap(session: AsyncSession, db: dict, hashes: dict, manifest: dict,
                              blocks: list[dict], *, settings: Settings, bootstrap_id: str,
                              bootstrap_identity: dict) -> dict | None:
    versions = list((await session.scalars(select(KnowledgeVersion).where(KnowledgeVersion.status == "ACTIVE"))).all())
    if len(versions) != 4:
        return None
    # Existing identities are accepted only when every persisted chunk declares the exact pack hash.
    source_versions = {}
    profile_id = None
    for version in versions:
        source = await session.get(KnowledgeSource, version.knowledge_source_id)
        if source.source_type == "LESSON":
            lesson = await session.get(Lesson, source.lesson_id)
            title_by_id = {row["source_id"]: row["source_title"] for row in blocks if row["source_kind"] == "LESSON"}
            source_id = next((key for key in LESSON_IDS if (
                lesson.lesson_number == EVALUATION_LESSON_NUMBER_BASE + int(key.split(".")[-2])
                and lesson.title == title_by_id[key]
            )), None)
        else:
            document = await session.get(Document, source.document_id)
            source_id = INTERNAL_ID if document and document.source_origin == FIXTURE_MARKER + INTERNAL_ID else None
        if not source_id:
            return None
        source_versions[source_id] = version.id
        chunks = list((await session.scalars(select(Chunk).where(Chunk.knowledge_version_id == version.id))).all())
        if not chunks or any((chunk.metadata_json or {}).get("fixture_bootstrap_id") != bootstrap_id
                             or (chunk.metadata_json or {}).get("fixture_content_sha256") != hashes["aggregate_fixture_content_sha256"]
                             or not (chunk.metadata_json or {}).get("fixture_stable_locators") for chunk in chunks):
            return None
    resolved = await _resolve_runtime_map(session, blocks, source_versions)
    profiles = list((await session.scalars(select(EmbeddingProfile).where(EmbeddingProfile.status == "ACTIVE"))).all())
    if len(profiles) != 1 or (profiles[0].model_name, profiles[0].model_version,
                              profiles[0].embedding_input_version) != (
        settings.embedding_model_name, settings.embedding_model_revision, settings.embedding_input_version,
    ):
        return None
    readiness = VectorStorageService(session)
    for version in versions:
        result = await readiness.check_vector_pair_readiness(version.id, profiles[0].id)
        if not result.ready:
            return None
    lesson_runtime_ids = {}
    lesson_runtime_ids_by_source_id = {}
    lesson_locator_by_source = {row["source_id"]: row.get("lesson_locator") for row in blocks
                                if row.get("source_kind") == "LESSON"}
    for source_id, version_id in source_versions.items():
        if source_id in LESSON_IDS:
            version = await session.get(KnowledgeVersion, version_id)
            source = await session.get(KnowledgeSource, version.knowledge_source_id)
            lesson = await session.get(Lesson, source.lesson_id)
            lesson_runtime_ids[lesson_locator_by_source[source_id]] = str(lesson.id)
            lesson_runtime_ids_by_source_id[source_id] = str(lesson.id)
    return {"fixture_bootstrap_id": bootstrap_id, "fixture_bootstrap_identity": bootstrap_identity,
            "created_at": datetime.now(UTC).isoformat(), "fixture_pack": "lesson_chat_rag",
            "fixture_pack_version": "0.1.0", "fixture_pack_status": manifest["status"],
            "fixture_source_count": 4, "lesson_source_count": 3, "internal_kb_source_count": 1,
            "fixture_block_count": 26, "fixture_hashes": hashes, "database_isolation": db,
            "source_runtime_ids": {key: str(value) for key, value in source_versions.items()},
            "lesson_runtime_ids": lesson_runtime_ids,
            "lesson_runtime_ids_by_source_id": lesson_runtime_ids_by_source_id,
            "active_source_version_count": 4, "stable_locator_count": len(resolved), "runtime_map": resolved,
            "idempotency": "NO_OP"}


async def _resolve_runtime_map(session: AsyncSession, blocks: list[dict], source_versions: dict[str, UUID],
                               allow_no_blocks: bool = False) -> dict:
    result: dict[str, set[str]] = {}
    expected = {b["stable_locator"] for b in blocks}
    for source_id, version_id in source_versions.items():
        chunks = list((await session.scalars(select(Chunk).where(
            Chunk.knowledge_version_id == version_id,
        ).order_by(Chunk.chunk_index))).all())
        version = await session.get(KnowledgeVersion, version_id)
        if version is None or version.status != "ACTIVE":
            raise RuntimeError("Stable locator resolver found a non-ACTIVE KnowledgeVersion")
        for chunk in chunks:
            metadata = chunk.metadata_json or {}
            if metadata.get("fixture_source_id") != source_id:
                raise RuntimeError("Chunk fixture source provenance conflicts with its KnowledgeSource")
            if not metadata.get("fixture_provenance"):
                raise RuntimeError("Chunk fixture stable-locator provenance record is missing")
            for locator in metadata.get("fixture_stable_locators", []):
                if expected and locator not in expected:
                    raise RuntimeError("Runtime fixture provenance contains an unknown stable locator")
                result.setdefault(locator, set()).add(str(chunk.id))
    if not allow_no_blocks and set(result) != expected:
        missing, unexpected = expected - set(result), set(result) - expected
        raise RuntimeError(f"Fixture locator resolution incomplete (missing={len(missing)}, unexpected={len(unexpected)})")
    return {locator: sorted(ids) for locator, ids in sorted(result.items())}
