from contextlib import contextmanager
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app.auth.security import hash_password
from app.database.seeds.required import seed_required_data
from app.database.models import (
    Assessment,
    AssessmentAttempt,
    Conversation,
    CurriculumUnit,
    HSKLevel,
    LearnerHSKProgress,
    LearnerLessonProgress,
    Lesson,
    Message,
    PronunciationProgress,
    PronunciationSection,
    User,
)
from app.database.session import SessionFactory
from app.main import app


TEST_PASSWORD = "conversation test password"
REQUIRED_PRONUNCIATION_SECTION_CODES = ("TONES", "INITIALS", "FINALS")


async def seed_user_lesson(*, accessible: bool = True, completed: bool = False) -> tuple:
    user_id, lesson_id = uuid4(), uuid4()
    await seed_required_data()
    async with SessionFactory.begin() as session:
        level = await session.scalar(select(HSKLevel).where(HSKLevel.level_number == 1))
        if level is None:
            level = HSKLevel(level_number=1, title="HSK 1", order_index=1)
            session.add(level)
            await session.flush()
        sections = list((await session.scalars(
            select(PronunciationSection)
            .where(PronunciationSection.code.in_(REQUIRED_PRONUNCIATION_SECTION_CODES))
            .order_by(PronunciationSection.order_index)
        )).all())
        session.add(User(
            id=user_id,
            email=f"conversation-{user_id}@example.invalid",
            password_hash=hash_password(TEST_PASSWORD),
            full_name="Conversation Learner",
            role="LEARNER",
        ))
        lesson = Lesson(
            id=lesson_id,
            hsk_level_id=level.id,
            lesson_number=500000 + user_id.int % 400000,
            title="Conversation test lesson",
            status="PUBLISHED",
        )
        session.add(lesson)
        await session.flush()
        minimum = await session.scalar(
            select(func.min(CurriculumUnit.order_index)).where(CurriculumUnit.hsk_level_id == level.id)
        )
        unit_order = (minimum if minimum is not None else 0) - 1
        session.add(CurriculumUnit(
            hsk_level_id=level.id,
            unit_type="LESSON",
            lesson_id=lesson_id,
            order_index=unit_order,
        ))
        if accessible:
            now = datetime.now(UTC)
            session.add_all([
                PronunciationProgress(
                    user_id=user_id,
                    pronunciation_section_id=section.id,
                    completed_at=now,
                )
                for section in sections
            ])
        if completed:
            session.add(LearnerLessonProgress(
                user_id=user_id,
                lesson_id=lesson_id,
                completed_at=datetime.now(UTC),
            ))
    return user_id, lesson_id


async def seed_user_for_lesson(lesson_id: UUID) -> UUID:
    user_id = uuid4()
    await seed_required_data()
    async with SessionFactory.begin() as session:
        sections = list((await session.scalars(
            select(PronunciationSection)
            .where(PronunciationSection.code.in_(REQUIRED_PRONUNCIATION_SECTION_CODES))
            .order_by(PronunciationSection.order_index)
        )).all())
        session.add(User(
            id=user_id,
            email=f"conversation-{user_id}@example.invalid",
            password_hash=hash_password(TEST_PASSWORD),
            full_name="Conversation Other Learner",
            role="LEARNER",
        ))
        await session.flush()
        now = datetime.now(UTC)
        session.add_all([
            PronunciationProgress(
                user_id=user_id,
                pronunciation_section_id=section.id,
                completed_at=now,
            )
            for section in sections
        ])
    return user_id


async def add_assessment_attempt(
    user_id,
    lesson_id,
    *,
    assessment_type: str,
    attempt_status: str = "IN_PROGRESS",
) -> tuple:
    assessment_id, attempt_id = uuid4(), uuid4()
    async with SessionFactory.begin() as session:
        assessment = Assessment(
            id=assessment_id,
            type=assessment_type,
            lesson_id=lesson_id if assessment_type == "LESSON_EXERCISE" else None,
            title=f"{assessment_type} test fixture",
            status="PUBLISHED",
            pass_threshold=90,
        )
        session.add(assessment)
        await session.flush()
        session.add(AssessmentAttempt(
            id=attempt_id,
            user_id=user_id,
            assessment_id=assessment_id,
            attempt_number=1,
            status=attempt_status,
        ))
    return assessment_id, attempt_id


@contextmanager
def authenticated_client(user_id):
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/v1/auth/login", json={
            "email": f"conversation-{user_id}@example.invalid",
            "password": TEST_PASSWORD,
        })
        assert response.status_code == 200, response.text
        yield client


async def cleanup_scenario(user_id, lesson_id, assessment_ids=()) -> None:
    async with SessionFactory.begin() as session:
        conversation_ids = select(Conversation.id).where(Conversation.user_id == user_id)
        await session.execute(delete(Message).where(Message.conversation_id.in_(conversation_ids)))
        await session.execute(delete(Conversation).where(Conversation.user_id == user_id))
        await session.execute(delete(AssessmentAttempt).where(AssessmentAttempt.user_id == user_id))
        await session.execute(delete(CurriculumUnit).where(CurriculumUnit.lesson_id == lesson_id))
        if assessment_ids:
            await session.execute(delete(CurriculumUnit).where(CurriculumUnit.assessment_id.in_(assessment_ids)))
            await session.execute(delete(Assessment).where(Assessment.id.in_(assessment_ids)))
        await session.execute(delete(LearnerLessonProgress).where(LearnerLessonProgress.user_id == user_id))
        await session.execute(delete(LearnerHSKProgress).where(LearnerHSKProgress.user_id == user_id))
        await session.execute(delete(PronunciationProgress).where(PronunciationProgress.user_id == user_id))
        await session.execute(delete(Lesson).where(Lesson.id == lesson_id))
        await session.execute(delete(User).where(User.id == user_id))


async def cleanup_user_only(user_id) -> None:
    async with SessionFactory.begin() as session:
        conversation_ids = select(Conversation.id).where(Conversation.user_id == user_id)
        await session.execute(delete(Message).where(Message.conversation_id.in_(conversation_ids)))
        await session.execute(delete(Conversation).where(Conversation.user_id == user_id))
        await session.execute(delete(AssessmentAttempt).where(AssessmentAttempt.user_id == user_id))
        await session.execute(delete(LearnerLessonProgress).where(LearnerLessonProgress.user_id == user_id))
        await session.execute(delete(LearnerHSKProgress).where(LearnerHSKProgress.user_id == user_id))
        await session.execute(delete(PronunciationProgress).where(PronunciationProgress.user_id == user_id))
        await session.execute(delete(User).where(User.id == user_id))


def scenario_cleanup(user_id, lesson_id, assessment_ids=()) -> None:
    import asyncio

    asyncio.run(cleanup_scenario(user_id, lesson_id, assessment_ids))
