from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from app.ai.citations.schemas import ValidatedCitation

NO_EVIDENCE_CONTENT = "Hiện tại mình chưa có đủ nguồn đáng tin cậy để trả lời câu hỏi này."


class RagRunStatus(StrEnum):
    GROUNDED_ANSWER = "GROUNDED_ANSWER"
    NO_EVIDENCE = "NO_EVIDENCE"


class RagInternalTier(StrEnum):
    CURRENT_LESSON = "CURRENT_LESSON"
    INTERNAL_KB = "INTERNAL_KB"


class RagTierUsed(StrEnum):
    CURRENT_LESSON = "CURRENT_LESSON"
    INTERNAL_KB = "INTERNAL_KB"
    TRUSTED_EXTERNAL = "TRUSTED_EXTERNAL"
    NONE = "NONE"


@dataclass(frozen=True)
class RetrievalTraceEntry:
    chunk_id: UUID
    rank: int
    retrieval_score: float
    rerank_score: float


@dataclass(frozen=True)
class RagRunResult:
    assistant_message_id: UUID
    status: RagRunStatus
    assistant_content: str
    tiers_attempted: tuple[RagTierUsed, ...]
    tier_used: RagTierUsed
    current_lesson_candidate_count: int
    current_lesson_scored_count: int
    internal_kb_candidate_count: int
    internal_kb_scored_count: int
    selected_context_count: int
    memory_selected_turn_count: int
    retrieval_trace: tuple[RetrievalTraceEntry, ...]
    validated_citations: tuple[ValidatedCitation, ...]
    external_candidate_count: int = 0
    external_scored_count: int = 0

    def __post_init__(self) -> None:
        counts = (
            self.current_lesson_candidate_count, self.current_lesson_scored_count,
            self.internal_kb_candidate_count, self.internal_kb_scored_count,
            self.selected_context_count, self.memory_selected_turn_count,
            self.external_candidate_count, self.external_scored_count,
        )
        if any(type(value) is not int or value < 0 for value in counts):
            raise ValueError("RAG result counts must be non-negative integers")
        if self.status is RagRunStatus.NO_EVIDENCE:
            if (self.assistant_content != NO_EVIDENCE_CONTENT or self.tier_used is not RagTierUsed.NONE
                    or self.tiers_attempted != (RagTierUsed.CURRENT_LESSON, RagTierUsed.INTERNAL_KB, RagTierUsed.TRUSTED_EXTERNAL)
                    or self.selected_context_count or self.memory_selected_turn_count
                    or self.retrieval_trace or self.validated_citations):
                raise ValueError("NO_EVIDENCE result violates the frozen contract")
        else:
            if self.status is not RagRunStatus.GROUNDED_ANSWER or not self.assistant_content.strip():
                raise ValueError("Grounded RAG result is invalid")
            expected_tiers = {
                RagTierUsed.CURRENT_LESSON: (RagTierUsed.CURRENT_LESSON,),
                RagTierUsed.INTERNAL_KB: (RagTierUsed.CURRENT_LESSON, RagTierUsed.INTERNAL_KB),
                RagTierUsed.TRUSTED_EXTERNAL: (RagTierUsed.CURRENT_LESSON, RagTierUsed.INTERNAL_KB, RagTierUsed.TRUSTED_EXTERNAL),
            }.get(self.tier_used)
            if (
                self.tiers_attempted != expected_tiers
                or self.tier_used is RagTierUsed.NONE
                or self.selected_context_count < 1
                or not self.validated_citations
            ):
                raise ValueError("Grounded RAG result violates the frozen contract")
            if self.tier_used is RagTierUsed.TRUSTED_EXTERNAL:
                if self.retrieval_trace or not self.external_candidate_count or not self.external_scored_count:
                    raise ValueError("External grounded RAG result violates the frozen contract")
                if any(citation.source_kind != "EXTERNAL_URL" for citation in self.validated_citations):
                    raise ValueError("External grounded citations must be external URLs")
            elif not self.retrieval_trace or self.external_candidate_count or self.external_scored_count:
                raise ValueError("Internal grounded RAG result violates the frozen contract")
            if self.tier_used is RagTierUsed.CURRENT_LESSON and (
                self.internal_kb_candidate_count or self.internal_kb_scored_count
            ):
                raise ValueError("CURRENT_LESSON result contains INTERNAL_KB work")


@dataclass(frozen=True)
class CalibrationScoreRequest:
    query: str
    lesson_id: UUID


@dataclass(frozen=True)
class CalibrationCandidateTrace:
    chunk_id: UUID
    retrieval_rank: int
    retrieval_score: float
    rerank_rank: int
    rerank_score: float
    knowledge_source_id: UUID
    source_type: str
    source_lesson_id: UUID | None
    content_type: str


@dataclass(frozen=True)
class CalibrationTierTrace:
    tier: RagInternalTier
    status: str
    retrieval_candidate_count: int
    scored_count: int
    candidates: tuple[CalibrationCandidateTrace, ...]


@dataclass(frozen=True)
class CalibrationScoreTrace:
    current_lesson: CalibrationTierTrace
    internal_kb: CalibrationTierTrace
