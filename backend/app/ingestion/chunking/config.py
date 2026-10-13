from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChunkingConfig:
    strategy: str = "structure_aware"
    version: str = "v1"
    target_chars: int = 1200
    max_chars: int = 1800
    overlap_chars: int = 150


DEFAULT_CHUNKING_CONFIG = ChunkingConfig()
METADATA_SCHEMA_VERSION = "chunk_metadata/v1"
TABLE_ROW_SEPARATOR = "\n"
LIST_ITEM_SEPARATOR = "\n"
BLOCK_SEPARATOR = "\n\n"
