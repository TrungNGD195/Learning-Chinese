"""Add the Step 6.2 vector storage readiness contract."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0012_vector_storage_readiness"
down_revision: Union[str, None] = "0011_embedding_profile_identity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_embeddings_embedding_profile_id", "embeddings", ["embedding_profile_id"], unique=False)
    op.create_index(
        "uq_embedding_profiles_one_active", "embedding_profiles", ["status"], unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )
    op.drop_constraint("fk_embeddings_chunk_id_chunks", "embeddings", type_="foreignkey")
    op.create_foreign_key(
        "fk_embeddings_chunk_id_chunks", "embeddings", "chunks", ["chunk_id"], ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_embeddings_chunk_id_chunks", "embeddings", type_="foreignkey")
    op.create_foreign_key(
        "fk_embeddings_chunk_id_chunks", "embeddings", "chunks", ["chunk_id"], ["id"]
    )
    op.drop_index("uq_embedding_profiles_one_active", table_name="embedding_profiles")
    op.drop_index("ix_embeddings_embedding_profile_id", table_name="embeddings")
