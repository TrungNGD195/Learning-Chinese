import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.database.models import Assessment, HSKLevel, Lesson
from app.database.session import SessionFactory
from app.main import app


def test_admin_lesson_and_assessment_detail_reads(persisted_admin_override):
    lesson_id, assessment_id = uuid4(), uuid4()

    async def seed():
        async with SessionFactory.begin() as session:
            hsk = (await session.execute(select(HSKLevel).where(HSKLevel.level_number == 1))).scalar_one()
            lesson = Lesson(
                id=lesson_id,
                hsk_level_id=hsk.id,
                lesson_number=900000 + lesson_id.int % 100000,
                title="Admin detail lesson",
                description="Canonical detail",
                status="DRAFT",
            )
            assessment = Assessment(
                id=assessment_id,
                type="PERIODIC_TEST",
                lesson_id=None,
                title="Admin detail assessment",
                description="Canonical detail",
                status="DRAFT",
                pass_threshold=75,
            )
            session.add_all([lesson, assessment])
            return hsk.id

    hsk_id = asyncio.run(seed())
    try:
        with TestClient(app) as client:
            lesson_response = client.get(f"/api/v1/admin/lessons/{lesson_id}")
            assert lesson_response.status_code == 200
            assert lesson_response.json() == {
                "id": str(lesson_id),
                "hsk_level_id": str(hsk_id),
                "lesson_number": 900000 + lesson_id.int % 100000,
                "title": "Admin detail lesson",
                "description": "Canonical detail",
                "status": "DRAFT",
                "published_at": None,
            }
            assessment_response = client.get(f"/api/v1/admin/assessments/{assessment_id}")
            assert assessment_response.status_code == 200
            assert assessment_response.json() == {
                "id": str(assessment_id),
                "type": "PERIODIC_TEST",
                "lesson_id": None,
                "title": "Admin detail assessment",
                "description": "Canonical detail",
                "status": "DRAFT",
                "pass_threshold": 75,
                "published_at": None,
            }

            missing = uuid4()
            for path in (f"/api/v1/admin/lessons/{missing}", f"/api/v1/admin/assessments/{missing}"):
                response = client.get(path)
                assert response.status_code == 404
                assert response.json()["error"]["code"] == "NOT_FOUND"
    finally:
        async def cleanup():
            async with SessionFactory.begin() as session:
                await session.execute(delete(Assessment).where(Assessment.id == assessment_id))
                await session.execute(delete(Lesson).where(Lesson.id == lesson_id))
        asyncio.run(cleanup())


def test_admin_openapi_response_schema_literals_and_stats_bucket():
    schemas = app.openapi()["components"]["schemas"]
    assert schemas["LessonAdminResponse"]["properties"]["status"]["enum"] == ["DRAFT", "PUBLISHED", "ARCHIVED"]
    assert schemas["AssessmentAdminResponse"]["properties"]["type"]["enum"] == ["LESSON_EXERCISE", "PERIODIC_TEST"]
    assert schemas["AssessmentAdminResponse"]["properties"]["status"]["enum"] == ["DRAFT", "REVIEW", "PUBLISHED", "ARCHIVED"]
    assert schemas["QuestionAdminResponse"]["properties"]["type"]["enum"] == [
        "multiple_choice", "fill_blank", "matching", "reorder_sentence", "translate_vi_zh", "translate_zh_vi", "sentence_writing",
    ]
    assert schemas["AdminCurriculumUnitResponse"]["properties"]["unit_type"]["enum"] == ["LESSON", "PERIODIC_TEST"]
    bucket = schemas["AdminStatsResponse"]["properties"]["users_by_current_hsk"]["items"]
    assert bucket["$ref"].endswith("/AdminHskUserCountResponse")
    assert schemas["AdminHskUserCountResponse"]["properties"] == {
        "hsk_level": {"type": "integer", "title": "Hsk Level"},
        "users": {"type": "integer", "title": "Users"},
    }
