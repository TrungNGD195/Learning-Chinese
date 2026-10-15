from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, is_dataclass
from time import perf_counter
from typing import Any

from sqlalchemy import select

from app.ai.memory.sanitizer import sanitize_historical_assistant_text


_CITATION_MARKER = re.compile(r"\[S[1-9][0-9]*\]")
_TIER_ORDER = {"CURRENT_LESSON": 0, "INTERNAL_KB": 1, "TRUSTED_EXTERNAL": 2}
_DETERMINISTIC_CITATION_ERRORS = {
    "CITATION_MISSING", "CITATION_FORMAT_INVALID", "CITATION_UNKNOWN_SOURCE",
    "CITATION_SOURCE_RESOLUTION_FAILED", "CITATION_EXTERNAL_URL_INVALID",
}


def historical_marker_sanitization_was_observed(original_texts: dict, sanitized_turns) -> bool:
    """Compare persisted historical text with the exact sanitized memory output."""
    return all(
        not _CITATION_MARKER.search(turn.assistant_text)
        and (not _CITATION_MARKER.search(original_texts.get(turn.assistant_message_id, ""))
             or sanitize_historical_assistant_text(
                 original_texts[turn.assistant_message_id]) == turn.assistant_text)
        for turn in sanitized_turns
    )


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    return str(value)


def _source_map_snapshot(package) -> dict[str, dict]:
    snapshot = {}
    for label, entry in package.source_map.items():
        url = getattr(entry, "url", None)
        chunk_id = getattr(entry, "chunk_id", None)
        source_kind = "EXTERNAL_URL" if url else "INTERNAL_CHUNK"
        source_id = url or (str(chunk_id) if chunk_id is not None else None)
        snapshot[label] = {
            "source_kind": source_kind, "source_id": source_id,
            "chunk_id": str(chunk_id) if chunk_id is not None else None,
            "url": url, "title": getattr(entry, "title", None),
            "domain": getattr(entry, "domain", None),
            "source_type": getattr(entry, "source_type", None),
            "source_document_id": (str(entry.source_document_id)
                                    if getattr(entry, "source_document_id", None) else None),
            "source_lesson_id": (str(entry.source_lesson_id)
                                 if getattr(entry, "source_lesson_id", None) else None),
            "page_number": getattr(entry, "page_number", None),
            "section": getattr(entry, "section", None),
            "locator_metadata": _jsonable(getattr(entry, "locator_metadata", None)),
        }
    return snapshot


