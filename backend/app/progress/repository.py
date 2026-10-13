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
    progress = await get_lesson_progress(session, user_id, lesson_id)
    vocab_ids=set(vocab_ids); grammar_ids=set(grammar_ids)
    viewed_vocab = set((await session.execute(select(LearnerVocabularyProgress.lesson_vocabulary_id).where(
        LearnerVocabularyProgress.user_id == user_id,
        LearnerVocabularyProgress.lesson_vocabulary_id.in_(vocab_ids) if vocab_ids else False,
    ))).scalars()) if vocab_ids else set()
    viewed_grammar = set((await session.execute(select(LearnerGrammarProgress.lesson_grammar_id).where(
        LearnerGrammarProgress.user_id == user_id,
        LearnerGrammarProgress.lesson_grammar_id.in_(grammar_ids) if grammar_ids else False,
    ))).scalars()) if grammar_ids else set()
    if progress is None:
        progress = LearnerLessonProgress(user_id=user_id, lesson_id=lesson_id)
        session.add(progress)
        await session.flush()
    if progress.theory_completed_at is None and vocab_ids == viewed_vocab and grammar_ids == viewed_grammar:
        progress.theory_completed_at = datetime.now(UTC)
        await session.flush()
    return progress


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


async def update_lesson_completion(session: AsyncSession, user_id: UUID, lesson_id: UUID, has_passing_exercise: bool) -> bool:
    progress = await get_lesson_progress(session, user_id, lesson_id)
    if progress is None or progress.theory_completed_at is None or progress.completed_at is not None:
        return False
    if has_passing_exercise:
        progress.completed_at = datetime.now(UTC)
        await session.flush()
        return True
    return False
