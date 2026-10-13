from __future__ import annotations

import hashlib
import json
import re
import time
from contextlib import contextmanager
from typing import Any
from uuid import UUID, uuid4

from pydantic import TypeAdapter

from app.ai.generation.prompt import ASSESSMENT_GENERATION_PROMPT_VERSION
from app.ai.generation.prompt import build_generation_prompt
from app.ai.generation.schemas import (AssessmentGenerationRequest,
                                       StructuredAssessmentGenerationOutput,
                                       StructuredAssessmentGenerationProviderResult)
from app.ai.generation.service import AssessmentGenerationService, validate_and_map_output
from app.core.config import Settings
from app.core.errors import ApplicationError

from .artifacts import canonical_json
from .contracts import GenerationCase

SCHEMA_ID = "app.ai.generation.schemas.StructuredAssessmentGenerationOutput/v1"
_SAFE_PROVIDER_REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
CRITICAL_FAILURES = ("SCHEMA_INVALID", "OUT_OF_SCOPE_GENERATION", "UNSUPPORTED_QUESTION_TYPE",
                     "ANSWER_REFERENCE_INCONSISTENT", "UNANSWERABLE_QUESTION",
                     "AUTO_PUBLISH_VIOLATION", "PARTIAL_PERSISTENCE_ON_FAILURE")


def scope_identity(case: GenerationCase) -> dict:
    if case.generation_kind == "LESSON_EXERCISE":
        return {"generation_kind": case.generation_kind, "lesson_id": case.lesson_id}
    return {"generation_kind": case.generation_kind, "lesson_ids": case.lesson_ids,
            "vocabulary_ids": case.vocabulary_ids, "grammar_ids": case.grammar_ids}


def generation_request_identity(case: GenerationCase, settings: Settings, *, request=None, scope=None) -> tuple[dict, str]:
    request_payload = request.model_dump(mode="json") if request is not None else {
        "type": case.generation_kind, "question_count": case.question_count,
        "allowed_types": case.allowed_question_types, "difficulty": case.difficulty,
        "title": case.title, "description": case.description, "pass_threshold": case.pass_threshold,
        **({"lesson_id": case.lesson_id} if case.generation_kind == "LESSON_EXERCISE" else {
            "lesson_ids": case.lesson_ids, "vocabulary_ids": case.vocabulary_ids,
            "grammar_ids": case.grammar_ids})}
    scope_payload = None
    prompt_hash = None
    normalized_input = {"request": request_payload, "materialized_scope": None}
    if scope is not None and request is not None:
        system_content, user_content = build_generation_prompt(scope, request)
        prompt_hash = hashlib.sha256((system_content + "\0" + user_content).encode("utf-8")).hexdigest()
        scope_payload = {"payload": scope.payload, "allowed_source_refs": sorted(scope.allowed_source_refs)}
        normalized_input = {"system_content": system_content, "user_content": user_content,
            "generation_kind": request.type, "requested_question_count": request.question_count,
            "allowed_types": list(request.allowed_types), "difficulty": request.difficulty}
    identity = {"track": "assessment_generation", "normalized_production_input": normalized_input,
        "provider": settings.llm_provider, "model": settings.llm_model,
        "prompt_identity": ASSESSMENT_GENERATION_PROMPT_VERSION,
        "prompt_sha256": prompt_hash,
        "structured_schema_identity": SCHEMA_ID, "structured_schema_version": "1.0.0",
        "temperature": settings.llm_temperature,
        "max_output_tokens": settings.ai_generation_max_output_tokens,
        "reasoning_effort": settings.llm_reasoning_effort,
        "model_input_limit": settings.llm_model_input_limit,
        "request_timeout_seconds": settings.llm_request_timeout_seconds,
        "max_transient_retries": settings.llm_max_transient_retries}
    return identity, hashlib.sha256(canonical_json(identity)).hexdigest()


def generation_provider_request_identity(request, *, provider: str = "openai") -> tuple[dict, str]:
    prompt_hash = hashlib.sha256((request.system_content + "\0" + request.user_content).encode("utf-8")).hexdigest()
    identity = {"track": "assessment_generation",
        "normalized_production_input": {"system_content": request.system_content,
            "user_content": request.user_content, "generation_kind": request.generation_kind,
            "requested_question_count": request.requested_question_count,
            "allowed_types": list(request.allowed_types), "difficulty": request.difficulty},
        "provider": provider, "model": request.model,
        "prompt_identity": ASSESSMENT_GENERATION_PROMPT_VERSION, "prompt_sha256": prompt_hash,
        "structured_schema_identity": SCHEMA_ID, "structured_schema_version": "1.0.0",
        "temperature": request.temperature, "max_output_tokens": request.max_output_tokens,
        "reasoning_effort": request.reasoning_effort,
        "model_input_limit": request.model_input_limit,
        "request_timeout_seconds": request.request_timeout_seconds,
        "max_transient_retries": request.max_transient_retries}
    return identity, hashlib.sha256(canonical_json(identity)).hexdigest()


