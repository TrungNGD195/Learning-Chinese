"""Persist parsing lifecycle metadata.

Revision ID: 0006_parsing_runs
Revises: 0005_raw_document_metadata
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006_parsing_runs"
down_revision: Union[str, None] = "0005_raw_document_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "parsing_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("lesson_id", sa.Uuid(), nullable=True),
        sa.Column("raw_storage_reference", sa.Text(), nullable=False),
        sa.Column("raw_content_hash", sa.String(), nullable=False),
        sa.Column("parser_name", sa.String(), nullable=False),
        sa.Column("parser_version", sa.String(), nullable=False),
        sa.Column("cleaning_strategy", sa.String(), nullable=False),
        sa.Column("cleaning_version", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("parsed_storage_reference", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("source_type IN ('DOCUMENT','LESSON')", name=op.f("ck_parsing_runs_source_type_values")),
        sa.CheckConstraint("status IN ('PENDING','PROCESSING','SUCCEEDED','FAILED')", name=op.f("ck_parsing_runs_status_values")),
        sa.CheckConstraint(
            "(source_type = 'DOCUMENT' AND document_id IS NOT NULL AND lesson_id IS NULL) OR "
            "(source_type = 'LESSON' AND lesson_id IS NOT NULL AND document_id IS NULL)",
            name=op.f("ck_parsing_runs_source_target_invariant"),
        ),
        sa.CheckConstraint(
            "status <> 'SUCCEEDED' OR (parsed_storage_reference IS NOT NULL AND error_code IS NULL)",
            name=op.f("ck_parsing_runs_success_invariant"),
        ),
        sa.CheckConstraint(
            "status <> 'FAILED' OR (parsed_storage_reference IS NULL AND error_code IS NOT NULL)",
            name=op.f("ck_parsing_runs_failure_invariant"),
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], name=op.f("fk_parsing_runs_document_id_documents"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], name=op.f("fk_parsing_runs_lesson_id_lessons"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_parsing_runs")),
    )
    op.create_index("ix_parsing_runs_document_id", "parsing_runs", ["document_id"])
    op.create_index("ix_parsing_runs_lesson_id", "parsing_runs", ["lesson_id"])
    op.create_index("ix_parsing_runs_status", "parsing_runs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_parsing_runs_status", table_name="parsing_runs")
    op.drop_index("ix_parsing_runs_lesson_id", table_name="parsing_runs")
    op.drop_index("ix_parsing_runs_document_id", table_name="parsing_runs")
    op.drop_table("parsing_runs")
