from __future__ import annotations

import asyncio
import copy
import logging
import random
from time import perf_counter
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    BadRequestError,
    PermissionDeniedError,
    RateLimitError,
)
from openai.lib._parsing._responses import type_to_text_format_param

from app.ai.grading.errors import (
    AI_GRADING_AUTHENTICATION_FAILED,
    AI_GRADING_INPUT_LIMIT_EXCEEDED,
    AI_GRADING_INVALID_RESPONSE,
    AI_GRADING_PERMISSION_DENIED,
    AI_GRADING_PROVIDER_NOT_CONFIGURED,
    AI_GRADING_PROVIDER_UNAVAILABLE,
    AI_GRADING_RATE_LIMITED,
    AI_GRADING_REQUEST_INVALID,
    AI_GRADING_SCHEMA_INVALID,
    AI_GRADING_TIMEOUT,
    StructuredGradingProviderError,
)
from app.ai.grading.prompt import GRADING_PROMPT_VERSION
from app.ai.grading.schemas import (
    StructuredGradingOutput,
    StructuredGradingProviderResult,
    StructuredGradingRequest,
)
from app.ai.llm.retry import transient_backoff
from app.core.config import Settings

logger = logging.getLogger("app.ai.grading")
_CONTEXT_LIMIT_CODES = {
    "context_length_exceeded",
    "input_tokens_exceeded",
    "max_input_tokens_exceeded",
}


def _is_context_limit(exc: BaseException) -> bool:
    code = getattr(exc, "code", None)
    if isinstance(code, str) and code.lower() in _CONTEXT_LIMIT_CODES:
        return True
    body = getattr(exc, "body", None)
    if not isinstance(body, dict):
        return False
    candidates = [body.get("code")]
    nested = body.get("error")
    if isinstance(nested, dict):
        candidates.append(nested.get("code"))
    return any(isinstance(value, str) and value.lower() in _CONTEXT_LIMIT_CODES for value in candidates)


def _provider_error(exc: BaseException) -> tuple[str, bool]:
    if isinstance(exc, APITimeoutError):
        return AI_GRADING_TIMEOUT, True
    if isinstance(exc, APIConnectionError):
        return AI_GRADING_PROVIDER_UNAVAILABLE, True
    if isinstance(exc, RateLimitError):
        return AI_GRADING_RATE_LIMITED, True
    if isinstance(exc, AuthenticationError):
        return AI_GRADING_AUTHENTICATION_FAILED, False
    if isinstance(exc, PermissionDeniedError):
        return AI_GRADING_PERMISSION_DENIED, False
    if isinstance(exc, BadRequestError):
        return (AI_GRADING_INPUT_LIMIT_EXCEEDED if _is_context_limit(exc) else AI_GRADING_REQUEST_INVALID), False
    if isinstance(exc, APIStatusError):
        status = getattr(exc, "status_code", None)
        if status == 429:
            return AI_GRADING_RATE_LIMITED, True
        if isinstance(status, int) and 500 <= status <= 599:
            return AI_GRADING_PROVIDER_UNAVAILABLE, True
        if status == 401:
            return AI_GRADING_AUTHENTICATION_FAILED, False
        if status == 403:
            return AI_GRADING_PERMISSION_DENIED, False
        if status == 400:
            return (AI_GRADING_INPUT_LIMIT_EXCEEDED if _is_context_limit(exc) else AI_GRADING_REQUEST_INVALID), False
    return AI_GRADING_SCHEMA_INVALID, False


