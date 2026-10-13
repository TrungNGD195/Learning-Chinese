from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from time import perf_counter
from typing import Mapping, Protocol
from urllib.parse import urlsplit
from uuid import UUID

from app.ai.citations.errors import (
    CITATION_EXTERNAL_URL_INVALID,
    CITATION_FORMAT_INVALID,
    CITATION_MISSING,
    CITATION_SOURCE_RESOLUTION_FAILED,
    CITATION_UNKNOWN_SOURCE,
    CITATION_VALIDATION_FAILED,
    citation_error,
)
from app.ai.citations.parser import parse_citations
from app.ai.citations.schemas import (
    CitationSource,
    CitationValidationResult,
    ExternalCitationSource,
    InternalCitationSource,
    ValidatedCitation,
)
from app.ai.prompting.schemas import ExternalSourceMapEntry, PromptPackage, SourceMapEntry

logger = logging.getLogger("app.ai.citations")
_LABEL = re.compile(r"S[1-9][0-9]*\Z")


class ExternalCitationTrustPolicy(Protocol):
    def is_trusted_hostname(self, hostname: str) -> bool: ...


@dataclass(frozen=True)
class TrustedExternalDomains:
    domains: frozenset[str] = frozenset()

    def is_trusted_hostname(self, hostname: str) -> bool:
        return hostname in self.domains


def sources_from_prompt_package(package: PromptPackage) -> Mapping[str, CitationSource]:
    """Copy only the typed display provenance needed by citation validation."""
    try:
        result: dict[str, CitationSource] = {}
        for key, entry in package.source_map.items():
            if isinstance(entry, ExternalSourceMapEntry):
                if (
                    key != entry.source_label or not _LABEL.fullmatch(key)
                    or not isinstance(entry.title, str) or not entry.title.strip()
                    or not isinstance(entry.url, str) or not entry.url.strip()
                    or not isinstance(entry.domain, str) or not entry.domain.strip()
                ):
                    raise ValueError
                result[key] = ExternalCitationSource(label=key, title=entry.title, url=entry.url)
                continue
            if (
                not isinstance(entry, SourceMapEntry)
                or key != entry.source_label
                or not _LABEL.fullmatch(key)
                or not isinstance(entry.chunk_id, UUID)
                or not isinstance(entry.title, str)
                or not entry.title.strip()
            ):
                raise ValueError
            if entry.source_type not in {"DOCUMENT", "LESSON"}:
                raise ValueError
            if entry.page_number is not None and (type(entry.page_number) is not int or entry.page_number < 1):
                raise ValueError
            if entry.section is not None and (not isinstance(entry.section, str) or not entry.section.strip()):
                raise ValueError
            result[key] = InternalCitationSource(
                label=key,
                chunk_id=entry.chunk_id,
                source_type=entry.source_type,
                title=entry.title,
                page_number=entry.page_number,
                section=entry.section,
            )
        return result
    except Exception:
        raise citation_error(CITATION_SOURCE_RESOLUTION_FAILED) from None


