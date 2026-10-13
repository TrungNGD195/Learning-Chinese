from __future__ import annotations

from copy import deepcopy
from math import isfinite
from types import MappingProxyType
from typing import Any
from uuid import UUID

from app.ai.prompting.errors import PROMPT_CONTEXT_BUILD_FAILED, prompt_context_error
from app.ai.prompting.schemas import ContextBlock, ExternalContextBlock, ExternalSourceMapEntry, LearningContext, SourceMapEntry
from app.ai.reranking.schemas import RerankedCandidate
from app.ai.prompting.evidence import ExternalContextEvidence


def _invalid_candidate() -> Exception:
    return prompt_context_error(
        PROMPT_CONTEXT_BUILD_FAILED,
        "Prompt evidence is invalid.",
    )


def render_learning_context(context: LearningContext | None) -> str | None:
    if context is None:
        return None
    if not isinstance(context, LearningContext):
        raise prompt_context_error(
            PROMPT_CONTEXT_BUILD_FAILED,
            "Learning context is invalid.",
        )

    lines = ["Current learning context:"]
    if context.hsk_level is not None:
        lines.append(f"HSK {context.hsk_level}")
    if context.lesson_title and context.lesson_title.strip():
        lines.append(f"Lesson: {context.lesson_title}")
    if context.current_module and context.current_module.strip():
        lines.append(f"Module: {context.current_module}")
    return "\n".join(lines) if len(lines) > 1 else None


class ContextBlockFormatter:
    @staticmethod
    def format(candidate: RerankedCandidate, source_label: str) -> ContextBlock:
        if not isinstance(candidate, RerankedCandidate):
            raise _invalid_candidate()
        if not isinstance(source_label, str) or not source_label:
            raise _invalid_candidate()
        if (
            not isinstance(candidate.chunk_id, UUID)
            or not isinstance(candidate.knowledge_source_id, UUID)
            or not isinstance(candidate.content, str)
            or not candidate.content.strip()
            or not isinstance(candidate.content_type, str)
            or not isinstance(candidate.locator_metadata, (dict, type(None)))
            or not isinstance(candidate.retrieval_score, (int, float))
            or isinstance(candidate.retrieval_score, bool)
            or not isfinite(candidate.retrieval_score)
            or not isinstance(candidate.rerank_score, (int, float))
            or isinstance(candidate.rerank_score, bool)
            or not isfinite(candidate.rerank_score)
        ):
            raise _invalid_candidate()

        if candidate.source_type == "DOCUMENT":
            if (
                not isinstance(candidate.source_document_id, UUID)
                or candidate.source_lesson_id is not None
                or not isinstance(candidate.document_title, str)
                or not candidate.document_title.strip()
                or candidate.source_type != "DOCUMENT"
            ):
                raise _invalid_candidate()
            title = candidate.document_title
            lines = [f"Source: {source_label}", f"Title: {title}"]
            if candidate.section:
                if not isinstance(candidate.section, str):
                    raise _invalid_candidate()
                lines.append(f"Section: {candidate.section}")
            text = "\n".join(lines) + f"\n\n{candidate.content}"
        elif candidate.source_type == "LESSON":
            if (
                not isinstance(candidate.source_lesson_id, UUID)
                or candidate.source_document_id is not None
                or not isinstance(candidate.lesson_title, str)
                or not candidate.lesson_title.strip()
                or type(candidate.hsk_level_number) is not int
                or candidate.content_type not in {"VOCABULARY", "GRAMMAR", "LESSON_GENERAL"}
            ):
                raise _invalid_candidate()
            title = candidate.lesson_title
            text = "\n".join(
                (
                    f"Source: {source_label}",
                    f"HSK: {candidate.hsk_level_number}",
                    f"Lesson: {title}",
                    f"Type: {candidate.content_type}",
                    "",
                    candidate.content,
                )
            )
        else:
            raise _invalid_candidate()

        locator: dict[str, Any] | None = (
            deepcopy(candidate.locator_metadata)
            if candidate.locator_metadata is not None
            else None
        )
        if locator is not None:
            locator = MappingProxyType(locator)
        return ContextBlock(
            source_label=source_label,
            text=text,
            chunk_id=candidate.chunk_id,
            knowledge_source_id=candidate.knowledge_source_id,
            source_type=candidate.source_type,
            source_document_id=candidate.source_document_id,
            source_lesson_id=candidate.source_lesson_id,
            title=title,
            section=candidate.section,
            hsk_level=candidate.hsk_level_number,
            lesson_title=candidate.lesson_title,
            content_type=candidate.content_type,
            page_number=candidate.page_number,
            locator_metadata=locator,
            retrieval_score=float(candidate.retrieval_score),
            rerank_score=float(candidate.rerank_score),
        )

    @staticmethod
    def source_map_entry(block: ContextBlock) -> SourceMapEntry:
        return SourceMapEntry(
            source_label=block.source_label,
            chunk_id=block.chunk_id,
            knowledge_source_id=block.knowledge_source_id,
            source_type=block.source_type,
            source_document_id=block.source_document_id,
            source_lesson_id=block.source_lesson_id,
            title=block.title,
            page_number=block.page_number,
            section=block.section,
            locator_metadata=block.locator_metadata,
        )

    @staticmethod
    def format_external(evidence: ExternalContextEvidence, source_label: str) -> ExternalContextBlock:
        if (
            not isinstance(evidence, ExternalContextEvidence)
            or type(evidence.final_order) is not int
            or evidence.final_order < 1
            or not all(isinstance(value, str) and value.strip() for value in (evidence.title, evidence.url, evidence.domain, evidence.content))
            or not isfinite(evidence.rerank_score)
            or not isinstance(source_label, str)
        ):
            raise _invalid_candidate()
        text = f"Source: {source_label}\nTitle: {evidence.title}\nDomain: {evidence.domain}\n\n{evidence.content}"
        return ExternalContextBlock(source_label, text, evidence.title, evidence.url, evidence.domain, evidence.rerank_score)

    @staticmethod
    def external_source_map_entry(block: ExternalContextBlock) -> ExternalSourceMapEntry:
        return ExternalSourceMapEntry(block.source_label, block.title, block.url, block.domain)
