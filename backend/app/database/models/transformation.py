from sqlalchemy import CheckConstraint, DateTime, Index, JSON, String, Text, Uuid

from app.database.models._factory import model
from app.database.models.curriculum import created, id_col, updated


TransformationRun = model(
    "TransformationRun",
    "transformation_runs",
    [
        id_col(),
        ("source_type", String, {"nullable": False}),
        ("document_id", Uuid(as_uuid=True), {"foreign_key": "documents.id", "ondelete": "CASCADE"}),
        ("lesson_id", Uuid(as_uuid=True), {"foreign_key": "lessons.id", "ondelete": "CASCADE"}),
        ("parsing_run_id", Uuid(as_uuid=True), {"nullable": False, "foreign_key": "parsing_runs.id", "ondelete": "RESTRICT"}),
        ("parsed_storage_reference", Text, {"nullable": False}),
        ("transformation_strategy", String, {"nullable": False}),
        ("transformation_version", String, {"nullable": False}),
        ("status", String, {"nullable": False}),
        ("transformed_storage_reference", Text),
        ("error_code", String),
        ("error_detail", Text),
        ("source_metadata_snapshot", JSON, {"nullable": False}),
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
        "status <> 'SUCCEEDED' OR (transformed_storage_reference IS NOT NULL AND error_code IS NULL)",
        name="success_invariant",
    ),
    CheckConstraint(
        "status <> 'FAILED' OR (transformed_storage_reference IS NULL AND error_code IS NOT NULL)",
        name="failure_invariant",
    ),
    indexes=[
        Index("ix_transformation_runs_document_id", "document_id"),
        Index("ix_transformation_runs_lesson_id", "lesson_id"),
        Index("ix_transformation_runs_parsing_run_id", "parsing_run_id"),
        Index("ix_transformation_runs_status", "status"),
    ],
)
