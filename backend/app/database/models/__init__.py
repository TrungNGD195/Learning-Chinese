"""Import all database mappings so Base.metadata is complete."""

from app.database.base import Base

from app.database.models.user import User
from app.database.models.auth import RefreshToken, PasswordResetToken
from app.database.models.curriculum import (
    HSKLevel,
    Lesson,
    CurriculumUnit,
    PronunciationSection,
    PronunciationProgress,
    PronunciationLessonProgress,
    Vocabulary,
    LessonVocabulary,
    Grammar,
    LessonGrammar,
    LessonReading,
)
from app.database.models.assessment import (
    Assessment,
    AssessmentLesson,
    AssessmentVocabulary,
    AssessmentGrammar,
    Question,
    QuestionOption,
    AssessmentAttempt,
    AttemptAnswer,
)
from app.database.models.progress import (
    LearnerLessonProgress,
    LearnerHSKProgress,
    LearnerVocabularyProgress,
    LearnerGrammarProgress,
    LearnerReadingProgress,
)
from app.database.models.conversation import Conversation, Message, MessageCitation
from app.database.models.document import Document
from app.database.models.ingestion import ParsingRun
from app.database.models.transformation import TransformationRun
from app.database.models.knowledge import (
    KnowledgeSource,
    KnowledgeVersion,
    Chunk,
    EmbeddingProfile,
    Embedding,
    MessageRetrieval,
)

__all__ = [name for name in globals() if not name.startswith("_")]
