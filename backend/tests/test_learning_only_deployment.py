import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.errors import ApplicationError
from app.core.features import require_knowledge_ai
from app.admin import service
from app.ingestion.orchestrator import IngestionOrchestrator
from app.main import create_app


def production_settings(**overrides):
    return Settings(_env_file=None, app_env='production', debug=False,
                    database_url='postgresql+psycopg://unused:unused@localhost/unused',
                    secret_key='test-only-key-' * 4, cookie_secure=True, **overrides)


def test_learning_only_production_still_requires_secure_settings():
    settings = production_settings(knowledge_ai_enabled=False)
    with pytest.raises(ApplicationError) as error:
        require_knowledge_ai(settings)
    assert error.value.code == 'KNOWLEDGE_AI_DISABLED'
    assert error.value.status_code == 503
    with pytest.raises(ValidationError, match='Production must use Modal'):
        production_settings(knowledge_ai_enabled=True)
    routes = create_app(settings).openapi()['paths']
    assert '/api/v1/lessons/{lesson_id}' in routes
    assert '/api/v1/conversations' not in routes


def test_publication_succeeds_without_starting_knowledge_build(monkeypatch):
    settings = production_settings(knowledge_ai_enabled=False)
    monkeypatch.setattr(service, 'get_settings', lambda: settings)
    published = {'status': 'PUBLISHED'}
    monkeypatch.setattr(service.curriculum_service, 'admin_lesson_transition', AsyncMock(return_value=published))
    monkeypatch.setattr(service.curriculum_service, 'admin_publish_lesson_package', AsyncMock(return_value=published))
    build = AsyncMock()
    monkeypatch.setattr('app.ingestion.orchestrator.process_published_lesson', build)

    async def verify():
        assert await service.lesson_transition(object(), uuid4(), 'publish') == published
        assert await service.publish_lesson_package(object(), uuid4()) == published
        build.assert_not_awaited()
    asyncio.run(verify())


def test_disabled_processing_does_not_touch_database_or_storage(monkeypatch):
    monkeypatch.setattr('app.core.features.get_settings', lambda: production_settings(knowledge_ai_enabled=False))

    async def verify():
        pipeline = IngestionOrchestrator(object(), object())
        for action, arguments in [(pipeline.process_document, (uuid4(),)),
                                  (pipeline.approve_document, (uuid4(), uuid4())),
                                  (pipeline.retry_document_knowledge, (uuid4(),)),
                                  (pipeline.process_published_lesson, (uuid4(),))]:
            with pytest.raises(ApplicationError, match='AI') as error:
                await action(*arguments)
            assert error.value.code == 'KNOWLEDGE_AI_DISABLED'
    asyncio.run(verify())
