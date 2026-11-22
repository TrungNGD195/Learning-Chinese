import asyncio
from types import SimpleNamespace
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import func, select

from app.database.models import (
    Assessment, AssessmentAttempt, HSKLevel, LearnerLessonProgress,
    LearnerVocabularyProgress, Lesson, LessonVocabulary, Question, User, Vocabulary,
)
from app.database.session import SessionFactory
from app.progress.vocabulary_review import ReviewDeck, ReviewLesson, review_deck, review_lessons
from scripts.import_curriculum_refresh import load_definitions, refresh, word_key


def test_review_api_requires_student_and_validates_filters():
    from fastapi.testclient import TestClient
    from app.auth.current_user import get_current_user
    from app.main import app
    with TestClient(app) as client:
        assert client.get('/api/v1/me/vocabulary-review').status_code == 401
        assert client.get('/api/v1/me/vocabulary-review/lessons').status_code == 401
        try:
            app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4(), role='ADMIN')
            assert client.get('/api/v1/me/vocabulary-review').status_code == 403
            assert client.get('/api/v1/me/vocabulary-review/lessons').status_code == 403
            app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4(), role='LEARNER')
            assert client.get('/api/v1/me/vocabulary-review?page_size=101').status_code == 422
            assert client.get('/api/v1/me/vocabulary-review?lesson_id=invalid').status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_user, None)


def test_all_25_drafts_have_unique_senses_valid_questions_and_correct_sources():
    definitions = load_definitions()
    assert len(definitions) == 25
    words = [word_key(w) for d in definitions for w in d['vocabulary']]
    assert len(words) == len(set(words))
    for d in definitions:
        n, h = d['lesson']['lesson_number'], d['lesson']['hsk_level']
        assert d['source_documents']['vocabulary'] == ('HSK1 PDF' if h == 1 and n >= 14 else 'DOCX')
        assert all(q['rubric'] for q in d['questions'])
        assert all(r['content'] and r['vietnamese_translation'] for r in d['readings'])
    assert {'上', '火车', '听见'} <= {w['hanzi'] for w in definitions[13]['vocabulary']}
    assert {'爱', '首都', '家人'} <= {w['hanzi'] for w in definitions[14]['vocabulary']}


def test_refresh_preserves_lesson_word_progress_and_attempts_and_is_idempotent():
    async def run():
        async with SessionFactory() as session:
            try:
                # A unique level keeps the test isolated, with rollback at the end.
                level_number = 10_000_000 + uuid4().int % 1_000_000
                level = HSKLevel(level_number=level_number, order_index=level_number)
                user = User(email=f'{uuid4()}@example.invalid', full_name='Review learner', password_hash='test-only', role='LEARNER')
                session.add_all([level, user])
                await session.flush()
                lesson = Lesson(hsk_level_id=level.id, lesson_number=1, title='Existing', status='PUBLISHED')
                session.add(lesson)
                await session.flush()
                first = load_definitions()[0]
                word = Vocabulary(**{k: first['vocabulary'][0][k] for k in ('hanzi', 'pinyin', 'vietnamese_meaning', 'part_of_speech')})
                session.add(word)
                await session.flush()
                link = LessonVocabulary(lesson_id=lesson.id, vocabulary_id=word.id, order_index=1)
                old_assessment = Assessment(type='LESSON_EXERCISE', lesson_id=lesson.id, title='Original', status='PUBLISHED', pass_threshold=80)
                session.add_all([link, old_assessment])
                await session.flush()
                now = datetime.now(timezone.utc)
                session.add_all([LearnerVocabularyProgress(user_id=user.id, lesson_vocabulary_id=link.id, viewed_at=now),
                    LearnerLessonProgress(user_id=user.id, lesson_id=lesson.id, completed_at=now),
                    AssessmentAttempt(user_id=user.id, assessment_id=old_assessment.id, attempt_number=1, status='GRADED', score=90, passed=True)])
                first['lesson']['hsk_level'] = level_number
                first['key'] += f'-test-{level_number}'
                original_id, link_id = lesson.id, link.id
                report = await refresh(session, [first])
                assert report[0]['id'] == str(original_id)
                assert lesson.status == 'DRAFT' and old_assessment.status == 'ARCHIVED'
                assert (await session.get(LessonVocabulary, link_id)).lesson_id == original_id
                assert await session.scalar(select(func.count()).select_from(AssessmentAttempt).where(AssessmentAttempt.assessment_id == old_assessment.id)) == 1
                assert (await review_deck(session, user.id))['total'] == 0  # Drafts cannot leak.
                count = await session.scalar(select(func.count()).select_from(Question))
                lesson.title = 'Admin edited after import'
                again = await refresh(session, [first])
                assert again[0]['action'] == 'already_imported_preserved'
                assert lesson.title == 'Admin edited after import'
                assert await session.scalar(select(func.count()).select_from(Question)) == count
            finally:
                await session.rollback()
    asyncio.run(run())


