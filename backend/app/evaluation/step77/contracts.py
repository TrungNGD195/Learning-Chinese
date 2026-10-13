from __future__ import annotations

from enum import StrEnum
import re
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Split(StrEnum):
    DEVELOPMENT = "DEVELOPMENT"
    HOLDOUT = "HOLDOUT"


class SemanticClass(StrEnum):
    CLEAR_CORRECT = "CLEAR_CORRECT"
    CLEAR_INCORRECT = "CLEAR_INCORRECT"
    PARTIAL = "PARTIAL"
    AMBIGUOUS = "AMBIGUOUS"
    EXPECTED_UNCERTAIN = "EXPECTED_UNCERTAIN"


class NormalizedState(StrEnum):
    UNCERTAIN = "UNCERTAIN"
    ZERO_CREDIT = "ZERO_CREDIT"
    PARTIAL_CREDIT = "PARTIAL_CREDIT"
    FULL_CREDIT = "FULL_CREDIT"


def _annotation_version(track: str, index: int) -> str:
    # Lazy import avoids the dataset/contracts import cycle while keeping the
    # annotation manifest as the single version source of truth.
    from .dataset import annotation_contract
    return annotation_contract(track)[index]


class GradingEvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str
    schema_version: str = "1.0.0"
    dataset_version: str = "v0.1.0"
    split: Split
    question_type: str
    semantic_class: SemanticClass
    question_content: str
    reference_answer: str | None = None
    rubric: str | None = None
    max_points: float = Field(gt=0)
    learner_answer: str
    annotation_ref: str
    review_status: str = "DRAFT"
    production_input_metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def fixed_contract(self):
        if self.question_type not in {"translate_vi_zh", "translate_zh_vi", "sentence_writing"}:
            raise ValueError("unsupported grading question type")
        if self.review_status not in {"DRAFT", "APPROVED"}:
            raise ValueError("invalid curation state")
        return self


GradingCase = GradingEvaluationCase


class GradingAnnotation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str
    annotation_version: str = Field(default_factory=lambda: _annotation_version("grading", 0))
    rubric_version: str = Field(default_factory=lambda: _annotation_version("grading", 1))
    expected_grading_status: str | None = None
    human_score: float | None = None
    human_is_correct: bool | None = None
    normalized_state: NormalizedState | None = None
    concise_rationale: str | None = None
    reviewer_id: str | None = None
    reviewed_at: str | None = None
    adjudication_note: str | None = None
    review_status: str = "DRAFT"

    @model_validator(mode="after")
    def validate_review_state(self):
        if self.review_status not in {"DRAFT", "NEEDS_ADJUDICATION", "HUMAN_APPROVED"}:
            raise ValueError("invalid annotation review state")
        if self.review_status == "HUMAN_APPROVED":
            if self.expected_grading_status == "UNCERTAIN":
                if self.human_score is not None or self.human_is_correct is not None or self.normalized_state != NormalizedState.UNCERTAIN:
                    raise ValueError("approved uncertain annotation is inconsistent")
            elif self.expected_grading_status == "GRADED":
                if self.human_score is None or self.human_is_correct is None or self.normalized_state is None:
                    raise ValueError("approved graded annotation is incomplete")
                if self.human_is_correct != (self.normalized_state == NormalizedState.FULL_CREDIT):
                    raise ValueError("human correctness must derive from full credit")
            else:
                raise ValueError("approved annotation requires expected status")
        return self


class GenerationEvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str
    schema_version: str = "1.0.0"
    dataset_version: str = "v0.1.0"
    split: Split
    generation_kind: str
    lesson_id: str | None = None
    lesson_ids: list[str] = Field(default_factory=list)
    vocabulary_ids: list[str] = Field(default_factory=list)
    grammar_ids: list[str] = Field(default_factory=list)
    question_count: int = 3
    allowed_question_types: list[str]
    difficulty: str
    title: str | None = None
    description: str | None = None
    pass_threshold: int = 90
    expected_policy_constraints: list[str] = Field(default_factory=list)
    fixture_scope_identity: str
    review_status: str = "DRAFT"

    @model_validator(mode="after")
    def scope_contract(self):
        if self.generation_kind == "LESSON_EXERCISE":
            if not self.lesson_id or self.lesson_ids or self.vocabulary_ids or self.grammar_ids:
                raise ValueError("lesson exercise must use only lesson_id")
        elif self.generation_kind == "PERIODIC_TEST":
            if self.lesson_id is not None or not self.lesson_ids or (not self.vocabulary_ids and not self.grammar_ids):
                raise ValueError("periodic test requires canonical selected scope IDs")
        else:
            raise ValueError("unsupported generation kind")
        ids = ([self.lesson_id] if self.lesson_id else []) + self.lesson_ids + self.vocabulary_ids + self.grammar_ids
        try:
            for value in ids:
                UUID(value)
        except (ValueError, TypeError, AttributeError):
            raise ValueError("generation scope IDs must be canonical UUID strings") from None
        if not self.allowed_question_types or set(self.allowed_question_types) - {
            "multiple_choice", "fill_blank", "matching", "reorder_sentence",
            "translate_vi_zh", "translate_zh_vi", "sentence_writing"}:
            raise ValueError("unsupported generation question type in fixture")
        if self.question_count != 3 or self.difficulty not in {"EASY", "MEDIUM", "HARD"}:
            raise ValueError("frozen generation settings violated")
        if self.review_status != "DRAFT":
            raise ValueError("offline generation cases must remain DRAFT")
        return self


GenerationCase = GenerationEvaluationCase


class GenerationQuestionAnnotation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step77_run_id: str | None = None
    generation_case_id: str
    execution_id: str | None = None
    question_index: int = Field(ge=1, le=3)
    persisted_question_id: str | None = None
    generated_draft_sha256: str | None = None
    generated_question_sha256: str | None = None
    materialized_scope_sha256: str | None = None
    generation_output_sha256: str | None = None
    cases_artifact_sha256: str | None = None
    annotation_version: str = Field(default_factory=lambda: _annotation_version("generation", 0))
    rubric_version: str = Field(default_factory=lambda: _annotation_version("generation", 1))
    answer_reference_consistency: str | None = None
    answerability: str | None = None
    concise_rationale: str | None = None
    reviewer_id: str | None = None
    reviewed_at: str | None = None
    adjudication_note: str | None = None
    review_status: str = "DRAFT"

    @model_validator(mode="after")
    def binding_contract(self):
        if self.review_status not in {"DRAFT", "NEEDS_ADJUDICATION", "HUMAN_APPROVED"}:
            raise ValueError("invalid generation annotation status")
        if self.review_status in {"NEEDS_ADJUDICATION", "HUMAN_APPROVED"}:
            required = (self.step77_run_id, self.execution_id, self.generated_draft_sha256,
                        self.generated_question_sha256, self.materialized_scope_sha256,
                        self.generation_output_sha256, self.cases_artifact_sha256)
            if any(value is None for value in required):
                raise ValueError("reviewed annotation requires exact output bindings")
            for value in (self.generated_draft_sha256, self.generated_question_sha256,
                          self.materialized_scope_sha256, self.generation_output_sha256,
                          self.cases_artifact_sha256):
                if not re.fullmatch(r"[0-9a-f]{64}", value or ""):
                    raise ValueError("reviewed annotation hash must be lowercase SHA-256")
        if self.review_status == "HUMAN_APPROVED":
            if self.answer_reference_consistency not in {"CONSISTENT", "INCONSISTENT"} or self.answerability not in {"ANSWERABLE", "UNANSWERABLE"}:
                raise ValueError("human-approved annotation requires semantic labels")
        return self

