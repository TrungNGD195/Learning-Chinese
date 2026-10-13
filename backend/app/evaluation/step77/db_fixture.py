from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID, uuid5

from sqlalchemy import delete, select, text
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.database.models import (Assessment, AssessmentGrammar, AssessmentLesson,
    AssessmentVocabulary, Grammar, HSKLevel, Lesson, LessonGrammar, LessonVocabulary,
    Question, QuestionOption, Vocabulary)

FIXTURE_NAMESPACE = UUID("ac06555e-61f1-45e8-9953-fc21d21c0a37")
FIXTURE_PATH = Path(__file__).resolve().parents[4] / "evaluation/fixtures/assessment_generation/v0.1.0/curriculum.json"
FIXTURE_LEVEL_ID = uuid5(FIXTURE_NAMESPACE, "level")
FIXTURE_LEVEL_NUMBER = 987_654_321


def fixture_uuid(name: str) -> UUID:
    return uuid5(FIXTURE_NAMESPACE, name)


async def dedicated_test_database_available() -> tuple[bool, str]:
    try:
        settings = get_settings()
        url = make_url(settings.effective_database_url)
        if settings.app_env != "test" or url.database != "chinese_learning_test":
            return False, "APP_ENV/test database identity is not the dedicated chinese_learning_test target"
        if settings.database_url and make_url(settings.database_url).database == url.database:
            return False, "test database is not isolated from DATABASE_URL"
        from app.database.engine import engine
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True, "dedicated test PostgreSQL reachable"
    except Exception as exc:
        return False, f"database unavailable ({type(exc).__name__})"


def _fixture_data() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


async def seed_curriculum_fixture() -> None:
    """Seed only deterministic Step-7.7 rows into the guarded dedicated test DB."""
    available, reason = await dedicated_test_database_available()
    if not available:
        raise RuntimeError(f"STEP77_SAFE_TEST_DATABASE_REQUIRED: {reason}")
    data = _fixture_data()
    from app.database.session import SessionFactory
    async with SessionFactory.begin() as session:
        existing = await session.get(HSKLevel, FIXTURE_LEVEL_ID)
        if existing is not None:
            return
        session.add(HSKLevel(id=FIXTURE_LEVEL_ID, level_number=FIXTURE_LEVEL_NUMBER,
                             title="Step 7.7 synthetic evaluation fixture", order_index=FIXTURE_LEVEL_NUMBER))
        await session.flush()
        for row in data["lessons"]:
            session.add(Lesson(id=UUID(row["lesson_id"]), hsk_level_id=FIXTURE_LEVEL_ID,
                lesson_number=row["lesson_number"], title=row["title"], description=row["description"], status="DRAFT"))
        for row in data["vocabulary"]:
            session.add(Vocabulary(id=UUID(row["id"]), hanzi=row["hanzi"], pinyin=row["pinyin"],
                vietnamese_meaning=row["vietnamese_meaning"], part_of_speech=row["part_of_speech"]))
        for row in data["grammar"]:
            session.add(Grammar(id=UUID(row["id"]), name=row["name"], structure=row["structure"],
                explanation=row["explanation"], usage=row["usage"]))
        await session.flush()
        for index, row in enumerate(data["vocabulary"], start=1):
            session.add(LessonVocabulary(id=fixture_uuid(f"lesson-vocabulary-{index}"),
                lesson_id=UUID(row["lesson_id"]), vocabulary_id=UUID(row["id"]), order_index=row["order_index"],
                note="Step 7.7 synthetic evaluation fixture", example=row["example"]))
        for index, row in enumerate(data["grammar"], start=1):
            session.add(LessonGrammar(id=fixture_uuid(f"lesson-grammar-{index}"),
                lesson_id=UUID(row["lesson_id"]), grammar_id=UUID(row["id"]), order_index=row["order_index"],
                note="Step 7.7 synthetic evaluation fixture", example=row["example"]))


async def cleanup_generation_assessments(assessment_ids: list[UUID]) -> None:
    if not assessment_ids:
        return
    from app.database.session import SessionFactory
    async with SessionFactory.begin() as session:
        q_ids = select(Question.id).where(Question.assessment_id.in_(assessment_ids))
        await session.execute(delete(QuestionOption).where(QuestionOption.question_id.in_(q_ids)))
        await session.execute(delete(Question).where(Question.assessment_id.in_(assessment_ids)))
        await session.execute(delete(AssessmentLesson).where(AssessmentLesson.c.assessment_id.in_(assessment_ids)))
        await session.execute(delete(AssessmentVocabulary).where(AssessmentVocabulary.c.assessment_id.in_(assessment_ids)))
        await session.execute(delete(AssessmentGrammar).where(AssessmentGrammar.c.assessment_id.in_(assessment_ids)))
        await session.execute(delete(Assessment).where(Assessment.id.in_(assessment_ids)))


async def cleanup_curriculum_fixture() -> None:
    """Remove only deterministic fixture IDs and only when no generated rows reference them."""
    data = _fixture_data()
    lesson_ids = [UUID(row["lesson_id"]) for row in data["lessons"]]
    from app.database.session import SessionFactory
    async with SessionFactory.begin() as session:
        linked = (await session.execute(select(Assessment.id).where(Assessment.lesson_id.in_(lesson_ids)))).scalars().all()
        if linked:
            raise RuntimeError("STEP77_FIXTURE_CLEANUP_BLOCKED_BY_ASSESSMENT_REFERENCE")
        await session.execute(delete(LessonVocabulary).where(LessonVocabulary.id.in_(
            [fixture_uuid(f"lesson-vocabulary-{i}") for i in range(1, 4)])))
        await session.execute(delete(LessonGrammar).where(LessonGrammar.id.in_(
            [fixture_uuid(f"lesson-grammar-{i}") for i in range(1, 4)])))
        await session.execute(delete(Vocabulary).where(Vocabulary.id.in_([UUID(row["id"]) for row in data["vocabulary"]])))
        await session.execute(delete(Grammar).where(Grammar.id.in_([UUID(row["id"]) for row in data["grammar"]])))
        await session.execute(delete(Lesson).where(Lesson.id.in_(lesson_ids)))
        await session.execute(delete(HSKLevel).where(HSKLevel.id == FIXTURE_LEVEL_ID))
