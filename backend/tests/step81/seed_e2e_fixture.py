"""Seed the small Step 8.1 browser fixture after the guarded DB reset."""

from __future__ import annotations

import argparse
import asyncio
import os
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import make_url

from app.auth.security import hash_password
from app.core.config import get_settings
from app.database.models import (
    Assessment, AssessmentLesson, CurriculumUnit, Grammar, HSKLevel, Lesson,
    LessonGrammar, LessonVocabulary, LearnerHSKProgress, LearnerLessonProgress,
    PronunciationProgress, PronunciationSection, Question, QuestionOption,
    User, Vocabulary,
)
from app.database.session import SessionFactory

FIXTURE_NS = NAMESPACE_URL
ADMIN_EMAIL = "step81-admin@example.invalid"
LEARNER_EMAIL = "step81-learner@example.invalid"


def fixture_id(name: str):
    return uuid5(FIXTURE_NS, f"trung-chinese-learning:step81:{name}")


def database_identity(value: str):
    url = make_url(value)
    return (url.host.lower() if url.host else "", url.port or 5432, url.database)


async def seed() -> None:
    test_password = os.environ.get("STEP81_TEST_PASSWORD")
    if not test_password or len(test_password) < 24:
        raise RuntimeError("A generated ephemeral Step 8.1 test password is required")
    settings = get_settings()
    if settings.app_env != "test" or not settings.test_database_url:
        raise RuntimeError("APP_ENV=test and TEST_DATABASE_URL are required")
    url = make_url(settings.test_database_url)
    if url.drivername != "postgresql+psycopg" or url.database != "chinese_learning_test":
        raise RuntimeError("Dedicated PostgreSQL test database required")
    if url.host not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("Test database must be loopback-hosted")
    if settings.database_url and database_identity(settings.database_url) == database_identity(settings.test_database_url):
        raise RuntimeError("Test database must differ from normal DATABASE_URL")

    async with SessionFactory.begin() as session:
        hsk1 = (await session.execute(select(HSKLevel).where(HSKLevel.level_number == 1))).scalar_one()
        hsk2 = (await session.execute(select(HSKLevel).where(HSKLevel.level_number == 2))).scalar_one()
        sections = list((await session.execute(select(PronunciationSection).order_by(PronunciationSection.order_index))).scalars())
        if len(sections) != 3:
            raise RuntimeError("Required pronunciation seed is incomplete")

        admin_id = fixture_id("admin")
        learner_id = fixture_id("learner")
        lesson_a_id = fixture_id("lesson-a")
        lesson_b_id = fixture_id("lesson-b")
        exercise_id = fixture_id("lesson-exercise")
        periodic_id = fixture_id("periodic-test")
        question_ids = [fixture_id("lesson-question"), fixture_id("periodic-question")]
        vocab_id, grammar_id = fixture_id("vocabulary"), fixture_id("grammar")
        lesson_vocab_id, lesson_grammar_id = fixture_id("lesson-vocabulary"), fixture_id("lesson-grammar")

        await session.execute(insert(User).values([
            {"id": admin_id, "email": ADMIN_EMAIL, "password_hash": hash_password(test_password), "full_name": "Step 8.1 Admin", "role": "ADMIN"},
            {"id": learner_id, "email": LEARNER_EMAIL, "password_hash": hash_password(test_password), "full_name": "Step 8.1 Learner", "role": "LEARNER"},
        ]).on_conflict_do_nothing(index_elements=["email"]))
        session.add_all([
            Lesson(id=lesson_a_id, hsk_level_id=hsk1.id, lesson_number=1, title="Step 8.1 Lesson A", description="你好 and 再见", status="PUBLISHED"),
            Lesson(id=lesson_b_id, hsk_level_id=hsk2.id, lesson_number=1, title="Step 8.1 Lesson B", description="Second-level unlock target", status="PUBLISHED"),
            Vocabulary(id=vocab_id, hanzi="你好", pinyin="nǐ hǎo", vietnamese_meaning="xin chào", part_of_speech="phrase"),
            Grammar(id=grammar_id, name="Greeting", structure="A", explanation="A fixture grammar", usage="Use in a greeting"),
        ])
        await session.flush()
        session.add_all([
            Assessment(id=exercise_id, type="LESSON_EXERCISE", lesson_id=lesson_a_id, title="Step 8.1 Exercise", status="PUBLISHED", pass_threshold=90),
            Assessment(id=periodic_id, type="PERIODIC_TEST", lesson_id=None, title="Step 8.1 Periodic Test", status="PUBLISHED", pass_threshold=90),
        ])
        await session.flush()
        session.add_all([
            LessonVocabulary(id=lesson_vocab_id, lesson_id=lesson_a_id, vocabulary_id=vocab_id, order_index=1, example="你好。"),
            LessonGrammar(id=lesson_grammar_id, lesson_id=lesson_a_id, grammar_id=grammar_id, order_index=1, example="你好。"),
            CurriculumUnit(hsk_level_id=hsk1.id, unit_type="LESSON", lesson_id=lesson_a_id, order_index=1),
            CurriculumUnit(hsk_level_id=hsk1.id, unit_type="PERIODIC_TEST", assessment_id=periodic_id, order_index=2),
            CurriculumUnit(hsk_level_id=hsk2.id, unit_type="LESSON", lesson_id=lesson_b_id, order_index=1),
            Question(id=question_ids[0], assessment_id=exercise_id, type="multiple_choice", prompt="Which word means hello?", order_index=1, points=1),
            Question(id=question_ids[1], assessment_id=periodic_id, type="multiple_choice", prompt="Which word means goodbye?", order_index=1, points=1),
            LearnerLessonProgress(user_id=learner_id, lesson_id=lesson_a_id, started_at=datetime.now(timezone.utc), completed_at=datetime.now(timezone.utc), theory_completed_at=datetime.now(timezone.utc)),
            LearnerHSKProgress(user_id=learner_id, hsk_level_id=hsk1.id),
        ])
        await session.flush()
        session.add_all([
            QuestionOption(question_id=question_ids[0], option_text="你好", order_index=1, is_correct=True),
            QuestionOption(question_id=question_ids[0], option_text="再见", order_index=2, is_correct=False),
            QuestionOption(question_id=question_ids[1], option_text="再见", order_index=1, is_correct=True),
            QuestionOption(question_id=question_ids[1], option_text="你好", order_index=2, is_correct=False),
            *(PronunciationProgress(user_id=learner_id, pronunciation_section_id=item.id, completed_at=datetime.now(timezone.utc)) for item in sections),
        ])
        await session.execute(AssessmentLesson.insert().values([
            {"assessment_id": periodic_id, "lesson_id": lesson_a_id},
        ]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-step81-seed", action="store_true")
    if not parser.parse_args().confirm_step81_seed:
        parser.error("pass --confirm-step81-seed to seed the dedicated Step 8.1 test fixture")
    asyncio.run(seed())
    print("SEED=PASS; fixture rows added to the dedicated Step 8.1 test database")


if __name__ == "__main__":
    main()