async def execute_generation_replay_case(*, case: GenerationCase, request, scope, settings,
                                         provider, run_id: str, domain_validator) -> dict[str, Any]:
    """Replay one Track-B output through production generation and validation seams."""
    started = time.perf_counter()
    identity, request_sha = generation_request_identity(case, settings, request=request, scope=scope)
    result: dict[str, Any] = {"step77_run_id": run_id, "generation_case_id": case.case_id,
        "split": case.split.value, "generation_kind": case.generation_kind,
        "provider_mode": "REPLAY", "request_sha256": request_sha,
        "technical_ok": False, "technical_error_code": None, "schema_valid": False,
        "scope_adherent": False, "supported_question_types_valid": False,
        "source_refs_valid": False, "requested_count_valid": False,
        "generated_questions": [], "critical_failures": [],
        "generation_case_status": "TECHNICAL_FAILURE", "generation_case_pass": False,
        "replay_origin": None}
    try:
        provider_result = await AssessmentGenerationService(provider, settings).generate(request, scope)
        mapped = validate_and_map_output(provider_result, request=request, scope=scope,
                                         domain_validator=domain_validator)
        questions = provider_result.output.questions
        result.update(technical_ok=True, schema_valid=True, scope_adherent=True,
            supported_question_types_valid=all(q.type in request.allowed_types for q in questions),
            source_refs_valid=all(ref in scope.allowed_source_refs for q in questions for ref in q.source_refs),
            requested_count_valid=len(questions) == request.question_count,
            generated_questions=[{"question_index": index, "question_type": item["type"],
                "question_sha256": hashlib.sha256(canonical_json(questions[index-1].model_dump(mode="json"))).hexdigest(),
                "source_refs": list(questions[index-1].source_refs)}
                for index, item in enumerate(mapped, start=1)],
            provider_response_sha256=hashlib.sha256(canonical_json(
                provider_result.output.model_dump(mode="json"))).hexdigest(),
            parsed_result_sha256=hashlib.sha256(canonical_json(
                provider_result.output.model_dump(mode="json"))).hexdigest(),
            generated_output_sha256=hashlib.sha256(canonical_json(
                provider_result.output.model_dump(mode="json"))).hexdigest(),
            generated_question_count=len(mapped),
            generation_case_status="DEFERRED_HUMAN_REVIEW", generation_case_pass=None)
        record = getattr(provider, "record", None)
        if record is not None:
            result.update(provider_response_sha256=record.response_sha256,
                parsed_result_sha256=record.parsed_result_sha256,
                replay_origin={"execution_mode": record.origin_execution_mode,
                               "run_id": record.origin_run_id})
        result["usage"] = {"input_tokens": provider_result.input_tokens,
            "output_tokens": provider_result.output_tokens, "total_tokens": provider_result.total_tokens}
    except Exception as exc:
        result["technical_error_code"] = getattr(provider, "last_error_code", None) or type(exc).__name__
    result["latency_ms"] = int((time.perf_counter() - started) * 1000)
    return result


def draft_lifecycle_valid(status: str | None, published_at: Any = None) -> bool:
    return status == "DRAFT" and published_at is None


def atomicity_after_failure(before_ids: set[str], after_ids: set[str]) -> bool:
    return before_ids == after_ids


