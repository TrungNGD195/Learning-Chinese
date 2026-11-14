import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.auth.current_user import get_current_user
from app.database.models import User, HSKLevel, Lesson, LearnerLessonProgress, PronunciationLessonProgress, Assessment, AssessmentAttempt
from app.database.session import SessionFactory
from app.main import app


def test_directory_search_pagination_details_and_no_mutations(persisted_admin_override):
    token = uuid4().hex
    ids = [uuid4(), uuid4()]
    hsk_id, lesson_id, assessment_id = uuid4(), uuid4(), uuid4()
    now = datetime.now(timezone.utc)

    async def seed():
        async with SessionFactory.begin() as session:
            for index, ident in enumerate(ids):
                session.add(User(id=ident, email=f"{token}-{index}@example.invalid", full_name=f"Directory {token} {index}",
                                 password_hash="never-disclose-this-hash", role="LEARNER", is_active=index == 0,
                                 created_at=now+timedelta(seconds=index)))
            session.add(HSKLevel(id=hsk_id, level_number=900000+int(token[:5],16), order_index=900000+int(token[:5],16), title="Directory test"))
            await session.flush()
            session.add(Lesson(id=lesson_id, hsk_level_id=hsk_id, lesson_number=1, title="Directory lesson", status="PUBLISHED"))
            await session.flush()
            session.add(Assessment(id=assessment_id, lesson_id=lesson_id, type="LESSON_EXERCISE", title="Practice", status="PUBLISHED", pass_threshold=80))
            session.add(LearnerLessonProgress(user_id=ids[0], lesson_id=lesson_id, started_at=now, completed_at=now))
            session.add(PronunciationLessonProgress(user_id=ids[0], section_index=4, step_index=0, completed_at=now))
            await session.flush()
            session.add(AssessmentAttempt(user_id=ids[0], assessment_id=assessment_id, attempt_number=1, status="GRADED", score=90, passed=True))

    async def snapshot():
        async with SessionFactory() as session:
            return [tuple(row) for row in (await session.execute(select(User.__table__).where(User.id.in_(ids)).order_by(User.id))).all()]

    asyncio.run(seed())
    before = asyncio.run(snapshot())
    try:
        with TestClient(app) as client:
            first = client.get('/api/v1/admin/users', params={"search": token.upper(), "page_size": 1}).json()
            assert first['total'] == 2 and first['items'][0]['id'] == str(ids[1])
            assert first['items'][0]['is_active'] is False
            second = client.get('/api/v1/admin/users', params={"search": token, "page_size": 1, "page": 2}).json()
            assert second['items'][0]['id'] == str(ids[0]) and second['items'][0]['completed_lessons'] == 1
            assert client.get('/api/v1/admin/users', params={"search": f"{token}-0@"}).json()['total'] == 1
            assert client.get('/api/v1/admin/users', params={"search": token, "role": "ADMIN"}).json()['items'] == []
            assert client.get('/api/v1/admin/users', params={"search": "%"+token}).json()['total'] == 0
            for query in ['page=0', 'page_size=101', 'role=ROOT', 'search='+'x'*101]:
                assert client.get('/api/v1/admin/users?'+query).status_code == 422
            detail = client.get(f'/api/v1/admin/users/{ids[0]}')
            assert detail.status_code == 200
            body = detail.json()
            assert body['pronunciation_completed'] is True
            assert body['graded_attempts'] == 1 and body['average_score'] == 90
            assert body['lesson_activity'][0]['lesson_id'] == str(lesson_id)
            assert 'password' not in detail.text and 'session_version' not in detail.text
            assert 'password' not in str(first) and 'session_version' not in str(first)
            assert client.get(f'/api/v1/admin/users/{uuid4()}').status_code == 404
            for method in ['post', 'patch', 'delete']:
                assert getattr(client, method)(f'/api/v1/admin/users/{ids[0]}').status_code == 405
        assert asyncio.run(snapshot()) == before
    finally:
        async def cleanup():
            async with SessionFactory.begin() as session:
                await session.execute(delete(AssessmentAttempt).where(AssessmentAttempt.user_id.in_(ids)))
                await session.execute(delete(Assessment).where(Assessment.id == assessment_id))
                await session.execute(delete(LearnerLessonProgress).where(LearnerLessonProgress.user_id.in_(ids)))
                await session.execute(delete(PronunciationLessonProgress).where(PronunciationLessonProgress.user_id.in_(ids)))
                await session.execute(delete(Lesson).where(Lesson.id == lesson_id))
                await session.execute(delete(HSKLevel).where(HSKLevel.id == hsk_id))
                await session.execute(delete(User).where(User.id.in_(ids)))
        asyncio.run(cleanup())


def test_directory_requires_admin():
    async def learner():
        return User(id=uuid4(), role="LEARNER")
    with TestClient(app) as client:
        assert client.get('/api/v1/admin/users').status_code == 401
        app.dependency_overrides[get_current_user] = learner
        try:
            assert client.get('/api/v1/admin/users').status_code == 403
            assert client.get(f'/api/v1/admin/users/{uuid4()}').status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)
