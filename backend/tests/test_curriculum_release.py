import asyncio
import json
from copy import deepcopy
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.engine import engine
from app.database.models import HSKLevel, Lesson
from scripts.import_curriculum_refresh import load_definitions
from scripts.release_curriculum import PROJECT, check_backup, check_target, protected_state, release


def test_release_refuses_wrong_project_environment_and_enabled_ai():
    settings = SimpleNamespace(app_env='production', knowledge_ai_enabled=False)
    check_target(settings, PROJECT, 'production')
    for project, environment in [(None, 'production'), ('other', 'production'), (PROJECT, 'staging')]:
        with pytest.raises(RuntimeError):
            check_target(settings, project, environment)
    with pytest.raises(RuntimeError):
        check_target(SimpleNamespace(app_env='development', knowledge_ai_enabled=False), PROJECT, 'production')
    with pytest.raises(RuntimeError):
        check_target(SimpleNamespace(app_env='production', knowledge_ai_enabled=True), PROJECT, 'production')


def test_release_requires_matching_verified_backup_receipt(tmp_path):
    receipt = tmp_path / 'receipt.json'
    with pytest.raises(RuntimeError):
        check_backup(receipt, 'a' * 64)
    body = {'project_id': PROJECT, 'environment': 'production', 'format': 'PostgreSQL custom dump',
            'bytes': 10000, 'verified_toc': True, 'sha256': 'a' * 64}
    receipt.write_text(json.dumps(body))
    check_backup(receipt, 'a' * 64)
    with pytest.raises(RuntimeError):
        check_backup(receipt, 'b' * 64)
    body['verified_toc'] = False
    receipt.write_text(json.dumps(body))
    with pytest.raises(RuntimeError):
        check_backup(receipt, 'a' * 64)


def test_release_publishes_with_outer_transaction_and_preserves_history():
    async def run():
        async with engine.connect() as connection:
            outer = await connection.begin()
            try:
                async with AsyncSession(bind=connection, expire_on_commit=False, join_transaction_mode='create_savepoint') as session:
                    number = 40_000_000 + uuid4().int % 1_000_000
                    level = HSKLevel(level_number=number, order_index=number)
                    session.add(level)
                    await session.flush()
                    definition = deepcopy(load_definitions()[0])
                    definition['lesson']['hsk_level'] = number
                    definition['key'] += f'-release-test-{number}'
                    before = await protected_state(session)
                    result = await release(session, [definition])
                    assert result['published_lessons'] == 1 and result['history_preserved']
                    assert await protected_state(session) == before
                    assert (await session.scalar(select(Lesson).where(Lesson.hsk_level_id == level.id))).status == 'PUBLISHED'
                    await session.commit()
                await outer.rollback()
                assert await connection.scalar(select(func.count()).select_from(HSKLevel).where(HSKLevel.id == level.id)) == 0
            finally:
                if outer.is_active:
                    await outer.rollback()
    asyncio.run(run())
