from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class NearestVectorResult:
    chunk_id: UUID
    distance: float


@dataclass(frozen=True)
class VectorReadinessResult:
    knowledge_version_id: UUID
    embedding_profile_id: UUID
    ready: bool
    required_chunk_count: int
    embedding_count: int
    expected_dimensions: int
    invalid_dimension_count: int
    probe_distance: float | None
    failure_code: str | None