def normalize_persisted_draft(value: Any) -> Any:
    """Convert persisted UUID identities to canonical strings for JSON artifacts."""
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {
            str(key) if isinstance(key, UUID) else key: normalize_persisted_draft(child)
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [normalize_persisted_draft(child) for child in value]
    if isinstance(value, tuple):
        return tuple(normalize_persisted_draft(child) for child in value)
    return value


async def _assessment_ids(session) -> set[str]:
    from sqlalchemy import select
    from app.database.models import Assessment
    rows = await session.execute(select(Assessment.id))
    return {str(value) for value in rows.scalars().all()}


def classify_invalid_generation_output(provider_result, request: AssessmentGenerationRequest, scope,
                                      *, domain_validator=None) -> dict[str, Any]:
    """Classify parsed production output by independent deterministic dimensions.

    `request` is the actual discriminated Admin request, whose authoritative
    count field is `question_count`. The provider DTO is deliberately not used
    as a substitute for the production request contract.
    """
    output = getattr(provider_result, "output", None)
    if not isinstance(output, StructuredAssessmentGenerationOutput):
        return {"schema_valid": False, "requested_count_valid": False,
                "supported_question_types_valid": False, "source_refs_valid": False,
                "scope_adherent": False, "domain_validation_valid": False,
                "critical_failures": ["SCHEMA_INVALID"]}

    questions = output.questions
    count_valid = len(questions) == request.question_count
    supported = all(question.type in request.allowed_types for question in questions)
    source_refs_valid = all(
        bool(question.source_refs)
        and len(question.source_refs) == len(set(question.source_refs))
        and all(isinstance(ref, str) and ref.strip() and ref in scope.allowed_source_refs
                for ref in question.source_refs)
        for question in questions
    )

    domain_valid: bool | None = None
    if domain_validator is not None and count_valid and supported and source_refs_valid:
        domain_valid = True
        for question in questions:
            try:
                domain_validator(map_generated_question(question, 1))
            except Exception:
                domain_valid = False
                break

    failures = []
    if not supported:
        failures.append("UNSUPPORTED_QUESTION_TYPE")
    if not source_refs_valid:
        failures.append("OUT_OF_SCOPE_GENERATION")
    # Count and generic production-domain failures have no frozen critical
    # failure enum. Their independent dimensions still fail the case.
    return {"schema_valid": True, "requested_count_valid": count_valid,
            "supported_question_types_valid": supported,
            "source_refs_valid": source_refs_valid, "scope_adherent": source_refs_valid,
            "domain_validation_valid": domain_valid,
            "critical_failures": sorted(failures)}


def _question(kind: str, source_ref: str, index: int) -> dict:
    common = {"type": kind, "prompt": f"Offline evaluation question {index} based on the selected curriculum.",
              "source_refs": [source_ref]}
    if kind == "multiple_choice":
        return {**common, "options": [{"option_text": "你好", "is_correct": True}, {"option_text": "再见", "is_correct": False}]}
    if kind == "fill_blank":
        return {**common, "reference_answer": "你好", "accepted_answers": []}
    if kind == "matching":
        return {**common, "left_items": [{"id": "l1", "text": "你好"}, {"id": "l2", "text": "再见"}],
                "right_items": [{"id": "r1", "text": "Xin chào"}, {"id": "r2", "text": "Tạm biệt"}],
                "correct_pairs": [{"left_id": "l1", "right_id": "r1"}, {"left_id": "l2", "right_id": "r2"}]}
    if kind == "reorder_sentence":
        return {**common, "items": [{"id": "w1", "text": "你好"}], "correct_order": ["w1"]}
    return {**common, "reference_answer": "你好。", "rubric": "Accept a response supported by the selected fixture curriculum."}


class DeterministicGenerationProvider:
    """Deterministic fake injected only through the existing provider protocol."""
    def __init__(self, question_types: list[str]):
        self.question_types = question_types
        self.last_request = None
        self.last_result: StructuredAssessmentGenerationProviderResult | None = None
        self.last_error_code: str | None = None

    async def generate(self, request):
        self.last_request = request
        payload = json.loads(request.user_content)
        refs = payload["allowed_source_refs"]
        if not refs:
            from app.ai.generation.errors import StructuredAssessmentGenerationProviderError, AI_GENERATION_INVALID_RESPONSE
            self.last_error_code = AI_GENERATION_INVALID_RESPONSE
            raise StructuredAssessmentGenerationProviderError(AI_GENERATION_INVALID_RESPONSE)
        selected = [kind for kind in self.question_types if kind in request.allowed_types]
        if len(selected) < request.requested_question_count:
            selected = (selected * (request.requested_question_count // len(selected) + 1))[:request.requested_question_count]
        questions = [_question(kind, refs[i % len(refs)], i + 1) for i, kind in enumerate(selected[:request.requested_question_count])]
        output = StructuredAssessmentGenerationOutput.model_validate({"questions": questions})
        self.last_result = StructuredAssessmentGenerationProviderResult(output=output, provider="test-only",
            model=request.model, input_tokens=None, output_tokens=None, total_tokens=None,
            provider_preflight_input_tokens=0, latency_ms=0, attempt_count=1, provider_request_id=None)
        return self.last_result


class ObservingGenerationProvider:
    """Evaluation-owned observer; execution mode is supplied by the runner."""

    def __init__(self, delegate, *, provider_mode: str):
        if provider_mode not in {"FAKE", "REPLAY", "REAL"}:
            raise ValueError("STEP77_PROVIDER_MODE_INVALID")
        self.delegate = delegate
        self.provider_mode = provider_mode
        self.provider_name = getattr(delegate, "provider_name", "openai")
        self.last_result: StructuredAssessmentGenerationProviderResult | None = None
        self.last_error_code: str | None = None
        self.replay_record = None
        self.safe_metadata: dict[str, Any] = {}

    async def generate(self, request):
        try:
            result = await self.delegate.generate(request)
        except Exception as exc:
            code = getattr(exc, "code", None)
            self.last_error_code = code if isinstance(code, str) and code.startswith(("AI_GENERATION_", "STEP77_REPLAY_")) else None
            self.safe_metadata = {"provider": self.provider_name, "model": getattr(request, "model", None),
                "provider_request_id": None, "usage": None, "latency_ms": None,
                "attempt_count": None, "finish_status_metadata": None,
                "error_code": self.last_error_code}
            raise
        if isinstance(result, StructuredAssessmentGenerationProviderResult):
            self.last_result = result
            if self.provider_mode == "REPLAY":
                self.replay_record = getattr(self.delegate, "record", None)
            request_id = getattr(result, "provider_request_id", None)
            if not isinstance(request_id, str) or not _SAFE_PROVIDER_REQUEST_ID.fullmatch(request_id):
                request_id = None
            self.safe_metadata = {
                "provider": getattr(result, "provider", self.provider_name),
                "model": getattr(result, "model", getattr(request, "model", None)),
                "provider_request_id": request_id,
                "usage": {key: getattr(result, key, None) for key in
                          ("input_tokens", "output_tokens", "total_tokens")},
                "latency_ms": getattr(result, "latency_ms", None),
                "attempt_count": getattr(result, "attempt_count", None),
                "finish_status_metadata": None,
            }
        return result


@contextmanager
def _provider_override(provider):
    """Replace only the paid network adapter for one serial offline request."""
    from app.admin import service as admin_service
    original = admin_service.get_assessment_generation_provider
    admin_service.get_assessment_generation_provider = lambda: provider
    try:
        yield admin_service
    finally:
        admin_service.get_assessment_generation_provider = original


async def execute_generation_case(session, case: GenerationCase, settings: Settings, *, run_id: str,
                                  provider: DeterministicGenerationProvider | None = None,
                                  human_annotation_statuses: list[str] | None = None,
                                  provider_mode: str = "FAKE") -> dict[str, Any]:
    """Run the frozen Admin application service with only its paid provider replaced."""
    from app.ai.generation.schemas import AssessmentGenerationRequest

    if provider is None:
        offset = sum(ord(ch) for ch in case.case_id) % len(case.allowed_question_types)
        rotated = case.allowed_question_types[offset:] + case.allowed_question_types[:offset]
        provider = DeterministicGenerationProvider(rotated[:3])
    observer = ObservingGenerationProvider(provider, provider_mode=provider_mode)
    request_body = {"type": case.generation_kind, "question_count": case.question_count,
        "allowed_types": case.allowed_question_types, "difficulty": case.difficulty,
        "title": case.title, "description": case.description, "pass_threshold": case.pass_threshold}
    if case.generation_kind == "LESSON_EXERCISE":
        request_body["lesson_id"] = case.lesson_id
    else:
        request_body.update(lesson_ids=case.lesson_ids, vocabulary_ids=case.vocabulary_ids,
                            grammar_ids=case.grammar_ids)
    request = TypeAdapter(AssessmentGenerationRequest).validate_python(request_body)
    before_assessment_ids = await _assessment_ids(session)
    started = time.perf_counter()
    base = {"execution_id": str(uuid4()), "step77_run_id": run_id,
        "generation_case_id": case.case_id, "split": case.split.value,
        "generation_kind": case.generation_kind, "difficulty": case.difficulty,
        "question_count": case.question_count,
        "allowed_question_types": list(case.allowed_question_types),
        "lesson_id": case.lesson_id, "lesson_ids": list(case.lesson_ids),
        "vocabulary_ids": list(case.vocabulary_ids), "grammar_ids": list(case.grammar_ids),
        "fixture_scope_identity": case.fixture_scope_identity, "provider_mode": provider_mode,
        "request_sha256": None, "materialized_scope_sha256": None,
        "provider_response_sha256": None, "parsed_result_sha256": None, "generated_output_sha256": None,
        "generated_draft_sha256": None, "generated_questions": [],
        "persisted_assessment_id": None, "persisted_assessment_status": None,
        "persisted_question_count": 0, "schema_valid": False, "scope_adherent": False,
        "supported_question_types_valid": False, "source_refs_valid": False, "domain_validation_valid": False,
        "requested_count_valid": False, "draft_lifecycle_valid": False,
        "atomic_persistence_valid": False, "technical_ok": True,
        "technical_error_code": None, "critical_failures": [],
        "human_review_complete": False, "human_annotation_status": "DRAFT",
        "human_annotation_statuses": human_annotation_statuses or ["DRAFT"] * case.question_count,
        "generation_case_status": "DEFERRED_HUMAN_REVIEW", "generation_case_pass": None,
        "latency_ms": None, "usage": None, "provider": observer.provider_name,
        "model": settings.llm_model, "provider_request_id": None,
        "provider_diagnostics": None, "replay_origin": None}
    try:
        with _provider_override(observer) as admin_service:
            # Materialize once for identity evidence; the production Admin service repeats the
            # authoritative read as part of its own accepted orchestration boundary.
            scope_data = await admin_service.curriculum_service.materialize_generation_scope(session, request)
            from app.ai.generation.schemas import MaterializedGenerationScope
            scope = MaterializedGenerationScope(assessment_type=scope_data["assessment_type"],
                lesson_id=scope_data["lesson_id"], lesson_ids=scope_data["lesson_ids"],
                vocabulary_ids=scope_data["vocabulary_ids"], grammar_ids=scope_data["grammar_ids"],
                title=scope_data["title"], description=scope_data["description"],
                pass_threshold=scope_data["pass_threshold"], payload=scope_data["payload"],
                allowed_source_refs=scope_data["allowed_source_refs"])
            scope_bytes = canonical_json({"identity": scope_identity(case), "payload": scope.payload,
                                          "allowed_source_refs": sorted(scope.allowed_source_refs)})
            base["materialized_scope_sha256"] = hashlib.sha256(scope_bytes).hexdigest()
            base["materialized_scope_content"] = {"identity": scope_identity(case),
                "payload": scope.payload, "allowed_source_refs": sorted(scope.allowed_source_refs)}
            _, request_sha = generation_request_identity(case, settings, request=request, scope=scope)
            base["request_sha256"] = request_sha
            await session.rollback()
            original_materializer = admin_service.curriculum_service.materialize_generation_scope
            async def use_same_materialized_scope(_session, _request):
                return scope_data
            admin_service.curriculum_service.materialize_generation_scope = use_same_materialized_scope
            try:
                response = await admin_service.generate_assessment_draft(session, request)
            finally:
                admin_service.curriculum_service.materialize_generation_scope = original_materializer
        assessment = response["assessment"]
        questions = response["questions"]
        provider_result = observer.last_result
        if provider_result is None:
            raise RuntimeError("offline provider returned no structured output")
        output = provider_result.output
        domain_validator = admin_service.exercise_service.admin_validate_generated_question
        mapped = validate_and_map_output(provider_result, request=request, scope=scope,
                                         domain_validator=domain_validator)
        source_refs = [ref for q in output.questions for ref in q.source_refs]
        supported = all(q.type in case.allowed_question_types for q in output.questions)
        source_ok = bool(source_refs) and all(ref in scope.allowed_source_refs for ref in source_refs)
        count_ok = len(output.questions) == request.question_count and len(questions) == request.question_count
        lifecycle_ok = draft_lifecycle_valid(assessment.get("status"), assessment.get("published_at"))
        schema_ok = isinstance(output, StructuredAssessmentGenerationOutput)
        deterministic = {"schema_valid": schema_ok, "scope_adherent": source_ok,
            "supported_question_types_valid": supported, "source_refs_valid": source_ok,
            "requested_count_valid": count_ok, "domain_validation_valid": True,
            "draft_lifecycle_valid": lifecycle_ok,
            "atomic_persistence_valid": len(mapped) == len(questions) == request.question_count}
        critical = []
        if not schema_ok: critical.append("SCHEMA_INVALID")
        if not source_ok: critical.append("OUT_OF_SCOPE_GENERATION")
        if not supported: critical.append("UNSUPPORTED_QUESTION_TYPE")
        if not lifecycle_ok: critical.append("AUTO_PUBLISH_VIOLATION")
        question_rows = []
        for index, question in enumerate(output.questions, start=1):
            item = question.model_dump(mode="json")
            question_rows.append({"question_index": index, "persisted_question_id": str(questions[index-1]["id"]),
                "question_type": question.type, "question_content": item,
                "question_sha256": hashlib.sha256(canonical_json(item)).hexdigest(),
                "source_refs": list(question.source_refs)})
        output_dict = output.model_dump(mode="json")
        draft_dict = normalize_persisted_draft({"assessment": assessment, "questions": questions})
        scope_content = base["materialized_scope_content"]
        response_hash = hashlib.sha256(canonical_json(output_dict)).hexdigest()
        draft_hash = hashlib.sha256(canonical_json(draft_dict)).hexdigest()
        base.update(deterministic, critical_failures=critical, generated_questions=question_rows,
            persisted_assessment_id=str(assessment["id"]), persisted_assessment_status=assessment["status"],
            persisted_question_count=len(questions), provider_response_sha256=response_hash,
            parsed_result_sha256=response_hash,
            generated_output_sha256=response_hash, generated_draft_sha256=draft_hash,
            generated_output_content=output_dict, generated_draft_content=draft_dict,
            materialized_scope_content=scope_content,
            generation_case_status="DETERMINISTIC_FAILURE" if critical else "DEFERRED_HUMAN_REVIEW",
            generation_case_pass=False if critical else None,
            latency_ms=int((time.perf_counter()-started)*1000),
            usage={"input_tokens": provider_result.input_tokens, "output_tokens": provider_result.output_tokens,
                   "total_tokens": provider_result.total_tokens},
            provider=getattr(provider_result, "provider", settings.llm_provider),
            model=getattr(provider_result, "model", settings.llm_model),
            provider_request_id=observer.safe_metadata.get("provider_request_id"),
            provider_diagnostics=observer.safe_metadata)
        replay_record = observer.replay_record
        if replay_record is not None:
            base.update(provider_response_sha256=replay_record.response_sha256,
                replay_origin={"execution_mode": replay_record.origin_execution_mode,
                              "run_id": replay_record.origin_run_id})
    except ApplicationError as exc:
        code = exc.code
        await session.rollback()
        atomicity_verified = False
        try:
            base["atomic_persistence_valid"] = atomicity_after_failure(
                before_assessment_ids, await _assessment_ids(session))
            atomicity_verified = True
        except Exception:
            base["atomic_persistence_valid"] = False
        deterministic_failure = code == "AI_GENERATION_INVALID_OUTPUT"
        base.update(technical_ok=deterministic_failure,
            technical_error_code=None if deterministic_failure else code,
            generation_case_status="DETERMINISTIC_FAILURE" if deterministic_failure else "TECHNICAL_FAILURE",
            generation_case_pass=False)
        if not atomicity_verified:
            base.update(technical_ok=False, technical_error_code="PERSISTENCE_STATE_UNVERIFIED",
                        generation_case_status="TECHNICAL_FAILURE")
        if code == "AI_GENERATION_INVALID_OUTPUT":
            classification = classify_invalid_generation_output(
                observer.last_result, request, scope,
                domain_validator=admin_service.exercise_service.admin_validate_generated_question,
            ) if "scope" in locals() else classify_invalid_generation_output(None, request, None)
            base.update(classification)
        if atomicity_verified and not base["atomic_persistence_valid"]:
            base["critical_failures"] = sorted(set(
                base["critical_failures"] + ["PARTIAL_PERSISTENCE_ON_FAILURE"]))
        base["latency_ms"] = int((time.perf_counter()-started)*1000)
    except Exception as exc:
        base.update(technical_ok=False, technical_error_code=observer.last_error_code or type(exc).__name__,
                    generation_case_status="TECHNICAL_FAILURE", generation_case_pass=False,
                    latency_ms=int((time.perf_counter()-started)*1000),
                    provider_diagnostics=observer.safe_metadata or None)
    return base


_GENERATION_REVIEW_ENRICHMENT_FIELDS = frozenset({
    "human_annotation_status", "human_annotation_statuses", "human_review_complete",
    "generation_case_status", "generation_case_pass",
    "provider_request_id", "usage", "latency_ms", "provider_diagnostics", "replay_origin",
})


def canonical_frozen_generation_projection(row: dict) -> dict:
    """Return the generated execution content, excluding post-generation review enrichment."""
    return {key: value for key, value in row.items() if key not in _GENERATION_REVIEW_ENRICHMENT_FIELDS}


def _projected_cases_artifact(rows: list[dict]) -> bytes:
    return b"".join(canonical_json(canonical_frozen_generation_projection(row)) + b"\n" for row in rows)


def _recomputed_d109_bindings(row: dict, cases_artifact: bytes) -> tuple[dict[int, str], str, str, str, str]:
    """Recompute D-109 identities from the canonical frozen content projection."""
    try:
        actual_rows = [json.loads(line) for line in cases_artifact.decode("utf-8", errors="strict").splitlines()
                       if line.strip()]
    except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
        raise ValueError("STEP77_GENERATION_ANNOTATION_ARTIFACT_UNVERIFIABLE") from None
    matching = [candidate for candidate in actual_rows
        if candidate.get("generation_case_id") == row.get("generation_case_id")
        and candidate.get("execution_id") == row.get("execution_id")
        and candidate.get("step77_run_id") == row.get("step77_run_id")]
    if (len(matching) != 1
            or canonical_frozen_generation_projection(matching[0])
            != canonical_frozen_generation_projection(row)):
        raise ValueError("STEP77_GENERATION_ANNOTATION_ARTIFACT_CONTENT_MISMATCH")
    questions = row.get("generated_questions")
    if not isinstance(questions, list):
        raise ValueError("STEP77_GENERATION_ANNOTATION_CONTENT_UNVERIFIABLE")
    question_hashes: dict[int, str] = {}
    for question in questions:
        content = question.get("question_content")
        index = question.get("question_index")
        if not isinstance(content, dict) or type(index) is not int or index in question_hashes:
            raise ValueError("STEP77_GENERATION_ANNOTATION_CONTENT_UNVERIFIABLE")
        question_hashes[index] = hashlib.sha256(canonical_json(content)).hexdigest()
    draft_content = row.get("generated_draft_content")
    output_content = row.get("generated_output_content")
    scope_content = row.get("materialized_scope_content")
    if not all(isinstance(value, dict) for value in (draft_content, output_content, scope_content)):
        raise ValueError("STEP77_GENERATION_ANNOTATION_CONTENT_UNVERIFIABLE")
    return (question_hashes, hashlib.sha256(canonical_json(draft_content)).hexdigest(),
            hashlib.sha256(canonical_json(output_content)).hexdigest(),
            hashlib.sha256(canonical_json(scope_content)).hexdigest(),
            hashlib.sha256(cases_artifact).hexdigest())


def evaluate_generation_human_labels(row: dict, annotations: list, *, run_id: str,
                                     cases_artifact: bytes | None = None) -> dict:
    """Apply D-109 only after recomputing all reviewed-content hashes from source content."""
    from .contracts import GenerationQuestionAnnotation
    output = dict(row)
    deterministic_checks = ("schema_valid", "scope_adherent", "supported_question_types_valid",
                            "source_refs_valid", "requested_count_valid", "domain_validation_valid",
                            "draft_lifecycle_valid", "atomic_persistence_valid")
    deterministic_failure = (output.get("generation_case_status") == "DETERMINISTIC_FAILURE"
                             or any(output.get(name) is False for name in deterministic_checks))
    if not output.get("technical_ok") or output.get("critical_failures") or deterministic_failure:
        output["generation_case_status"] = "TECHNICAL_FAILURE" if not output.get("technical_ok") else "DETERMINISTIC_FAILURE"
        output["generation_case_pass"] = False
        return output
    if len(annotations) != output.get("persisted_question_count"):
        raise ValueError("STEP77_GENERATION_ANNOTATION_COUNT_MISMATCH")
    parsed = [item if isinstance(item, GenerationQuestionAnnotation)
              else GenerationQuestionAnnotation.model_validate(item) for item in annotations]
    from .dataset import annotation_contract
    expected_annotation_contract = annotation_contract("generation")
    if any((item.annotation_version, item.rubric_version) != expected_annotation_contract
           for item in parsed):
        raise ValueError("STEP77_GENERATION_ANNOTATION_VERSION_MISMATCH")
    if any(item.generation_case_id != output.get("generation_case_id") for item in parsed):
        raise ValueError("STEP77_GENERATION_ANNOTATION_CASE_MISMATCH")
    output["human_annotation_statuses"] = [item.review_status for item in parsed]
    question_by_index = {q["question_index"]: q for q in output["generated_questions"]}
    reviewed = [item for item in parsed if item.review_status in {"HUMAN_APPROVED", "NEEDS_ADJUDICATION"}]
    if reviewed:
        if cases_artifact is None:
            raise ValueError("STEP77_GENERATION_ANNOTATION_ARTIFACT_REQUIRED")
        question_hashes, draft_hash, output_hash, scope_hash, cases_hash = _recomputed_d109_bindings(
            output, cases_artifact)
    for item in parsed:
        if item.review_status == "DRAFT":
            continue
        question = question_by_index.get(item.question_index)
        question_hash = question_hashes.get(item.question_index) if reviewed else None
        if (question is None or item.step77_run_id != run_id
                or item.generation_case_id != output["generation_case_id"]
                or item.step77_run_id != output.get("step77_run_id")
                or item.execution_id != output["execution_id"]
                or item.persisted_question_id != question["persisted_question_id"]
                or not reviewed
                or item.generated_draft_sha256 != draft_hash
                or item.generated_draft_sha256 != output.get("generated_draft_sha256")
                or item.generated_question_sha256 != question_hash
                or item.generated_question_sha256 != question.get("question_sha256")
                or item.materialized_scope_sha256 != scope_hash
                or item.materialized_scope_sha256 != output.get("materialized_scope_sha256")
                or item.generation_output_sha256 != output_hash
                or item.generation_output_sha256 != output.get("generated_output_sha256")
                or item.cases_artifact_sha256 != cases_hash):
            raise ValueError("STEP77_GENERATION_ANNOTATION_STALE_OR_WRONGLY_BOUND")
    approved = all(item.review_status == "HUMAN_APPROVED" for item in parsed)
    if not approved:
        if any(item.review_status not in {"DRAFT", "NEEDS_ADJUDICATION"} for item in parsed):
            raise ValueError("STEP77_GENERATION_ANNOTATION_STATE_INVALID")
        output.update(human_review_complete=False, generation_case_status="DEFERRED_HUMAN_REVIEW",
                      generation_case_pass=None)
        return output
    failures = list(output.get("critical_failures", []))
    for item in parsed:
        if item.answer_reference_consistency == "INCONSISTENT":
            failures.append("ANSWER_REFERENCE_INCONSISTENT")
        if item.answerability == "UNANSWERABLE":
            failures.append("UNANSWERABLE_QUESTION")
    failures = sorted(set(failures))
    output.update(human_review_complete=True, critical_failures=failures,
        generation_case_status="HUMAN_SEMANTIC_FAILURE" if failures else "PASS",
        generation_case_pass=not failures)
    return output


def build_generation_summary(rows: list[dict]) -> dict:
    check_names = ("schema_valid", "scope_adherent", "supported_question_types_valid", "source_refs_valid",
                   "requested_count_valid", "domain_validation_valid", "draft_lifecycle_valid",
                   "atomic_persistence_valid")
    technical = sum(row.get("technical_ok") is False for row in rows)
    critical = [failure for row in rows for failure in row["critical_failures"]]
    statuses = {status: sum(row["generation_case_status"] == status for row in rows)
                for status in ("TECHNICAL_FAILURE", "DETERMINISTIC_FAILURE", "DEFERRED_HUMAN_REVIEW", "HUMAN_SEMANTIC_FAILURE", "PASS")}
    finalizable = [row for row in rows if row.get("human_review_complete") is True]
    counts = {name: sum(bool(row.get(name)) for row in rows) for name in check_names}
    rates = {name: counts[name] / len(rows) if rows else None for name in check_names}
    annotation_counts = {status: 0 for status in ("DRAFT", "NEEDS_ADJUDICATION", "HUMAN_APPROVED")}
    for row in rows:
        statuses_for_case = row.get("human_annotation_statuses")
        if statuses_for_case is None:
            status = row.get("human_annotation_status")
            statuses_for_case = [status] if status is not None else []
        for status in statuses_for_case:
            if status not in annotation_counts:
                raise ValueError("STEP77_GENERATION_ANNOTATION_STATUS_INVALID")
            annotation_counts[status] += 1
    pass_count = sum(row.get("generation_case_pass") is True for row in rows)
    fail_count = sum(row.get("generation_case_pass") is False for row in rows)
    pass_denominator = pass_count + fail_count
    return {"planned_case_count": 16, "executed_case_count": len(rows),
        "counts_by_split": {split: sum(row["split"] == split for row in rows) for split in ("DEVELOPMENT", "HOLDOUT")},
        "counts_by_generation_kind": {kind: sum(row["generation_kind"] == kind for row in rows) for kind in ("LESSON_EXERCISE", "PERIODIC_TEST")},
        "counts_by_difficulty": {difficulty: sum(row.get("difficulty") == difficulty for row in rows)
                                 for difficulty in ("EASY", "MEDIUM", "HARD")},
        "question_type_coverage": sorted({q["question_type"] for row in rows for q in row["generated_questions"]}),
        "technical_failure_count": technical, "technical_failure_rate": technical/len(rows) if rows else None,
        "checks": {name: {"count": counts[name], "rate": rates[name]} for name in check_names},
        "critical_failure_count": len(critical), "critical_failure_rate": len([row for row in rows if row["critical_failures"]])/len(rows) if rows else None,
        "critical_failures_by_type": {name: critical.count(name) for name in sorted(set(critical))},
        "human_annotation_counts": annotation_counts,
        "human_review_complete_case_count": len(finalizable), "deferred_human_review_case_count": statuses["DEFERRED_HUMAN_REVIEW"],
        "generation_case_status_counts": statuses, "generation_case_pass_count": pass_count,
        "generation_case_fail_count": fail_count,
        "generation_case_pass_rate": pass_count / pass_denominator if pass_denominator else None,
        "official_eligible": False, "runtime_api_calls": 0}
