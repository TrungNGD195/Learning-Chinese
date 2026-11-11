import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.auth.current_user import get_current_user
from app.database.models import Assessment, AssessmentAttempt, HSKLevel, LearnerLessonProgress, Lesson, Question, User
from app.database.session import SessionFactory
from app.main import app


@pytest.fixture
def publication(monkeypatch):
    ids = {key: uuid4() for key in ('level', 'lesson', 'first', 'second', 'archived', 'user', 'attempt', 'progress')}
    now = datetime.now(UTC)
    role = ['ADMIN']
    ingested = []

    async def setup():
        async with SessionFactory.begin() as session:
            session.add_all([
                HSKLevel(id=ids['level'], level_number=5_000_000 + ids['level'].int % 1_000_000, order_index=900, title='Publication test'),
                User(id=ids['user'], email=f"publication-{ids['user']}@example.invalid", password_hash='test-only', full_name='Editor', role='ADMIN'),
            ])
            await session.flush()
            session.add(Lesson(id=ids['lesson'], hsk_level_id=ids['level'], lesson_number=1, title='Package lesson', status='DRAFT'))
            await session.flush()
            session.add_all([Assessment(id=ids[key], type='LESSON_EXERCISE', lesson_id=ids['lesson'], title=key, status=status, pass_threshold=80) for key, status in [('first', 'DRAFT'), ('second', 'REVIEW'), ('archived', 'ARCHIVED')]])
            await session.flush()
            for key in ('first', 'second'):
                session.add_all([Question(assessment_id=ids[key], type=('fill_blank', 'translate_zh_vi', 'sentence_writing')[index % 3], prompt=f'Question {index}', order_index=index + 1, reference_answer='你好', points=1) for index in range(30)])
            session.add_all([
                AssessmentAttempt(id=ids['attempt'], user_id=ids['user'], assessment_id=ids['archived'], attempt_number=1, status='GRADED', score=90, passed=True),
                LearnerLessonProgress(id=ids['progress'], user_id=ids['user'], lesson_id=ids['lesson'], started_at=now, theory_completed_at=now, completed_at=now),
            ])
    asyncio.run(setup())

    async def current():
        async with SessionFactory() as session:
            user = await session.get(User, ids['user'])
            user.role = role[0]
            return user

    async def ingestion(session, lesson_id, storage):
        # Prove publication has committed before the optional knowledge pipeline.
        async with SessionFactory() as observer:
            assert (await observer.get(Lesson, lesson_id)).status == 'PUBLISHED'
            assert (await observer.get(Assessment, ids['first'])).status == 'PUBLISHED'
        ingested.append(lesson_id)

    monkeypatch.setattr('app.ingestion.orchestrator.process_published_lesson', ingestion)
    app.dependency_overrides[get_current_user] = current
    ids.update(now=now, role=role, ingested=ingested)
    try:
        with TestClient(app) as client:
            yield ids, client
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        async def cleanup():
            async with SessionFactory.begin() as session:
                await session.execute(delete(AssessmentAttempt).where(AssessmentAttempt.id == ids['attempt']))
                await session.execute(delete(LearnerLessonProgress).where(LearnerLessonProgress.id == ids['progress']))
                await session.execute(delete(Question).where(Question.assessment_id.in_([ids['first'], ids['second'], ids['archived']])))
                await session.execute(delete(Assessment).where(Assessment.lesson_id == ids['lesson']))
                await session.execute(delete(Lesson).where(Lesson.id == ids['lesson']))
                await session.execute(delete(HSKLevel).where(HSKLevel.id == ids['level']))
                await session.execute(delete(User).where(User.id == ids['user']))
        asyncio.run(cleanup())


def snapshot(ids):
    async def read():
        async with SessionFactory() as session:
            lesson = await session.get(Lesson, ids['lesson'])
            assessments = (await session.execute(select(Assessment).where(Assessment.lesson_id == lesson.id))).scalars().all()
            progress = await session.get(LearnerLessonProgress, ids['progress'])
            attempt = await session.get(AssessmentAttempt, ids['attempt'])
            return {'lesson': lesson.status, 'published_at': lesson.published_at,
                    'assessments': {row.title: row.status for row in assessments},
                    'progress': progress.completed_at, 'score': attempt.score}
    return asyncio.run(read())


