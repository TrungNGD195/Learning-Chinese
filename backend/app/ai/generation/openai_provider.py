from __future__ import annotations

import asyncio
import copy
import logging
import random
from time import perf_counter
from typing import Any

from openai import (
    APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI,
    AuthenticationError, BadRequestError, PermissionDeniedError, RateLimitError,
)
from openai.lib._parsing._responses import type_to_text_format_param

from app.ai.generation.errors import (
    AI_GENERATION_AUTHENTICATION_FAILED, AI_GENERATION_INPUT_TOO_LARGE,
    AI_GENERATION_INVALID_RESPONSE, AI_GENERATION_PERMISSION_DENIED,
    AI_GENERATION_PROVIDER_NOT_CONFIGURED, AI_GENERATION_PROVIDER_UNAVAILABLE,
    AI_GENERATION_RATE_LIMITED, AI_GENERATION_REQUEST_INVALID,
    AI_GENERATION_SCHEMA_INVALID, AI_GENERATION_TIMEOUT,
    StructuredAssessmentGenerationProviderError,
)
from app.ai.generation.prompt import ASSESSMENT_GENERATION_PROMPT_VERSION
from app.ai.generation.schemas import (
    StructuredAssessmentGenerationOutput,
    StructuredAssessmentGenerationProviderResult,
    StructuredAssessmentGenerationRequest,
)
from app.ai.llm.retry import transient_backoff
from app.core.config import Settings

logger = logging.getLogger("app.ai.generation")
_CONTEXT_LIMIT_CODES = {"context_length_exceeded", "input_tokens_exceeded", "max_input_tokens_exceeded"}


def _is_context_limit(exc: BaseException) -> bool:
    body = getattr(exc, "body", None)
    candidates = [getattr(exc, "code", None)]
    if isinstance(body, dict):
        candidates.append(body.get("code"))
        error = body.get("error")
        if isinstance(error, dict):
            candidates.append(error.get("code"))
    return any(isinstance(value, str) and value.lower() in _CONTEXT_LIMIT_CODES for value in candidates)


def _provider_error(exc: BaseException) -> tuple[str, bool]:
    if isinstance(exc, APITimeoutError):
        return AI_GENERATION_TIMEOUT, True
    if isinstance(exc, APIConnectionError):
        return AI_GENERATION_PROVIDER_UNAVAILABLE, True
    if isinstance(exc, RateLimitError):
        return AI_GENERATION_RATE_LIMITED, True
    if isinstance(exc, AuthenticationError):
        return AI_GENERATION_AUTHENTICATION_FAILED, False
    if isinstance(exc, PermissionDeniedError):
        return AI_GENERATION_PERMISSION_DENIED, False
    if isinstance(exc, BadRequestError):
        return (AI_GENERATION_INPUT_TOO_LARGE if _is_context_limit(exc) else AI_GENERATION_REQUEST_INVALID), False
    if isinstance(exc, APIStatusError):
        status = getattr(exc, "status_code", None)
        if status == 429:
            return AI_GENERATION_RATE_LIMITED, True
        if isinstance(status, int) and 500 <= status <= 599:
            return AI_GENERATION_PROVIDER_UNAVAILABLE, True
        if status == 401:
            return AI_GENERATION_AUTHENTICATION_FAILED, False
        if status == 403:
            return AI_GENERATION_PERMISSION_DENIED, False
        if status == 400:
            return (AI_GENERATION_INPUT_TOO_LARGE if _is_context_limit(exc) else AI_GENERATION_REQUEST_INVALID), False
    return AI_GENERATION_PROVIDER_UNAVAILABLE, False


