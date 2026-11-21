"""Read-only review deck derived from the learner's completed, published lessons."""
import hashlib
import re
import unicodedata
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.current_user import require_learner
from app.database.models import HSKLevel, LearnerLessonProgress, Lesson, LessonVocabulary, User, Vocabulary
from app.database.session import get_db_session


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


async def review_deck(session, user_id, *, hsk_level=None, lesson_id=None, page=1, page_size=50):
    statement = (select(Vocabulary, LessonVocabulary, Lesson, HSKLevel.level_number)
        .join(LessonVocabulary, LessonVocabulary.vocabulary_id == Vocabulary.id)
        .join(Lesson, Lesson.id == LessonVocabulary.lesson_id)
        .join(HSKLevel, HSKLevel.id == Lesson.hsk_level_id)
        .join(LearnerLessonProgress, LearnerLessonProgress.lesson_id == Lesson.id)
        .where(LearnerLessonProgress.user_id == user_id,
               LearnerLessonProgress.completed_at.is_not(None), Lesson.status == 'PUBLISHED')
        .order_by(HSKLevel.level_number, Lesson.lesson_number, LessonVocabulary.order_index))
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
    values = list(cards.values())
    return dict(items=values[(page - 1) * page_size:page * page_size], total=len(values), page=page, page_size=page_size)


router = APIRouter()


@router.get('/me/vocabulary-review', response_model=ReviewDeck)
async def vocabulary_review(
    hsk_level: int | None = Query(default=None, ge=1, le=3),
    lesson_id: UUID | None = None,
    page: int = Query(default=1, ge=1), page_size: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(require_learner), session: AsyncSession = Depends(get_db_session),
):
    return await review_deck(session, current_user.id, hsk_level=hsk_level, lesson_id=lesson_id, page=page, page_size=page_size)
