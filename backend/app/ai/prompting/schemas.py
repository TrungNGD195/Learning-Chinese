from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping
from uuid import UUID

from app.ai.prompting.errors import (
    INVALID_PROMPT_BUDGET,
    PROMPT_CONTEXT_BUILD_FAILED,
    prompt_context_error,
)
from app.ai.memory.schemas import ConversationMemory


@dataclass(frozen=True)
class PromptBudget:
    model_input_limit: int
    reserved_output_tokens: int
    serialization_overhead_tokens: int

    def __post_init__(self) -> None:
        values = (
            self.model_input_limit,
            self.reserved_output_tokens,
            self.serialization_overhead_tokens,
        )
        if any(type(value) is not int for value in values):
            raise prompt_context_error(
                INVALID_PROMPT_BUDGET,
                "Prompt budget values must be integers.",
            )
        if (
            self.model_input_limit < 1
            or self.reserved_output_tokens < 0
            or self.serialization_overhead_tokens < 0
        ):
            raise prompt_context_error(
                INVALID_PROMPT_BUDGET,
                "Prompt budget structure is invalid.",
            )


@dataclass(frozen=True)
class LearningContext:
    hsk_level: int | None = None
    lesson_title: str | None = None
    current_module: str | None = None

    def __post_init__(self) -> None:
        if self.hsk_level is not None and type(self.hsk_level) is not int:
            raise prompt_context_error(
                PROMPT_CONTEXT_BUILD_FAILED,
                "Learning context is invalid.",
            )
        if any(
            value is not None and not isinstance(value, str)
            for value in (self.lesson_title, self.current_module)
        ):
            raise prompt_context_error(
                PROMPT_CONTEXT_BUILD_FAILED,
                "Learning context is invalid.",
            )


@dataclass(frozen=True)
class ContextBlock:
    source_label: str
    text: str
    chunk_id: UUID
    knowledge_source_id: UUID
    source_type: str
    source_document_id: UUID | None
    source_lesson_id: UUID | None
    title: str
    section: str | None
    hsk_level: int | None
    lesson_title: str | None
    content_type: str
    page_number: int | None
    locator_metadata: Mapping | None
    retrieval_score: float
    rerank_score: float


@dataclass(frozen=True)
class SourceMapEntry:
    source_label: str
    chunk_id: UUID
    knowledge_source_id: UUID
    source_type: str
    source_document_id: UUID | None
    source_lesson_id: UUID | None
    title: str
    page_number: int | None
    section: str | None
    locator_metadata: Mapping | None


@dataclass(frozen=True)
class ExternalContextBlock:
    source_label: str
    text: str
    title: str
    url: str
    domain: str
    rerank_score: float


@dataclass(frozen=True)
class ExternalSourceMapEntry:
    source_label: str
    title: str
    url: str
    domain: str


@dataclass(frozen=True)
class BudgetUsage:
    system_tokens: int
    learning_context_tokens: int
    user_query_tokens: int
    serialization_overhead_tokens: int
    reserved_output_tokens: int
    base_input_tokens: int
    available_context_tokens: int
    selected_context_tokens: int
    estimated_input_tokens: int
    model_input_limit: int


@dataclass(frozen=True)
class PromptPackage:
    system_instructions: str
    learning_context: str | None
    context_blocks: tuple[ContextBlock | ExternalContextBlock, ...]
    user_query: str
    selected_chunk_ids: tuple[UUID, ...]
    omitted_chunk_ids: tuple[UUID, ...]
    source_map: Mapping[str, SourceMapEntry | ExternalSourceMapEntry]
    budget_usage: BudgetUsage
    conversation_memory: ConversationMemory | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_map", MappingProxyType(dict(self.source_map)))


@dataclass(frozen=True)
class ContextBuildResult:
    status: str
    reason: str | None
    selected_count: int
    omitted_count: int
    package: PromptPackage