class OpenAIResponsesAssessmentGenerationProvider:
    """Stateless, strict OpenAI Responses adapter for assessment generation."""

    def __init__(self, settings: Settings, *, client: Any | None = None, sleep=asyncio.sleep, uniform=random.uniform):
        self.settings = settings
        self._client = client
        self._sleep = sleep
        self._uniform = uniform

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        key = self.settings.llm_api_key
        if key is None or not key.get_secret_value().strip():
            raise StructuredAssessmentGenerationProviderError(AI_GENERATION_PROVIDER_NOT_CONFIGURED)
        self._client = AsyncOpenAI(
            api_key=key.get_secret_value(), timeout=self.settings.llm_request_timeout_seconds, max_retries=0
        )
        return self._client

    @staticmethod
    def _structured_text_config() -> dict[str, Any]:
        return {"format": copy.deepcopy(type_to_text_format_param(StructuredAssessmentGenerationOutput))}

    def _validate_request(self, request: StructuredAssessmentGenerationRequest) -> None:
        if (
            not isinstance(request, StructuredAssessmentGenerationRequest)
            or not request.system_content.strip() or not request.user_content.strip()
            or request.model != self.settings.llm_model
            or request.temperature != self.settings.llm_temperature
            or request.max_output_tokens != self.settings.ai_generation_max_output_tokens
            or request.reasoning_effort != self.settings.llm_reasoning_effort
            or request.model_input_limit != self.settings.llm_model_input_limit
            or request.request_timeout_seconds != self.settings.llm_request_timeout_seconds
            or request.max_transient_retries != self.settings.llm_max_transient_retries
            or request.generation_kind not in {"LESSON_EXERCISE", "PERIODIC_TEST"}
            or not 1 <= request.requested_question_count <= self.settings.ai_generation_max_questions
            or request.difficulty not in {"EASY", "MEDIUM", "HARD"}
            or not request.allowed_types
        ):
            raise StructuredAssessmentGenerationProviderError(AI_GENERATION_REQUEST_INVALID)

    async def generate(self, request: StructuredAssessmentGenerationRequest) -> StructuredAssessmentGenerationProviderResult:
        self._validate_request(request)
        client = self._get_client()
        started = perf_counter()
        max_attempts = request.max_transient_retries + 1
        for attempt in range(1, max_attempts + 1):
            preflight_tokens = None
            try:
                text_config = self._structured_text_config()
                count = await client.responses.input_tokens.count(
                    model=request.model,
                    instructions=request.system_content,
                    input=[{"role": "user", "content": request.user_content}],
                    reasoning={"effort": request.reasoning_effort},
                    text=copy.deepcopy(text_config),
                    truncation="disabled",
                    timeout=request.request_timeout_seconds,
                )
                preflight_tokens = getattr(count, "input_tokens", None)
                if type(preflight_tokens) is not int or preflight_tokens < 0:
                    raise StructuredAssessmentGenerationProviderError(AI_GENERATION_INVALID_RESPONSE)
                if preflight_tokens + request.max_output_tokens > request.model_input_limit:
                    raise StructuredAssessmentGenerationProviderError(AI_GENERATION_INPUT_TOO_LARGE)

                response = await client.responses.parse(
                    model=request.model,
                    instructions=request.system_content,
                    input=[{"role": "user", "content": request.user_content}],
                    reasoning={"effort": request.reasoning_effort},
                    temperature=request.temperature,
                    max_output_tokens=request.max_output_tokens,
                    truncation="disabled",
                    store=False,
                    stream=False,
                    text_format=StructuredAssessmentGenerationOutput,
                    timeout=request.request_timeout_seconds,
                )
                if getattr(response, "status", None) != "completed":
                    raise StructuredAssessmentGenerationProviderError(AI_GENERATION_INVALID_RESPONSE)
                output = getattr(response, "output_parsed", None)
                if not isinstance(output, StructuredAssessmentGenerationOutput):
                    raise StructuredAssessmentGenerationProviderError(AI_GENERATION_SCHEMA_INVALID)
                usage = getattr(response, "usage", None)
                values = [getattr(usage, field, None) if usage is not None else None for field in ("input_tokens", "output_tokens", "total_tokens")]
                if any(value is not None and (type(value) is not int or value < 0) for value in values):
                    raise StructuredAssessmentGenerationProviderError(AI_GENERATION_INVALID_RESPONSE)
                request_id = getattr(response, "_request_id", None)
                if not isinstance(request_id, str):
                    request_id = None
                result = StructuredAssessmentGenerationProviderResult(
                    output=output, provider="openai", model=request.model,
                    input_tokens=values[0], output_tokens=values[1], total_tokens=values[2],
                    provider_preflight_input_tokens=preflight_tokens,
                    latency_ms=round((perf_counter() - started) * 1000),
                    attempt_count=attempt, provider_request_id=request_id,
                )
                logger.info("ai_assessment_generation_provider_completed", extra={
                    "feature": "ai_assessment_generation", "provider": "openai", "model": request.model,
                    "prompt_version": ASSESSMENT_GENERATION_PROMPT_VERSION,
                    "generation_kind": request.generation_kind,
                    "requested_question_count": request.requested_question_count,
                    "allowed_types": request.allowed_types, "difficulty": request.difficulty,
                    "attempt_count": attempt, "latency_ms": result.latency_ms,
                    "provider_preflight_input_tokens": preflight_tokens,
                    "provider_usage_input_tokens": values[0], "provider_usage_output_tokens": values[1],
                    "provider_usage_total_tokens": values[2], "provider_request_id": request_id,
                    "error_code": None,
                })
                return result
            except StructuredAssessmentGenerationProviderError as exc:
                code, transient = exc.code, False
            except Exception as exc:
                code, transient = _provider_error(exc)
            if transient and attempt < max_attempts:
                logger.warning("ai_assessment_generation_provider_retrying", extra={
                    "feature": "ai_assessment_generation", "provider": "openai", "model": request.model,
                    "prompt_version": ASSESSMENT_GENERATION_PROMPT_VERSION,
                    "generation_kind": request.generation_kind, "requested_question_count": request.requested_question_count,
                    "allowed_types": request.allowed_types, "difficulty": request.difficulty,
                    "attempt_count": attempt, "provider_preflight_input_tokens": preflight_tokens, "error_code": code,
                })
                await transient_backoff(sleep=self._sleep, uniform=self._uniform)
                continue
            logger.warning("ai_assessment_generation_provider_failed", extra={
                "feature": "ai_assessment_generation", "provider": "openai", "model": request.model,
                "prompt_version": ASSESSMENT_GENERATION_PROMPT_VERSION,
                "generation_kind": request.generation_kind, "requested_question_count": request.requested_question_count,
                "allowed_types": request.allowed_types, "difficulty": request.difficulty,
                "attempt_count": attempt, "latency_ms": round((perf_counter() - started) * 1000),
                "provider_preflight_input_tokens": preflight_tokens, "error_code": code,
            })
            raise StructuredAssessmentGenerationProviderError(code) from None
        raise StructuredAssessmentGenerationProviderError(AI_GENERATION_PROVIDER_UNAVAILABLE)
