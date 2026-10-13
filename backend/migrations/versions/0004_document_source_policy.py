"""Add nullable Document source-policy and provenance fields.

Revision ID: 0004_document_source_policy
Revises: 0003_conversation_message_flow
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_document_source_policy"
down_revision: Union[str, None] = "0003_conversation_message_flow"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("title", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("source_category", sa.String(), nullable=True))
    op.add_column("documents", sa.Column("source_origin", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("source_language", sa.String(), nullable=True))
    op.add_column("documents", sa.Column("usage_rights_note", sa.Text(), nullable=True))

    op.create_check_constraint(
        op.f("ck_documents_source_category_values"),
        "documents",
        "source_category IS NULL OR source_category IN ('CURRICULUM_MATERIAL', 'INTERNAL_AUTHORED')",
    )
    op.create_check_constraint(
        op.f("ck_documents_source_language_values"),
        "documents",
        "source_language IS NULL OR source_language IN ('vi', 'zh', 'en')",
    )
    op.create_check_constraint(
        op.f("ck_documents_title_non_blank"),
        "documents",
        "title IS NULL OR length(btrim(title)) > 0",
    )
    op.create_check_constraint(
        op.f("ck_documents_source_origin_non_blank"),
        "documents",
        "source_origin IS NULL OR length(btrim(source_origin)) > 0",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_documents_source_origin_non_blank"), "documents", type_="check")
    op.drop_constraint(op.f("ck_documents_title_non_blank"), "documents", type_="check")
    op.drop_constraint(op.f("ck_documents_source_language_values"), "documents", type_="check")
    op.drop_constraint(op.f("ck_documents_source_category_values"), "documents", type_="check")
    op.drop_column("documents", "usage_rights_note")
    op.drop_column("documents", "source_language")
    op.drop_column("documents", "source_origin")
    op.drop_column("documents", "source_category")
    op.drop_column("documents", "title")
