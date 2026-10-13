"""Persist document transformation lifecycle metadata.

Revision ID: 0007_transformation_runs
Revises: 0006_parsing_runs
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0007_transformation_runs"
down_revision: Union[str, None] = "0006_parsing_runs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "transformation_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("lesson_id", sa.Uuid(), nullable=True),
        sa.Column("parsing_run_id", sa.Uuid(), nullable=False),
        sa.Column("parsed_storage_reference", sa.Text(), nullable=False),
        sa.Column("transformation_strategy", sa.String(), nullable=False),
        sa.Column("transformation_version", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("transformed_storage_reference", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("source_metadata_snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("source_type IN ('DOCUMENT','LESSON')", name=op.f("ck_transformation_runs_source_type_values")),
        sa.CheckConstraint("status IN ('PENDING','PROCESSING','SUCCEEDED','FAILED')", name=op.f("ck_transformation_runs_status_values")),
        sa.CheckConstraint(
            "(source_type = 'DOCUMENT' AND document_id IS NOT NULL AND lesson_id IS NULL) OR "
            "(source_type = 'LESSON' AND lesson_id IS NOT NULL AND document_id IS NULL)",
            name=op.f("ck_transformation_runs_source_target_invariant"),
        ),
        sa.CheckConstraint(
            "status <> 'SUCCEEDED' OR (transformed_storage_reference IS NOT NULL AND error_code IS NULL)",
            name=op.f("ck_transformation_runs_success_invariant"),
        ),
        sa.CheckConstraint(
            "status <> 'FAILED' OR (transformed_storage_reference IS NULL AND error_code IS NOT NULL)",
            name=op.f("ck_transformation_runs_failure_invariant"),
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], name=op.f("fk_transformation_runs_document_id_documents"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], name=op.f("fk_transformation_runs_lesson_id_lessons"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parsing_run_id"], ["parsing_runs.id"], name=op.f("fk_transformation_runs_parsing_run_id_parsing_runs"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transformation_runs")),
    )
    op.create_index("ix_transformation_runs_document_id", "transformation_runs", ["document_id"])
    op.create_index("ix_transformation_runs_lesson_id", "transformation_runs", ["lesson_id"])
    op.create_index("ix_transformation_runs_parsing_run_id", "transformation_runs", ["parsing_run_id"])
    op.create_index("ix_transformation_runs_status", "transformation_runs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_transformation_runs_status", table_name="transformation_runs")
    op.drop_index("ix_transformation_runs_parsing_run_id", table_name="transformation_runs")
    op.drop_index("ix_transformation_runs_lesson_id", table_name="transformation_runs")
    op.drop_index("ix_transformation_runs_document_id", table_name="transformation_runs")
    op.drop_table("transformation_runs")
