"""Add account-scoped flashcard preferences and versioned self-ratings."""
from alembic import op
import sqlalchemy as sa

revision = '0019_vocabulary_review_progress'
down_revision = '0018_learning_assessment_sessions'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('vocabulary_review_preferences',
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('tracking_enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_table('vocabulary_review_states',
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('card_id', sa.String(24), primary_key=True),
        sa.Column('status', sa.String(16)),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IS NULL OR status IN ('LEARNING','KNOWN')", name='vocabulary_review_status'),
        sa.CheckConstraint('version > 0', name='vocabulary_review_version'))


def downgrade():
    op.drop_table('vocabulary_review_states')
    op.drop_table('vocabulary_review_preferences')
