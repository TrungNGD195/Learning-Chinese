import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.exercise.grading import DeterministicGrader, GradeResult, GradingUnavailable, UnavailableAIGrader
from app.core.errors import ApplicationError
from app.exercise.service import _validate_answer, _validate_stored_question, calculate_score
from app.main import app
from app.auth.current_user import get_current_user
from app.database.models import User
from app.database.session import SessionFactory


def test_business_routes_require_temporary_current_user():
    response = TestClient(app).get("/api/v1/me/dashboard")
    assert response.status_code == 401
    assert response.json() == {"error": {"code": "AUTHENTICATION_REQUIRED", "message": "Authentication is required", "details": None}}


def test_history_pagination_bounds_and_filter_whitelist():
    user_id=uuid4()
    async def setup_user():
        async with SessionFactory.begin() as session:
            session.add(User(id=user_id,email=f"boundary-{user_id}@example.invalid",password_hash="test-only",full_name="Boundary",role="LEARNER"))
    asyncio.run(setup_user())
    async def current_user():
        async with SessionFactory() as session:
            return await session.get(User,user_id)
    app.dependency_overrides[get_current_user]=current_user
    try:
        client=TestClient(app)
        result=client.get("/api/v1/me/assessment-attempts")
        assert result.status_code==200 and result.json()=={"items":[],"page":1,"page_size":20,"total":0}
        assert client.get("/api/v1/me/assessment-attempts?page=0").status_code==422
        assert client.get("/api/v1/me/assessment-attempts?page_size=101").status_code==422
        invalid=client.get("/api/v1/me/assessment-attempts?assessment_type=UNKNOWN")
        assert invalid.status_code==422 and invalid.json()["error"]["code"]=="INVALID_FILTER"
    finally:
        app.dependency_overrides.pop(get_current_user,None)
        async def cleanup_user():
            async with SessionFactory.begin() as session:
                user=await session.get(User,user_id)
                if user is not None: await session.delete(user)
        asyncio.run(cleanup_user())


def test_deterministic_grading_contract():
    grader = DeterministicGrader()
    question = {"type": "fill_blank", "points": 2, "config": {"accepted_answers": [" alternate answer "]}, "reference_answer": " 你好 "}
    assert grader.grade(question, {"text": " 你好 "}) == GradeResult("GRADED", 2, True)
    assert grader.grade(question, {"text": "你 好"}) == GradeResult("GRADED", 0, False)

    matching = {"type": "matching", "points": 1, "config": {
        "left_items": [{"id": "a"}, {"id": "b"}], "right_items": [{"id": "x"}, {"id": "y"}],
        "correct_pairs": [{"left_id": "a", "right_id": "x"}, {"left_id": "b", "right_id": "y"}]}}
    assert grader.grade(matching, {"pairs": [{"left_id": "b", "right_id": "y"}, {"left_id": "a", "right_id": "x"}]}).is_correct
    reorder = {"type": "reorder_sentence", "points": 3, "config": {"items": [{"id": "a"}, {"id": "b"}], "correct_order": ["b", "a"]}}
    assert grader.grade(reorder, {"item_ids": ["b", "a"]}).score == 3


@pytest.mark.parametrize("answer", [
    {"pairs":[{"left_id":"a","right_id":"x"},{"left_id":"a","right_id":"y"}]},
    {"pairs":[{"left_id":"a","right_id":"x"},{"left_id":"b","right_id":"y"},{"left_id":"extra","right_id":"x"}]},
    {"pairs":[{"left_id":"foreign","right_id":"x"},{"left_id":"b","right_id":"y"}]},
])
def test_malformed_matching_answers_are_client_errors(answer):
    question={"type":"matching","config":{"left_items":[{"id":"a"},{"id":"b"}],"right_items":[{"id":"x"},{"id":"y"}]}}
    with pytest.raises(ApplicationError) as raised: _validate_answer(question,answer)
    assert raised.value.status_code==422 and raised.value.code=="INVALID_ANSWER"


def test_matching_answer_may_leave_valid_distractor_unused():
    question={"type":"matching","config":{"left_items":[{"id":"a"},{"id":"b"}],
        "right_items":[{"id":"x"},{"id":"y"},{"id":"distractor"}],
        "correct_pairs":[{"left_id":"a","right_id":"x"},{"left_id":"b","right_id":"y"}]}}
    answer={"pairs":[{"left_id":"a","right_id":"x"},{"left_id":"b","right_id":"y"}]}
    assert _validate_answer(question,answer)==answer
    assert DeterministicGrader().grade({**question,"points":1},answer).is_correct


@pytest.mark.parametrize("answer", [
    {"item_ids":["a","a"]}, {"item_ids":["a"]}, {"item_ids":["a","b","c"]}, {"item_ids":["a","foreign"]}
])
def test_malformed_reorder_answers_are_client_errors(answer):
    question={"type":"reorder_sentence","config":{"items":[{"id":"a"},{"id":"b"}]}}
    with pytest.raises(ApplicationError) as raised: _validate_answer(question,answer)
    assert raised.value.status_code==422 and raised.value.code=="INVALID_ANSWER"


def test_invalid_persisted_matching_config_remains_server_error():
    question={"type":"matching","config":{"left_items":[{"id":"a","text":"A"}],"right_items":[{"id":"x","text":"X"}],"correct_pairs":[{"left_id":"other","right_id":"x"}]}}
    with pytest.raises(ApplicationError) as raised: _validate_stored_question(question)
    assert raised.value.status_code==500 and raised.value.code=="INVALID_QUESTION_CONFIGURATION"


def test_unavailable_ai_grader_is_technical_failure():
    async def call():
        await UnavailableAIGrader().grade(question={}, answer={"text": "response"})
    with pytest.raises(GradingUnavailable):
        asyncio.run(call())


def test_score_is_undefined_when_no_answers_are_gradable():
    question={"id":uuid4(),"points":2}
    assert calculate_score([question],{question["id"]:GradeResult("UNCERTAIN",None,None)},90)==(None,None)
