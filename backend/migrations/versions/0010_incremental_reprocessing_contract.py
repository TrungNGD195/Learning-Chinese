"""Add exact approved-artifact and KnowledgeVersion build lineage."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0010_incremental_reprocessing_contract"
down_revision: Union[str, None] = "0009_pipeline_orchestration_contract"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("approved_transformation_run_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_documents_approved_transformation_run_id_transformation_runs"),
        "documents",
        "transformation_runs",
        ["approved_transformation_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "knowledge_versions",
        sa.Column("transformation_run_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_knowledge_versions_transformation_run_id_transformation_runs"),
        "knowledge_versions",
        "transformation_runs",
        ["transformation_run_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.execute(sa.text("""
        UPDATE documents AS document
        SET approved_transformation_run_id = document.review_transformation_run_id
        WHERE document.review_status = 'APPROVED'
          AND document.review_transformation_run_id IS NOT NULL
          AND EXISTS (
              SELECT 1
              FROM transformation_runs AS run
              WHERE run.id = document.review_transformation_run_id
                AND run.source_type = 'DOCUMENT'
                AND run.document_id = document.id
                AND run.status = 'SUCCEEDED'
                AND run.transformed_storage_reference IS NOT NULL
                AND run.error_code IS NULL
          )
    """))


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_knowledge_versions_transformation_run_id_transformation_runs"),
        "knowledge_versions",
        type_="foreignkey",
    )
    op.drop_column("knowledge_versions", "transformation_run_id")
    op.drop_constraint(
        op.f("fk_documents_approved_transformation_run_id_transformation_runs"),
        "documents",
        type_="foreignkey",
    )
    op.drop_column("documents", "approved_transformation_run_id")