def _context_snapshot(package) -> list[dict]:
    result = []
    for block in package.context_blocks:
        text = getattr(block, "text", "")
        result.append({
            "label": block.source_label,
            "source_kind": "EXTERNAL_URL" if getattr(block, "url", None) else "INTERNAL_CHUNK",
            "chunk_id": str(block.chunk_id) if getattr(block, "chunk_id", None) else None,
            "url": getattr(block, "url", None),
            "content_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        })
    return result


class CitationValidatorObserver:
    """Record the exact production validator outcome without changing its policy."""

    def __init__(self, delegate, observer):
        self.delegate = delegate
        self.observer = observer

    def __getattr__(self, name):
        return getattr(self.delegate, name)

    def validate(self, *args, **kwargs):
        started = perf_counter()
        self.observer.citation_validation_attempted = True
        try:
            return self.delegate.validate(*args, **kwargs)
        except Exception as exc:
            self.observer.citation_validation_error_code = getattr(
                exc, "code", "CITATION_VALIDATION_FAILED")
            raise
        finally:
            self.observer.citation_validation_latency_ms += max(
                0, round((perf_counter() - started) * 1000))


def citation_validation_snapshot(observer, citations, *, valid: bool) -> dict:
    """Serialize the validator outcome with its production error identity intact."""
    rows = list(citations)
    return {
        "attempted": observer.citation_validation_attempted,
        "valid": valid,
        "error_code": observer.citation_validation_error_code,
        "validated_citations": rows,
        "cited_labels": [row.get("label") for row in rows if row.get("label")],
    }


class ProductionTraceObserver:
    """Evaluation-local wrappers observing the existing production RAG seams."""

    def __init__(self, orchestrator, *, evidence_metadata_by_chunk_id=None):
        self.orchestrator = orchestrator
        self.metadata = evidence_metadata_by_chunk_id or {}
        self.tiers: list[dict] = []
        self.external_candidates: tuple = ()
        self.external_result = None
        self.prompt_package = None
        self.memory = None
        self.memory_builder_invocation_count = 0
        self.memory_composition_applied = False
        self.generated_memory_selected_turn_count = 0
        self.memory_dropped_after_preflight = False
        self.memory_applied_to_generation = False
        self.eligible_memory_turn_rows = ()
        self.generated_latency_ms = None
        self.generation_error_code = None
        self.provider = getattr(getattr(orchestrator.generation_service, "provider", None), "provider_name", None)
        self.model = getattr(getattr(orchestrator.generation_service, "provider", None), "model_name", None)
        self.memory_markers_removed = None
        self.memory_historical_citation_labels: list[str] = []
        self.sanitized_memory_snapshot: dict | None = None
        self.token_usage: dict[str, int | None] | None = None
        self.prompt_package_sha256 = None
        self.context_build_duration_ms = None
        self.citation_validation_latency_ms = 0
        self.citation_validation_attempted = False
        self.citation_validation_error_code = None
        self.generation_called = False
        self.generated_answer = None
        self.citation_finalization_latency_ms = 0
        self.persistence_readback_latency_ms = 0
        self.started_at = perf_counter()
        self._active_tier: str | None = None
        self._originals: list[tuple[object, str, Any]] = []
        self._install()

    def _replace(self, target, name: str, value) -> None:
        self._originals.append((target, name, getattr(target, name)))
        setattr(target, name, value)

    def _install(self) -> None:
        orchestrator = self.orchestrator
        original_score = orchestrator._score_tier
        original_factory = orchestrator.retrieval_factory
        original_reranker = orchestrator.reranker

        observer = self

        class RetrievalProxy:
            def __init__(self, delegate): self.delegate = delegate
            async def retrieve(self, query, *, retrieval_filter):
                row = observer._tier_row(observer._active_tier)
                started = perf_counter()
                try:
                    candidates = await self.delegate.retrieve(query, retrieval_filter=retrieval_filter)
                    row["retrieval_status"] = "SUCCESS"
                    row["semantic_candidates"] = [observer._internal_candidate(item) for item in candidates]
                    row["candidate_count"] = len(candidates)
                    return candidates
                except Exception as exc:
                    row["retrieval_status"] = "TECHNICAL_FAILURE"
                    row["rerank_status"] = "NOT_APPLICABLE"
                    row["error_code"] = getattr(exc, "code", "RETRIEVAL_FAILED")
                    raise
                finally:
                    row["retrieval_latency_ms"] = max(0, round((perf_counter() - started) * 1000))

        class RerankerProxy:
            def __init__(self, delegate): self.delegate = delegate
            async def rerank(self, query, candidates):
                row = observer._tier_row(observer._active_tier)
                started = perf_counter()
                try:
                    result = await self.delegate.rerank(query, candidates)
                    row["rerank_status"] = "SUCCESS"
                    row["reranked_evidence"] = [observer._internal_candidate(item) for item in result.scored_candidates]
                    scores = [float(item.rerank_score) for item in result.scored_candidates]
                    row["max_rerank_score"] = max(scores) if scores else None
                    row["evidence_gate_threshold"] = observer.orchestrator.settings.rag_min_rerank_score
                    threshold = observer.orchestrator.settings.rag_min_rerank_score
                    row["evidence_gate_passed"] = bool(threshold is not None and any(score >= threshold for score in scores))
                    return result
                except Exception as exc:
                    row["rerank_status"] = "TECHNICAL_FAILURE"
                    row["error_code"] = getattr(exc, "code", "RERANK_FAILED")
                    raise
                finally:
                    row["rerank_latency_ms"] = max(0, round((perf_counter() - started) * 1000))

        def retrieval_factory(session):
            return RetrievalProxy(original_factory(session))

        self._replace(orchestrator, "retrieval_factory", retrieval_factory)
        self._replace(orchestrator, "reranker", RerankerProxy(original_reranker))

        async def score_tier(query, lesson_id, tier):
            name = tier.value
            self._active_tier = name
            row = self._tier_row(name)
            row["scope_identity"] = (f"CURRENT_LESSON:lesson={lesson_id}" if name == "CURRENT_LESSON"
                                      else "INTERNAL_KB:published-lessons+approved-documents")
            row["lesson_id"] = str(lesson_id)
            row["retrieval_status"] = "SUCCESS"
            row["rerank_status"] = "NOT_APPLICABLE"
            try:
                value = await original_score(query, lesson_id, tier)
                return value
            except Exception as exc:
                if row.get("retrieval_status") == "SUCCESS" and row.get("reranked_evidence") is None:
                    row["rerank_status"] = "TECHNICAL_FAILURE"
                row["error_code"] = row.get("error_code") or getattr(exc, "code", "TIER_SCORING_FAILED")
                raise
            finally:
                self._active_tier = None

        self._replace(orchestrator, "_score_tier", score_tier)

        original_search = orchestrator.external_retrieval_service.search
        original_external_rerank = orchestrator.external_reranking_service.rerank

        async def search(query, *args, **kwargs):
            started = perf_counter()
            row = self._tier_row("TRUSTED_EXTERNAL")
            row.setdefault("scope_identity", "TRUSTED_EXTERNAL:approved-domain-policy")
            try:
                candidates = await original_search(query, *args, **kwargs)
                self.external_candidates = tuple(candidates)
                row["retrieval_status"] = "SUCCESS"
                row["candidate_count"] = len(candidates)
                row["semantic_candidates"] = [self._external_candidate(item) for item in candidates]
                return candidates
            except Exception as exc:
                row["retrieval_status"] = "TECHNICAL_FAILURE"
                row["rerank_status"] = "NOT_APPLICABLE"
                row["error_code"] = getattr(exc, "code", "EXTERNAL_RETRIEVAL_FAILED")
                raise
            finally:
                row["retrieval_latency_ms"] = max(0, round((perf_counter() - started) * 1000))

        async def external_rerank(query, candidates):
            started = perf_counter()
            row = self._tier_row("TRUSTED_EXTERNAL")
            try:
                result = await original_external_rerank(query, candidates)
                self.external_result = result
                row["rerank_status"] = "SUCCESS"
                row["reranked_evidence"] = [self._external_candidate(item, reranked=True)
                                             for item in result.scored_candidates]
                scores = [float(item.rerank_score) for item in result.scored_candidates]
                row["max_rerank_score"] = max(scores) if scores else None
                threshold = self.orchestrator.settings.rag_min_rerank_score
                row["evidence_gate_threshold"] = threshold
                row["evidence_gate_passed"] = bool(threshold is not None and any(score >= threshold for score in scores))
                return result
            except Exception as exc:
                row["rerank_status"] = "TECHNICAL_FAILURE"
                row["error_code"] = getattr(exc, "code", "RERANK_FAILED")
                raise
            finally:
                row["rerank_latency_ms"] = max(0, round((perf_counter() - started) * 1000))

        self._replace(orchestrator.external_retrieval_service, "search", search)
        self._replace(orchestrator.external_reranking_service, "rerank", external_rerank)

        original_prompt_builder = orchestrator.prompt_builder

        class PromptBuilderProxy:
            def __getattr__(self, name): return getattr(original_prompt_builder, name)
            def build(self, *args, **kwargs):
                started = perf_counter()
                result = original_prompt_builder.build(*args, **kwargs)
                observer.record_package(result.package)
                observer.context_build_duration_ms = max(0, round((perf_counter() - started) * 1000))
                return result
            def build_from_evidence(self, *args, **kwargs):
                started = perf_counter()
                result = original_prompt_builder.build_from_evidence(*args, **kwargs)
                observer.record_package(result.package)
                observer.context_build_duration_ms = max(0, round((perf_counter() - started) * 1000))
                return result

        self._replace(orchestrator, "prompt_builder", PromptBuilderProxy())
        original_generation = orchestrator.generation_service

        class GenerationProxy:
            async def generate_with_attempt_preparer(self, package, config, prepare_attempt):
                observer.record_package(package)
                async def observed_prepare(attempt):
                    prepared = await prepare_attempt(attempt)
                    if prepared is not package:
                        await observer.record_memory(getattr(prepared, "conversation_memory", None))
                        observer.record_package(prepared)
                    return prepared
                started = perf_counter()
                try:
                    result = await original_generation.generate_with_attempt_preparer(
                        package, config, observed_prepare)
                    observer.generation_called = True
                    observer.generated_answer = getattr(result, "text", None)
                    observer.generated_memory_selected_turn_count = getattr(
                        result, "memory_selected_turn_count", 0)
                    observer.memory_dropped_after_preflight = bool(getattr(
                        result, "memory_dropped_after_exact_preflight", False))
                    observer.memory_applied_to_generation = (
                        observer.generated_memory_selected_turn_count > 0
                        and not observer.memory_dropped_after_preflight
                    )
                    observer.token_usage = {
                        "input_tokens": getattr(result, "input_tokens", None),
                        "output_tokens": getattr(result, "output_tokens", None),
                        "total_tokens": getattr(result, "total_tokens", None),
                    }
                    return result
                except Exception as exc:
                    observer.generation_error_code = getattr(exc, "code", "GENERATION_FAILED")
                    raise
                finally:
                    observer.generated_latency_ms = max(0, round((perf_counter() - started) * 1000))

        self._replace(orchestrator, "generation_service", GenerationProxy())

        original_memory_factory = getattr(orchestrator, "memory_builder_factory", None)
        if original_memory_factory is not None:
            def observed_memory_factory(session):
                builder = original_memory_factory(session)
                original_build = builder.build
                async def observed_build(*args, **kwargs):
                    observer.memory_builder_invocation_count += 1
                    return await original_build(*args, **kwargs)
                builder.build = observed_build
                original_repository = builder.repository
                class MemoryRepositoryProxy:
                    def __getattr__(self, name): return getattr(original_repository, name)
                    async def list_recent_completed_turn_pairs_for_memory(self, *args, **kwargs):
                        rows = await original_repository.list_recent_completed_turn_pairs_for_memory(*args, **kwargs)
                        observer.eligible_memory_turn_rows = tuple(rows)
                        return rows
                builder.repository = MemoryRepositoryProxy()
                return builder
            self._replace(orchestrator, "memory_builder_factory", observed_memory_factory)

        original_validator = getattr(orchestrator, "citation_validator", None)
        if original_validator is not None:
            self._replace(orchestrator, "citation_validator",
                          CitationValidatorObserver(original_validator, self))

    def _tier_row(self, tier: str | None) -> dict:
        if tier is None:
            tier = "CURRENT_LESSON"
        for row in self.tiers:
            if row["tier"] == tier:
                return row
        row = {"tier": tier, "attempt_index": len(self.tiers) + 1,
               "scope_identity": tier, "retrieval_status": "SUCCESS",
               "semantic_candidates": [], "candidate_count": 0,
               "rerank_status": "NOT_APPLICABLE", "reranked_evidence": [],
               "max_rerank_score": None, "evidence_gate_threshold": None,
               "evidence_gate_passed": False, "scope_violation": False,
               "retrieval_latency_ms": None, "rerank_latency_ms": None,
               "usable_higher_priority_evidence": False}
        self.tiers.append(row)
        return row

    def _internal_candidate(self, item) -> dict:
        chunk_id = str(item.chunk_id)
        metadata = self.metadata.get(chunk_id, {})
        value = {"chunk_id": chunk_id, "rank": getattr(item, "rank", None),
                 "retrieval_score": float(item.retrieval_score),
                 "distance": float(item.distance),
                 "source_kind": "INTERNAL_CHUNK",
                 "fixture_source_kind": metadata.get("source_kind"),
                 "source_id": metadata.get("source_id", chunk_id),
                 "stable_locators": list(metadata.get("stable_locators", [])),
                 "lesson_locator": metadata.get("lesson_locator"),
                 "source_type": getattr(item, "source_type", None),
                 "source_lesson_id": str(item.source_lesson_id) if item.source_lesson_id else None,
                 "chunk_lesson_id": str(item.chunk_lesson_id) if item.chunk_lesson_id else None,
                 "source_document_id": str(item.source_document_id) if item.source_document_id else None}
        if hasattr(item, "rerank_score"):
            value.update(rerank_rank=getattr(item, "rerank_rank", None), rerank_score=float(item.rerank_score))
        return value

    def _external_candidate(self, item, *, reranked=False) -> dict:
        import hashlib
        provider = getattr(self.orchestrator.external_retrieval_service, "provider", None)
        provenance = (provider.provenance_for_url(item.url)
                     if hasattr(provider, "provenance_for_url") else None)
        value = {"source_kind": "EXTERNAL_URL", "source_id": item.url,
                 "title": item.title, "url": item.url, "domain": item.domain,
                 "content_sha256": hashlib.sha256(item.content.encode("utf-8")).hexdigest(),
                 "rank": getattr(item, "provider_rank", None)}
        if provenance:
            value.update(source_id=provenance.get("source_id"),
                         reviewed_claims_sha256=provenance.get("reviewed_claims_sha256"))
        if reranked:
            value.update(rerank_rank=item.rerank_rank, rerank_score=float(item.rerank_score))
        return value

    def record_package(self, package) -> None:
        self.prompt_package = package
        self.prompt_package_sha256 = self.sha256({
            "system_instructions_sha256": self.sha256(package.system_instructions),
            "learning_context_sha256": self.sha256(package.learning_context or ""),
            "user_query": package.user_query,
            "source_map": self.source_map_snapshot,
            "context_blocks": self.context_blocks_snapshot,
            "selected_chunk_ids": [str(value) for value in package.selected_chunk_ids],
            "omitted_chunk_ids": [str(value) for value in package.omitted_chunk_ids],
            "memory_sha256": self.sha256([
                {"user_text_sha256": self.sha256(turn.user_text),
                 "assistant_text_sha256": self.sha256(turn.assistant_text)}
                for turn in (package.conversation_memory.turns if package.conversation_memory else ())
            ]),
        })

    @staticmethod
    def sha256(value) -> str:
        data = value.encode("utf-8") if isinstance(value, str) else json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(data).hexdigest()

    @property
    def source_map_snapshot(self):
        return _source_map_snapshot(self.prompt_package) if self.prompt_package else {}

    @property
    def context_blocks_snapshot(self):
        return _context_snapshot(self.prompt_package) if self.prompt_package else []

    async def record_memory(self, memory) -> None:
        if memory is None:
            return
        from app.database.models import Message
        self.memory = memory
        self.memory_composition_applied = True
        ids = [turn.assistant_message_id for turn in memory.turns]
        originals = {}
        if ids:
            async with self.orchestrator.session_factory() as session:
                rows = await session.scalars(select(Message).where(Message.id.in_(ids)))
                originals = {row.id: row.content or "" for row in rows}
        self.memory_markers_removed = historical_marker_sanitization_was_observed(originals, memory.turns)
        self.memory_historical_citation_labels = sorted({
            label for turn in memory.turns for label in
            _CITATION_MARKER.findall(originals.get(turn.assistant_message_id, ""))
        })
        self.sanitized_memory_snapshot = {
            "status": memory.status,
            "selected_turn_count": memory.selected_turn_count,
            "omitted_turn_count": memory.omitted_turn_count,
            "token_count": memory.token_count,
            "turns": [{
                "user_message_id": str(turn.user_message_id),
                "assistant_message_id": str(turn.assistant_message_id),
                "user_sequence_number": turn.user_sequence_number,
                "assistant_sequence_number": turn.assistant_sequence_number,
                "user_text": turn.user_text,
                "assistant_text": turn.assistant_text,
                "assistant_text_sha256": self.sha256(turn.assistant_text),
                "historical_citation_labels_removed": _CITATION_MARKER.findall(
                    originals.get(turn.assistant_message_id, "")),
                "assistant_citation_markers_removed": bool(
                    _CITATION_MARKER.search(originals.get(turn.assistant_message_id, ""))
                    and not _CITATION_MARKER.search(turn.assistant_text)),
            } for turn in memory.turns],
            "messages": [message for turn in memory.turns for message in (
                {"role": "user", "message_id": str(turn.user_message_id),
                 "sequence_number": turn.user_sequence_number, "content": turn.user_text},
                {"role": "assistant", "message_id": str(turn.assistant_message_id),
                 "sequence_number": turn.assistant_sequence_number, "content": turn.assistant_text},
            )],
            "eligible_turns_considered": [{
                "user_message_id": str(row.user_message_id),
                "assistant_message_id": str(row.assistant_message_id),
                "user_sequence_number": row.user_sequence_number,
                "assistant_sequence_number": row.assistant_sequence_number,
            } for row in self.eligible_memory_turn_rows],
            "omitted_turns_considered": [{
                "user_message_id": str(row.user_message_id),
                "assistant_message_id": str(row.assistant_message_id),
                "user_sequence_number": row.user_sequence_number,
                "assistant_sequence_number": row.assistant_sequence_number,
            } for row in self.eligible_memory_turn_rows
                if row.user_message_id not in {turn.user_message_id for turn in memory.turns}],
            "evidence_authority": False,
        }

    def actual_evidence(self, result) -> list[dict]:
        if not self.prompt_package:
            return []
        evidence = []
        for block in self.prompt_package.context_blocks:
            if getattr(block, "url", None):
                scored = next((item for item in (self.external_result.scored_candidates
                                                  if self.external_result else ())
                               if item.url == block.url), None)
                source = (self._external_candidate(scored, reranked=True) if scored else {
                    "source_kind": "EXTERNAL_URL", "source_id": block.url,
                    "url": block.url, "domain": block.domain, "title": block.title,
                    "rerank_score": float(block.rerank_score)})
                evidence.append({**source, "stable_locator": block.url,
                                 "label": block.source_label,
                                 "rerank_score": float(block.rerank_score)})
            else:
                candidate = block.candidate
                metadata = self.metadata.get(str(candidate.chunk_id), {})
                evidence.append({"source_kind": "INTERNAL_CHUNK", "chunk_id": str(candidate.chunk_id),
                                 "source_id": metadata.get("source_id", str(candidate.chunk_id)),
                                 "stable_locators": list(metadata.get("stable_locators", [])),
                                 "lesson_locator": metadata.get("lesson_locator"),
                                 "label": block.source_label,
                                 "rerank_rank": int(candidate.rerank_rank),
                                 "rerank_score": float(candidate.rerank_score)})
        return evidence

    def finalize_tier_policy(self, selected_tier: str) -> None:
        for row in self.tiers:
            row["usable_higher_priority_evidence"] = bool(
                row["evidence_gate_passed"] and selected_tier != "NONE"
                and _TIER_ORDER.get(row["tier"], 99) < _TIER_ORDER.get(selected_tier, 99))

    def tier_trace(self, attempted_tiers) -> list[dict]:
        by_tier = {row["tier"]: row for row in self.tiers}
        result = []
        for tier in attempted_tiers:
            name = tier.value if hasattr(tier, "value") else str(tier)
            if name not in by_tier:
                raise ValueError("E2E_OBSERVER_MISSING_ATTEMPTED_TIER")
            row = by_tier[name]
            if name == "CURRENT_LESSON":
                row["scope_violation"] = any(
                    (candidate.get("source_lesson_id") is not None
                     and candidate.get("source_lesson_id") != row.get("lesson_id"))
                    or (candidate.get("chunk_lesson_id") is not None
                        and candidate.get("chunk_lesson_id") != row.get("lesson_id"))
                    for candidate in row.get("semantic_candidates", [])
                )
            if name == "TRUSTED_EXTERNAL":
                allowed = {str(item).lower().rstrip(".") for item in
                           self.orchestrator.settings.external_retrieval_allowed_domains}
                row["scope_violation"] = any(
                    str(candidate.get("domain", "")).lower().rstrip(".") not in allowed
                    for candidate in row.get("semantic_candidates", [])
                )
            result.append(row)
        return result

    def start_production_request(self) -> None:
        self.production_started_at = perf_counter()
        self.production_response_at = None

    def finish_production_request(self) -> None:
        if getattr(self, "production_started_at", None) is not None:
            self.production_response_at = perf_counter()

    @property
    def total_latency_ms(self):
        started = getattr(self, "production_started_at", self.started_at)
        finished = getattr(self, "production_response_at", None) or perf_counter()
        return max(0, round((finished - started) * 1000))

    def failure_trace(self, execution, conversation_id, lesson_id, user_message_id,
                      assistant, persisted, *, current_question: str,
                      error_code="APPLICATION_SERVICE_FAILED") -> dict:
        status = persisted.get("final_message_status")
        selected_row = next((row for row in reversed(self.tiers)
                             if row.get("evidence_gate_passed") is True), None)
        selected_tier = selected_row["tier"] if selected_row and self.prompt_package else "NONE"
        deterministic_citation_failure = (
            self.citation_validation_error_code in _DETERMINISTIC_CITATION_ERRORS
        )
        self.finalize_tier_policy(selected_tier)
        selected_evidence = self.actual_evidence(None) if selected_tier != "NONE" else []
        trace = {
            "schema_version": "1.0.0", "execution_id": execution["execution_id"],
            "case_id": execution["case_id"], "repeat_index": execution["repeat_index"],
            "conversation": {"conversation_id": str(conversation_id),
                             "current_user_message_id": user_message_id,
                             "assistant_message_id": str(assistant.id) if assistant else None,
                             "lesson_id": str(lesson_id) if lesson_id else None,
                             "current_user_sequence_number": None,
                             "current_question": current_question},
            "domain_guard": {"status": "NOT_PRESENT", "out_of_domain_detected": False,
                             "error_code": None},
            "tiers_attempted": self.tier_trace([_TierValue(row["tier"]) for row in self.tiers]),
            "selected_tier": selected_tier, "selected_evidence": selected_evidence,
            "prompt": {"built": bool(self.prompt_package),
                       "source_map_snapshot": self.source_map_snapshot,
                       "context_blocks": self.context_blocks_snapshot,
                       "source_map_sha256": self.sha256(self.source_map_snapshot),
                       "prompt_package_sha256": self.prompt_package_sha256,
                       "selected_context_count": len(self.prompt_package.context_blocks) if self.prompt_package else 0,
                       "omitted_context_count": len(self.prompt_package.omitted_chunk_ids) if self.prompt_package else 0,
                       "context_build_duration_ms": self.context_build_duration_ms},
            "memory": {"applied": self.memory_applied_to_generation,
                       "production_path_ran": self.memory_builder_invocation_count > 0,
                       "builder_invocation_count": self.memory_builder_invocation_count,
                       "composition_applied": self.memory_composition_applied,
                       "generation_selected_turn_count": self.generated_memory_selected_turn_count,
                       "dropped_after_preflight": self.memory_dropped_after_preflight,
                       "selected_turn_count": getattr(self.memory, "selected_turn_count", 0),
                       "omitted_turn_count": getattr(self.memory, "omitted_turn_count", 0),
                       "token_count": getattr(self.memory, "token_count", 0),
                       "historical_citation_markers_removed": self.memory_markers_removed,
                       "historical_citation_labels": self.memory_historical_citation_labels,
                       "sanitized_context": self.sanitized_memory_snapshot,
                       "sanitized_context_sha256": self.sha256(self.sanitized_memory_snapshot)},
            "generation": {"called": self.generation_called, "answer": self.generated_answer,
                           "provider": self.provider, "model": self.model,
                           "error_code": self.generation_error_code,
                           "token_usage": self.token_usage},
            "citation_validation": citation_validation_snapshot(self, [], valid=False),
            "persistence": {**persisted, "error_code": persisted.get("error_code") or
                            (None if status == "COMPLETED" or deterministic_citation_failure
                             else "APPLICATION_SERVICE_FAILED")},
            "actual_behavior": ({"CURRENT_LESSON": "ANSWER", "INTERNAL_KB": "FALLBACK_INTERNAL",
                                 "TRUSTED_EXTERNAL": "FALLBACK_EXTERNAL"}.get(selected_tier)
                                if deterministic_citation_failure and self.generation_called
                                else "TECHNICAL_FAILURE"),
            "technical_error": (None if deterministic_citation_failure else {
                "stage": "APPLICATION_SERVICE", "code": error_code}),
            "semantic_no_evidence": False, "frozen_no_evidence_content": None,
            "all_applicable_tiers_semantically_exhausted": False,
            "selected_evidence_gate_passed": selected_tier == "NONE" or bool(selected_row),
            "timings": {"total_latency_ms": self.total_latency_ms,
                        "retrieval_latency_ms": sum(row.get("retrieval_latency_ms") or 0 for row in self.tiers),
                        "rerank_latency_ms": sum(row.get("rerank_latency_ms") or 0 for row in self.tiers),
                        "context_build_duration_ms": self.context_build_duration_ms,
                        "llm_latency_ms": self.generated_latency_ms,
                        "citation_finalization_latency_ms": self.citation_finalization_latency_ms},
        }
        from .contracts import E2EExecutionTrace
        return E2EExecutionTrace.model_validate(trace).model_dump(mode="json")

    def restore(self) -> None:
        for target, name, original in reversed(self._originals):
            setattr(target, name, original)


class _TierValue:
    """Local enum-compatible value used to order recorded failures by runtime attempt."""
    def __init__(self, value): self.value = value


async def load_persisted_state(session, assistant_message_id) -> dict:
    from app.database.models import Message, MessageCitation, MessageRetrieval
    message = await session.get(Message, assistant_message_id)
    retrievals = await session.scalars(select(MessageRetrieval).where(
        MessageRetrieval.message_id == assistant_message_id).order_by(MessageRetrieval.rank))
    citations = await session.scalars(select(MessageCitation).where(
        MessageCitation.message_id == assistant_message_id).order_by(MessageCitation.source_label))
    retrieval_rows = list(retrievals)
    citation_rows = list(citations)
    return {"final_message_status": message.status if message else None,
            "message_retrieval_count": len(retrieval_rows),
            "message_citation_count": len(citation_rows),
            "persisted_retrievals": [{"chunk_id": str(row.chunk_id), "rank": row.rank,
                                      "retrieval_score": float(row.retrieval_score),
                                      "rerank_score": float(row.rerank_score)} for row in retrieval_rows],
            "persisted_citations": [{"label": row.source_label, "source_kind": row.source_kind,
                                     "source_id": row.url or (str(row.chunk_id) if row.chunk_id else None),
                                     "chunk_id": str(row.chunk_id) if row.chunk_id else None,
                                     "url": row.url, "domain": row.domain, "title": row.title,
                                     "source_type": row.source_type, "locator": _jsonable(row.locator),
                                     "metadata": _jsonable(row.metadata)} for row in citation_rows]}
