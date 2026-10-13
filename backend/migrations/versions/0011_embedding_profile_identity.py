"""Add durable semantic identity to EmbeddingProfile."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0011_embedding_profile_identity"
down_revision: Union[str, None] = "0010_incremental_reprocessing_contract"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("embedding_profiles", sa.Column("provider_version", sa.Text(), nullable=True))
    op.add_column("embedding_profiles", sa.Column("embedding_input_version", sa.Text(), nullable=True))
    op.add_column("embedding_profiles", sa.Column("normalize_embeddings", sa.Boolean(), nullable=True))
    op.create_unique_constraint(
        "uq_embedding_profiles_semantic_identity",
        "embedding_profiles",
        [
            "provider",
            "provider_version",
            "model_name",
            "model_version",
            "dimensions",
            "embedding_input_version",
            "normalize_embeddings",
        ],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_embedding_profiles_semantic_identity", "embedding_profiles", type_="unique"
    )
    op.drop_column("embedding_profiles", "normalize_embeddings")
    op.drop_column("embedding_profiles", "embedding_input_version")
    op.drop_column("embedding_profiles", "provider_version")
