"""Add raw ingestion metadata to Documents.

Revision ID: 0005_raw_document_metadata
Revises: 0004_document_source_policy
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005_raw_document_metadata"
down_revision: Union[str, None] = "0004_document_source_policy"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("mime_type", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("file_size_bytes", sa.BigInteger(), nullable=True))
    op.add_column("documents", sa.Column("content_hash", sa.Text(), nullable=True))
    op.create_unique_constraint("uq_documents_content_hash", "documents", ["content_hash"])
    op.create_check_constraint(
        op.f("ck_documents_file_size_positive"), "documents",
        "file_size_bytes IS NULL OR file_size_bytes > 0",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_documents_file_size_positive"), "documents", type_="check")
    op.drop_constraint("uq_documents_content_hash", "documents", type_="unique")
    op.drop_column("documents", "content_hash")
    op.drop_column("documents", "file_size_bytes")
    op.drop_column("documents", "mime_type")
