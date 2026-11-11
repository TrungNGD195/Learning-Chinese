import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.core.errors import ApplicationError
from app.progress import service


@pytest.mark.parametrize('entry_level', [2, 3])
def test_advanced_entry_preserves_unit_order_and_content_publication(monkeypatch, entry_level):
    levels = [SimpleNamespace(id=uuid4(), level_number=n, title=f'HSK {n}', description=None) for n in (1, 2, 3)]
    advanced = levels[entry_level - 1]
    empty = next(level for level in levels if level.level_number > 1 and level is not advanced)
    lessons, rows = {}, []
    for level, status, order in [(levels[0], 'PUBLISHED', 1), (advanced, 'PUBLISHED', 1),
                                 (advanced, 'PUBLISHED', 2), (empty, 'DRAFT', 1),
                                 (empty, 'ARCHIVED', 2)]:
        lesson = SimpleNamespace(id=uuid4(), hsk_level_id=level.id, status=status)
        lessons[lesson.id] = lesson
        unit = SimpleNamespace(id=uuid4(), lesson_id=lesson.id, assessment_id=None,
                               unit_type='LESSON', hsk_level_id=level.id, order_index=order)
        rows.append((unit, lesson, None))
    monkeypatch.setattr(service.curriculum_repository, 'catalog_snapshot', AsyncMock(return_value=(levels, rows)))
    monkeypatch.setattr(service.curriculum_repository, 'pronunciation_rows', AsyncMock(return_value=[]))
    monkeypatch.setattr(service.curriculum_repository, 'get_lesson', AsyncMock(side_effect=lambda _, ident: lessons[ident]))
    monkeypatch.setattr(service.repository, 'learner_completion_snapshot', AsyncMock(return_value=set()))
    monkeypatch.setattr(service.repository, 'get_pronunciation_lesson', AsyncMock(return_value=None))
    monkeypatch.setattr(service.exercise_repository, 'passed_periodic_assessment_ids', AsyncMock(return_value=set()))

    async def verify():
        session, learner = object(), uuid4()
        _, states, _, foundation_done, _ = await service.progression_snapshot(session, learner)
        assert not foundation_done
        assert states[levels[0].id][0]['state'] == 'LOCKED'
        assert [entry['state'] for entry in states[advanced.id]] == ['AVAILABLE', 'LOCKED']
        assert [entry['state'] for entry in states[empty.id]] == ['LOCKED', 'LOCKED']
        assert [entry['state'] for entry in service.learner_hsk_states(levels, states)] == ['LOCKED', 'AVAILABLE', 'AVAILABLE']
        assert await service.require_lesson_access(session, learner, rows[1][1].id) is rows[1][1]
        for index, code in [(0, 'LESSON_LOCKED'), (2, 'LESSON_LOCKED'), (3, 'NOT_FOUND'), (4, 'CONTENT_ARCHIVED')]:
            with pytest.raises(ApplicationError) as error:
                await service.require_lesson_access(session, learner, rows[index][1].id)
            assert error.value.code == code

    asyncio.run(verify())
