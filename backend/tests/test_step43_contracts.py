from uuid import uuid4

from pydantic import TypeAdapter, ValidationError

from app.exercise.schemas import AttemptDetailResponse
from app.main import app
from app.progress.schemas import (
    ContinueLearningResponse,
    CurriculumResponse,
    DashboardResponse,
    LessonProgressResponse,
    LessonResponse,
)


def test_progress_and_lesson_contracts_validate_current_runtime_shapes():
    hsk_id, lesson_id, vocabulary_link_id, grammar_link_id = (uuid4() for _ in range(4))
    vocabulary_id, grammar_id = uuid4(), uuid4()
    CurriculumResponse.model_validate({
        "hsk": {"id": hsk_id, "level_number": 1, "title": None},
        "units": [{"id": uuid4(), "order_index": 1, "unit_type": "LESSON", "state": "AVAILABLE",
                   "lesson": {"id": lesson_id, "lesson_number": 1, "title": "Hello", "status": "PUBLISHED"},
                   "assessment": None}],
    })
    LessonResponse.model_validate({
        "id": lesson_id, "hsk_level_id": hsk_id, "lesson_number": 1, "title": "Hello", "description": None,
        "vocabulary": [{"id": vocabulary_link_id, "order_index": 1, "note": None, "example": "你好",
                        "item": {"id": vocabulary_id, "hanzi": "你好", "pinyin": "nǐ hǎo",
                                 "vietnamese_meaning": "xin chào", "part_of_speech": None}}],
        "grammar": [{"id": grammar_link_id, "order_index": 1, "note": "Ghi chú", "example": None,
                     "item": {"id": grammar_id, "name": "A 是 B", "structure": None,
                              "explanation": "Câu khẳng định", "usage": None}}],
        "assessment_ids": [],
    })
    LessonProgressResponse.model_validate({
        "lesson_id": lesson_id, "started_at": None, "theory_completed_at": None, "completed_at": None,
        "vocabulary": [{"id": vocabulary_link_id, "viewed": False}],
        "grammar": [{"id": grammar_link_id, "viewed": True}],
    })


def test_dashboard_continue_learning_is_discriminated_and_preserves_null_targets():
    variants = [
        {"type": "PRONUNCIATION", "section_id": uuid4(), "code": "pinyin", "lesson_id": None, "assessment_id": None},
        {"type": "LESSON", "section_id": None, "code": None, "lesson_id": uuid4(), "assessment_id": None},
        {"type": "PERIODIC_TEST", "section_id": None, "code": None, "lesson_id": None, "assessment_id": uuid4()},
    ]
    for variant in variants:
        assert TypeAdapter(ContinueLearningResponse).validate_python(variant).type == variant["type"]
    try:
        TypeAdapter(ContinueLearningResponse).validate_python({"type": "LESSON", "lesson_id": None})
    except ValidationError:
        pass
    else:
        raise AssertionError("A Lesson target without a Lesson ID must be rejected")

    DashboardResponse.model_validate({
        "current_hsk": {"id": uuid4(), "level_number": 1, "title": "HSK 1"},
        "current_unit": None,
        "current_lesson": {"id": uuid4(), "lesson_number": 1, "title": "Hello", "description": None},
        "progress_percentage": 0,
        "continue_learning": variants[0],
    })


