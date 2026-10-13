from datetime import datetime
from typing import Annotated, Literal, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_serializer


class InputModel(BaseModel):
    model_config=ConfigDict(extra="forbid")


class MultipleChoiceAnswer(InputModel): option_id: UUID
class FillBlankAnswer(InputModel): text: str
class MatchingPair(InputModel): left_id: str; right_id: str
class MatchingAnswer(InputModel): pairs: list[MatchingPair]
class ReorderAnswer(InputModel): item_ids: list[str]
class TextAnswer(InputModel): text: str

AnswerVariant=Annotated[Union[MultipleChoiceAnswer,FillBlankAnswer,MatchingAnswer,ReorderAnswer,TextAnswer],Field(union_mode="left_to_right")]


class SubmissionAnswer(InputModel):
    question_id: UUID
    answer: AnswerVariant


class SubmitAttemptRequest(InputModel):
    answers: list[SubmissionAnswer]


class LearnerOptionResponse(BaseModel):
    id: UUID
    option_text: str


class MatchItemResponse(BaseModel):
    model_config=ConfigDict(extra="forbid")
    id: str
    text: str


class MatchingLearnerConfig(BaseModel):
    left_items: list[MatchItemResponse]
    right_items: list[MatchItemResponse]


class ReorderItemResponse(BaseModel):
    model_config=ConfigDict(extra="forbid")
    id: str
    text: str


class ReorderLearnerConfig(BaseModel):
    items: list[ReorderItemResponse]


class AnswerKeyFreeConfig(BaseModel):
    model_config=ConfigDict(extra="forbid")


class LearnerQuestionBase(BaseModel):
    prompt: str
    order_index: int
    points: float
    id: UUID


class LearnerMultipleChoiceQuestion(LearnerQuestionBase):
    type: Literal["multiple_choice"]
    config: AnswerKeyFreeConfig
    options: list[LearnerOptionResponse]


class LearnerFillBlankQuestion(LearnerQuestionBase):
    type: Literal["fill_blank"]
    config: AnswerKeyFreeConfig


class LearnerMatchingQuestion(LearnerQuestionBase):
    type: Literal["matching"]
    config: MatchingLearnerConfig


class LearnerReorderQuestion(LearnerQuestionBase):
    type: Literal["reorder_sentence"]
    config: ReorderLearnerConfig


class LearnerTextQuestion(LearnerQuestionBase):
    type: Literal["translate_vi_zh","translate_zh_vi","sentence_writing"]
    config: AnswerKeyFreeConfig


LearnerQuestionResponse=Annotated[Union[LearnerMultipleChoiceQuestion,LearnerFillBlankQuestion,
    LearnerMatchingQuestion,LearnerReorderQuestion,LearnerTextQuestion],Field(discriminator="type")]


class AssessmentResponse(BaseModel):
    id: UUID
    type: Literal["LESSON_EXERCISE", "PERIODIC_TEST"]
    title: str
    description: str | None
    pass_threshold: int
    questions: list[LearnerQuestionResponse]


class AttemptResponse(BaseModel):
    id: UUID
    assessment_id: UUID
    attempt_number: int
    status: Literal["IN_PROGRESS", "SUBMITTED", "GRADED", "GRADING_FAILED"]
    started_at: datetime


class AttemptSubmissionResponse(BaseModel):
    attempt_id: UUID
    status: Literal["GRADED"]
    score: float | None
    passed: bool | None


class AttemptHistoryItem(BaseModel):
    id: UUID
    assessment_id: UUID
    assessment_title: str
    assessment_type: Literal["LESSON_EXERCISE", "PERIODIC_TEST"]
    attempt_number: int
    status: Literal["IN_PROGRESS", "SUBMITTED", "GRADED", "GRADING_FAILED"]
    started_at: datetime
    submitted_at: datetime | None
    score: float | None
    passed: bool | None


class AttemptHistoryPage(BaseModel):
    items: list[AttemptHistoryItem]
    page: int
    page_size: int
    total: int


class ResultConfigBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @model_serializer(mode="wrap")
    def preserve_present_keys(self, handler):
        serialized = handler(self)
        return {key: value for key, value in serialized.items() if key in self.model_fields_set}


class ResultFillBlankConfig(ResultConfigBase):
    accepted_answers: list[str] | None = None


class ResultMatchingConfig(ResultConfigBase):
    left_items: list[MatchItemResponse]
    right_items: list[MatchItemResponse]
    correct_pairs: list[MatchingPair]


class ResultReorderConfig(ResultConfigBase):
    items: list[ReorderItemResponse]
    correct_order: list[str]


class AttemptAnswerResultBase(BaseModel):
    question_id: UUID
    prompt: str
    grading_status: Literal["PENDING", "GRADED", "UNCERTAIN", "FAILED"]
    score: float | None
    is_correct: bool | None
    feedback: str | None
    reference_answer: str | None = None
    rubric: str | None = None


class MultipleChoiceAttemptAnswerResult(AttemptAnswerResultBase):
    type: Literal["multiple_choice"]
    answer: MultipleChoiceAnswer | None
    config: AnswerKeyFreeConfig | None = None


class FillBlankAttemptAnswerResult(AttemptAnswerResultBase):
    type: Literal["fill_blank"]
    answer: FillBlankAnswer | None
    config: ResultFillBlankConfig | None = None


class MatchingAttemptAnswerResult(AttemptAnswerResultBase):
    type: Literal["matching"]
    answer: MatchingAnswer | None
    config: ResultMatchingConfig | None = None


class ReorderAttemptAnswerResult(AttemptAnswerResultBase):
    type: Literal["reorder_sentence"]
    answer: ReorderAnswer | None
    config: ResultReorderConfig | None = None


class TextAttemptAnswerResult(AttemptAnswerResultBase):
    type: Literal["translate_vi_zh", "translate_zh_vi", "sentence_writing"]
    answer: TextAnswer | None
    config: AnswerKeyFreeConfig | None = None


AttemptAnswerResult = Annotated[
    Union[
        MultipleChoiceAttemptAnswerResult,
        FillBlankAttemptAnswerResult,
        MatchingAttemptAnswerResult,
        ReorderAttemptAnswerResult,
        TextAttemptAnswerResult,
    ],
    Field(discriminator="type"),
]


class AttemptDetailResponse(BaseModel):
    id: UUID
    assessment_id: UUID
    attempt_number: int
    status: Literal["IN_PROGRESS", "SUBMITTED", "GRADED", "GRADING_FAILED"]
    score: float | None
    passed: bool | None
    submitted_at: datetime | None
    answers: list[AttemptAnswerResult]
