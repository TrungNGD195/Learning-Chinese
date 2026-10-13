from __future__ import annotations

import hashlib
import re
import time
from time import perf_counter
from collections import Counter, defaultdict
from dataclasses import asdict
from typing import Any
from uuid import uuid4

from app.ai.grading.errors import StructuredGradingProviderError
from app.ai.grading.prompt import GRADING_PROMPT_VERSION, build_grading_prompt
from app.ai.grading.schemas import (ProviderGradingStatus, StructuredGradingOutput,
                                    StructuredGradingProviderResult, StructuredGradingRequest)
from app.ai.grading.service import LLMGradingService
from app.core.config import Settings
from app.exercise.grading import GradingUnavailable

from .artifacts import canonical_json
from .contracts import GradingAnnotation, GradingCase, NormalizedState

SCHEMA_ID = "app.ai.grading.schemas.StructuredGradingOutput/v1"


class ObservingGradingProvider:
    """Evaluation-only transparent proxy retaining typed provider diagnostics."""
    _SAFE_CODES = frozenset({
        "AI_GRADING_PROVIDER_NOT_CONFIGURED", "AI_GRADING_AUTHENTICATION_FAILED",
        "AI_GRADING_PERMISSION_DENIED", "AI_GRADING_TIMEOUT", "AI_GRADING_RATE_LIMITED",
        "AI_GRADING_PROVIDER_UNAVAILABLE", "AI_GRADING_INPUT_LIMIT_EXCEEDED",
        "AI_GRADING_REQUEST_INVALID", "AI_GRADING_INVALID_RESPONSE", "AI_GRADING_SCHEMA_INVALID",
    })
    _SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")

    def __init__(self, delegate, *, provider_mode: str):
        if provider_mode not in {"FAKE", "REPLAY", "REAL"}:
            raise ValueError("STEP77_PROVIDER_MODE_INVALID")
        self.delegate = delegate
        self.provider_mode = provider_mode
        self.provider_name = getattr(delegate, "provider_name", "openai")
        self.last_error_code = None
        self.last_result = None
        self.replay_record = None
        self.safe_metadata: dict[str, Any] = {}

    async def grade(self, request):
        started = perf_counter()
        try:
            result = await self.delegate.grade(request)
            self.last_result = result
            if self.provider_mode == "REPLAY":
                self.replay_record = getattr(self.delegate, "record", None)
            if not isinstance(result, StructuredGradingProviderResult):
                self.last_error_code = "AI_GRADING_INVALID_RESPONSE"
            elif not isinstance(result.output, StructuredGradingOutput):
                self.last_error_code = "AI_GRADING_SCHEMA_INVALID"
            request_id = getattr(result, "provider_request_id", None)
            if not isinstance(request_id, str) or not self._SAFE_REQUEST_ID.fullmatch(request_id):
                request_id = None
            self.safe_metadata = {
                "provider": getattr(result, "provider", self.provider_name),
                "model": getattr(result, "model", request.model),
                "provider_request_id": request_id,
                "usage": {key: getattr(result, key, None) for key in
                          ("input_tokens", "output_tokens", "total_tokens")},
                "latency_ms": getattr(result, "latency_ms", None),
                "attempt_count": getattr(result, "attempt_count", None),
                "provider_preflight_input_tokens": getattr(result, "provider_preflight_input_tokens", None),
                "finish_status_metadata": {},
            }
            return result
        except Exception as exc:
            code = getattr(self.delegate, "last_error_code", None) or getattr(exc, "code", None)
            if code not in self._SAFE_CODES and not (isinstance(code, str) and
                    (code.startswith("STEP77_REPLAY_") or re.fullmatch(r"AI_GRADING_[A-Z0-9_]{1,80}", code))):
                code = "AI_GRADING_INVALID_RESPONSE" if type(exc).__name__ in {
                    "ValidationError", "JSONDecodeError"} else "AI_GRADING_PROVIDER_UNAVAILABLE"
            self.last_error_code = code
            self.safe_metadata = {"provider": self.provider_name, "model": request.model,
                                  "error_code": code,
                                  "latency_ms": round((perf_counter() - started) * 1000),
                                  "provider_request_id": None, "usage": None,
                                  "finish_status_metadata": {}}
            raise


