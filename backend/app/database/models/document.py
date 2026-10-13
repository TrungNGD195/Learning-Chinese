from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, Uuid, func

from app.database.models._factory import model
from app.database.models.curriculum import created, id_col, updated

Document = model(
    "Document",
    "documents",
    [
        id_col(),
        ("original_filename", Text, {"nullable": False}),
        ("file_type", Text, {"nullable": False}),
        ("storage_reference", Text, {"nullable": False}),
        ("mime_type", Text, {"nullable": True}),
        ("file_size_bytes", BigInteger, {"nullable": True}),
        ("content_hash", Text, {"nullable": True}),
        ("processing_status", String, {"nullable": False}),
        ("review_status", String, {"nullable": False}),
        ("uploaded_by", Uuid(as_uuid=True), {"nullable": False, "foreign_key": "users.id"}),
        ("approved_by", Uuid(as_uuid=True), {"foreign_key": "users.id"}),
        ("approved_at", DateTime(timezone=True)),
        ("review_transformation_run_id", Uuid(as_uuid=True), {
            "foreign_key": "transformation_runs.id", "ondelete": "SET NULL",
        }),
        ("approved_transformation_run_id", Uuid(as_uuid=True), {
            "foreign_key": "transformation_runs.id", "ondelete": "SET NULL",
        }),
        ("title", Text, {"nullable": True}),
        ("source_category", String, {"nullable": True}),
        ("source_origin", Text, {"nullable": True}),
        ("source_language", String, {"nullable": True}),
        ("usage_rights_note", Text, {"nullable": True}),
        created(),
        updated(),
    ],
    CheckConstraint("processing_status IN ('UPLOADED','PROCESSING','PREVIEW_READY','FAILED')", name="processing_status_values"),
    CheckConstraint("review_status IN ('PENDING','APPROVED','REJECTED')", name="review_status_values"),
    CheckConstraint(
        "review_status <> 'APPROVED' OR (processing_status = 'PREVIEW_READY' AND approved_by IS NOT NULL AND approved_at IS NOT NULL)",
        name="approval_invariant",
    ),
    CheckConstraint(
        "source_category IS NULL OR source_category IN ('CURRICULUM_MATERIAL', 'INTERNAL_AUTHORED')",
        name="source_category_values",
    ),
    CheckConstraint("source_language IS NULL OR source_language IN ('vi', 'zh', 'en')", name="source_language_values"),
    CheckConstraint("title IS NULL OR length(btrim(title)) > 0", name="title_non_blank"),
    CheckConstraint("source_origin IS NULL OR length(btrim(source_origin)) > 0", name="source_origin_non_blank"),
    CheckConstraint("file_size_bytes IS NULL OR file_size_bytes > 0", name="file_size_positive"),
    UniqueConstraint("content_hash", name="uq_documents_content_hash"),
    indexes=[Index("ix_documents_processing_status", "processing_status"), Index("ix_documents_review_status", "review_status")],
)
