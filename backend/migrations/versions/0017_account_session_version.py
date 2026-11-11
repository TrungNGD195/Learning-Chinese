"""Invalidate access cookies when account-wide sessions are revoked."""
from alembic import op
import sqlalchemy as sa

revision = '0017_account_session_version'
down_revision = '0016_pronunciation_sandhi'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('session_version', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    op.drop_column('users', 'session_version')
