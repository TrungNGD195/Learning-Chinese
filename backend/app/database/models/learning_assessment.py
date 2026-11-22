"""Additive assessment state; existing lesson/attempt records keep their contracts."""
from sqlalchemy import DateTime, Integer, String, Text, Uuid, UniqueConstraint, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from app.database.models._factory import model
from app.database.models.curriculum import id_col, created, updated

PracticeResponse = model('PracticeResponse', 'practice_responses', [id_col(),
    ('attempt_id', Uuid(as_uuid=True), {'nullable': False, 'foreign_key': 'assessment_attempts.id', 'ondelete': 'CASCADE'}),
    ('question_id', Uuid(as_uuid=True), {'nullable': False, 'foreign_key': 'questions.id'}),
    ('answer', JSONB, {'nullable': False}), ('result', JSONB, {'nullable': False}), created()],
    UniqueConstraint('attempt_id', 'question_id', name='uq_practice_response_attempt_question'))

HskExamAttempt = model('HskExamAttempt', 'hsk_exam_attempts', [id_col(),
    ('user_id', Uuid(as_uuid=True), {'nullable': False, 'foreign_key': 'users.id'}),
    ('hsk_level', Integer, {'nullable': False}), ('attempt_number', Integer, {'nullable': False}),
    ('status', String, {'nullable': False}), ('content_version', Text, {'nullable': False}),
    ('paper', JSONB, {'nullable': False}), ('answers', JSONB, {'nullable': False}),
    ('section_index', Integer, {'nullable': False}), ('section_started_at', DateTime(timezone=True), {'nullable': False}),
    ('started_at', DateTime(timezone=True), {'nullable': False}), ('submitted_at', DateTime(timezone=True)),
    ('result', JSONB), created(), updated()],
    CheckConstraint('hsk_level BETWEEN 1 AND 3', name='hsk_exam_level'),
    CheckConstraint("status IN ('IN_PROGRESS','GRADED')", name='hsk_exam_status'),
    UniqueConstraint('user_id', 'hsk_level', 'attempt_number', name='uq_hsk_exam_attempt_number'),
    indexes=(Index('uq_hsk_exam_active_user_level', 'user_id', 'hsk_level', unique=True,
                   postgresql_where=__import__('sqlalchemy').text("status = 'IN_PROGRESS'")),))