def normalize_result(status: str, score: float | None, max_points: float,
                     is_correct: bool | None = None) -> NormalizedState:
    """D-106 normalization shared by model results and approved human labels."""
    if status == "UNCERTAIN":
        if score is not None or is_correct is not None:
            raise ValueError("UNCERTAIN_REQUIRES_NULL_SCORE_AND_CORRECTNESS")
        return NormalizedState.UNCERTAIN
    if status != "GRADED" or score is None or isinstance(score, bool):
        raise ValueError("GRADED_REQUIRES_NUMERIC_SCORE")
    value = float(score)
    if value < 0 or value > max_points:
        raise ValueError("GRADED_SCORE_OUT_OF_RANGE")
    correct = value == max_points
    if is_correct is not None and is_correct is not correct:
        raise ValueError("D095_CORRECTNESS_INCONSISTENT")
    if value == 0:
        return NormalizedState.ZERO_CREDIT
    if correct:
        return NormalizedState.FULL_CREDIT
    return NormalizedState.PARTIAL_CREDIT


def validate_human_annotation(annotation: GradingAnnotation, case: GradingCase) -> None:
    from .dataset import annotation_contract
    if (annotation.case_id != case.case_id
            or (annotation.annotation_version, annotation.rubric_version) != annotation_contract("grading")):
        raise ValueError("STEP77_GRADING_ANNOTATION_IDENTITY_MISMATCH")
    if annotation.review_status in {"NEEDS_ADJUDICATION", "HUMAN_APPROVED"}:
        if annotation.expected_grading_status == "GRADED":
            normalized = normalize_result("GRADED", annotation.human_score, case.max_points,
                                          annotation.human_is_correct)
        elif annotation.expected_grading_status == "UNCERTAIN":
            normalized = normalize_result("UNCERTAIN", annotation.human_score, case.max_points,
                                          annotation.human_is_correct)
        else:
            raise ValueError("HUMAN_APPROVED_EXPECTED_STATUS_REQUIRED")
        if annotation.normalized_state != normalized:
            raise ValueError("HUMAN_APPROVED_NORMALIZED_STATE_MISMATCH")


def grading_request_identity(case: GradingCase, settings: Settings) -> tuple[dict, str]:
    system, user = build_grading_prompt(question_type=case.question_type, prompt=case.question_content,
        reference_answer=case.reference_answer, rubric=case.rubric, max_points=case.max_points,
        learner_answer=case.learner_answer)
    request = StructuredGradingRequest(case.question_type, system, user, settings.llm_model,
        settings.llm_temperature, settings.llm_max_output_tokens, settings.llm_reasoning_effort,
        settings.llm_model_input_limit, settings.llm_request_timeout_seconds,
        settings.llm_max_transient_retries)
    return grading_provider_request_identity(request, provider=settings.llm_provider)


def grading_provider_request_identity(request: StructuredGradingRequest, *, provider: str = "openai") -> tuple[dict, str]:
    prompt_sha = hashlib.sha256((request.system_content + "\0" + request.user_content).encode("utf-8")).hexdigest()
    identity = {"track": "grading",
        "normalized_production_input": {"question_type": request.question_type,
            "system_content": request.system_content, "user_content": request.user_content},
        "provider": provider, "model": request.model,
        "prompt_identity": GRADING_PROMPT_VERSION, "prompt_sha256": prompt_sha,
        "structured_schema_identity": SCHEMA_ID, "structured_schema_version": "1.0.0",
        "temperature": request.temperature, "max_output_tokens": request.max_output_tokens,
        "reasoning_effort": request.reasoning_effort,
        "model_input_limit": request.model_input_limit,
        "request_timeout_seconds": request.request_timeout_seconds,
        "max_transient_retries": request.max_transient_retries}
    return identity, hashlib.sha256(canonical_json(identity)).hexdigest()


class DeterministicGradingProvider:
    """Fake only at the frozen structured provider protocol; never an official result."""
    def __init__(self, semantic_class: str):
        self.semantic_class = semantic_class
        self.last_request: StructuredGradingRequest | None = None
        self.last_result: StructuredGradingProviderResult | None = None
        self.last_error_code: str | None = None

    async def grade(self, request: StructuredGradingRequest) -> StructuredGradingProviderResult:
        self.last_request = request
        if self.semantic_class == "CLEAR_CORRECT":
            output = StructuredGradingOutput(grading_status=ProviderGradingStatus.GRADED,
                score=2.0, feedback="Câu trả lời đúng theo tiêu chí minh họa.")
        elif self.semantic_class == "CLEAR_INCORRECT":
            output = StructuredGradingOutput(grading_status=ProviderGradingStatus.GRADED,
                score=0.0, feedback="Câu trả lời chưa đúng theo tiêu chí minh họa.")
        elif self.semantic_class == "PARTIAL":
            output = StructuredGradingOutput(grading_status=ProviderGradingStatus.GRADED,
                score=1.0, feedback="Câu trả lời đúng một phần theo tiêu chí minh họa.")
        else:
            output = StructuredGradingOutput(grading_status=ProviderGradingStatus.UNCERTAIN,
                score=None, feedback="Chưa đủ căn cứ để chấm chắc chắn.")
        self.last_result = StructuredGradingProviderResult(output=output, provider="test-only",
            model=request.model, input_tokens=None, output_tokens=None, total_tokens=None,
            provider_preflight_input_tokens=0, latency_ms=0, attempt_count=1,
            provider_request_id=None)
        return self.last_result


