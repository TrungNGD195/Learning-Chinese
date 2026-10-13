from datetime import datetime
from typing import Annotated, Literal, Union
from uuid import UUID

from pydantic import BaseModel, Field


UnitState = Literal["LOCKED", "AVAILABLE", "COMPLETED"]
UnitType = Literal["LESSON", "PERIODIC_TEST"]
LessonStatus = Literal["DRAFT", "PUBLISHED", "ARCHIVED"]
AssessmentType = Literal["LESSON_EXERCISE", "PERIODIC_TEST"]
AssessmentLifecycleStatus = Literal["DRAFT", "REVIEW", "PUBLISHED", "ARCHIVED"]


class HskSummaryResponse(BaseModel):
    id: UUID
    level_number: int
    title: str | None


class CurriculumLessonSummary(BaseModel):
    id: UUID
    lesson_number: int
    title: str
    status: LessonStatus


class CurriculumAssessmentSummary(BaseModel):
    id: UUID
    title: str
    type: AssessmentType
    status: AssessmentLifecycleStatus


class UnitProgress(BaseModel):
    id: UUID
    order_index: int
    unit_type: UnitType
    state: UnitState
    lesson: CurriculumLessonSummary | None = None
    assessment: CurriculumAssessmentSummary | None = None


class PronunciationSectionResponse(BaseModel):
    id: UUID
    code: str
    title: str | None
    description: str | None
    order_index: int
    completed_at: datetime | None


class ViewProgressResponse(BaseModel):
    viewed_at: datetime
    theory_completed_at: datetime | None


class HSKLevelResponse(BaseModel):
    id: UUID
    level_number: int
    title: str | None
    description: str | None = None
    state: UnitState


class CurriculumResponse(BaseModel):
    hsk: HskSummaryResponse
    units: list[UnitProgress]


class PronunciationContinueLearning(BaseModel):
    type: Literal["PRONUNCIATION"]
    section_id: UUID
    code: str
    lesson_id: None = None
    assessment_id: None = None


class LessonContinueLearning(BaseModel):
    type: Literal["LESSON"]
    section_id: None = None
    code: None = None
    lesson_id: UUID
    assessment_id: None = None


class PeriodicTestContinueLearning(BaseModel):
    type: Literal["PERIODIC_TEST"]
    section_id: None = None
    code: None = None
    lesson_id: None = None
    assessment_id: UUID


ContinueLearningResponse = Annotated[
    Union[PronunciationContinueLearning, LessonContinueLearning, PeriodicTestContinueLearning],
    Field(discriminator="type"),
]


class DashboardLessonSummary(BaseModel):
    id: UUID
    lesson_number: int
    title: str
    description: str | None


class DashboardResponse(BaseModel):
    current_hsk: HskSummaryResponse | None
    current_unit: UnitProgress | None
    current_lesson: DashboardLessonSummary | None
    progress_percentage: float
    continue_learning: ContinueLearningResponse | None


class VocabularyItemResponse(BaseModel):
    id: UUID
    hanzi: str
    pinyin: str
    vietnamese_meaning: str
    part_of_speech: str | None


class GrammarItemResponse(BaseModel):
    id: UUID
    name: str
    structure: str | None
    explanation: str
    usage: str | None


class TheoryContentProgressResponse(BaseModel):
    id: UUID
    viewed: bool


class VocabularyLessonItem(BaseModel):
    id: UUID
    order_index: int
    note: str | None
    example: str | None
    item: VocabularyItemResponse


class GrammarLessonItem(BaseModel):
    id: UUID
    order_index: int
    note: str | None
    example: str | None
    item: GrammarItemResponse


class LessonResponse(BaseModel):
    id: UUID
    hsk_level_id: UUID
    lesson_number: int
    title: str
    description: str | None
    vocabulary: list[VocabularyLessonItem]
    grammar: list[GrammarLessonItem]
    assessment_ids: list[UUID]


class LessonProgressResponse(BaseModel):
    lesson_id: UUID
    started_at: datetime | None
    theory_completed_at: datetime | None
    completed_at: datetime | None
    vocabulary: list[TheoryContentProgressResponse]
    grammar: list[TheoryContentProgressResponse]


class ProgressOverviewResponse(BaseModel):
    current_hsk: int | None
    progress_percentage: float
    pronunciation_complete: bool
    hsk_levels: list[HSKLevelResponse]


class HSKProgressResponse(CurriculumResponse):
    progress_percentage: float
