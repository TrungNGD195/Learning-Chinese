from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class EmbeddingProviderIdentity:
    provider: str
    provider_version: str
    model_name: str
    model_version: str
    dimensions: int
    embedding_input_version: str
    normalize_embeddings: bool


@dataclass(frozen=True)
class EmbeddingProfileIdentity(EmbeddingProviderIdentity):
    """Durable semantic identity, deliberately excluding lifecycle status."""


@dataclass(frozen=True)
class EmbeddingChunkContext:
    chunk_id: UUID
    chunk_index: int
    content: str
    content_type: str
    section: str | None = None
    document_title: str | None = None
    lesson_id: UUID | None = None
    lesson_title: str | None = None
    hsk_level_number: int | None = None
    source_type: str | None = None
    source_document_id: UUID | None = None
    source_lesson_id: UUID | None = None
    chunk_lesson_id: UUID | None = None


@dataclass(frozen=True)
class EmbeddingBuildResult:
    knowledge_version_id: UUID
    embedding_profile_id: UUID
    required_count: int
    embedded_count: int
    embedded_this_run: int
    skipped_count: int
    knowledge_version_status: str = "PROCESSING"
