"""Persist the pronunciation lesson cursor and explicit final completion.

Learners who completed all three legacy sections retain access to HSK 1.
"""
from alembic import op
import sqlalchemy as sa

revision = "0013_pronunciation_lesson"
down_revision = "0012_vector_storage_readiness"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pronunciation_lesson_progress",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("section_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("step_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("section_index BETWEEN 0 AND 3", name=op.f("ck_pronunciation_lesson_progress_section_index_range")),
        sa.CheckConstraint("step_index >= 0", name=op.f("ck_pronunciation_lesson_progress_step_index_nonnegative")),
    )
    op.execute(sa.text("""
        INSERT INTO pronunciation_lesson_progress (user_id, section_index, step_index, completed_at)
        SELECT p.user_id, 3, 0, MAX(p.completed_at)
        FROM pronunciation_progress p
        JOIN pronunciation_sections s ON s.id = p.pronunciation_section_id
        WHERE s.code IN ('INITIALS', 'FINALS', 'TONES') AND p.completed_at IS NOT NULL
        GROUP BY p.user_id
        HAVING COUNT(DISTINCT s.code) = 3
    """))


def downgrade() -> None:
    op.drop_table("pronunciation_lesson_progress")
