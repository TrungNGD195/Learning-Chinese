from sqlalchemy import CheckConstraint, DateTime, Index, String, Text, Uuid

from app.database.models._factory import model
from app.database.models.curriculum import created, id_col, updated


ParsingRun = model(
    "ParsingRun",
    "parsing_runs",
    [
        id_col(),
        ("source_type", String, {"nullable": False}),
        ("document_id", Uuid(as_uuid=True), {"foreign_key": "documents.id", "ondelete": "CASCADE"}),
        ("lesson_id", Uuid(as_uuid=True), {"foreign_key": "lessons.id", "ondelete": "CASCADE"}),
        ("raw_storage_reference", Text, {"nullable": False}),
        ("raw_content_hash", String, {"nullable": False}),
        ("parser_name", String, {"nullable": False}),
        ("parser_version", String, {"nullable": False}),
        ("cleaning_strategy", String, {"nullable": False}),
        ("cleaning_version", String, {"nullable": False}),
        ("status", String, {"nullable": False}),
        ("parsed_storage_reference", Text),
        ("error_code", String),
        ("error_detail", Text),
        created(),
        updated(),
    ],
    CheckConstraint("source_type IN ('DOCUMENT','LESSON')", name="source_type_values"),
    CheckConstraint("status IN ('PENDING','PROCESSING','SUCCEEDED','FAILED')", name="status_values"),
    CheckConstraint(
        "(source_type = 'DOCUMENT' AND document_id IS NOT NULL AND lesson_id IS NULL) OR "
        "(source_type = 'LESSON' AND lesson_id IS NOT NULL AND document_id IS NULL)",
        name="source_target_invariant",
    ),
    CheckConstraint(
        "status <> 'SUCCEEDED' OR (parsed_storage_reference IS NOT NULL AND error_code IS NULL)",
        name="success_invariant",
    ),
    CheckConstraint(
        "status <> 'FAILED' OR (parsed_storage_reference IS NULL AND error_code IS NOT NULL)",
        name="failure_invariant",
    ),
    indexes=[
        Index("ix_parsing_runs_document_id", "document_id"),
        Index("ix_parsing_runs_lesson_id", "lesson_id"),
        Index("ix_parsing_runs_status", "status"),
    ],
)
