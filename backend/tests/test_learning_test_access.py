"""A configured test learner can explore published learning without fake progress."""
import asyncio
from uuid import uuid4

import pytest
from pydantic import ValidationError
from app.auth.learning_access import bypasses_learning_prerequisites
from app.core.config import Settings, get_settings
from app.core.errors import ApplicationError
from app.database.models import Assessment, Lesson, LessonVocabulary, User, Vocabulary
from app.exercise import service as exercises
from app.hsk_exam import service as exams
from app.progress import service as progress
from app.progress.vocabulary_review import review_deck, review_lessons
from tests.test_hsk_mock_exams import isolated


def test_test_learner_configuration_accepts_only_explicit_uuids():
    ident = uuid4()
    values = dict(app_env='test', debug=False, secret_key='test-only-secret',
                  test_database_url='postgresql+psycopg://localhost/chinese_learning_test')
    assert Settings(_env_file=None, **values, learning_test_user_ids='').learning_test_user_ids == ()
    assert Settings(_env_file=None, **values, learning_test_user_ids=f' {ident}, ').learning_test_user_ids == (ident,)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values, learning_test_user_ids='student456')


def test_only_the_configured_active_learner_gets_the_capability(monkeypatch):
    async def scenario(session, tester, ordinary):
        monkeypatch.setattr(get_settings(), 'learning_test_user_ids', (tester, uuid4()))
        assert await bypasses_learning_prerequisites(session, tester)
        other = await session.get(User, ordinary)
        other.full_name = 'student456'
        other.email = 'student456@example.invalid'
        await session.flush()
        assert not await bypasses_learning_prerequisites(session, ordinary)
        account = await session.get(User, tester)
        account.is_active = False
        assert not await bypasses_learning_prerequisites(session, tester)
        account.is_active = True
        account.role = 'ADMIN'
        assert not await bypasses_learning_prerequisites(session, tester)
        assert not await bypasses_learning_prerequisites(session, uuid4())
    asyncio.run(isolated(scenario, complete=False))


def test_lesson_practice_exam_and_review_prerequisites_are_account_scoped(monkeypatch):
    async def scenario(session, tester, ordinary):
        monkeypatch.setattr(get_settings(), 'learning_test_user_ids', (tester,))
        _, states, _, pronunciation_complete, _ = await progress.progression_snapshot(session, tester)
        assert not pronunciation_complete
        entries = [entry for group in states.values() for entry in group if entry['active']]
        assert len(entries) >= 40 and all(entry['state'] == 'AVAILABLE' and not entry['complete'] for entry in entries)
        target = next(entry['lesson'] for entry in entries if entry['lesson'].lesson_number == 15)
        lesson_id = target.id
        assert (await progress.require_lesson_access(session, tester, lesson_id)).id == lesson_id
        with pytest.raises(ApplicationError):
            await progress.require_lesson_access(session, ordinary, lesson_id)
        state = await progress.lesson_progress(session, tester, lesson_id)
        assert state['prerequisites_bypassed'] and state['theory_completed_at'] is None and state['completed_at'] is None

        assessment = Assessment(type='LESSON_EXERCISE', lesson_id=lesson_id, title='Test prerequisite access', status='PUBLISHED')
        session.add(assessment)
        word = Vocabulary(hanzi='测试', pinyin='cèshì', vietnamese_meaning='kiểm thử')
        session.add(word)
        await session.flush()
        session.add(LessonVocabulary(lesson_id=lesson_id, vocabulary_id=word.id, order_index=9999))
        await session.flush()
        assert (await exercises.assessment_payload(session, tester, assessment.id))['pass_threshold'] == 80
        with pytest.raises(ApplicationError):
            await exercises.assessment_payload(session, ordinary, assessment.id)
        assert (await exercises.start_attempt(session, tester, assessment.id))[1] == 201
        assert any(row['lesson_id'] == lesson_id for row in await review_lessons(session, tester))
        assert (await review_deck(session, tester, lesson_id=lesson_id))['total'] >= 1
        assert not await review_lessons(session, ordinary)
        assert (await review_deck(session, ordinary))['total'] == 0

        for level in (1, 2, 3):
            access = await exams.availability(session, tester, level)
            assert access['unlocked'] and access['completed_lessons'] == 0
            attempt = await exams.start(session, tester, level)
            assert attempt['status'] == 'IN_PROGRESS' and attempt['result'] is None
            assert not (await exams.availability(session, ordinary, level))['unlocked']
            with pytest.raises(ApplicationError):
                await exams.start(session, ordinary, level)
            with pytest.raises(ApplicationError):
                await exams.get_session(session, ordinary, attempt['id'])

        # Publication and account administration remain enforced.
        target = await session.get(Lesson, lesson_id)
        target.status = 'DRAFT'
        await session.flush()
        with pytest.raises(ApplicationError) as error:
            await progress.require_lesson_access(session, tester, lesson_id)
        assert error.value.status_code == 404
        with pytest.raises(ApplicationError):
            await exercises.assessment_payload(session, tester, assessment.id)
        target.status = 'PUBLISHED'
        assessment.status = 'DRAFT'
        await session.flush()
        with pytest.raises(ApplicationError):
            await exercises.assessment_payload(session, tester, assessment.id)

        monkeypatch.setattr(get_settings(), 'learning_test_user_ids', ())
        assert not (await exams.availability(session, tester, 1))['unlocked']
        assert (await review_deck(session, tester))['total'] == 0
        with pytest.raises(ApplicationError):
            await progress.require_lesson_access(session, tester, lesson_id)
    asyncio.run(isolated(scenario, complete=False))


def test_pronunciation_can_be_visited_and_completed_out_of_order_without_completing_other_sections(monkeypatch):
    async def scenario(session, tester, ordinary):
        monkeypatch.setattr(get_settings(), 'learning_test_user_ids', (tester,))
        state = await progress.pronunciation_lesson(session, tester)
        assert state['prerequisites_bypassed'] and state['completed_at'] is None
        assert all(section['completed_at'] is None for section in state['sections'])
        advanced = await progress.advance_pronunciation(session, tester, 'SANDHI', 4)
        assert advanced['prerequisites_bypassed'] and advanced['step_index'] == 5
        with pytest.raises(ApplicationError):
            await progress.advance_pronunciation(session, ordinary, 'SANDHI', 4)
        with pytest.raises(ApplicationError):
            await progress.advance_pronunciation(session, tester, 'SANDHI', 999)
        tone = next(section for section in state['sections'] if section['code'] == 'TONES')
        await progress.complete_pronunciation(session, tester, tone['id'])
        after = await progress.pronunciation_lesson(session, tester)
        assert [row['code'] for row in after['sections'] if row['completed_at']] == ['TONES']
        assert after['completed_at'] is None
        with pytest.raises(ApplicationError):
            await progress.complete_pronunciation(session, ordinary, tone['id'])
    asyncio.run(isolated(scenario, complete=False))
