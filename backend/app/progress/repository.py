from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    LearnerGrammarProgress,
    LearnerHSKProgress,
    LearnerLessonProgress,
    LearnerVocabularyProgress,
    PronunciationProgress,
    PronunciationLessonProgress,
    LessonReading,
    LearnerReadingProgress,
)


async def learner_completion_snapshot(session: AsyncSession, user_id: UUID):
    lesson_done = set(
        (await session.execute(
            select(LearnerLessonProgress.lesson_id).where(
                LearnerLessonProgress.user_id == user_id,
                LearnerLessonProgress.completed_at.is_not(None),
            )
        )).scalars()
    )
    return lesson_done


async def get_lesson_progress(session: AsyncSession, user_id: UUID, lesson_id: UUID):
    return (
        await session.execute(
            select(LearnerLessonProgress).where(
                LearnerLessonProgress.user_id == user_id,
                LearnerLessonProgress.lesson_id == lesson_id,
            )
        )
    ).scalar_one_or_none()


async def get_hsk_progress(session: AsyncSession,user_id: UUID,hsk_id: UUID):
    return (await session.execute(select(LearnerHSKProgress).where(
    LearnerHSKProgress.user_id==user_id,LearnerHSKProgress.hsk_level_id==hsk_id))).scalar_one_or_none()


async def mark_hsk_completed(session: AsyncSession,user_id: UUID,hsk_id: UUID,completed_at: datetime) -> None:
    progress=await get_hsk_progress(session,user_id,hsk_id)
    if progress is None:
        session.add(LearnerHSKProgress(user_id=user_id,hsk_level_id=hsk_id,started_at=completed_at,completed_at=completed_at))
    elif progress.completed_at is None:
        progress.completed_at=completed_at
    await session.flush()


async def viewed_vocabulary_ids(session: AsyncSession,user_id: UUID,junction_ids: list[UUID]) -> set[UUID]:
    if not junction_ids:return set()
    return set((await session.execute(select(LearnerVocabularyProgress.lesson_vocabulary_id).where(
        LearnerVocabularyProgress.user_id==user_id,LearnerVocabularyProgress.lesson_vocabulary_id.in_(junction_ids)))).scalars())


async def viewed_grammar_ids(session: AsyncSession,user_id: UUID,junction_ids: list[UUID]) -> set[UUID]:
    if not junction_ids:return set()
    return set((await session.execute(select(LearnerGrammarProgress.lesson_grammar_id).where(
        LearnerGrammarProgress.user_id==user_id,LearnerGrammarProgress.lesson_grammar_id.in_(junction_ids)))).scalars())


async def mark_vocabulary_viewed(session: AsyncSession, user_id: UUID, junction_id: UUID) -> datetime:
    viewed_at = datetime.now(UTC)
    await session.execute(
        insert(LearnerVocabularyProgress)
        .values(user_id=user_id, lesson_vocabulary_id=junction_id, viewed_at=viewed_at)
        .on_conflict_do_nothing(index_elements=["user_id", "lesson_vocabulary_id"])
    )
    return (await session.execute(select(LearnerVocabularyProgress.viewed_at).where(
        LearnerVocabularyProgress.user_id == user_id,
        LearnerVocabularyProgress.lesson_vocabulary_id == junction_id,
    ))).scalar_one()


async def mark_grammar_viewed(session: AsyncSession, user_id: UUID, junction_id: UUID) -> datetime:
    viewed_at = datetime.now(UTC)
    await session.execute(
        insert(LearnerGrammarProgress)
        .values(user_id=user_id, lesson_grammar_id=junction_id, viewed_at=viewed_at)
        .on_conflict_do_nothing(index_elements=["user_id", "lesson_grammar_id"])
    )
    return (await session.execute(select(LearnerGrammarProgress.viewed_at).where(
        LearnerGrammarProgress.user_id == user_id,
        LearnerGrammarProgress.lesson_grammar_id == junction_id,
    ))).scalar_one()


async def mark_theory_complete_if_ready(session: AsyncSession, user_id: UUID, lesson_id: UUID, vocab_ids, grammar_ids):
    # Serialize the final theory checks for this learner/lesson. Otherwise two
    # overlapping views can each miss the other's uncommitted row and neither
    # transaction records completion. The lock lasts until the caller commits.
    await session.execute(
        insert(LearnerLessonProgress).values(user_id=user_id, lesson_id=lesson_id)
        .on_conflict_do_nothing(index_elements=["user_id", "lesson_id"])
    )
    progress = (await session.execute(
        select(LearnerLessonProgress).where(
            LearnerLessonProgress.user_id == user_id,
            LearnerLessonProgress.lesson_id == lesson_id,
        ).with_for_update().execution_options(populate_existing=True)
    )).scalar_one()
    vocab_ids=set(vocab_ids); grammar_ids=set(grammar_ids)
    viewed_vocab = set((await session.execute(select(LearnerVocabularyProgress.lesson_vocabulary_id).where(
        LearnerVocabularyProgress.user_id == user_id,
        LearnerVocabularyProgress.lesson_vocabulary_id.in_(vocab_ids) if vocab_ids else False,
    ))).scalars()) if vocab_ids else set()
    viewed_grammar = set((await session.execute(select(LearnerGrammarProgress.lesson_grammar_id).where(
        LearnerGrammarProgress.user_id == user_id,
        LearnerGrammarProgress.lesson_grammar_id.in_(grammar_ids) if grammar_ids else False,
    ))).scalars()) if grammar_ids else set()
    readings_ready = await readings_complete(session, user_id, lesson_id)
    ready = vocab_ids == viewed_vocab and grammar_ids == viewed_grammar and readings_ready
    if progress.theory_completed_at is None and ready:
        progress.theory_completed_at = datetime.now(UTC)
        await session.flush()
    elif progress.theory_completed_at is not None and not readings_ready:
        progress.theory_completed_at = None
        await session.flush()
    return progress


