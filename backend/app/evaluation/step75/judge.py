from __future__ import annotations

import json
from time import perf_counter
from typing import Protocol

from openai import AsyncOpenAI

from app.core.config import Settings, get_settings

from .contracts import (DIMENSIONS, JUDGE_CRITICAL_FAILURES, JUDGE_PROMPT_VERSION,
                       JUDGE_SCHEMA_VERSION, RUBRIC_VERSION, E2EJudgeResult)

JUDGE_MODEL = "gpt-5.4-2026-03-05"


def expected_request_identity() -> dict:
    return {"api": "responses", "model": JUDGE_MODEL, "reasoning_effort": "none",
            "temperature": 0, "max_output_tokens": 1600,
            "structured_output": True, "tools": []}


def judge_json_schema() -> dict:
    score = {"type": "object", "additionalProperties": False,
             "required": ["score", "rationale"],
             "properties": {"score": {"type": "integer", "enum": [0, 1, 2]},
                            "rationale": {"type": "string"}}}
    claim = {"type": "object", "additionalProperties": False,
             "required": ["claim_id", "claim_text", "requires_grounding", "cited_labels",
                          "supporting_labels", "verdict", "concise_rationale"],
             "properties": {"claim_id": {"type": "string"}, "claim_text": {"type": "string"},
                            "requires_grounding": {"type": "boolean"},
                            "cited_labels": {"type": "array", "items": {"type": "string"}},
                            "supporting_labels": {"type": "array", "items": {"type": "string"}},
                            "verdict": {"type": "string", "enum": ["SUPPORTED", "UNSUPPORTED", "CONTRADICTED"]},
                            "concise_rationale": {"type": "string"}}}
    context = {"type": "object", "additionalProperties": False,
               "required": ["material_violation", "memory_used_as_evidence",
                            "historical_citation_label_leak", "current_evidence_overridden_by_history",
                            "concise_rationale"],
               "properties": {name: {"type": "boolean"} for name in (
                   "material_violation", "memory_used_as_evidence", "historical_citation_label_leak",
                   "current_evidence_overridden_by_history")} | {"concise_rationale": {"type": "string"}}}
    return {"type": "object", "additionalProperties": False,
            "required": ["schema_version", "case_id", "repeat_index", "generation_dimension_scores",
                         "claims", "context_adherence", "semantic_critical_failures",
                         "concise_overall_rationale"],
            "properties": {"schema_version": {"type": "string", "enum": [JUDGE_SCHEMA_VERSION]},
                           "case_id": {"type": "string"}, "repeat_index": {"type": "integer"},
                           "generation_dimension_scores": {
                               "type": "object", "additionalProperties": False,
                               "required": list(DIMENSIONS),
                               "properties": {key: score for key in DIMENSIONS}},
                           "claims": {"type": "array", "items": claim}, "context_adherence": context,
                           "semantic_critical_failures": {"type": "array", "items": {
                               "type": "string", "enum": list(JUDGE_CRITICAL_FAILURES)}},
                           "concise_overall_rationale": {"type": "string"}}}


JUDGE_INSTRUCTIONS = """Evaluate the supplied Lesson Chat answer. Score the five generation dimensions independently on 0/1/2; no numeric pass threshold exists. expected_information is primary correctness/completeness ground truth. Evaluate grounding against actual current evidence only; memory is context, not evidence. Outside facts unsupported by current evidence remain unsupported. Use only current source-map labels for citations; historical citation markers cannot support current claims. Identify material factual/instructional claims, classify each SUPPORTED, UNSUPPORTED, or CONTRADICTED, and mark whether each requires grounding. Detect material context adherence violations. Do not evaluate retrieval tier selection or fallback policy. Return concise rationale only and do not reveal chain-of-thought."""


