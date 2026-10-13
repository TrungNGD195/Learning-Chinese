"""Persist the Step-5.5 chunking contract.

Revision ID: 0008_chunking_contract
Revises: 0007_transformation_runs
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0008_chunking_contract"
down_revision: Union[str, None] = "0007_transformation_runs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("knowledge_versions", sa.Column("chunking_version", sa.Text(), nullable=True))
    op.add_column("knowledge_versions", sa.Column("chunk_max_chars", sa.Integer(), nullable=True))
    op.add_column("chunks", sa.Column("content_hash", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("chunks", "content_hash")
    op.drop_column("knowledge_versions", "chunk_max_chars")
    op.drop_column("knowledge_versions", "chunking_version")
