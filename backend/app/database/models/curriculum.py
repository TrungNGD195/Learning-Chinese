from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, Uuid, UniqueConstraint, func

from app.database.models._factory import model

id_col = lambda: ("id", Uuid(as_uuid=True), {"primary_key": True, "default": uuid4})
created = lambda: ("created_at", DateTime(timezone=True), {"nullable": False, "server_default": func.now()})
updated = lambda: ("updated_at", DateTime(timezone=True), {"nullable": False, "server_default": func.now(), "onupdate": func.now()})

HSKLevel = model("HSKLevel", "hsk_levels", [id_col(), ("level_number", Integer, {"nullable": False, "unique": True}), ("title", Text), ("description", Text), ("order_index", Integer, {"nullable": False})])
from sqlalchemy import Index
Lesson = model("Lesson", "lessons", [id_col(), ("hsk_level_id", Uuid(as_uuid=True), {"nullable": False, "foreign_key": "hsk_levels.id"}), ("lesson_number", Integer, {"nullable": False}), ("title", Text, {"nullable": False}), ("description", Text), ("status", String, {"nullable": False}), created(), updated(), ("published_at", DateTime(timezone=True))], UniqueConstraint("hsk_level_id", "lesson_number"), CheckConstraint("status IN ('DRAFT','PUBLISHED','ARCHIVED')", name="status_values"), indexes=[Index("ix_lessons_hsk_level_id", "hsk_level_id")])

CurriculumUnit = model("CurriculumUnit", "curriculum_units", [id_col(), ("hsk_level_id", Uuid(as_uuid=True), {"nullable": False, "foreign_key": "hsk_levels.id"}), ("unit_type", String, {"nullable": False}), ("lesson_id", Uuid(as_uuid=True), {"foreign_key": "lessons.id"}), ("assessment_id", Uuid(as_uuid=True), {"foreign_key": "assessments.id"}), ("order_index", Integer, {"nullable": False})], UniqueConstraint("hsk_level_id", "order_index"), CheckConstraint("unit_type IN ('LESSON','PERIODIC_TEST')", name="unit_type_values"), CheckConstraint("(unit_type = 'LESSON' AND lesson_id IS NOT NULL AND assessment_id IS NULL) OR (unit_type = 'PERIODIC_TEST' AND assessment_id IS NOT NULL AND lesson_id IS NULL)", name="target_invariant"), indexes=[Index("ix_curriculum_units_hsk_level_id_order_index", "hsk_level_id", "order_index")])

PronunciationSection = model("PronunciationSection", "pronunciation_sections", [id_col(), ("code", String, {"nullable": False, "unique": True}), ("title", Text), ("description", Text), ("order_index", Integer, {"nullable": False})])
PronunciationProgress = model("PronunciationProgress", "pronunciation_progress", [id_col(), ("user_id", Uuid(as_uuid=True), {"nullable": False, "foreign_key": "users.id"}), ("pronunciation_section_id", Uuid(as_uuid=True), {"nullable": False, "foreign_key": "pronunciation_sections.id"}), ("completed_at", DateTime(timezone=True)), created(), updated()], UniqueConstraint("user_id", "pronunciation_section_id"))
Vocabulary = model("Vocabulary", "vocabulary", [id_col(), ("hanzi", Text, {"nullable": False}), ("pinyin", Text, {"nullable": False}), ("vietnamese_meaning", Text, {"nullable": False}), ("part_of_speech", Text), created(), updated()])
LessonVocabulary = model("LessonVocabulary", "lesson_vocabulary", [id_col(), ("lesson_id", Uuid(as_uuid=True), {"nullable": False, "foreign_key": "lessons.id"}), ("vocabulary_id", Uuid(as_uuid=True), {"nullable": False, "foreign_key": "vocabulary.id"}), ("order_index", Integer, {"nullable": False}), ("note", Text), ("example", Text)], UniqueConstraint("lesson_id", "vocabulary_id"), UniqueConstraint("lesson_id", "order_index"))
Grammar = model("Grammar", "grammar", [id_col(), ("name", Text, {"nullable": False}), ("structure", Text), ("explanation", Text, {"nullable": False}), ("usage", Text), created(), updated()])
LessonGrammar = model("LessonGrammar", "lesson_grammar", [id_col(), ("lesson_id", Uuid(as_uuid=True), {"nullable": False, "foreign_key": "lessons.id"}), ("grammar_id", Uuid(as_uuid=True), {"nullable": False, "foreign_key": "grammar.id"}), ("order_index", Integer, {"nullable": False}), ("note", Text), ("example", Text)], UniqueConstraint("lesson_id", "grammar_id"), UniqueConstraint("lesson_id", "order_index"))
