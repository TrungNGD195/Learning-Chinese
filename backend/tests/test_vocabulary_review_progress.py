"""Flashcard progress is private, eligible, durable and independent of grades."""
import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.current_user import get_current_user
from app.core.errors import ApplicationError
from app.database.engine import engine
from app.database.models import (HSKLevel, LearnerLessonProgress, Lesson, LessonVocabulary, User,
    Vocabulary, VocabularyReviewPreference, VocabularyReviewState)
from app.database.session import get_db_session
from app.main import app
from app.progress import vocabulary_review as review


async def isolated(work):
    async with engine.connect() as connection:
        outer = await connection.begin()
        try:
            async with AsyncSession(bind=connection, expire_on_commit=False, join_transaction_mode='create_savepoint') as session:
                level = await session.scalar(select(HSKLevel).where(HSKLevel.level_number == 1))
                if level is None:
                    level = HSKLevel(level_number=1, order_index=1, title='HSK 1')
                    session.add(level)
                users = [User(id=uuid4(), email=f'review-{uuid4()}@example.invalid', password_hash='unused',
                              full_name='Review fixture', role='LEARNER') for _ in range(2)]
                session.add_all(users)
                await session.flush()
                number = 50_000_000+uuid4().int % 1_000_000
                lessons = [Lesson(hsk_level_id=level.id, lesson_number=number+i, title='Review fixture', status=status)
                           for i, status in enumerate(['PUBLISHED', 'PUBLISHED', 'DRAFT', 'ARCHIVED'])]
                words = [Vocabulary(hanzi=f'词{i}', pinyin='cí', vietnamese_meaning=f'từ {i}') for i in range(18)]
                words += [Vocabulary(hanzi='行', pinyin='xíng', vietnamese_meaning='đi'),
                          Vocabulary(hanzi='行', pinyin='háng', vietnamese_meaning='ngành')]
                session.add_all(lessons+words)
                await session.flush()
                for index, word in enumerate(words):
                    session.add(LessonVocabulary(lesson_id=lessons[0].id, vocabulary_id=word.id, order_index=index+1))
                private = Vocabulary(hanzi='单独', pinyin='dāndú', vietnamese_meaning='riêng')
                session.add(private)
                await session.flush()
                session.add_all([
                    LessonVocabulary(lesson_id=lessons[1].id, vocabulary_id=words[0].id, order_index=1),
                    LessonVocabulary(lesson_id=lessons[1].id, vocabulary_id=private.id, order_index=2),
                    LessonVocabulary(lesson_id=lessons[2].id, vocabulary_id=words[1].id, order_index=1),
                    LessonVocabulary(lesson_id=lessons[3].id, vocabulary_id=words[2].id, order_index=1),
                ])
                for user in users:
                    for lesson in lessons if user is users[0] else [lessons[0]]:
                        session.add(LearnerLessonProgress(user_id=user.id, lesson_id=lesson.id, completed_at=datetime.now(UTC)))
                await session.commit()
                await work(session, users[0].id, users[1].id, lessons)
        finally:
            await outer.rollback()


def test_read_only_defaults_deduplication_and_filtered_progress():
    async def work(session, user, other, lessons):
        initial = await review.review_progress(session, user)
        assert initial == dict(tracking_enabled=True, total=21, known=0, learning=0, unseen=21, cards=[])
        assert await session.scalar(select(func.count()).select_from(VocabularyReviewState).where(VocabularyReviewState.user_id == user)) == 0
        assert await session.scalar(select(func.count()).select_from(VocabularyReviewPreference).where(VocabularyReviewPreference.user_id == user)) == 0
        deck = await review.review_deck(session, user)
        assert len([card for card in deck['items'] if card['hanzi'] == '行']) == 2
        shared = next(card for card in deck['items'] if card['hanzi'] == '词0')
        assert len(shared['lessons']) == 2
        await review.set_review_state(session, user, shared['id'], review.ReviewStateInput(status='KNOWN', expected_version=0))
        filtered = await review.review_progress(session, user, lesson_id=lessons[1].id)
        assert (filtered['total'], filtered['known'], filtered['unseen']) == (2, 1, 1)
        assert (await review.review_progress(session, user, hsk_level=2))['total'] == 0
        assert (await review.review_progress(session, other))['known'] == 0
    asyncio.run(isolated(work))


