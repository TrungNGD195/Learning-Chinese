"""Eligible review cards and private, versioned self-ratings; never lesson grades."""
from datetime import UTC, datetime
import hashlib
import re
import unicodedata
from uuid import UUID
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Path as PathParameter
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.current_user import require_learner
from app.auth.learning_access import bypasses_learning_prerequisites
from app.database.models import (HSKLevel, LearnerLessonProgress, Lesson, LessonVocabulary,
    User, Vocabulary, VocabularyReviewPreference, VocabularyReviewState)
from app.database.session import get_db_session
from app.core.errors import ApplicationError


class ReviewOrigin(BaseModel):
    lesson_id: UUID
    hsk_level: int
    lesson_number: int
    title: str
    note: str | None


class ReviewCard(BaseModel):
    id: str
    hanzi: str
    pinyin: str
    vietnamese_meaning: str
    part_of_speech: str | None
    lessons: list[ReviewOrigin]


class ReviewDeck(BaseModel):
    items: list[ReviewCard]
    total: int
    page: int
    page_size: int


class ReviewLesson(BaseModel):
    lesson_id: UUID
    hsk_level: int
    lesson_number: int
    title: str


ReviewStatus = Literal['LEARNING', 'KNOWN']


class ReviewState(BaseModel):
    card_id: str
    status: ReviewStatus | None
    version: int


class ReviewProgress(BaseModel):
    tracking_enabled: bool
    total: int
    known: int
    learning: int
    unseen: int
    cards: list[ReviewState]


class ReviewPreferenceInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    tracking_enabled: bool


class ReviewStateInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: ReviewStatus | None
    expected_version: int = Field(ge=0)


async def review_lessons(session, user_id):
    statement = (select(Lesson.id.label('lesson_id'), HSKLevel.level_number.label('hsk_level'),
                        Lesson.lesson_number, Lesson.title)
        .join(HSKLevel, HSKLevel.id == Lesson.hsk_level_id)
        .join(LessonVocabulary, LessonVocabulary.lesson_id == Lesson.id)
        .where(Lesson.status == 'PUBLISHED')
        .distinct().order_by(HSKLevel.level_number, Lesson.lesson_number, Lesson.id))
    if not await bypasses_learning_prerequisites(session, user_id):
        statement = statement.join(LearnerLessonProgress, LearnerLessonProgress.lesson_id == Lesson.id).where(
            LearnerLessonProgress.user_id == user_id, LearnerLessonProgress.completed_at.is_not(None))
    return (await session.execute(statement)).mappings().all()


async def _eligible_cards(session, user_id, *, hsk_level=None, lesson_id=None):
    statement = (select(Vocabulary, LessonVocabulary, Lesson, HSKLevel.level_number)
        .join(LessonVocabulary, LessonVocabulary.vocabulary_id == Vocabulary.id)
        .join(Lesson, Lesson.id == LessonVocabulary.lesson_id)
        .join(HSKLevel, HSKLevel.id == Lesson.hsk_level_id)
        .where(Lesson.status == 'PUBLISHED')
        .order_by(HSKLevel.level_number, Lesson.lesson_number, LessonVocabulary.order_index))
    if not await bypasses_learning_prerequisites(session, user_id):
        statement = statement.join(LearnerLessonProgress, LearnerLessonProgress.lesson_id == Lesson.id).where(
            LearnerLessonProgress.user_id == user_id, LearnerLessonProgress.completed_at.is_not(None))
    if hsk_level is not None:
        statement = statement.where(HSKLevel.level_number == hsk_level)
    if lesson_id is not None:
        statement = statement.where(Lesson.id == lesson_id)
    cards = {}
    for word, link, lesson, level in (await session.execute(statement)).all():
        # Same spelling with another pronunciation or meaning remains a separate card.
        normalize = lambda text: ' '.join(unicodedata.normalize('NFC', text).split()).casefold()
        key = (normalize(word.hanzi), re.sub(r"[\s·’'-]", '', normalize(word.pinyin)), normalize(word.vietnamese_meaning))
        if key not in cards:
            cards[key] = dict(id=hashlib.sha256('\0'.join(key).encode()).hexdigest()[:24],
                hanzi=word.hanzi, pinyin=word.pinyin, vietnamese_meaning=word.vietnamese_meaning,
                part_of_speech=word.part_of_speech, lessons=[])
        cards[key]['lessons'].append(dict(lesson_id=lesson.id, hsk_level=level,
            lesson_number=lesson.lesson_number, title=lesson.title, note=link.note))
    return list(cards.values())


async def review_deck(session, user_id, *, hsk_level=None, lesson_id=None, page=1, page_size=50, shuffle_seed=None):
    values = await _eligible_cards(session, user_id, hsk_level=hsk_level, lesson_id=lesson_id)
    if shuffle_seed:
        # Stable across page loads: shuffling one 50-card page loses deck continuity.
        values.sort(key=lambda card: hashlib.sha256(f'{shuffle_seed}:{card["id"]}'.encode()).digest())
    return dict(items=values[(page - 1) * page_size:page * page_size], total=len(values), page=page, page_size=page_size)


