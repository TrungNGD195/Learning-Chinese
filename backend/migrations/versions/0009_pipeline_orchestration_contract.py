"""Add Step-5.6 orchestration identity and concurrency constraints.

Revision ID: 0009_pipeline_orchestration_contract
Revises: 0008_chunking_contract
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0009_pipeline_orchestration_contract"
down_revision: Union[str, None] = "0008_chunking_contract"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _version_num_width() -> int | None:
    bind = op.get_bind()
    columns = sa.inspect(bind).get_columns("alembic_version")
    column = next((item for item in columns if item["name"] == "version_num"), None)
    if column is None:
        raise RuntimeError("Alembic version_num column is unavailable")
    return getattr(column["type"], "length", None)


def upgrade() -> None:
    # Keep the frozen full revision ID storable before Alembic stamps it.
    width = _version_num_width()
    if width == 32:
        op.alter_column(
            "alembic_version",
            "version_num",
            existing_type=sa.String(length=32),
            type_=sa.String(length=64),
            existing_nullable=False,
        )
    elif width != 64:
        raise RuntimeError("Unsupported alembic_version.version_num width")

    op.add_column(
        "documents",
        sa.Column("review_transformation_run_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_documents_review_transformation_run_id_transformation_runs"),
        "documents",
        "transformation_runs",
        ["review_transformation_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint(
        "uq_knowledge_sources_document_id", "knowledge_sources", ["document_id"]
    )
    op.create_index(
        "uq_knowledge_versions_one_processing_per_source",
        "knowledge_versions",
        ["knowledge_source_id"],
        unique=True,
        postgresql_where=sa.text("status = 'PROCESSING'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_knowledge_versions_one_processing_per_source",
        table_name="knowledge_versions",
        postgresql_where=sa.text("status = 'PROCESSING'"),
    )
    op.drop_constraint(
        "uq_knowledge_sources_document_id", "knowledge_sources", type_="unique"
    )
    op.drop_constraint(
        op.f("fk_documents_review_transformation_run_id_transformation_runs"),
        "documents",
        type_="foreignkey",
    )
    op.drop_column("documents", "review_transformation_run_id")
    # D-064 intentionally retains VARCHAR(64) after downgrade.
