import pytest
from pydantic import ValidationError

from app.admin.schemas import (AssessmentPatchRequest, GrammarAttachRequest, GrammarPatchRequest,
    LessonPatchRequest, QuestionCreateRequest, QuestionPatchRequest, VocabularyAttachRequest,
    VocabularyPatchRequest)


@pytest.mark.parametrize(("model", "payload"), [
    (LessonPatchRequest, {"title": None}),
    (VocabularyAttachRequest, {"order_index": 1, "hanzi": None}),
    (VocabularyAttachRequest, {"order_index": 1, "pinyin": None}),
    (VocabularyAttachRequest, {"order_index": 1, "vietnamese_meaning": None}),
    (VocabularyAttachRequest, {"order_index": None}),
    (VocabularyPatchRequest, {"hanzi": None}),
    (VocabularyPatchRequest, {"pinyin": None}),
    (VocabularyPatchRequest, {"vietnamese_meaning": None}),
    (VocabularyPatchRequest, {"order_index": None}),
    (GrammarAttachRequest, {"order_index": 1, "name": None}),
    (GrammarAttachRequest, {"order_index": 1, "explanation": None}),
    (GrammarAttachRequest, {"order_index": None}),
    (GrammarPatchRequest, {"name": None}),
    (GrammarPatchRequest, {"explanation": None}),
    (GrammarPatchRequest, {"order_index": None}),
    (AssessmentPatchRequest, {"title": None}),
    (AssessmentPatchRequest, {"pass_threshold": None}),
    (QuestionCreateRequest, {"type": None, "prompt": "Q", "order_index": 1}),
    (QuestionCreateRequest, {"type": "sentence_writing", "prompt": None, "order_index": 1}),
    (QuestionCreateRequest, {"type": "sentence_writing", "prompt": "Q", "order_index": None}),
    (QuestionCreateRequest, {"type": "sentence_writing", "prompt": "Q", "order_index": 1, "points": None}),
    (QuestionPatchRequest, {"prompt": None}),
    (QuestionPatchRequest, {"order_index": None}),
    (QuestionPatchRequest, {"points": None}),
])
def test_non_nullable_admin_fields_reject_explicit_null_before_service(model, payload):
    with pytest.raises(ValidationError):
        model.model_validate(payload)


def test_semantically_nullable_admin_fields_still_accept_explicit_null():
    assert LessonPatchRequest.model_validate({"description": None}).description is None
    assert VocabularyAttachRequest.model_validate({"order_index": 1, "hanzi": "字", "pinyin": "zì",
        "vietnamese_meaning": "chữ", "part_of_speech": None}).part_of_speech is None
    assert GrammarAttachRequest.model_validate({"order_index": 1, "name": "N", "explanation": "E",
        "structure": None, "usage": None}).usage is None
    assert AssessmentPatchRequest.model_validate({"description": None}).description is None
    assert QuestionPatchRequest.model_validate({"rubric": None}).rubric is None


def test_admin_patch_contracts_are_optional_but_not_nullable_in_openapi():
    cases = ((LessonPatchRequest, "title"), (VocabularyPatchRequest, "hanzi"),
             (GrammarPatchRequest, "name"), (AssessmentPatchRequest, "title"),
             (QuestionPatchRequest, "prompt"))
    for model, field in cases:
        schema = model.model_json_schema()["properties"][field]
        assert "null" not in str(schema).lower()