def test_versions_safe_undo_tracking_and_content_access_do_not_change_learning_history():
    async def work(session, user, other, lessons):
        before = (await session.execute(select(LearnerLessonProgress.lesson_id, LearnerLessonProgress.completed_at)
                                        .where(LearnerLessonProgress.user_id == user).order_by(LearnerLessonProgress.lesson_id))).all()
        cards = (await review.review_deck(session, user))['items']
        card = cards[0]['id']
        first = await review.set_review_state(session, user, card, review.ReviewStateInput(status='KNOWN', expected_version=0))
        assert first == {'card_id': card, 'status': 'KNOWN', 'version': 1}
        with pytest.raises(ApplicationError) as error:
            await review.set_review_state(session, user, card, review.ReviewStateInput(status='LEARNING', expected_version=0))
        assert error.value.code == 'REVIEW_VERSION_CONFLICT'
        second = await review.set_review_state(session, user, card, review.ReviewStateInput(status='LEARNING', expected_version=1))
        assert second['version'] == 2
        with pytest.raises(ApplicationError):  # A stale undo cannot erase a newer rating.
            await review.set_review_state(session, user, card, review.ReviewStateInput(status=None, expected_version=1))
        undone = await review.set_review_state(session, user, card, review.ReviewStateInput(status=None, expected_version=2))
        assert undone['version'] == 3
        current = await review.review_progress(session, user)
        assert current['known'] == current['learning'] == 0 and current['unseen'] == 21
        assert current['cards'] == [undone]
        with pytest.raises(ApplicationError):  # Null status keeps its version; it never returns to revision zero.
            await review.set_review_state(session, user, card, review.ReviewStateInput(status='KNOWN', expected_version=0))
        await review.set_review_preference(session, user, False)
        assert not (await review.review_progress(session, user))['tracking_enabled']
        assert (await review.review_progress(session, other))['tracking_enabled']
        with pytest.raises(ApplicationError) as error:
            await review.set_review_state(session, user, card, review.ReviewStateInput(status='KNOWN', expected_version=3))
        assert error.value.code == 'REVIEW_TRACKING_DISABLED'
        await review.set_review_preference(session, user, True)
        private = next(row['id'] for row in cards if row['hanzi'] == '单独')
        with pytest.raises(ApplicationError) as error:
            await review.set_review_state(session, other, private, review.ReviewStateInput(status='KNOWN', expected_version=0))
        assert error.value.status_code == 404
        lessons[0].status = 'ARCHIVED'
        await session.commit()
        not_shared = next(row['id'] for row in cards if row['hanzi'] == '词1')
        with pytest.raises(ApplicationError):
            await review.set_review_state(session, user, not_shared, review.ReviewStateInput(status='KNOWN', expected_version=0))
        after = (await session.execute(select(LearnerLessonProgress.lesson_id, LearnerLessonProgress.completed_at)
                                       .where(LearnerLessonProgress.user_id == user).order_by(LearnerLessonProgress.lesson_id))).all()
        assert before == after
    asyncio.run(isolated(work))


def test_shuffle_covers_the_whole_filtered_deck_and_is_stable_across_pages():
    async def work(session, user, other, lessons):
        original = (await review.review_deck(session, user))['items']
        pages = [(await review.review_deck(session, user, page=p, page_size=7, shuffle_seed='session-1'))['items'] for p in [1, 2, 3]]
        ids = [card['id'] for page in pages for card in page]
        assert len(ids) == len(set(ids)) == 21
        assert set(ids) == {card['id'] for card in original}
        assert pages[1] == (await review.review_deck(session, user, page=2, page_size=7, shuffle_seed='session-1'))['items']
        assert ids != [card['id'] for card in original]
        assert ids != [card['id'] for card in (await review.review_deck(session, user, shuffle_seed='session-2'))['items']]
        limited = await review.review_deck(session, user, lesson_id=lessons[1].id, shuffle_seed='session-1')
        assert limited['total'] == 2
    asyncio.run(isolated(work))


def test_new_routes_require_a_learner_and_do_not_accept_forged_users_or_invalid_ratings():
    async def work(session, user, other, lessons):
        current = SimpleNamespace(id=user, role='LEARNER')
        async def user_override(): return current
        async def db_override(): yield session
        app.dependency_overrides[get_current_user] = user_override
        app.dependency_overrides[get_db_session] = db_override
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
                card = (await review.review_deck(session, user))['items'][0]['id']
                root = '/api/v1/me/vocabulary-review'
                assert (await client.get(root+'/progress')).status_code == 200
                body = {'status': 'KNOWN', 'expected_version': 0}
                assert (await client.put(root+'/cards/'+card, json={**body, 'user_id': str(other)})).status_code == 422
                assert (await client.put(root+'/cards/'+card, json={**body, 'status': 'PASSED'})).status_code == 422
                assert (await client.put(root+'/cards/'+card, json={**body, 'expected_version': -1})).status_code == 422
                assert (await client.put(root+'/cards/not-a-card', json=body)).status_code == 422
                assert (await client.put(root+'/cards/'+'0'*24, json=body)).status_code == 404
                assert (await client.get(root+'?shuffle_seed=bad%20seed')).status_code == 422
                assert (await client.put(root+'/preferences', json={'tracking_enabled': False, 'user_id': str(other)})).status_code == 422
                assert (await client.put(root+'/cards/'+card, json=body)).status_code == 200
                current.role = 'ADMIN'
                assert (await client.get(root+'/progress')).status_code == 403
                assert (await client.put(root+'/preferences', json={'tracking_enabled': False})).status_code == 403
                assert (await client.put(root+'/cards/'+card, json=body)).status_code == 403
                app.dependency_overrides.pop(get_current_user)
                assert (await client.get(root+'/progress')).status_code == 401
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db_session, None)
    asyncio.run(isolated(work))