def test_attempt_answer_results_are_typed_by_question_kind_and_keep_public_config_shape():
    question_id = uuid4()
    option_id = uuid4()
    payload = {
        "id": uuid4(), "assessment_id": uuid4(), "attempt_number": 1, "status": "GRADED",
        "score": 100, "passed": True, "submitted_at": None,
        "answers": [
            {"question_id": question_id, "type": "multiple_choice", "prompt": "Pick", "answer": {"option_id": option_id},
             "grading_status": "GRADED", "score": 1, "is_correct": True, "feedback": None,
             "reference_answer": None, "rubric": None, "config": {}},
            {"question_id": uuid4(), "type": "fill_blank", "prompt": "Fill", "answer": {"text": "你好"},
             "grading_status": "UNCERTAIN", "score": None, "is_correct": None, "feedback": "Needs review",
             "reference_answer": "你好", "rubric": None, "config": {"accepted_answers": ["你好"]}},
            {"question_id": uuid4(), "type": "matching", "prompt": "Match", "answer": {"pairs": [{"left_id": "a", "right_id": "b"}]},
             "grading_status": "GRADED", "score": 1, "is_correct": True, "feedback": None,
             "reference_answer": None, "rubric": None,
             "config": {"left_items": [{"id": "a", "text": "A"}], "right_items": [{"id": "b", "text": "B"}],
                        "correct_pairs": [{"left_id": "a", "right_id": "b"}]}},
            {"question_id": uuid4(), "type": "reorder_sentence", "prompt": "Order", "answer": {"item_ids": ["a"]},
             "grading_status": "GRADED", "score": 1, "is_correct": True, "feedback": None,
             "reference_answer": None, "rubric": None,
             "config": {"items": [{"id": "a", "text": "A"}], "correct_order": ["a"]}},
            *[{
                "question_id": uuid4(), "type": kind, "prompt": "Write", "answer": {"text": "你好"},
                "grading_status": "FAILED", "score": None, "is_correct": None, "feedback": None,
                "reference_answer": "你好", "rubric": "Meaning", "config": {},
            } for kind in ("translate_vi_zh", "translate_zh_vi", "sentence_writing")],
        ],
    }
    response = AttemptDetailResponse.model_validate(payload)
    assert [answer.type for answer in response.answers] == [
        "multiple_choice", "fill_blank", "matching", "reorder_sentence",
        "translate_vi_zh", "translate_zh_vi", "sentence_writing",
    ]
    assert response.answers[1].model_dump(mode="json")["config"] == {"accepted_answers": ["你好"]}
    assert response.answers[1].grading_status == "UNCERTAIN"


def test_openapi_exposes_typed_nested_contracts_and_discriminators():
    schemas = app.openapi()["components"]["schemas"]
    for model in (
        "VocabularyItemResponse", "GrammarItemResponse", "TheoryContentProgressResponse",
        "HskSummaryResponse", "CurriculumLessonSummary", "CurriculumAssessmentSummary",
        "DashboardLessonSummary",
    ):
        assert schemas[model]["properties"]

    dashboard = schemas["DashboardResponse"]["properties"]
    continue_schema = dashboard["continue_learning"]
    assert len(continue_schema["anyOf"][0]["oneOf"]) == 3
    assert "type" in continue_schema["anyOf"][0]["discriminator"]["propertyName"]

    detail_schema = schemas["AttemptDetailResponse"]["properties"]["answers"]["items"]
    assert len(detail_schema["oneOf"]) == 5
    assert detail_schema["discriminator"]["propertyName"] == "type"
    assert schemas["UnitProgress"]["properties"]["lesson"]["anyOf"][0]["$ref"].endswith("CurriculumLessonSummary")
    assert schemas["UnitProgress"]["properties"]["assessment"]["anyOf"][0]["$ref"].endswith("CurriculumAssessmentSummary")
    assert schemas["VocabularyLessonItem"]["properties"]["item"]["$ref"].endswith("VocabularyItemResponse")
    assert schemas["GrammarLessonItem"]["properties"]["item"]["$ref"].endswith("GrammarItemResponse")
    assert schemas["DashboardResponse"]["properties"]["current_hsk"]["anyOf"][0]["$ref"].endswith("HskSummaryResponse")
    assert schemas["LessonProgressResponse"]["properties"]["vocabulary"]["items"]["$ref"].endswith("TheoryContentProgressResponse")

    assert schemas["AssessmentResponse"]["properties"]["type"]["enum"] == ["LESSON_EXERCISE", "PERIODIC_TEST"]
    for model in ("AttemptResponse", "AttemptHistoryItem", "AttemptDetailResponse"):
        assert schemas[model]["properties"]["status"]["enum"] == ["IN_PROGRESS", "SUBMITTED", "GRADED", "GRADING_FAILED"]
    assert schemas["AttemptHistoryItem"]["properties"]["assessment_type"]["enum"] == ["LESSON_EXERCISE", "PERIODIC_TEST"]
    for model in (
        "MultipleChoiceAttemptAnswerResult", "FillBlankAttemptAnswerResult", "MatchingAttemptAnswerResult",
        "ReorderAttemptAnswerResult", "TextAttemptAnswerResult",
    ):
        assert schemas[model]["properties"]["grading_status"]["enum"] == ["PENDING", "GRADED", "UNCERTAIN", "FAILED"]
