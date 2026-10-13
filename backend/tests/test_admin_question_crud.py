import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.database.models import Assessment, Question, QuestionOption
from app.database.session import SessionFactory
from app.main import app


def test_admin_question_crud_in_draft_and_review(persisted_admin_override):
    assessment_id = uuid4()

    async def seed():
        async with SessionFactory.begin() as session:
            session.add(Assessment(id=assessment_id, type="PERIODIC_TEST", title="Question CRUD test",
                                   status="DRAFT", pass_threshold=90))
    asyncio.run(seed())
    try:
        with TestClient(app) as client:
            base = f"/api/v1/admin/assessments/{assessment_id}"
            mcq = client.post(f"{base}/questions", json={"type": "multiple_choice", "prompt": "Choose",
                "order_index": 1, "options": [{"option_text": "yes", "is_correct": True},
                                                {"option_text": "no", "is_correct": False}]})
            assert mcq.status_code == 201
            assert client.patch(f"{base}/questions/{mcq.json()['id']}", json={"prompt": "Choose correctly"}).status_code == 200
            immutable_type = client.patch(f"{base}/questions/{mcq.json()['id']}",
                                          json={"type": "fill_blank", "prompt": "Choose correctly"})
            assert immutable_type.status_code == 422

            matching_config = {"left_items": [{"id": "l1", "text": "one"}, {"id": "l2", "text": "two"}],
                "right_items": [{"id": "r1", "text": "一"}, {"id": "r2", "text": "二"}, {"id": "d", "text": "extra"}],
                "correct_pairs": [{"left_id": "l1", "right_id": "r1"}, {"left_id": "l2", "right_id": "r2"}]}
            matching = client.post(f"{base}/questions", json={"type": "matching", "prompt": "Match",
                "order_index": 2, "config": matching_config})
            assert matching.status_code == 201 and matching.json()["config"] == matching_config

            reorder_config = {"items": [{"id": "a", "text": "我"}, {"id": "b", "text": "好"}],
                              "correct_order": ["a", "b"]}
            reorder = client.post(f"{base}/questions", json={"type": "reorder_sentence", "prompt": "Order",
                "order_index": 3, "config": reorder_config})
            assert reorder.status_code == 201 and reorder.json()["config"] == reorder_config

            disposable = client.post(f"{base}/questions", json={"type": "sentence_writing", "prompt": "Write",
                "order_index": 4})
            assert disposable.status_code == 201
            assert client.delete(f"{base}/questions/{disposable.json()['id']}").status_code == 200

            assert client.post(f"{base}/submit-review").status_code == 200
            review_patch = client.patch(f"{base}/questions/{matching.json()['id']}",
                                        json={"prompt": "Match the pairs"})
            assert review_patch.status_code == 200 and review_patch.json()["config"] == matching_config
            assert review_patch.json()["prompt"] == "Match the pairs"
            assert review_patch.json()["type"] == "matching"
    finally:
        async def cleanup():
            async with SessionFactory.begin() as session:
                question_ids = select(Question.id).where(Question.assessment_id == assessment_id)
                await session.execute(delete(QuestionOption).where(QuestionOption.question_id.in_(question_ids)))
                await session.execute(delete(Question).where(Question.assessment_id == assessment_id))
                await session.execute(delete(Assessment).where(Assessment.id == assessment_id))
        asyncio.run(cleanup())
