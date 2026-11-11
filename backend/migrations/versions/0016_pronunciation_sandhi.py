"""Add tone-sandhi study without erasing existing pronunciation completion."""
from alembic import op
import sqlalchemy as sa

revision = '0016_pronunciation_sandhi'
down_revision = '0015_lesson_readings'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint(op.f('ck_pronunciation_lesson_progress_section_index_range'), 'pronunciation_lesson_progress', type_='check')
    op.create_check_constraint(op.f('ck_pronunciation_lesson_progress_section_index_range'), 'pronunciation_lesson_progress', 'section_index BETWEEN 0 AND 4')
    op.execute(sa.text("""INSERT INTO pronunciation_sections (id, code, title, description, order_index)
        VALUES (gen_random_uuid(), 'SANDHI', 'Biến điệu', 'Thanh 3, 一, 不 và thanh nhẹ trong lời nói.', 4)
        ON CONFLICT (code) DO NOTHING"""))


def downgrade():
    op.execute("DELETE FROM pronunciation_progress WHERE pronunciation_section_id IN (SELECT id FROM pronunciation_sections WHERE code = 'SANDHI')")
    op.execute("DELETE FROM pronunciation_sections WHERE code = 'SANDHI'")
    op.execute("UPDATE pronunciation_lesson_progress SET section_index = 3, step_index = 0 WHERE section_index >= 3")
    op.drop_constraint(op.f('ck_pronunciation_lesson_progress_section_index_range'), 'pronunciation_lesson_progress', type_='check')
    op.create_check_constraint(op.f('ck_pronunciation_lesson_progress_section_index_range'), 'pronunciation_lesson_progress', 'section_index BETWEEN 0 AND 3')
