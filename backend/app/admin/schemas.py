from datetime import datetime
from typing import ClassVar, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.ai.generation.schemas import AssessmentGenerationRequest
from app.exercise.schemas import MatchItemResponse, ReorderItemResponse

LessonStatus = Literal["DRAFT", "PUBLISHED", "ARCHIVED"]
AssessmentType = Literal["LESSON_EXERCISE", "PERIODIC_TEST"]
AssessmentStatus = Literal["DRAFT", "REVIEW", "PUBLISHED", "ARCHIVED"]
QuestionType = Literal[
    "multiple_choice",
    "fill_blank",
    "matching",
    "reorder_sentence",
    "translate_vi_zh",
    "translate_zh_vi",
    "sentence_writing",
]


class AdminInput(BaseModel):
    model_config=ConfigDict(extra="forbid")


class ExplicitNullForbidden(AdminInput):
    non_null_if_supplied: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="after")
    def reject_explicit_null_for_non_nullable_fields(self):
        for name in self.non_null_if_supplied & self.model_fields_set:
            if getattr(self,name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class HSKPatchRequest(AdminInput):
    title: str | None = None
    description: str | None = None


class HSKAdminResponse(BaseModel):
    id: UUID
    level_number: int
    title: str | None
    description: str | None
    order_index: int


class CurriculumUnitInput(AdminInput):
    unit_type: Literal["LESSON","PERIODIC_TEST"]
    target_id: UUID
    order_index: int = Field(ge=1)


class CurriculumPutRequest(AdminInput):
    units: list[CurriculumUnitInput]


class AdminCurriculumUnitResponse(BaseModel):
    id: UUID
    order_index: int
    unit_type: Literal["LESSON", "PERIODIC_TEST"]
    lesson_id: UUID | None
    assessment_id: UUID | None
    lesson_title: str | None
    assessment_title: str | None


class LessonCreateRequest(AdminInput):
    hsk_level_id: UUID
    lesson_number: int = Field(ge=1)
    title: str
    description: str | None = None


class LessonPatchRequest(ExplicitNullForbidden):
    non_null_if_supplied: ClassVar[frozenset[str]] = frozenset({"title"})
    title: str = Field(default=None)
    description: str | None = None


class LessonAdminResponse(BaseModel):
    id: UUID
    hsk_level_id: UUID
    lesson_number: int
    title: str
    description: str | None
    status: LessonStatus
    published_at: datetime | None


class LessonAdminPageResponse(BaseModel):
    items: list[LessonAdminResponse]
    page: int
    page_size: int
    total: int


class VocabularyAttachRequest(ExplicitNullForbidden):
    non_null_if_supplied: ClassVar[frozenset[str]] = frozenset({"vocabulary_id","hanzi","pinyin","vietnamese_meaning","order_index"})
    vocabulary_id: UUID = Field(default=None)
    hanzi: str = Field(default=None)
    pinyin: str = Field(default=None)
    vietnamese_meaning: str = Field(default=None)
    part_of_speech: str | None = None
    order_index: int = Field(ge=1)
    note: str | None = None
    example: str | None = None


class VocabularyPatchRequest(ExplicitNullForbidden):
    non_null_if_supplied: ClassVar[frozenset[str]] = frozenset({"order_index","hanzi","pinyin","vietnamese_meaning"})
    order_index: int = Field(default=None,ge=1)
    note: str | None = None
    example: str | None = None
    hanzi: str = Field(default=None)
    pinyin: str = Field(default=None)
    vietnamese_meaning: str = Field(default=None)
    part_of_speech: str | None = None


class GrammarAttachRequest(ExplicitNullForbidden):
    non_null_if_supplied: ClassVar[frozenset[str]] = frozenset({"grammar_id","name","explanation","order_index"})
    grammar_id: UUID = Field(default=None)
    name: str = Field(default=None)
    structure: str | None = None
    explanation: str = Field(default=None)
    usage: str | None = None
    order_index: int = Field(ge=1)
    note: str | None = None
    example: str | None = None


class GrammarPatchRequest(ExplicitNullForbidden):
    non_null_if_supplied: ClassVar[frozenset[str]] = frozenset({"order_index","name","explanation"})
    order_index: int = Field(default=None,ge=1)
    note: str | None = None
    example: str | None = None
    name: str = Field(default=None)
    structure: str | None = None
    explanation: str = Field(default=None)
    usage: str | None = None


class LessonContentAdminResponse(BaseModel):
    id: UUID
    order_index: int
    note: str | None
    example: str | None
    vocabulary_id: UUID | None = None
    grammar_id: UUID | None = None
    hanzi: str | None = None
    pinyin: str | None = None
    vietnamese_meaning: str | None = None
    part_of_speech: str | None = None
    name: str | None = None
    structure: str | None = None
    explanation: str | None = None
    usage: str | None = None


class AssessmentCreateRequest(AdminInput):
    type: Literal["LESSON_EXERCISE","PERIODIC_TEST"]
    lesson_id: UUID | None = None
    title: str
    description: str | None = None
    pass_threshold: int = Field(default=90,ge=0,le=100)
    lesson_ids: list[UUID] | None = None
    vocabulary_ids: list[UUID] | None = None
    grammar_ids: list[UUID] | None = None


class AssessmentPatchRequest(ExplicitNullForbidden):
    non_null_if_supplied: ClassVar[frozenset[str]] = frozenset({"title","pass_threshold"})
    title: str = Field(default=None)
    description: str | None = None
    pass_threshold: int = Field(default=None,ge=0,le=100)
    lesson_ids: list[UUID] | None = None
    vocabulary_ids: list[UUID] | None = None
    grammar_ids: list[UUID] | None = None


class AssessmentAdminResponse(BaseModel):
    id: UUID
    type: AssessmentType
    lesson_id: UUID | None
    title: str
    description: str | None
    status: AssessmentStatus
    pass_threshold: int
    published_at: datetime | None


class AssessmentAdminPageResponse(BaseModel):
    items: list[AssessmentAdminResponse]
    page: int
    page_size: int
    total: int


class AssessmentGenerationDraftResponse(BaseModel):
    assessment: AssessmentAdminResponse
    questions: list["QuestionAdminResponse"]


class QuestionOptionInput(AdminInput):
    option_text: str
    is_correct: bool


class MatchingConfigInput(AdminInput):
    left_items: list[MatchItemResponse]
    right_items: list[MatchItemResponse]
    correct_pairs: list["CorrectPairInput"]


class CorrectPairInput(AdminInput):
    left_id: str
    right_id: str


class ReorderConfigInput(AdminInput):
    items: list[ReorderItemResponse]
    correct_order: list[str]


class FillBlankConfigInput(AdminInput):
    accepted_answers: list[str] = Field(default_factory=list)


class AnswerKeyFreeConfig(AdminInput):
    pass


QuestionConfigInput = MatchingConfigInput | ReorderConfigInput | FillBlankConfigInput | AnswerKeyFreeConfig


class QuestionConfigContract(AdminInput):
    @model_validator(mode="after")
    def validate_config_matches_question_type(self):
        if self.type == "matching" and not isinstance(self.config, MatchingConfigInput):
            raise ValueError("matching questions require matching config")
        if self.type == "reorder_sentence" and not isinstance(self.config, ReorderConfigInput):
            raise ValueError("reorder_sentence questions require reorder config")
        if self.type == "fill_blank" and self.config is not None and not isinstance(self.config, FillBlankConfigInput):
            raise ValueError("fill_blank config is invalid")
        if self.type in {"multiple_choice","translate_vi_zh","translate_zh_vi","sentence_writing"} and self.config not in (None, AnswerKeyFreeConfig()):
            raise ValueError("this question type does not accept config")
        return self


class QuestionCreateRequest(QuestionConfigContract):
    type: Literal["multiple_choice","fill_blank","matching","reorder_sentence","translate_vi_zh","translate_zh_vi","sentence_writing"]
    prompt: str
    order_index: int = Field(ge=1)
    reference_answer: str | None = None
    rubric: str | None = None
    config: QuestionConfigInput | None = None
    points: float = Field(default=1,gt=0)
    options: list[QuestionOptionInput] | None = None


class QuestionPatchRequest(ExplicitNullForbidden):
    non_null_if_supplied: ClassVar[frozenset[str]] = frozenset({"prompt","order_index","points"})
    prompt: str = Field(default=None)
    order_index: int = Field(default=None,ge=1)
    reference_answer: str | None = None
    rubric: str | None = None
    config: QuestionConfigInput | None = None
    points: float = Field(default=None,gt=0)
    options: list[QuestionOptionInput] | None = None


class QuestionOptionAdminResponse(BaseModel):
    id: UUID
    option_text: str
    order_index: int
    is_correct: bool


class QuestionAdminResponse(BaseModel):
    id: UUID
    assessment_id: UUID
    type: QuestionType
    prompt: str
    order_index: int
    reference_answer: str | None
    rubric: str | None
    config: QuestionConfigInput | None
    points: float
    options: list[QuestionOptionAdminResponse]


class AdminHskUserCountResponse(BaseModel):
    hsk_level: int
    users: int


class AdminStatsResponse(BaseModel):
    total_users: int
    users_by_current_hsk: list[AdminHskUserCountResponse]
    average_exercise_score: float | None