def test_flashcards_only_own_completed_published_lessons_and_keep_distinct_senses():
    async def run():
        async with SessionFactory() as session:
            try:
                level = HSKLevel(level_number=20_000_000 + uuid4().int % 1_000_000, order_index=9999)
                users = [User(email=f'{uuid4()}@example.invalid', full_name='Test learner', password_hash='test-only', role='LEARNER') for _ in range(2)]
                session.add_all([level, *users])
                await session.flush()
                now = datetime.now(timezone.utc)
                for n, (status, owner, completed, meaning) in enumerate([
                    ('PUBLISHED', 0, True, 'trên'), ('PUBLISHED', 0, True, 'trên'),
                    ('PUBLISHED', 0, True, 'lên xe'), ('DRAFT', 0, True, 'bản nháp'),
                    ('PUBLISHED', 1, True, 'của người khác'), ('PUBLISHED', 0, False, 'chưa xong'),
                ], 1):
                    lesson = Lesson(hsk_level_id=level.id, lesson_number=n, title=str(n), status=status)
                    word = Vocabulary(hanzi='上', pinyin='shàng', vietnamese_meaning=meaning)
                    session.add_all([lesson, word])
                    await session.flush()
                    session.add_all([LessonVocabulary(lesson_id=lesson.id, vocabulary_id=word.id, order_index=1),
                        LearnerLessonProgress(user_id=users[owner].id, lesson_id=lesson.id, completed_at=now if completed else None)])
                await session.flush()
                deck = ReviewDeck.model_validate(await review_deck(session, users[0].id))
                assert deck.total == 2 and len(deck.items[0].lessons) == 2
                assert {c.vietnamese_meaning for c in deck.items} == {'trên', 'lên xe'}
                page2 = await review_deck(session, users[0].id, page=2, page_size=1)
                assert page2['total'] == 2 and len(page2['items']) == 1
                assert (await review_deck(session, users[0].id, lesson_id=uuid4()))['total'] == 0
                options = [ReviewLesson.model_validate(row) for row in await review_lessons(session, users[0].id)]
                assert [row.lesson_number for row in options] == [1, 2, 3]
                selected = await review_deck(session, users[0].id, hsk_level=level.level_number, lesson_id=options[2].lesson_id)
                assert selected['total'] == 1 and selected['items'][0]['vietnamese_meaning'] == 'lên xe'
                assert len(selected['items'][0]['lessons']) == 1
                assert (await review_deck(session, users[0].id, hsk_level=level.level_number + 1, lesson_id=options[2].lesson_id))['total'] == 0
                other_options = [ReviewLesson.model_validate(row) for row in await review_lessons(session, users[1].id)]
                assert [row.lesson_number for row in other_options] == [5]
                assert (await review_deck(session, users[0].id, lesson_id=other_options[0].lesson_id))['total'] == 0
            finally:
                await session.rollback()
    asyncio.run(run())
