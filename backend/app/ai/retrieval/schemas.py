from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ActiveEmbeddingProfileSnapshot:
    id: UUID
    provider: str
    provider_version: str
    model_name: str
    model_version: str
    dimensions: int
    embedding_input_version: str
    normalize_embeddings: bool


@dataclass(frozen=True)
class CandidateMetadata:
    chunk_id: UUID
    chunk_index: int
    content: str
    content_type: str
    knowledge_version_id: UUID
    knowledge_source_id: UUID
    source_type: str
    source_document_id: UUID | None
    source_lesson_id: UUID | None
    chunk_lesson_id: UUID | None
    document_title: str | None
    lesson_title: str | None
    hsk_level_number: int | None
    page_number: int | None
    section: str | None
    locator_metadata: dict | None


@dataclass(frozen=True)
class RetrievalCandidate:
    rank: int
    chunk_id: UUID
    chunk_index: int
    content: str
    content_type: str
    knowledge_version_id: UUID
    knowledge_source_id: UUID
    source_type: str
    source_document_id: UUID | None
    source_lesson_id: UUID | None
    chunk_lesson_id: UUID | None
    document_title: str | None
    lesson_title: str | None
    hsk_level_number: int | None
    page_number: int | None
    section: str | None
    locator_metadata: dict | None
    distance: float
    retrieval_score: float
