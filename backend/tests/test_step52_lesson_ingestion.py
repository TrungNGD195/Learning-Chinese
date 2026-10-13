import asyncio
import hashlib
import json
from pathlib import Path
from shutil import rmtree
from uuid import uuid4
import pytest
from sqlalchemy import delete, update

from app.core.errors import ApplicationError
from app.database.models import Grammar, HSKLevel, Lesson, LessonGrammar, LessonVocabulary, Vocabulary
from app.database.session import SessionFactory
from app.ingestion.service import create_lesson_snapshot
from app.ingestion.storage import LocalFileStorage


def test_published_lesson_snapshot_is_canonical_and_hash_addressed() -> None:
    root = Path(__file__).resolve().parents[2] / "tmp" / f"step52-lesson-{uuid4().hex}"
    root.mkdir(parents=True)
    lesson_id, hsk_id = uuid4(), uuid4()
    vocabulary_ids = [uuid4(), uuid4()]
    grammar_ids = [uuid4(), uuid4()]

    async def run() -> None:
        async with SessionFactory.begin() as session:
            session.add(HSKLevel(id=hsk_id, level_number=900000 + (int(hsk_id.int % 90000)), title="Snapshot HSK", order_index=1))
            session.add(Lesson(id=lesson_id, hsk_level_id=hsk_id, lesson_number=1,
                               title="Snapshot", description="Source state", status="PUBLISHED"))
            session.add_all([
                Vocabulary(id=vocabulary_ids[0], hanzi="乙", pinyin="yǐ", vietnamese_meaning="hai"),
                Vocabulary(id=vocabulary_ids[1], hanzi="甲", pinyin="jiǎ", vietnamese_meaning="một"),
                Grammar(id=grammar_ids[0], name="second", explanation="Second grammar"),
                Grammar(id=grammar_ids[1], name="first", explanation="First grammar"),
            ])
            await session.flush()
            session.add_all([
                LessonVocabulary(lesson_id=lesson_id, vocabulary_id=vocabulary_ids[0], order_index=2),
                LessonVocabulary(lesson_id=lesson_id, vocabulary_id=vocabulary_ids[1], order_index=1),
                LessonGrammar(lesson_id=lesson_id, grammar_id=grammar_ids[0], order_index=2),
                LessonGrammar(lesson_id=lesson_id, grammar_id=grammar_ids[1], order_index=1),
            ])
        async with SessionFactory() as session:
            storage = LocalFileStorage(root / "raw")
            first = await create_lesson_snapshot(session, lesson_id, storage)
            second = await create_lesson_snapshot(session, lesson_id, storage)
            assert first == second
            with storage.open(first.storage_key) as artifact:
                content = artifact.read()
            assert first.content_hash == hashlib.sha256(content).hexdigest()
            snapshot = json.loads(content)
            assert snapshot["schema_version"] == "raw_lesson_snapshot/v1"
            assert set(snapshot) == {"schema_version", "lesson", "vocabulary", "grammar"}
            assert snapshot["lesson"]["hsk"]["id"] == str(hsk_id)
            assert [row["hanzi"] for row in snapshot["vocabulary"]] == ["甲", "乙"]
            assert [row["name"] for row in snapshot["grammar"]] == ["first", "second"]
            assert "processing_timestamp" not in snapshot
        async with SessionFactory.begin() as session:
            await session.execute(update(Lesson).where(Lesson.id == lesson_id).values(status="DRAFT"))
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as exc:
                await create_lesson_snapshot(session, lesson_id, storage)
            assert exc.value.code == "LESSON_NOT_PUBLISHED"
        async with SessionFactory.begin() as session:
            await session.execute(update(Lesson).where(Lesson.id == lesson_id).values(status="PUBLISHED", title="Changed source"))
        async with SessionFactory() as session:
            changed = await create_lesson_snapshot(session, lesson_id, storage)
            assert changed.content_hash != first.content_hash
        async with SessionFactory.begin() as session:
            await session.execute(update(Lesson).where(Lesson.id == lesson_id).values(status="ARCHIVED"))
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as exc:
                await create_lesson_snapshot(session, lesson_id, storage)
            assert exc.value.code == "LESSON_NOT_PUBLISHED"
    try:
        asyncio.run(run())
    finally:
        async def cleanup() -> None:
            async with SessionFactory.begin() as session:
                await session.execute(delete(LessonVocabulary).where(LessonVocabulary.lesson_id == lesson_id))
                await session.execute(delete(LessonGrammar).where(LessonGrammar.lesson_id == lesson_id))
                await session.execute(delete(Lesson).where(Lesson.id == lesson_id))
                await session.execute(delete(Vocabulary).where(Vocabulary.id.in_(vocabulary_ids)))
                await session.execute(delete(Grammar).where(Grammar.id.in_(grammar_ids)))
                await session.execute(delete(HSKLevel).where(HSKLevel.id == hsk_id))
        asyncio.run(cleanup())
        rmtree(root)
