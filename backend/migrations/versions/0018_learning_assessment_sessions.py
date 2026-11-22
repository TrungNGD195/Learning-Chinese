"""Persist first practice answers and isolated, versioned HSK mock-exam attempts."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0018_learning_assessment_sessions'
down_revision = '0017_account_session_version'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('practice_responses',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('attempt_id', sa.Uuid(), sa.ForeignKey('assessment_attempts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('question_id', sa.Uuid(), sa.ForeignKey('questions.id'), nullable=False),
        sa.Column('answer', postgresql.JSONB(), nullable=False), sa.Column('result', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('attempt_id', 'question_id', name='uq_practice_response_attempt_question'))
    op.create_table('hsk_exam_attempts',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('hsk_level', sa.Integer(), nullable=False), sa.Column('attempt_number', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(), nullable=False), sa.Column('content_version', sa.Text(), nullable=False),
        sa.Column('paper', postgresql.JSONB(), nullable=False), sa.Column('answers', postgresql.JSONB(), nullable=False),
        sa.Column('section_index', sa.Integer(), nullable=False),
        sa.Column('section_started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False), sa.Column('submitted_at', sa.DateTime(timezone=True)),
        sa.Column('result', postgresql.JSONB()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('hsk_level BETWEEN 1 AND 3', name='hsk_exam_level'),
        sa.CheckConstraint("status IN ('IN_PROGRESS','GRADED')", name='hsk_exam_status'),
        sa.UniqueConstraint('user_id', 'hsk_level', 'attempt_number', name='uq_hsk_exam_attempt_number'))
    op.create_index('uq_hsk_exam_active_user_level', 'hsk_exam_attempts', ['user_id', 'hsk_level'], unique=True,
                    postgresql_where=sa.text("status = 'IN_PROGRESS'"))

def downgrade():
    op.drop_table('hsk_exam_attempts')
    op.drop_table('practice_responses')