async def reading_progress(session: AsyncSession, user_id: UUID, lesson_id: UUID):
    rows = (await session.execute(select(LessonReading, LearnerReadingProgress).outerjoin(
        LearnerReadingProgress,
        (LearnerReadingProgress.lesson_reading_id == LessonReading.id) &
        (LearnerReadingProgress.user_id == user_id) &
        (LearnerReadingProgress.reading_version == LessonReading.version),
    ).where(LessonReading.lesson_id == lesson_id).order_by(LessonReading.order_index, LessonReading.id))).all()
    return [{'id': row.id, 'completed': progress is not None,
             'completed_at': progress.completed_at if progress else None} for row, progress in rows]


async def readings_complete(session: AsyncSession, user_id: UUID, lesson_id: UUID) -> bool:
    return all(row['completed'] for row in await reading_progress(session, user_id, lesson_id))


async def mark_reading_complete(session: AsyncSession, user_id: UUID, reading: LessonReading):
    await session.execute(insert(LearnerReadingProgress).values(
        user_id=user_id, lesson_reading_id=reading.id, reading_version=reading.version, completed_at=datetime.now(UTC),
    ).on_conflict_do_update(
        index_elements=['user_id', 'lesson_reading_id'],
        set_={'reading_version': reading.version, 'completed_at': datetime.now(UTC)},
        where=LearnerReadingProgress.reading_version != reading.version,
    ))
    return await session.scalar(select(LearnerReadingProgress.completed_at).where(
        LearnerReadingProgress.user_id == user_id, LearnerReadingProgress.lesson_reading_id == reading.id))


async def ensure_hsk_started(session: AsyncSession, user_id: UUID, hsk_id: UUID) -> None:
    await session.execute(
        insert(LearnerHSKProgress)
        .values(user_id=user_id, hsk_level_id=hsk_id, started_at=datetime.now(UTC))
        .on_conflict_do_nothing(index_elements=["user_id", "hsk_level_id"])
    )


async def ensure_lesson_started(session: AsyncSession, user_id: UUID, lesson_id: UUID) -> LearnerLessonProgress:
    await session.execute(insert(LearnerLessonProgress).values(
        user_id=user_id, lesson_id=lesson_id, started_at=datetime.now(UTC)
    ).on_conflict_do_nothing(index_elements=["user_id", "lesson_id"]))
    progress = await get_lesson_progress(session, user_id, lesson_id)
    if progress.started_at is None:
        progress.started_at = datetime.now(UTC)
        await session.flush()
    return progress


async def complete_pronunciation(session: AsyncSession, user_id: UUID, section_id: UUID) -> datetime:
    completed_at = datetime.now(UTC)
    await session.execute(
        insert(PronunciationProgress)
        .values(user_id=user_id, pronunciation_section_id=section_id, completed_at=completed_at)
        .on_conflict_do_nothing(index_elements=["user_id", "pronunciation_section_id"])
    )
    await session.flush()
    existing = (
        await session.execute(select(PronunciationProgress.completed_at).where(
            PronunciationProgress.user_id == user_id,
            PronunciationProgress.pronunciation_section_id == section_id,
        ))
    ).scalar_one()
    return existing


async def get_pronunciation_lesson(session: AsyncSession, user_id: UUID, *, for_update: bool = False):
    query = select(PronunciationLessonProgress).where(PronunciationLessonProgress.user_id == user_id)
    if for_update:
        query = query.with_for_update()
    return (await session.execute(query)).scalar_one_or_none()


async def lock_pronunciation_lesson(session: AsyncSession, user_id: UUID, initial_section: int):
    await session.execute(
        insert(PronunciationLessonProgress)
        .values(user_id=user_id, section_index=initial_section, step_index=0)
        .on_conflict_do_nothing(index_elements=["user_id"])
    )
    return await get_pronunciation_lesson(session, user_id, for_update=True)


async def update_lesson_completion(session: AsyncSession, user_id: UUID, lesson_id: UUID, has_passing_exercise: bool) -> bool:
    progress = await get_lesson_progress(session, user_id, lesson_id)
    if progress is None or progress.theory_completed_at is None or progress.completed_at is not None:
        return False
    if has_passing_exercise and await readings_complete(session, user_id, lesson_id):
        progress.completed_at = datetime.now(UTC)
        await session.flush()
        return True
    return False
