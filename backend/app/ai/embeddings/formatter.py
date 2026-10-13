from app.core.errors import ApplicationError
from app.ai.embeddings.schemas import EmbeddingChunkContext


class EmbeddingInputFormatter:
    version = "v1"

    def format(self, item: EmbeddingChunkContext) -> str:
        content_type = item.content_type
        if content_type == "DOCUMENT_TEXT":
            if item.source_type != "DOCUMENT" or item.source_document_id is None:
                raise ApplicationError("EMBEDDING_BUILD_FAILED", "Chunk source context is inconsistent.", status_code=500)
            title = (item.document_title or "").strip()
            if not title:
                raise ApplicationError("EMBEDDING_BUILD_FAILED", "Required Document context is unavailable.", status_code=500)
            lines = [f"Title: {title}"]
            if item.section is not None and item.section.strip():
                lines.append(f"Section: {item.section.strip()}")
            return "\n".join(lines) + f"\n\n{item.content}"
        if content_type in {"VOCABULARY", "GRAMMAR", "LESSON_GENERAL"}:
            if (item.source_type != "LESSON" or item.source_lesson_id is None
                    or item.chunk_lesson_id != item.source_lesson_id):
                raise ApplicationError("EMBEDDING_BUILD_FAILED", "Chunk source context is inconsistent.", status_code=500)
            title = (item.lesson_title or "").strip()
            if not title or item.hsk_level_number is None or item.lesson_id is None:
                raise ApplicationError("EMBEDDING_BUILD_FAILED", "Required Lesson context is unavailable.", status_code=500)
            return (
                f"HSK: {item.hsk_level_number}\nLesson: {title}\nType: {content_type}"
                f"\n\n{item.content}"
            )
        raise ApplicationError("EMBEDDING_BUILD_FAILED", "Chunk content type is unsupported for embedding.", status_code=500)
