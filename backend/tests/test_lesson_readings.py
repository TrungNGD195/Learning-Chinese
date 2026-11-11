import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.auth.current_user import get_current_user
from app.core.errors import ApplicationError
from app.database.models import (
    Assessment, AssessmentAttempt, AttemptAnswer, Grammar, HSKLevel, LearnerGrammarProgress,
    LearnerHSKProgress, LearnerLessonProgress, LearnerReadingProgress, LearnerVocabularyProgress,
    Lesson, LessonGrammar, LessonReading, LessonVocabulary, Question, QuestionOption, User, Vocabulary,
)
from app.database.seeds.required import seed_required_data
from app.database.session import SessionFactory
from app.main import app
from app.progress import service as progress_service


@pytest.fixture
def reading_scenario(monkeypatch):
    ids = {key: uuid4() for key in ('user', 'lesson', 'other_lesson', 'word', 'grammar', 'vocab_link', 'grammar_link', 'reading', 'second', 'assessment', 'question', 'option')}
    async def setup():
        await seed_required_data()
        async with SessionFactory.begin() as session:
            level = await session.scalar(select(HSKLevel).where(HSKLevel.level_number == 1))
            number = 3_000_000 + ids['lesson'].int % 100_000
            session.add_all([
                User(id=ids['user'], email=f"reading-{ids['user']}@example.invalid", password_hash='test-only', full_name='Reading learner', role='LEARNER'),
                Lesson(id=ids['lesson'], hsk_level_id=level.id, lesson_number=number, title='Reading lesson', status='PUBLISHED'),
                Lesson(id=ids['other_lesson'], hsk_level_id=level.id, lesson_number=number + 100001, title='Other lesson', status='PUBLISHED'),
                Vocabulary(id=ids['word'], hanzi='你', pinyin='nǐ', vietnamese_meaning='bạn'),
                Grammar(id=ids['grammar'], name='Greeting', explanation='Chào hỏi'),
            ])
            await session.flush()
            session.add_all([
                LessonVocabulary(id=ids['vocab_link'], lesson_id=ids['lesson'], vocabulary_id=ids['word'], order_index=1),
                LessonGrammar(id=ids['grammar_link'], lesson_id=ids['lesson'], grammar_id=ids['grammar'], order_index=1),
                LessonReading(id=ids['reading'], lesson_id=ids['lesson'], order_index=1, title='Chào hỏi', content='A：你好！\nB：你好！'),
                Assessment(id=ids['assessment'], lesson_id=ids['lesson'], type='LESSON_EXERCISE', title='Practice', status='PUBLISHED', pass_threshold=80),
            ])
            await session.flush()
            session.add(Question(id=ids['question'], assessment_id=ids['assessment'], type='multiple_choice', prompt='Chọn lời chào.', order_index=1, points=1))
            await session.flush()
            session.add(QuestionOption(id=ids['option'], question_id=ids['question'], option_text='你好', is_correct=True, order_index=1))
    asyncio.run(setup())

    # Existing progression tests own curriculum/pronunciation access. Here only
    # that prerequisite is isolated so the real three-part gate can be tested.
    async def access(session, user_id, lesson_id):
        lesson = await session.get(Lesson, lesson_id)
        if not lesson or lesson.status != 'PUBLISHED':
            raise ApplicationError('NOT_FOUND', 'Lesson was not found', status_code=404)
        return lesson
    monkeypatch.setattr(progress_service, 'require_lesson_access', access)
    async def current_user():
        async with SessionFactory() as session:
            return await session.get(User, ids['user'])
    app.dependency_overrides[get_current_user] = current_user

    def set_state(role='LEARNER', status='PUBLISHED'):
        async def update():
            async with SessionFactory.begin() as session:
                (await session.get(User, ids['user'])).role = role
                (await session.get(Lesson, ids['lesson'])).status = status
        asyncio.run(update())
    ids['set_state'] = set_state
    try:
        with TestClient(app) as client:
            yield ids, client
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        async def cleanup():
            async with SessionFactory.begin() as session:
                attempts = select(AssessmentAttempt.id).where(AssessmentAttempt.assessment_id == ids['assessment'])
                await session.execute(delete(AttemptAnswer).where(AttemptAnswer.assessment_attempt_id.in_(attempts)))
                await session.execute(delete(AssessmentAttempt).where(AssessmentAttempt.assessment_id == ids['assessment']))
                await session.execute(delete(QuestionOption).where(QuestionOption.question_id == ids['question']))
                await session.execute(delete(Question).where(Question.id == ids['question']))
                await session.execute(delete(Assessment).where(Assessment.id == ids['assessment']))
                for model in (LearnerReadingProgress, LearnerVocabularyProgress, LearnerGrammarProgress, LearnerLessonProgress, LearnerHSKProgress):
                    await session.execute(delete(model).where(model.user_id == ids['user']))
                await session.execute(delete(LessonReading).where(LessonReading.lesson_id.in_((ids['lesson'], ids['other_lesson']))))
                await session.execute(delete(LessonVocabulary).where(LessonVocabulary.lesson_id == ids['lesson']))
                await session.execute(delete(LessonGrammar).where(LessonGrammar.lesson_id == ids['lesson']))
                await session.execute(delete(Vocabulary).where(Vocabulary.id == ids['word']))
                await session.execute(delete(Grammar).where(Grammar.id == ids['grammar']))
                await session.execute(delete(Lesson).where(Lesson.id.in_((ids['lesson'], ids['other_lesson']))))
                await session.execute(delete(User).where(User.id == ids['user']))
        asyncio.run(cleanup())


