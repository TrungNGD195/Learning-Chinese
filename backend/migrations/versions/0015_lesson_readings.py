"""Lesson reading content and explicit, versioned learner completion."""
from alembic import op
import sqlalchemy as sa

revision = '0015_lesson_readings'
down_revision = '0014_lesson_exercise_defaults'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('lesson_readings',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('lesson_id', sa.Uuid(), sa.ForeignKey('lessons.id'), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.Column('title', sa.Text(), nullable=False), sa.Column('content', sa.Text(), nullable=False),
        sa.Column('pinyin', sa.Text()), sa.Column('vietnamese_translation', sa.Text()),
        sa.Column('source_reference', sa.Text()), sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('lesson_id', 'order_index'),
        sa.CheckConstraint('version >= 1', name=op.f('ck_lesson_readings_version_positive')),
        sa.CheckConstraint('order_index >= 1', name=op.f('ck_lesson_readings_order_positive')),
    )
    op.create_table('learner_reading_progress',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('lesson_reading_id', sa.Uuid(), sa.ForeignKey('lesson_readings.id'), nullable=False),
        sa.Column('reading_version', sa.Integer(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('user_id', 'lesson_reading_id'),
    )


def downgrade():
    op.drop_table('learner_reading_progress')
    op.drop_table('lesson_readings')
