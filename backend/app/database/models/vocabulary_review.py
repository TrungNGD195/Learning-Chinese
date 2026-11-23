"""Private vocabulary self-ratings; independent of lesson completion and grades."""
from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, String, Uuid, func
from app.database.models._factory import model

VocabularyReviewPreference = model('VocabularyReviewPreference', 'vocabulary_review_preferences', [
    ('user_id', Uuid(as_uuid=True), {'primary_key': True, 'foreign_key': 'users.id', 'ondelete': 'CASCADE'}),
    ('tracking_enabled', Boolean, {'nullable': False, 'server_default': 'true'}),
    ('updated_at', DateTime(timezone=True), {'nullable': False, 'server_default': func.now()}),
])

VocabularyReviewState = model('VocabularyReviewState', 'vocabulary_review_states', [
    ('user_id', Uuid(as_uuid=True), {'primary_key': True, 'foreign_key': 'users.id', 'ondelete': 'CASCADE'}),
    ('card_id', String(24), {'primary_key': True}),
    ('status', String(16)),
    ('version', Integer, {'nullable': False}),
    ('updated_at', DateTime(timezone=True), {'nullable': False, 'server_default': func.now()}),
], CheckConstraint("status IS NULL OR status IN ('LEARNING','KNOWN')", name='vocabulary_review_status'),
   CheckConstraint('version > 0', name='vocabulary_review_version'))
