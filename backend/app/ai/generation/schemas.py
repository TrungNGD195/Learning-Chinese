from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Literal, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

GenerationQuestionType = Literal[
    "multiple_choice", "fill_blank", "matching", "reorder_sentence",
    "translate_vi_zh", "translate_zh_vi", "sentence_writing",
]
GenerationDifficulty = Literal["EASY", "MEDIUM", "HARD"]


class _GenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    description: str | None = None
    pass_threshold: int = Field(default=90, ge=0, le=100)
    question_count: int = Field(ge=1, le=10)
    allowed_types: list[GenerationQuestionType] = Field(min_length=1, max_length=7)
    difficulty: GenerationDifficulty

    @field_validator("title")
    @classmethod
    def title_must_be_nonblank_when_supplied(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("title cannot be blank")
        return value

    @field_validator("allowed_types")
    @classmethod
    def allowed_types_are_unique(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("allowed_types must be unique")
        return value


class LessonExerciseGenerationRequest(_GenerationRequest):
    type: Literal["LESSON_EXERCISE"]
    lesson_id: UUID


class PeriodicTestGenerationRequest(_GenerationRequest):
    type: Literal["PERIODIC_TEST"]
    lesson_ids: list[UUID] = Field(min_length=1)
    vocabulary_ids: list[UUID] = Field(default_factory=list)
    grammar_ids: list[UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_periodic_scope(self) -> "PeriodicTestGenerationRequest":
        for name in ("lesson_ids", "vocabulary_ids", "grammar_ids"):
            values = getattr(self, name)
            if len(values) != len(set(values)):
                raise ValueError(f"{name} must be unique")
        if not self.vocabulary_ids and not self.grammar_ids:
            raise ValueError("At least one vocabulary or grammar item is required")
        return self


AssessmentGenerationRequest = Annotated[
    Union[LessonExerciseGenerationRequest, PeriodicTestGenerationRequest],
    Field(discriminator="type"),
]


class GeneratedModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class GeneratedCommon(GeneratedModel):
    prompt: str
    source_refs: list[str] = Field(min_length=1)

    @field_validator("prompt")
    @classmethod
    def prompt_nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("prompt cannot be blank")
        return value


class GeneratedMCQOption(GeneratedModel):
    option_text: str
    is_correct: bool


class GeneratedMultipleChoiceQuestion(GeneratedCommon):
    type: Literal["multiple_choice"]
    options: list[GeneratedMCQOption] = Field(min_length=2)

    @model_validator(mode="after")
    def exactly_one_correct(self) -> "GeneratedMultipleChoiceQuestion":
        if sum(item.is_correct for item in self.options) != 1:
            raise ValueError("multiple choice requires exactly one correct option")
        if any(not item.option_text.strip() for item in self.options):
            raise ValueError("option text cannot be blank")
        return self


class GeneratedFillBlankQuestion(GeneratedCommon):
    type: Literal["fill_blank"]
    reference_answer: str
    accepted_answers: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def answers_nonblank(self) -> "GeneratedFillBlankQuestion":
        if not self.reference_answer.strip() or any(not answer.strip() for answer in self.accepted_answers):
            raise ValueError("fill blank answers cannot be blank")
        return self


class GeneratedMatchItem(GeneratedModel):
    id: str
    text: str


class GeneratedCorrectPair(GeneratedModel):
    left_id: str
    right_id: str


class GeneratedMatchingQuestion(GeneratedCommon):
    type: Literal["matching"]
    left_items: list[GeneratedMatchItem] = Field(min_length=1)
    right_items: list[GeneratedMatchItem] = Field(min_length=1)
    correct_pairs: list[GeneratedCorrectPair] = Field(min_length=1)


class GeneratedReorderItem(GeneratedModel):
    id: str
    text: str


class GeneratedReorderSentenceQuestion(GeneratedCommon):
    type: Literal["reorder_sentence"]
    items: list[GeneratedReorderItem] = Field(min_length=1)
    correct_order: list[str] = Field(min_length=1)


class _GeneratedFreeForm(GeneratedCommon):
    reference_answer: str
    rubric: str

    @model_validator(mode="after")
    def answer_and_rubric_nonblank(self):
        if not self.reference_answer.strip() or not self.rubric.strip():
            raise ValueError("reference_answer and rubric must be nonblank")
        return self


class GeneratedViToZhQuestion(_GeneratedFreeForm):
    type: Literal["translate_vi_zh"]


class GeneratedZhToViQuestion(_GeneratedFreeForm):
    type: Literal["translate_zh_vi"]


class GeneratedSentenceWritingQuestion(_GeneratedFreeForm):
    type: Literal["sentence_writing"]


GeneratedQuestion = Annotated[
    Union[
        GeneratedMultipleChoiceQuestion, GeneratedFillBlankQuestion,
        GeneratedMatchingQuestion, GeneratedReorderSentenceQuestion,
        GeneratedViToZhQuestion, GeneratedZhToViQuestion,
        GeneratedSentenceWritingQuestion,
    ],
    Field(discriminator="type"),
]


class StructuredAssessmentGenerationOutput(GeneratedModel):
    questions: list[GeneratedQuestion] = Field(min_length=1, max_length=10)


@dataclass(frozen=True)
class MaterializedGenerationScope:
    assessment_type: str
    lesson_id: UUID | None
    lesson_ids: tuple[UUID, ...]
    vocabulary_ids: tuple[UUID, ...]
    grammar_ids: tuple[UUID, ...]
    title: str
    description: str | None
    pass_threshold: int
    payload: dict
    allowed_source_refs: frozenset[str]


@dataclass(frozen=True)
class StructuredAssessmentGenerationRequest:
    system_content: str
    user_content: str
    model: str
    temperature: float
    max_output_tokens: int
    reasoning_effort: str
    model_input_limit: int
    request_timeout_seconds: float
    max_transient_retries: int
    generation_kind: str
    requested_question_count: int
    allowed_types: tuple[str, ...]
    difficulty: str


@dataclass(frozen=True)
class StructuredAssessmentGenerationProviderResult:
    output: StructuredAssessmentGenerationOutput
    provider: str
    model: str
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    provider_preflight_input_tokens: int
    latency_ms: int
    attempt_count: int
    provider_request_id: str | None