class CitationValidator:
    def __init__(self, trust_policy: ExternalCitationTrustPolicy | None = None) -> None:
        self.trust_policy = trust_policy or TrustedExternalDomains()

    def validate(
        self,
        *,
        text: str,
        sources: Mapping[str, CitationSource],
        citation_required: bool,
    ) -> CitationValidationResult:
        started = perf_counter()
        unknown = 0
        cited_kinds: list[str] = []
        try:
            parsed = parse_citations(text)
            if type(citation_required) is not bool or not isinstance(sources, Mapping):
                raise citation_error(CITATION_SOURCE_RESOLUTION_FAILED)
            labels = tuple(dict.fromkeys(item.label for item in parsed.occurrences))
            if any(label not in sources for label in labels):
                unknown = sum(label not in sources for label in labels)
                raise citation_error(CITATION_UNKNOWN_SOURCE)
            resolved_sources: list[tuple[str, CitationSource]] = []
            for label in labels:
                source = sources[label]
                if (
                    not isinstance(source, (InternalCitationSource, ExternalCitationSource))
                    or not isinstance(source.label, str)
                    or source.label != label
                    or not _LABEL.fullmatch(source.label)
                ):
                    raise citation_error(CITATION_SOURCE_RESOLUTION_FAILED)
                if isinstance(source, InternalCitationSource) and (
                    not isinstance(source.chunk_id, UUID)
                    or source.source_type not in {"DOCUMENT", "LESSON"}
                    or not isinstance(source.title, str)
                    or not source.title.strip()
                    or (source.page_number is not None and (type(source.page_number) is not int or source.page_number < 1))
                    or (source.section is not None and (not isinstance(source.section, str) or not source.section.strip()))
                ):
                    raise citation_error(CITATION_SOURCE_RESOLUTION_FAILED)
                if isinstance(source, ExternalCitationSource) and (
                    not isinstance(source.title, str)
                    or not source.title.strip()
                    or not isinstance(source.url, str)
                    or not source.url
                ):
                    raise citation_error(CITATION_SOURCE_RESOLUTION_FAILED)
                resolved_sources.append((label, source))
            snapshots: list[ValidatedCitation] = []
            for label, source in resolved_sources:
                if isinstance(source, InternalCitationSource):
                    if (
                        not isinstance(source.chunk_id, UUID)
                        or source.source_type not in {"DOCUMENT", "LESSON"}
                        or not isinstance(source.title, str)
                        or not source.title.strip()
                        or (source.page_number is not None and (type(source.page_number) is not int or source.page_number < 1))
                        or (source.section is not None and (not isinstance(source.section, str) or not source.section.strip()))
                    ):
                        raise citation_error(CITATION_SOURCE_RESOLUTION_FAILED)
                    locator = {}
                    if source.page_number is not None:
                        locator["page_number"] = source.page_number
                    if source.section is not None:
                        locator["section"] = source.section
                    snapshots.append(ValidatedCitation(
                        label=label,
                        source_kind="INTERNAL_CHUNK",
                        chunk_id=source.chunk_id,
                        title=source.title,
                        source_type=source.source_type,
                        locator=locator or None,
                    ))
                    cited_kinds.append("INTERNAL_CHUNK")
                else:
                    try:
                        parsed_url = urlsplit(source.url)
                        hostname = parsed_url.hostname
                        normalized_hostname = hostname.lower().removesuffix(".") if hostname else None
                        safe = (
                            isinstance(source.title, str)
                            and bool(source.title.strip())
                            and parsed_url.scheme.lower() == "https"
                            and bool(normalized_hostname)
                            and parsed_url.username is None
                            and parsed_url.password is None
                            and self.trust_policy.is_trusted_hostname(normalized_hostname)
                        )
                    except Exception:
                        safe = False
                        normalized_hostname = None
                    if not safe or normalized_hostname is None:
                        raise citation_error(CITATION_EXTERNAL_URL_INVALID)
                    snapshots.append(ValidatedCitation(
                        label=label,
                        source_kind="EXTERNAL_URL",
                        title=source.title,
                        url=source.url,
                        domain=normalized_hostname,
                    ))
                    cited_kinds.append("EXTERNAL_URL")
            if citation_required and not parsed.occurrences:
                raise citation_error(CITATION_MISSING)
            result = CitationValidationResult(
                text=text,
                cited_labels=labels,
                citations=tuple(snapshots),
                citation_count=len(snapshots),
                occurrence_count=parsed.occurrence_count,
            )
            logger.info("citation_validation_completed", extra={
                "available_source_count": len(sources),
                "cited_unique_source_count": result.citation_count,
                "citation_occurrence_count": result.occurrence_count,
                "citation_validation_status": "VALID",
                "unknown_label_count": 0,
                "citation_source_kinds": tuple(cited_kinds),
                "validation_duration_ms": round((perf_counter() - started) * 1000, 2),
                "error_code": None,
            })
            return result
        except Exception as exc:
            code = getattr(exc, "code", CITATION_VALIDATION_FAILED)
            allowed = {
                CITATION_MISSING,
                CITATION_FORMAT_INVALID,
                CITATION_UNKNOWN_SOURCE,
                CITATION_SOURCE_RESOLUTION_FAILED,
                CITATION_EXTERNAL_URL_INVALID,
            }
            if code not in allowed:
                code = CITATION_VALIDATION_FAILED
            logger.warning("citation_validation_failed", extra={
                "available_source_count": len(sources) if isinstance(sources, Mapping) else 0,
                "cited_unique_source_count": 0,
                "citation_occurrence_count": 0,
                "citation_validation_status": "FAILED",
                "unknown_label_count": unknown,
                "citation_source_kinds": tuple(cited_kinds),
                "validation_duration_ms": round((perf_counter() - started) * 1000, 2),
                "error_code": code,
            })
            raise citation_error(code) from None
