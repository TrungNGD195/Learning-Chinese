"""Add deterministic conversation message flow fields.

Revision ID: 0003_conversation_message_flow
Revises: 0002_auth_token_tables
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_conversation_message_flow"
down_revision: Union[str, None] = "0002_auth_token_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("conversations", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("messages", sa.Column("sequence_number", sa.Integer(), nullable=True))
    op.add_column("messages", sa.Column("reply_to_message_id", sa.Uuid(), nullable=True))

    op.execute(
        sa.text(
            """
            WITH ordered_messages AS (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY conversation_id
                           ORDER BY created_at ASC, id ASC
                       ) AS assigned_sequence
                FROM messages
            )
            UPDATE messages AS target
            SET sequence_number = ordered_messages.assigned_sequence
            FROM ordered_messages
            WHERE target.id = ordered_messages.id
            """
        )
    )

    op.alter_column("messages", "sequence_number", existing_type=sa.Integer(), nullable=False)
    op.create_unique_constraint(
        "uq_messages_conversation_id_sequence_number",
        "messages",
        ["conversation_id", "sequence_number"],
    )
    op.create_foreign_key(
        "fk_messages_reply_to_message_id_messages",
        "messages",
        "messages",
        ["reply_to_message_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_messages_reply_to_message_id", "messages", ["reply_to_message_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_messages_reply_to_message_id", table_name="messages")
    op.drop_constraint("fk_messages_reply_to_message_id_messages", "messages", type_="foreignkey")
    op.drop_constraint("uq_messages_conversation_id_sequence_number", "messages", type_="unique")
    op.drop_column("messages", "reply_to_message_id")
    op.drop_column("messages", "sequence_number")
    op.drop_column("conversations", "deleted_at")