def complete_part(client, ids, part):
    root = f"/api/v1/lessons/{ids['lesson']}/theory"
    if part == 'reading':
        return client.post(f"{root}/readings/{ids['reading']}/complete", json={'version': 1})
    return client.post(f"{root}/{part}/{ids['vocab_link' if part == 'vocabulary' else 'grammar_link']}/view")


@pytest.mark.parametrize('order', [
    ('vocabulary', 'grammar', 'reading'), ('reading', 'vocabulary', 'grammar'), ('grammar', 'reading', 'vocabulary'),
])
def test_each_theory_part_is_required_before_read_start_and_submit(reading_scenario, order):
    ids, client = reading_scenario
    root = f"/api/v1/assessments/{ids['assessment']}"
    # Simulate a pre-existing attempt to prove the submit endpoint cannot bypass
    # a newly required reading, independently of UI and start-attempt gating.
    attempt_id = uuid4()
    async def attempt():
        async with SessionFactory.begin() as session:
            session.add(AssessmentAttempt(id=attempt_id, user_id=ids['user'], assessment_id=ids['assessment'], attempt_number=1, status='IN_PROGRESS'))
    asyncio.run(attempt())
    submit = f'/api/v1/assessment-attempts/{attempt_id}/submit'
    answer = {'answers': [{'question_id': str(ids['question']), 'answer': {'option_id': str(ids['option'])}}]}
    for part in order:
        for result in (client.get(root), client.post(root + '/attempts'), client.post(submit, json=answer)):
            assert result.status_code == 403, result.text
            assert result.json()['error']['code'] == 'THEORY_INCOMPLETE'
        response = complete_part(client, ids, part)
        assert response.status_code == 200, response.text
    assert response.json()['theory_completed_at'] is not None
    assert client.get(root).status_code == 200
    assert client.post(root + '/attempts').status_code == 200
    result = client.post(submit, json=answer)
    assert result.status_code == 200, result.text
    assert result.json()['passed'] is True


def test_reading_is_explicit_idempotent_and_scoped_to_the_lesson(reading_scenario):
    ids, client = reading_scenario
    lesson = client.get(f"/api/v1/lessons/{ids['lesson']}")
    assert lesson.status_code == 200 and len(lesson.json()['readings']) == 1
    progress = f"/api/v1/me/progress/lessons/{ids['lesson']}"
    assert client.get(progress).json()['readings'][0]['completed'] is False
    wrong = client.post(f"/api/v1/lessons/{ids['other_lesson']}/theory/readings/{ids['reading']}/complete", json={'version': 1})
    assert wrong.status_code == 404
    assert client.post(f"/api/v1/lessons/{ids['lesson']}/theory/readings/{ids['reading']}/complete", json={}).status_code == 422
    first = complete_part(client, ids, 'reading')
    second = complete_part(client, ids, 'reading')
    assert first.status_code == second.status_code == 200
    assert first.json()['completed_at'] == second.json()['completed_at']
    assert client.get(progress).json()['readings'][0]['completed'] is True
    assert client.get(progress).json()['theory_completed_at'] is None