async def execute_grading_case(case: GradingCase, annotation: GradingAnnotation,
                               settings: Settings, *, run_id: str,
                               provider=None, provider_mode: str = "FAKE") -> dict[str, Any]:
    """Call the production LLMGradingService with only its provider replaced."""
    provider = provider or DeterministicGradingProvider(case.semantic_class.value)
    observed_provider = ObservingGradingProvider(provider, provider_mode=provider_mode)
    _, request_sha = grading_request_identity(case, settings)
    started = time.perf_counter()
    result: dict[str, Any] = {"execution_id": str(uuid4()), "run_id": run_id,
        "case_id": case.case_id, "split": case.split.value, "question_type": case.question_type,
        "semantic_class": case.semantic_class.value, "max_points": case.max_points,
        "production_input_metadata": case.production_input_metadata, "provider_mode": provider_mode,
        "request_sha256": request_sha, "provider_response_sha256": None,
        "parsed_result_sha256": None,
        "grading_status": None, "score": None, "is_correct": None,
        "normalized_state": None, "feedback": None, "technical_status": "SUCCESS",
        "technical_error_code": None, "provider": getattr(provider, "provider_name", "test-only"), "model": settings.llm_model,
        "provider_request_id": None, "provider_diagnostics": None,
        "latency_ms": None, "usage": None, "replay_origin": None,
        "annotation_review_status": annotation.review_status,
        "human_normalized_state": None, "agreement": None,
        "false_confident": None, "over_abstention": None}
    try:
        grade = await LLMGradingService(observed_provider, settings).grade(
            question={"type": case.question_type, "prompt": case.question_content,
                      "reference_answer": case.reference_answer, "rubric": case.rubric,
                      "points": case.max_points}, answer={"text": case.learner_answer})
        state = normalize_result(grade.grading_status, grade.score, case.max_points, grade.is_correct)
        result.update(grading_status=grade.grading_status, score=grade.score,
                      is_correct=grade.is_correct, normalized_state=state.value,
                      feedback=grade.feedback)
        raw = getattr(observed_provider, "last_result", None)
        result["provider_diagnostics"] = observed_provider.safe_metadata
        if raw is not None:
            parsed_result_sha256 = hashlib.sha256(canonical_json(raw.output.model_dump(mode="json"))).hexdigest()
            result["provider_response_sha256"] = parsed_result_sha256
            result["parsed_result_sha256"] = parsed_result_sha256
            result["usage"] = {"input_tokens": raw.input_tokens, "output_tokens": raw.output_tokens,
                               "total_tokens": raw.total_tokens}
            result["latency_ms"] = raw.latency_ms
            result["provider"] = raw.provider
            result["model"] = raw.model
            result["provider_request_id"] = observed_provider.safe_metadata.get("provider_request_id")
        replay_record = observed_provider.replay_record
        if replay_record is not None:
            result["provider_response_sha256"] = replay_record.response_sha256
            result["parsed_result_sha256"] = replay_record.parsed_result_sha256
            result["replay_origin"] = {"execution_mode": replay_record.origin_execution_mode,
                                        "run_id": replay_record.origin_run_id}
        result["latency_ms"] = result["latency_ms"] if result["latency_ms"] is not None else int((time.perf_counter()-started)*1000)
        if annotation.review_status in {"NEEDS_ADJUDICATION", "HUMAN_APPROVED"}:
            validate_human_annotation(annotation, case)
            result["human_normalized_state"] = annotation.normalized_state.value
            result["agreement"] = result["normalized_state"] == annotation.normalized_state.value
            result["over_abstention"] = annotation.expected_grading_status == "GRADED" and grade.grading_status == "UNCERTAIN"
            result["false_confident"] = ((annotation.expected_grading_status == "UNCERTAIN" and grade.grading_status == "GRADED")
                or (annotation.expected_grading_status == "GRADED" and grade.grading_status == "GRADED"
                    and result["normalized_state"] != annotation.normalized_state.value))
    except GradingUnavailable:
        if observed_provider.last_error_code:
            observed_provider.safe_metadata = {**observed_provider.safe_metadata,
                                               "error_code": observed_provider.last_error_code}
        result.update(technical_status="TECHNICAL_FAILURE", technical_error_code=
                      observed_provider.last_error_code or "AI_GRADING_PROVIDER_UNAVAILABLE",
                      provider_diagnostics=observed_provider.safe_metadata,
                      latency_ms=int((time.perf_counter()-started)*1000))
        result["provider_request_id"] = observed_provider.safe_metadata.get("provider_request_id")
    except (ValueError, TypeError) as exc:
        # Validation defects are kept distinct from semantic abstention.
        result.update(technical_status="TECHNICAL_FAILURE", technical_error_code=
                      observed_provider.last_error_code or str(exc),
                      grading_status=None, score=None, is_correct=None, normalized_state=None,
                      feedback=None, latency_ms=int((time.perf_counter()-started)*1000))
    return result