def build_judge_payload(case: dict, trace: dict) -> dict:
    """Build judge input without expected tier/behavior/scope or human annotations."""
    payload = {
        "case_id": case["case_id"], "repeat_index": trace["repeat_index"],
        "question": case["question"], "expected_information": case["expected_information"],
        "actual_current_evidence": trace.get("selected_evidence", []),
        "current_source_map": trace.get("prompt", {}).get("source_map_snapshot", {}),
        "validated_current_citations": trace.get("citation_validation", {}).get("validated_citations", []),
        "generated_answer": trace.get("generation", {}).get("answer"),
        "generation_rubrics": {"version": RUBRIC_VERSION, "dimensions": list(DIMENSIONS)},
        "citation_context_rubric": "lesson-chat-citation-semantics/v1",
        "critical_semantic_failure_definitions": list(JUDGE_CRITICAL_FAILURES),
    }
    if case.get("reference_answer"):
        payload["reference_answer"] = case["reference_answer"]
    if case.get("learning_context"):
        payload["learning_context"] = case["learning_context"]
    memory = trace.get("memory", {})
    if memory.get("sanitized_context"):
        payload["sanitized_conversation_memory"] = memory["sanitized_context"]
    return payload


class Judge(Protocol):
    async def evaluate(self, payload: dict, *, case_id: str, repeat_index: int,
                       current_citation_labels: set[str], source_map_labels: set[str]) -> E2EJudgeResult: ...


class JudgeTechnicalFailure(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class OpenAIResponsesE2EJudge:
    """D-100 adapter; available for runtime readiness but never called offline."""

    def __init__(self, settings: Settings | None = None, *, client=None):
        self.settings = settings or get_settings()
        self.client = client
        self.last_request_identity: dict | None = None

    def _client(self):
        if self.client is None:
            key = self.settings.llm_api_key
            if key is None or not key.get_secret_value().strip():
                raise JudgeTechnicalFailure("JUDGE_PROVIDER_NOT_CONFIGURED")
            self.client = AsyncOpenAI(api_key=key.get_secret_value(), max_retries=0)
        return self.client

    async def evaluate(self, payload: dict, *, case_id: str, repeat_index: int,
                       current_citation_labels: set[str], source_map_labels: set[str]) -> E2EJudgeResult:
        if payload.get("case_id") != case_id or payload.get("repeat_index") != repeat_index:
            raise JudgeTechnicalFailure("JUDGE_REQUEST_IDENTITY_MISMATCH")
        self.last_request_identity = expected_request_identity()
        try:
            started = perf_counter()
            response = await self._client().responses.create(
                model=JUDGE_MODEL, instructions=JUDGE_INSTRUCTIONS,
                input=json.dumps({"prompt_version": JUDGE_PROMPT_VERSION,
                                  "rubric_version": RUBRIC_VERSION, **payload},
                                 ensure_ascii=False, sort_keys=True),
                reasoning={"effort": "none"}, temperature=0, max_output_tokens=1600,
                truncation="disabled", store=False, stream=False,
                text={"format": {"type": "json_schema", "name": "step75_e2e_judge_result",
                                 "strict": True, "schema": judge_json_schema()}},
            )
            if getattr(response, "status", None) != "completed" or getattr(response, "model", None) != JUDGE_MODEL:
                raise JudgeTechnicalFailure("JUDGE_PROVIDER_INCOMPLETE")
            output = getattr(response, "output_text", None)
            if not isinstance(output, str) or not output.strip():
                raise JudgeTechnicalFailure("JUDGE_INVALID_RESPONSE")
            result = E2EJudgeResult.model_validate_json(output)
            result.validate_labels(case_id=case_id, repeat_index=repeat_index,
                                   current_citation_labels=current_citation_labels,
                                   source_map_labels=source_map_labels)
            # Avoid returning/storing latency or provider text here: caller owns safe trace fields.
            _ = round((perf_counter() - started) * 1000)
            return result
        except JudgeTechnicalFailure:
            raise
        except Exception as exc:
            code = "JUDGE_INVALID_RESPONSE" if isinstance(exc, (ValueError, TypeError)) else "JUDGE_PROVIDER_FAILURE"
            raise JudgeTechnicalFailure(code) from None
