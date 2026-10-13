import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.database.models import Assessment, HSKLevel, Lesson
from app.database.session import SessionFactory
from app.main import app


def test_admin_lesson_and_assessment_pages_are_bounded_and_stable(persisted_admin_override):
    lesson_ids=[uuid4(),uuid4()]
    assessment_ids=[uuid4(),uuid4()]
    async def seed():
        async with SessionFactory.begin() as session:
            hsk=(await session.execute(select(HSKLevel).where(HSKLevel.level_number==3))).scalar_one()
            for index,ident in enumerate(lesson_ids):
                session.add(Lesson(id=ident,hsk_level_id=hsk.id,lesson_number=980000+ident.int%10000,
                    title=f"Pagination lesson {index}",status="DRAFT"))
            for index,ident in enumerate(assessment_ids):
                session.add(Assessment(id=ident,type="PERIODIC_TEST",title=f"Pagination assessment {index}",
                    status="DRAFT",pass_threshold=90))
            return hsk.id
    hsk_id=asyncio.run(seed())
    try:
        with TestClient(app) as client:
            lessons_url=f"/api/v1/admin/lessons?status=DRAFT&hsk_level_id={hsk_id}"
            lesson_default=client.get(lessons_url)
            assert lesson_default.status_code==200
            assert lesson_default.json()["page"]==1 and lesson_default.json()["page_size"]==20
            assert lesson_default.json()["total"]>=2
            first=client.get(lessons_url+"&page=1&page_size=1").json()
            second=client.get(lessons_url+"&page=2&page_size=1").json()
            assert first["total"]==second["total"] and first["items"][0]["id"]!=second["items"][0]["id"]
            assert client.get(lessons_url+"&page=0").status_code==422
            assert client.get(lessons_url+"&page_size=101").status_code==422
            assert client.get(lessons_url+"&page_size=100").status_code==200

            assessments_url="/api/v1/admin/assessments?status=DRAFT&assessment_type=PERIODIC_TEST"
            assessment_default=client.get(assessments_url)
            assert assessment_default.status_code==200
            assert assessment_default.json()["page"]==1 and assessment_default.json()["page_size"]==20
            assert assessment_default.json()["total"]>=2
            first=client.get(assessments_url+"&page=1&page_size=1").json()
            second=client.get(assessments_url+"&page=2&page_size=1").json()
            assert first["total"]==second["total"] and first["items"][0]["id"]!=second["items"][0]["id"]
            assert client.get(assessments_url+"&page=0").status_code==422
            assert client.get(assessments_url+"&page_size=101").status_code==422
            assert client.get(assessments_url+"&page_size=100").status_code==200
    finally:
        async def cleanup():
            async with SessionFactory.begin() as session:
                await session.execute(delete(Assessment).where(Assessment.id.in_(assessment_ids)))
                await session.execute(delete(Lesson).where(Lesson.id.in_(lesson_ids)))
        asyncio.run(cleanup())