class OpenAIResponsesGradingProvider:
    """Stateless OpenAI Responses structured-output adapter for assessment grading."""

    def __init__(
        self,
        settings: Settings,
        *,
        client: Any | None = None,
        sleep=asyncio.sleep,
        uniform=random.uniform,
    ) -> None:
        self.settings = settings
        self._client = client
        self._sleep = sleep
        self._uniform = uniform

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        key = self.settings.llm_api_key
        if key is None or not key.get_secret_value().strip():
            raise StructuredGradingProviderError(AI_GRADING_PROVIDER_NOT_CONFIGURED)
        self._client = AsyncOpenAI(
            api_key=key.get_secret_value(),
            timeout=self.settings.llm_request_timeout_seconds,
            max_retries=0,
        )
        return self._client

    @staticmethod
    def _structured_text_config() -> dict[str, Any]:
        # Match the exact schema transformation used by responses.parse(text_format=...).
        # The Responses input-token endpoint accepts this effective format as `text`.
        return {"format": copy.deepcopy(type_to_text_format_param(StructuredGradingOutput))}

    def _validate_request(self, request: StructuredGradingRequest) -> None:
        if (
            not isinstance(request, StructuredGradingRequest)
            or not isinstance(request.question_type, str)
            or request.question_type not in {"translate_vi_zh", "translate_zh_vi", "sentence_writing"}
            or not request.system_content.strip()
            or not request.user_content.strip()
            or request.model != self.settings.llm_model
            or request.temperature != self.settings.llm_temperature
            or request.reasoning_effort != self.settings.llm_reasoning_effort
            or request.max_output_tokens != self.settings.llm_max_output_tokens
            or request.model_input_limit != self.settings.llm_model_input_limit
            or request.request_timeout_seconds != self.settings.llm_request_timeout_seconds
            or request.max_transient_retries != self.settings.llm_max_transient_retries
        ):
            raise StructuredGradingProviderError(AI_GRADING_REQUEST_INVALID)

    async def grade(self, request: StructuredGradingRequest) -> StructuredGradingProviderResult:
        self._validate_request(request)
        client = self._get_client()
        started = perf_counter()
        max_attempts = request.max_transient_retries + 1
        preflight_tokens: int | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                # `text.format` is the same strict schema that `parse` derives from
                # text_format=StructuredGradingOutput; schema tokens count as input.
                format_config = self._structured_text_config()
                count = await client.responses.input_tokens.count(
                    model=request.model,
                    instructions=request.system_content,
                    input=[{"role": "user", "content": request.user_content}],
                    reasoning={"effort": request.reasoning_effort},
                    text=format_config,
                    truncation="disabled",
                    timeout=request.request_timeout_seconds,
                )
                preflight_tokens = getattr(count, "input_tokens", None)
                if type(preflight_tokens) is not int or preflight_tokens < 0:
                    raise StructuredGradingProviderError(AI_GRADING_INVALID_RESPONSE)
                if preflight_tokens + request.max_output_tokens > request.model_input_limit:
                    raise StructuredGradingProviderError(AI_GRADING_INPUT_LIMIT_EXCEEDED)

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
                    text_format=StructuredGradingOutput,
                    timeout=request.request_timeout_seconds,
                )
                if getattr(response, "status", None) != "completed":
                    raise StructuredGradingProviderError(AI_GRADING_INVALID_RESPONSE)
                output = getattr(response, "output_parsed", None)
                if not isinstance(output, StructuredGradingOutput):
                    raise StructuredGradingProviderError(AI_GRADING_SCHEMA_INVALID)
                usage = getattr(response, "usage", None)
                input_tokens = getattr(usage, "input_tokens", None) if usage is not None else None
                output_tokens = getattr(usage, "output_tokens", None) if usage is not None else None
                total_tokens = getattr(usage, "total_tokens", None) if usage is not None else None
                for value in (input_tokens, output_tokens, total_tokens):
                    if value is not None and (type(value) is not int or value < 0):
                        raise StructuredGradingProviderError(AI_GRADING_INVALID_RESPONSE)
                request_id = getattr(response, "_request_id", None)
                if request_id is not None and not isinstance(request_id, str):
                    request_id = None
                result = StructuredGradingProviderResult(
                    output=output,
                    provider="openai",
                    model=request.model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    provider_preflight_input_tokens=preflight_tokens,
                    latency_ms=round((perf_counter() - started) * 1000),
                    attempt_count=attempt,
                    provider_request_id=request_id,
                )
                logger.info("ai_grading_provider_completed", extra={
                    "feature": "ai_grading", "provider": "openai", "model": request.model,
                    "prompt_version": GRADING_PROMPT_VERSION, "question_type": request.question_type,
                    "attempt_count": attempt, "latency_ms": result.latency_ms,
                    "provider_preflight_input_tokens": preflight_tokens,
                    "provider_usage_input_tokens": input_tokens, "provider_usage_output_tokens": output_tokens,
                    "provider_usage_total_tokens": total_tokens, "provider_request_id": request_id,
                    "error_code": None,
                })
                return result
            except StructuredGradingProviderError as exc:
                code, transient = exc.code, False
            except Exception as exc:
                code, transient = _provider_error(exc)
            if transient and attempt < max_attempts:
                logger.warning("ai_grading_provider_retrying", extra={
                    "feature": "ai_grading", "provider": "openai", "model": request.model,
                    "prompt_version": GRADING_PROMPT_VERSION, "question_type": request.question_type,
                    "attempt_count": attempt, "provider_preflight_input_tokens": preflight_tokens,
                    "error_code": code,
                })
                await transient_backoff(sleep=self._sleep, uniform=self._uniform)
                continue
            logger.warning("ai_grading_provider_failed", extra={
                "feature": "ai_grading", "provider": "openai", "model": request.model,
                "prompt_version": GRADING_PROMPT_VERSION, "question_type": request.question_type,
                "attempt_count": attempt, "latency_ms": round((perf_counter() - started) * 1000),
                "provider_preflight_input_tokens": preflight_tokens, "error_code": code,
            })
            raise StructuredGradingProviderError(code) from None

        raise StructuredGradingProviderError(AI_GRADING_PROVIDER_UNAVAILABLE)