def test_admin_reading_crud_validation_roles_and_readonly_archive(reading_scenario):
    ids, client = reading_scenario
    root = f"/api/v1/admin/lessons/{ids['lesson']}/readings"
    body = {'order_index': 2, 'title': 'Bài khóa mới', 'content': '你好吗？', 'pinyin': 'Nǐ hǎo ma?', 'vietnamese_translation': 'Bạn khỏe không?'}
    assert client.get(root).status_code == 403
    assert client.post(root, json=body).status_code == 403
    ids['set_state']('ADMIN', 'DRAFT')
    for field in ('title', 'content'):
        assert client.post(root, json={**body, field: '  '}).status_code == 422
    created = client.post(root, json=body)
    assert created.status_code == 201, created.text
    reading = created.json()
    assert reading['version'] == 1
    assert client.post(root, json=body).json()['error']['code'] == 'READING_ORDER_CONFLICT'
    changed = client.put(root + '/' + reading['id'], json={**body, 'content': '我很好。'})
    assert changed.status_code == 200 and changed.json()['version'] == 2
    reordered = client.put(root + '/' + reading['id'], json={**body, 'content': '我很好。', 'order_index': 3})
    assert reordered.status_code == 200 and reordered.json()['version'] == 2
    assert client.put(f"/api/v1/admin/lessons/{ids['other_lesson']}/readings/{reading['id']}", json=body).status_code == 404
    assert client.delete(root + '/' + reading['id']).status_code == 200
    ids['set_state']('ADMIN', 'ARCHIVED')
    assert client.get(root).status_code == 200
    assert client.post(root, json=body).status_code == 409
    assert client.put(root + '/' + str(ids['reading']), json={**body, 'order_index': 1}).status_code == 409


def test_changed_reading_requires_current_version_and_keeps_historical_result(reading_scenario):
    ids, client = reading_scenario
    for part in ('vocabulary', 'grammar', 'reading'):
        assert complete_part(client, ids, part).status_code == 200
    root = f"/api/v1/assessments/{ids['assessment']}"
    attempt = client.post(root + '/attempts').json()
    submitted = client.post(f"/api/v1/assessment-attempts/{attempt['id']}/submit", json={'answers': [{'question_id': str(ids['question']), 'answer': {'option_id': str(ids['option'])}}]})
    assert submitted.status_code == 200 and submitted.json()['passed'] is True
    ids['set_state']('ADMIN')
    edited = client.put(f"/api/v1/admin/lessons/{ids['lesson']}/readings/{ids['reading']}", json={'order_index': 1, 'title': 'Chào hỏi', 'content': 'A：你好！\nB：你好吗？'})
    assert edited.status_code == 200 and edited.json()['version'] == 2
    ids['set_state']()
    assert client.get(root).status_code == 403
    progress = client.get(f"/api/v1/me/progress/lessons/{ids['lesson']}").json()
    assert progress['theory_completed_at'] is None and progress['readings'][0]['completed'] is False
    stale = complete_part(client, ids, 'reading')
    assert stale.status_code == 409 and stale.json()['error']['code'] == 'READING_VERSION_CHANGED'
    current = client.post(f"/api/v1/lessons/{ids['lesson']}/theory/readings/{ids['reading']}/complete", json={'version': 2})
    assert current.status_code == 200 and current.json()['theory_completed_at']
    assert client.get(root).status_code == 200
    history = client.get(f"/api/v1/me/assessment-attempts/{attempt['id']}")
    assert history.status_code == 200 and history.json()['passed'] is True and history.json()['score'] == 100


def test_multiple_readings_all_required_and_history_prevents_deletion(reading_scenario):
    ids, client = reading_scenario
    async def second():
        async with SessionFactory.begin() as session:
            session.add(LessonReading(id=ids['second'], lesson_id=ids['lesson'], order_index=2, title='Đọc tiếp', content='你好吗？'))
    asyncio.run(second())
    for part in ('vocabulary', 'grammar', 'reading'):
        assert complete_part(client, ids, part).status_code == 200
    assert client.get(f"/api/v1/assessments/{ids['assessment']}").status_code == 403
    assert client.post(f"/api/v1/lessons/{ids['lesson']}/theory/readings/{ids['second']}/complete", json={'version': 1}).json()['theory_completed_at']
    ids['set_state']('ADMIN', 'DRAFT')
    blocked = client.delete(f"/api/v1/admin/lessons/{ids['lesson']}/readings/{ids['reading']}")
    assert blocked.status_code == 409 and blocked.json()['error']['code'] == 'ITEM_HAS_LEARNER_HISTORY'


def test_existing_theory_completion_is_preserved_for_lessons_without_readings(reading_scenario):
    ids, client = reading_scenario
    completed_at = datetime.now(UTC)
    async def legacy():
        async with SessionFactory.begin() as session:
            await session.execute(delete(LessonReading).where(LessonReading.lesson_id == ids['lesson']))
            session.add(LearnerLessonProgress(user_id=ids['user'], lesson_id=ids['lesson'], started_at=completed_at, theory_completed_at=completed_at))
    asyncio.run(legacy())
    assert client.get(f"/api/v1/lessons/{ids['lesson']}").status_code == 200
    data = client.get(f"/api/v1/me/progress/lessons/{ids['lesson']}").json()
    assert data['readings'] == [] and data['theory_completed_at'] is not None
    assert client.get(f"/api/v1/assessments/{ids['assessment']}").status_code == 200