def build_grading_summary(rows: list[dict], *, execution_mode: str = "OFFLINE_TEST") -> dict:
    annotations = Counter(row["annotation_review_status"] for row in rows)
    eligible = [row for row in rows if row["annotation_review_status"] == "HUMAN_APPROVED"
                and row["technical_status"] == "SUCCESS" and row["grading_status"] in {"GRADED", "UNCERTAIN"}]
    failures = Counter(row.get("technical_error_code") or "UNCLASSIFIED_TECHNICAL_FAILURE"
                       for row in rows if row["technical_status"] == "TECHNICAL_FAILURE")
    n = len(eligible)
    agreement = sum(row["agreement"] is True for row in eligible)
    false_confident = sum(row["false_confident"] is True for row in eligible)
    over_abstention = sum(row["over_abstention"] is True for row in eligible)
    uncertain = sum(row["grading_status"] == "UNCERTAIN" for row in eligible)
    state_names = [state.value for state in NormalizedState]
    matrix = {human: {model: 0 for model in state_names} for human in state_names}
    for row in eligible:
        matrix[row["human_normalized_state"]][row["normalized_state"]] += 1
    group_rates = {}
    for field in ("question_type", "semantic_class"):
        groups = sorted({row[field] for row in eligible})
        group_rates[field] = {group: {"count": sum(row[field] == group for row in eligible),
            "agreement_count": sum(row[field] == group and row["agreement"] is True for row in eligible),
            "agreement_rate": (sum(row[field] == group and row["agreement"] is True for row in eligible)
                / sum(row[field] == group for row in eligible)) if any(row[field] == group for row in eligible) else None}
            for group in groups}
    return {"planned_case_count": len(rows), "executed_case_count": len(rows),
        "technical_failure_count": sum(row["technical_status"] == "TECHNICAL_FAILURE" for row in rows),
        "technical_failure_rate": (sum(row["technical_status"] == "TECHNICAL_FAILURE" for row in rows)/len(rows)) if rows else None,
        "technical_failures_by_code": dict(sorted(failures.items())),
        "human_approved_count": annotations["HUMAN_APPROVED"], "draft_count": annotations["DRAFT"],
        "needs_adjudication_count": annotations["NEEDS_ADJUDICATION"],
        "semantic_denominator_count": n, "agreement_count": agreement,
        "agreement_rate": agreement/n if n else None, "launch_target": 0.95,
        "launch_target_status": "OFFLINE_NOT_OFFICIAL" if execution_mode == "OFFLINE_TEST" else ("UNAVAILABLE" if not n else "PASS" if agreement/n >= .95 else "FAIL"),
        "false_confident_count": false_confident, "false_confident_rate": false_confident/n if n else None,
        "over_abstention_count": over_abstention, "over_abstention_rate": over_abstention/n if n else None,
        "model_uncertainty_count": uncertain, "model_uncertainty_rate": uncertain/n if n else None,
        "agreement_by_question_type": group_rates["question_type"],
        "agreement_by_semantic_class": group_rates["semantic_class"],
        "normalized_state_confusion_matrix": matrix,
        # Summary metrics are not eligibility evidence. The complete-coverage gate lives
        # in eligibility.grading_official_eligibility and consumes actual artifacts.
        "official_eligible": False,
        "official_eligibility_requires_complete_coverage": True,
        "runtime_api_calls": 0 if execution_mode != "OFFICIAL_RUNTIME" else None}