async def _tracking_enabled(session, user_id):
    row = await session.get(VocabularyReviewPreference, user_id)
    return row.tracking_enabled if row else True


async def review_progress(session, user_id, *, hsk_level=None, lesson_id=None):
    eligible = await _eligible_cards(session, user_id, hsk_level=hsk_level, lesson_id=lesson_id)
    ids = [card['id'] for card in eligible]
    states = (await session.scalars(select(VocabularyReviewState).where(
        VocabularyReviewState.user_id == user_id, VocabularyReviewState.card_id.in_(ids)))).all() if ids else []
    known = sum(row.status == 'KNOWN' for row in states)
    learning = sum(row.status == 'LEARNING' for row in states)
    return dict(tracking_enabled=await _tracking_enabled(session, user_id), total=len(ids), known=known,
                learning=learning, unseen=len(ids)-known-learning,
                cards=[dict(card_id=row.card_id, status=row.status, version=row.version) for row in states])


async def set_review_preference(session, user_id, enabled):
    async with session.begin_nested():
        statement = insert(VocabularyReviewPreference).values(user_id=user_id, tracking_enabled=enabled)
        await session.execute(statement.on_conflict_do_update(index_elements=['user_id'],
            set_={'tracking_enabled': enabled, 'updated_at': datetime.now(UTC)}))
    await session.commit()
    return {'tracking_enabled': enabled}


async def set_review_state(session, user_id, card_id, body: ReviewStateInput):
    async with session.begin_nested():
        if not await _tracking_enabled(session, user_id):
            raise ApplicationError('REVIEW_TRACKING_DISABLED', 'Turn on progress tracking first', status_code=409)
        if not any(card['id'] == card_id for card in await _eligible_cards(session, user_id)):
            raise ApplicationError('NOT_FOUND', 'Review card was not found', status_code=404)
        now = datetime.now(UTC)
        if body.expected_version == 0:
            statement = insert(VocabularyReviewState).values(user_id=user_id, card_id=card_id, status=body.status,
                version=1, updated_at=now).on_conflict_do_nothing(index_elements=['user_id', 'card_id'])
        else:
            statement = update(VocabularyReviewState).where(VocabularyReviewState.user_id == user_id,
                VocabularyReviewState.card_id == card_id, VocabularyReviewState.version == body.expected_version).values(
                status=body.status, version=VocabularyReviewState.version+1, updated_at=now)
        row = (await session.execute(statement.returning(VocabularyReviewState.card_id,
            VocabularyReviewState.status, VocabularyReviewState.version))).mappings().first()
        if row is None:
            raise ApplicationError('REVIEW_VERSION_CONFLICT', 'Progress changed; reload before trying again', status_code=409)
        result = dict(row)
    await session.commit()
    return result


router = APIRouter()


@router.get('/me/vocabulary-review/lessons', response_model=list[ReviewLesson])
async def vocabulary_review_lessons(
    current_user: User = Depends(require_learner), session: AsyncSession = Depends(get_db_session),
):
    return await review_lessons(session, current_user.id)


@router.get('/me/vocabulary-review', response_model=ReviewDeck)
async def vocabulary_review(
    hsk_level: int | None = Query(default=None, ge=1, le=3),
    lesson_id: UUID | None = None,
    page: int = Query(default=1, ge=1), page_size: int = Query(default=50, ge=1, le=100),
    shuffle_seed: str | None = Query(default=None, min_length=1, max_length=64, pattern=r'^[A-Za-z0-9_-]+$'),
    current_user: User = Depends(require_learner), session: AsyncSession = Depends(get_db_session),
):
    return await review_deck(session, current_user.id, hsk_level=hsk_level, lesson_id=lesson_id, page=page, page_size=page_size, shuffle_seed=shuffle_seed)


@router.get('/me/vocabulary-review/progress', response_model=ReviewProgress)
async def vocabulary_review_progress(
    hsk_level: int | None = Query(default=None, ge=1, le=3), lesson_id: UUID | None = None,
    current_user: User = Depends(require_learner), session: AsyncSession = Depends(get_db_session),
):
    return await review_progress(session, current_user.id, hsk_level=hsk_level, lesson_id=lesson_id)


@router.put('/me/vocabulary-review/preferences', response_model=ReviewPreferenceInput)
async def vocabulary_review_preference(body: ReviewPreferenceInput,
    current_user: User = Depends(require_learner), session: AsyncSession = Depends(get_db_session),
):
    return await set_review_preference(session, current_user.id, body.tracking_enabled)


@router.put('/me/vocabulary-review/cards/{card_id}', response_model=ReviewState)
async def vocabulary_review_state(card_id: Annotated[str, PathParameter(pattern=r'^[0-9a-f]{24}$')], body: ReviewStateInput,
    current_user: User = Depends(require_learner), session: AsyncSession = Depends(get_db_session),
):
    return await set_review_state(session, current_user.id, card_id, body)