def test_publish_package_commits_all_active_parts_together_and_preserves_history(publication):
    ids, client = publication
    result = client.post(f"/api/v1/admin/lessons/{ids['lesson']}/publish-package")
    assert result.status_code == 200, result.text
    actual = snapshot(ids)
    assert actual['lesson'] == 'PUBLISHED'
    assert actual['assessments'] == {'first': 'PUBLISHED', 'second': 'PUBLISHED', 'archived': 'ARCHIVED'}
    assert actual['progress'] == ids['now'] and actual['score'] == 90
    assert ids['ingested'] == [ids['lesson']]
    # Retrying after a lost response is safe.
    assert client.post(f"/api/v1/admin/lessons/{ids['lesson']}/publish-package").status_code == 200
    assert snapshot(ids)['published_at'] == actual['published_at']


@pytest.mark.parametrize('invalid', ['count', 'types', 'missing'])
def test_invalid_practice_never_publishes_theory_or_other_exercises(publication, invalid):
    ids, client = publication
    async def invalidate():
        async with SessionFactory.begin() as session:
            if invalid == 'missing':
                for key in ('first', 'second'):
                    (await session.get(Assessment, ids[key])).status = 'ARCHIVED'
            else:
                rows = (await session.execute(select(Question).where(Question.assessment_id == ids['second']))).scalars().all()
                if invalid == 'count':
                    await session.delete(rows[-1])
                else:
                    for row in rows:
                        row.type = 'fill_blank'
    asyncio.run(invalidate())
    before = snapshot(ids)
    result = client.post(f"/api/v1/admin/lessons/{ids['lesson']}/publish-package")
    assert result.status_code == 409
    assert result.json()['error']['code'] == ('LESSON_PRACTICE_REQUIRED' if invalid == 'missing' else 'LESSON_PRACTICE_NOT_READY')
    assert snapshot(ids) == before
    assert ids['ingested'] == []


def test_mid_publication_failure_rolls_back_every_part(publication, monkeypatch):
    ids, client = publication
    from app.exercise import repository
    original = repository.admin_transition_assessment
    calls = []
    async def fail_second(*args, **kwargs):
        calls.append(True)
        if len(calls) == 2:
            raise RuntimeError('simulated write failure')
        return await original(*args, **kwargs)
    monkeypatch.setattr(repository, 'admin_transition_assessment', fail_second)
    before = snapshot(ids)
    with pytest.raises(RuntimeError, match='simulated write failure'):
        client.post(f"/api/v1/admin/lessons/{ids['lesson']}/publish-package")
    assert snapshot(ids) == before and ids['ingested'] == []


def test_unpublish_hides_lesson_without_deleting_content_or_history(publication):
    ids, client = publication
    root = f"/api/v1/admin/lessons/{ids['lesson']}"
    assert client.post(root + '/publish-package').status_code == 200
    before = snapshot(ids)
    result = client.post(root + '/unpublish')
    assert result.status_code == 200 and result.json()['status'] == 'DRAFT'
    assert snapshot(ids) == {**before, 'lesson': 'DRAFT'}
    assert client.get(root + '/vocabulary').status_code == 200
    ids['role'][0] = 'LEARNER'
    assert client.get(f"/api/v1/lessons/{ids['lesson']}").status_code == 404
    assert client.get(f"/api/v1/assessments/{ids['first']}").status_code == 404


@pytest.mark.parametrize('action', ['unpublish', 'publish-package'])
def test_publication_actions_require_admin(publication, action):
    ids, client = publication
    ids['role'][0] = 'LEARNER'
    assert client.post(f"/api/v1/admin/lessons/{ids['lesson']}/{action}").status_code == 403
    assert snapshot(ids)['lesson'] == 'DRAFT'


def test_archived_lesson_cannot_be_published_or_unpublished(publication):
    ids, client = publication
    async def archive():
        async with SessionFactory.begin() as session:
            (await session.get(Lesson, ids['lesson'])).status = 'ARCHIVED'
    asyncio.run(archive())
    for action in ('unpublish', 'publish-package'):
        assert client.post(f"/api/v1/admin/lessons/{ids['lesson']}/{action}").status_code == 409
    assert snapshot(ids)['lesson'] == 'ARCHIVED'
