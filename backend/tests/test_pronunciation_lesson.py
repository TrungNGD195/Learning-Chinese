"""Regression coverage for server-owned pronunciation progression."""
import asyncio
from uuid import uuid4

import httpx
from sqlalchemy import delete, select

from app.auth.current_user import require_learner
from app.database.models import CurriculumUnit, HSKLevel, LearnerHSKProgress, Lesson, PronunciationProgress, User
from app.database.seeds.required import seed_required_data
from app.database.session import SessionFactory
from app.main import app


def test_pronunciation_steps_and_final_gate_are_server_owned():
    async def scenario():
        await seed_required_data()
        first_id, second_id, lesson_id = uuid4(), uuid4(), uuid4()
        async with SessionFactory.begin() as session:
            hsk = (await session.execute(select(HSKLevel).where(HSKLevel.level_number == 1))).scalar_one()
            session.add_all([
                User(id=first_id, email=f'{first_id}@example.invalid', password_hash='test-only', full_name='First', role='LEARNER'),
                User(id=second_id, email=f'{second_id}@example.invalid', password_hash='test-only', full_name='Second', role='LEARNER'),
                Lesson(id=lesson_id, hsk_level_id=hsk.id, lesson_number=901, title='Test lesson', status='PUBLISHED'),
            ])
            await session.flush()
            session.add(CurriculumUnit(id=uuid4(), hsk_level_id=hsk.id, unit_type='LESSON', lesson_id=lesson_id, order_index=1))

        current_user = [first_id]
        async def learner():
            return User(id=current_user[0], email='test@example.invalid', password_hash='test-only', full_name='Test', role='LEARNER')
        app.dependency_overrides[require_learner] = learner
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
                async def state():
                    response = await client.get('/api/v1/pronunciation/lesson')
                    assert response.status_code == 200, response.text
                    return response.json()

                async def hsk_state():
                    response = await client.get('/api/v1/hsk-levels')
                    assert response.status_code == 200, response.text
                    return next(level['state'] for level in response.json() if level['level_number'] == 1)

                assert await hsk_state() == 'LOCKED'
                assert (await client.get(f'/api/v1/lessons/{lesson_id}')).status_code == 403
                initial = await state()
                assert initial['current_section'] == 'INITIALS' and initial['step_index'] == 0
                sections = {item['code']: item for item in initial['sections']}
                assert (await client.post(f"/api/v1/pronunciation/{sections['INITIALS']['id']}/complete")).status_code == 409
                assert (await client.post('/api/v1/pronunciation/lesson/complete')).status_code == 409
                assert (await client.post('/api/v1/pronunciation/lesson/advance', json={'section_code': 'FINALS', 'step_index': 0})).status_code == 409

                for code, count in [('INITIALS', 21), ('FINALS', 36), ('TONES', 5)]:
                    current = await state()
                    assert current['current_section'] == code and current['total_steps'] == count
                    for index in range(count):
                        response = await client.post('/api/v1/pronunciation/lesson/advance', json={'section_code': code, 'step_index': index})
                        assert response.status_code == 200, response.text
                        assert response.json()['step_index'] == index + 1
                        if index == 0:
                            assert (await client.post('/api/v1/pronunciation/lesson/advance', json={'section_code': code, 'step_index': index})).status_code == 409
                    assert (await state())['step_index'] == count
                    response = await client.post(f"/api/v1/pronunciation/{sections[code]['id']}/complete")
                    assert response.status_code == 200, response.text

                assert (await state())['can_finish'] is True
                assert await hsk_state() == 'LOCKED'
                assert (await client.get(f'/api/v1/lessons/{lesson_id}')).status_code == 403
                current_user[0] = second_id
                assert (await state())['current_section'] == 'INITIALS'
                assert await hsk_state() == 'LOCKED'
                current_user[0] = first_id
                response = await client.post('/api/v1/pronunciation/lesson/complete')
                assert response.status_code == 200, response.text
                assert response.json()['completed_at'] is not None
                assert await hsk_state() == 'AVAILABLE'
                assert (await client.post('/api/v1/pronunciation/lesson/complete')).status_code == 200
        finally:
            app.dependency_overrides.pop(require_learner, None)
            async with SessionFactory.begin() as session:
                await session.execute(delete(CurriculumUnit).where(CurriculumUnit.lesson_id == lesson_id))
                await session.execute(delete(PronunciationProgress).where(PronunciationProgress.user_id.in_((first_id, second_id))))
                await session.execute(delete(LearnerHSKProgress).where(LearnerHSKProgress.user_id.in_((first_id, second_id))))
                await session.execute(delete(Lesson).where(Lesson.id == lesson_id))
                await session.execute(delete(User).where(User.id.in_((first_id, second_id))))

    asyncio.run(scenario())
