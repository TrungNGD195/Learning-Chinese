from __future__ import annotations

import logging
from math import isfinite
from typing import Any

from app.ai.grading.errors import (
    AI_GRADING_INVALID_RESPONSE,
    StructuredGradingProviderError,
)
from app.ai.grading.prompt import GRADING_PROMPT_VERSION, build_grading_prompt
from app.ai.grading.provider import StructuredGradingProvider
from app.ai.grading.schemas import (
    ProviderGradingStatus,
    StructuredGradingOutput,
    StructuredGradingRequest,
    StructuredGradingProviderResult,
)
from app.core.config import Settings
from app.exercise.grading import GradeResult, GradingUnavailable

logger = logging.getLogger("app.ai.grading")
_FREE_FORM_TYPES = frozenset({"translate_vi_zh", "translate_zh_vi", "sentence_writing"})


class LLMGradingService:
    """Application AIGrader implementation; assessment pass/progress stays elsewhere."""

    def __init__(self, provider: StructuredGradingProvider, settings: Settings) -> None:
        self.provider = provider
        self.settings = settings

    @staticmethod
    def _grading_material(question: dict, answer: dict) -> tuple[str, str, str | None, str | None, float, str]:
        try:
            question_type = question["type"]
            prompt = question["prompt"]
            reference_answer = question["reference_answer"]
            rubric = question["rubric"]
            points = question["points"]
            learner_answer = answer["text"]
        except (KeyError, TypeError):
            raise GradingUnavailable from None
        if (
            not isinstance(question_type, str) or question_type not in _FREE_FORM_TYPES
            or not isinstance(prompt, str) or not prompt.strip()
            or (reference_answer is not None and not isinstance(reference_answer, str))
            or (rubric is not None and not isinstance(rubric, str))
            or isinstance(points, bool) or not isinstance(points, (int, float))
            or not isfinite(float(points)) or float(points) <= 0
            or not isinstance(answer, dict)
            or set(answer) != {"text"}
            or not isinstance(learner_answer, str)
        ):
            raise GradingUnavailable
        return question_type, prompt, reference_answer, rubric, float(points), learner_answer

    @staticmethod
    def _map_output(output: StructuredGradingOutput, max_points: float) -> GradeResult:
        if not isinstance(output, StructuredGradingOutput):
            raise ValueError("provider output has an invalid type")
        feedback = output.feedback.strip() if isinstance(output.feedback, str) else ""
        if not feedback:
            raise ValueError("feedback is blank")
        if output.grading_status is ProviderGradingStatus.GRADED:
            score = output.score
            if (
                isinstance(score, bool) or not isinstance(score, (int, float))
                or not isfinite(float(score)) or not 0 <= float(score) <= max_points
            ):
                raise ValueError("graded score is invalid")
            normalized_score = float(score)
            return GradeResult("GRADED", normalized_score, normalized_score == float(max_points), feedback)
        if output.grading_status is ProviderGradingStatus.UNCERTAIN and output.score is None:
            return GradeResult("UNCERTAIN", None, None, feedback)
        raise ValueError("grading status and score are inconsistent")

    async def grade(self, *, question: dict, answer: dict) -> GradeResult:
        material = self._grading_material(question, answer)
        question_type, prompt, reference_answer, rubric, max_points, learner_answer = material
        system_content, user_content = build_grading_prompt(
            question_type=question_type,
            prompt=prompt,
            reference_answer=reference_answer,
            rubric=rubric,
            max_points=max_points,
            learner_answer=learner_answer,
        )
        request = StructuredGradingRequest(
            question_type=question_type,
            system_content=system_content,
            user_content=user_content,
            model=self.settings.llm_model,
            temperature=self.settings.llm_temperature,
            max_output_tokens=self.settings.llm_max_output_tokens,
            reasoning_effort=self.settings.llm_reasoning_effort,
            model_input_limit=self.settings.llm_model_input_limit,
            request_timeout_seconds=self.settings.llm_request_timeout_seconds,
            max_transient_retries=self.settings.llm_max_transient_retries,
        )
        try:
            provider_result: Any = await self.provider.grade(request)
            if not isinstance(provider_result, StructuredGradingProviderResult):
                raise StructuredGradingProviderError(AI_GRADING_INVALID_RESPONSE)
            result = self._map_output(provider_result.output, max_points)
        except Exception as exc:
            code = exc.code if isinstance(exc, StructuredGradingProviderError) else AI_GRADING_INVALID_RESPONSE
            logger.warning("ai_grading_failed", extra={
                "feature": "ai_grading", "provider": "openai", "model": self.settings.llm_model,
                "prompt_version": GRADING_PROMPT_VERSION, "question_type": question_type,
                "error_code": code,
            })
            raise GradingUnavailable from None
        logger.info("ai_grading_completed", extra={
            "feature": "ai_grading", "provider": provider_result.provider,
            "model": provider_result.model, "prompt_version": GRADING_PROMPT_VERSION,
            "question_type": question_type, "grading_status": result.grading_status,
            "attempt_count": provider_result.attempt_count,
            "latency_ms": provider_result.latency_ms,
            "provider_preflight_input_tokens": provider_result.provider_preflight_input_tokens,
            "provider_usage_input_tokens": provider_result.input_tokens,
            "provider_usage_output_tokens": provider_result.output_tokens,
            "provider_usage_total_tokens": provider_result.total_tokens,
            "provider_request_id": provider_result.provider_request_id,
            "error_code": None,
        })
        return result
