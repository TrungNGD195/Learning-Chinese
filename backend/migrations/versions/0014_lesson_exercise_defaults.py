"""Use type-specific assessment defaults and set existing lesson exercises to 80.

Periodic thresholds and historical attempt results are preserved. PostgreSQL's
insert trigger covers SQL callers; ORM and request defaults cover application use.
"""
from alembic import op
import sqlalchemy as sa

revision = "0014_lesson_exercise_defaults"
down_revision = "0013_pronunciation_lesson"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("assessments", "pass_threshold", existing_type=sa.Integer(), server_default=None)
    op.execute("""
        CREATE FUNCTION assessment_threshold_default() RETURNS trigger AS $$
        BEGIN
            IF NEW.pass_threshold IS NULL THEN
                NEW.pass_threshold := CASE WHEN NEW.type = 'LESSON_EXERCISE' THEN 80 ELSE 90 END;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER assessment_threshold_default_insert
        BEFORE INSERT ON assessments FOR EACH ROW
        EXECUTE FUNCTION assessment_threshold_default();
    """)
    op.execute("UPDATE assessments SET pass_threshold = 80 WHERE type = 'LESSON_EXERCISE'")


def downgrade() -> None:
    op.execute("DROP TRIGGER assessment_threshold_default_insert ON assessments")
    op.execute("DROP FUNCTION assessment_threshold_default()")
    op.alter_column("assessments", "pass_threshold", existing_type=sa.Integer(), server_default="90")
