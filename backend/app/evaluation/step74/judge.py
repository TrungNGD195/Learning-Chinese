from __future__ import annotations

import json
from time import perf_counter
from typing import Protocol

from openai import AsyncOpenAI

from app.core.config import Settings, get_settings

from .contracts import (
    CRITICAL_FAILURES,
    DIMENSIONS,
    JudgeCallResult,
    JUDGE_MODEL,
    JUDGE_PROMPT_VERSION,
    GenerationJudgeResult,
    JudgeTechnicalFailure,
)
from .rubrics import JUDGE_INSTRUCTIONS, rubrics_for_prompt


def expected_judge_request_identity() -> dict:
    return {
        "model": JUDGE_MODEL,
        "reasoning_effort": "none",
        "temperature": 0,
        "max_output_tokens": 1600,
        "structured_output": True,
        "tools": [],
    }


def judge_json_schema() -> dict:
    score = {
        "type": "object", "additionalProperties": False,
        "required": ["score", "rationale"],
        "properties": {"score": {"type": "integer", "enum": [0, 1, 2]},
                       "rationale": {"type": "string"}},
    }
    return {
        "type": "object", "additionalProperties": False,
        "required": ["schema_version", "case_id", "dimension_scores", "claims",
                     "critical_failures", "concise_overall_rationale"],
        "properties": {
            "schema_version": {"type": "string", "enum": ["1.0.0"]},
            "case_id": {"type": "string"},
            "dimension_scores": {
                "type": "object", "additionalProperties": False,
                "required": list(DIMENSIONS),
                "properties": {key: score for key in DIMENSIONS},
            },
            "claims": {"type": "array", "items": {
                "type": "object", "additionalProperties": False,
                "required": ["claim_id", "claim_text", "verdict", "supporting_evidence_ids", "concise_rationale"],
                "properties": {
                    "claim_id": {"type": "string"}, "claim_text": {"type": "string"},
                    "verdict": {"type": "string", "enum": ["SUPPORTED", "UNSUPPORTED", "CONTRADICTED"]},
                    "supporting_evidence_ids": {"type": "array", "items": {"type": "string"}},
                    "concise_rationale": {"type": "string"},
                },
            }},
            "critical_failures": {"type": "array", "items": {"type": "string", "enum": list(CRITICAL_FAILURES)}},
            "concise_overall_rationale": {"type": "string"},
        },
    }


class Judge(Protocol):
    async def evaluate(self, case: dict, generated_answer: str, evidence: list[dict]) -> JudgeCallResult: ...


class OpenAIResponsesGenerationJudge:
    """D-100 adapter; offline tests inject a fake Responses client."""

    def __init__(self, settings: Settings | None = None, *, client=None):
        self.settings = settings or get_settings()
        self._client = client
        self.last_request_identity: dict | None = None

    def _get_client(self):
        if self._client is None:
            secret = self.settings.llm_api_key
            if secret is None or not secret.get_secret_value().strip():
                raise JudgeTechnicalFailure("JUDGE_PROVIDER_NOT_CONFIGURED")
            self._client = AsyncOpenAI(api_key=secret.get_secret_value(), max_retries=0)
        return self._client

    async def evaluate(self, case: dict, generated_answer: str, evidence: list[dict]) -> GenerationJudgeResult:
        user_payload = {
            "case_id": case["case_id"], "question": case["question"],
            "expected_information": case["expected_information"],
            "fixed_evidence": [{"evidence_ids": item["evidence_ids"],
                                "content": item["llm_visible_content"]} for item in evidence],
            "generated_answer": generated_answer,
            "rubrics": rubrics_for_prompt(),
        }
        if case.get("reference_answer"):
            user_payload["reference_answer"] = case["reference_answer"]
        self.last_request_identity = expected_judge_request_identity()
        try:
            started = perf_counter()
            response = await self._get_client().responses.create(
                model=JUDGE_MODEL,
                instructions=JUDGE_INSTRUCTIONS,
                input=json.dumps(user_payload, ensure_ascii=False, sort_keys=True),
                reasoning={"effort": "none"}, temperature=0,
                max_output_tokens=1600, truncation="disabled", store=False, stream=False,
                text={"format": {"type": "json_schema", "name": "generation_judge_result",
                                 "strict": True, "schema": judge_json_schema()}},
            )
            if getattr(response, "status", None) != "completed":
                raise JudgeTechnicalFailure("JUDGE_PROVIDER_INCOMPLETE")
            if getattr(response, "model", None) != JUDGE_MODEL:
                raise JudgeTechnicalFailure("JUDGE_MODEL_IDENTITY_MISMATCH")
            output = getattr(response, "output_text", None)
            if not isinstance(output, str) or not output.strip():
                raise JudgeTechnicalFailure("JUDGE_INVALID_RESPONSE")
            result = GenerationJudgeResult.model_validate_json(output)
            result.validate_evidence_ids(case["case_id"], {
                evidence_id for item in evidence for evidence_id in item["evidence_ids"]
            })
            usage = getattr(response, "usage", None)
            token_usage = {
                "input_tokens": getattr(usage, "input_tokens", None) if usage is not None else None,
                "output_tokens": getattr(usage, "output_tokens", None) if usage is not None else None,
                "total_tokens": getattr(usage, "total_tokens", None) if usage is not None else None,
            }
            request_id = getattr(response, "_request_id", None)
            if not isinstance(request_id, str):
                request_id = None
            return JudgeCallResult(result, round((perf_counter() - started) * 1000), 1, request_id, token_usage)
        except JudgeTechnicalFailure:
            raise
        except Exception as exc:
            # Never retain provider messages which might echo request material.
            code = "JUDGE_INVALID_RESPONSE" if isinstance(exc, (ValueError, TypeError)) else "JUDGE_PROVIDER_FAILURE"
            raise JudgeTechnicalFailure(code) from None
