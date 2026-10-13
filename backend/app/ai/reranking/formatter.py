from app.ai.reranking.errors import reranking_error
from app.ai.retrieval.schemas import RetrievalCandidate


class RerankPassageFormatter:
    """Build the frozen, deterministic reranker input passage v1."""

    VERSION = "v1"

    @staticmethod
    def format(candidate: RetrievalCandidate) -> str:
        if not isinstance(candidate, RetrievalCandidate):
            raise reranking_error("INVALID_RERANK_INPUT", "Reranker candidate is invalid.", 422)
        content = candidate.content
        if not isinstance(content, str) or not content.strip():
            raise reranking_error("INVALID_RERANK_INPUT", "Reranker candidate content is invalid.", 422)

        if candidate.source_type == "DOCUMENT":
            title = candidate.document_title
            if not isinstance(title, str) or not title.strip():
                raise reranking_error("INVALID_RERANK_INPUT", "Reranker document provenance is incomplete.", 422)
            lines = [f"Title: {title}"]
            if candidate.section is not None:
                if not isinstance(candidate.section, str) or not candidate.section.strip():
                    raise reranking_error("INVALID_RERANK_INPUT", "Reranker document section is invalid.", 422)
                lines.append(f"Section: {candidate.section}")
            return "\n".join(lines) + "\n\n" + content

        if candidate.source_type == "LESSON":
            title = candidate.lesson_title
            hsk_level = candidate.hsk_level_number
            if (
                not isinstance(title, str)
                or not title.strip()
                or not isinstance(hsk_level, int)
                or isinstance(hsk_level, bool)
                or not isinstance(candidate.content_type, str)
                or not candidate.content_type.strip()
            ):
                raise reranking_error("INVALID_RERANK_INPUT", "Reranker lesson provenance is incomplete.", 422)
            return (
                f"HSK: {hsk_level}\n"
                f"Lesson: {title}\n"
                f"Type: {candidate.content_type}\n\n"
                f"{content}"
            )

        raise reranking_error("INVALID_RERANK_INPUT", "Reranker candidate source is invalid.", 422)
