from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
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

from app.ai.llm.errors import (
    EMPTY_LLM_RESPONSE,
    INVALID_LLM_RESPONSE,
    LLM_AUTHENTICATION_FAILED,
    LLM_CONTEXT_LIMIT_EXCEEDED,
    LLM_GENERATION_FAILED,
    LLM_PERMISSION_DENIED,
    LLM_PROVIDER_NOT_CONFIGURED,
    LLM_PROVIDER_UNAVAILABLE,
    LLM_RATE_LIMITED,
    LLM_REQUEST_INVALID,
    LLM_TIMEOUT,
    llm_error,
)
from app.ai.llm.retry import transient_backoff
from app.ai.llm.schemas import LLMGenerationRequest, LLMGenerationResult, LLMRoleMessage
from app.core.config import Settings
from app.core.errors import ApplicationError

logger = logging.getLogger(__name__)

_CONTEXT_LIMIT_CODES = {
    "context_length_exceeded",
    "input_tokens_exceeded",
    "max_input_tokens_exceeded",
}


def _context_limit_error(exc: BaseException) -> bool:
    code = getattr(exc, "code", None)
    if isinstance(code, str) and code.lower() in _CONTEXT_LIMIT_CODES:
        return True

    body = getattr(exc, "body", None)
    if not isinstance(body, dict):
        return False

    body_code = body.get("code")
    if isinstance(body_code, str) and body_code.lower() in _CONTEXT_LIMIT_CODES:
        return True

    nested = body.get("error")
    nested_code = nested.get("code") if isinstance(nested, dict) else None
    return isinstance(nested_code, str) and nested_code.lower() in _CONTEXT_LIMIT_CODES


def _provider_error(exc: BaseException) -> tuple[str, bool]:
    if isinstance(exc, APITimeoutError):
        return LLM_TIMEOUT, True
    if isinstance(exc, APIConnectionError):
        return LLM_PROVIDER_UNAVAILABLE, True
    if isinstance(exc, RateLimitError):
        return LLM_RATE_LIMITED, True
    if isinstance(exc, AuthenticationError):
        return LLM_AUTHENTICATION_FAILED, False
    if isinstance(exc, PermissionDeniedError):
        return LLM_PERMISSION_DENIED, False
    if isinstance(exc, BadRequestError):
        return (LLM_CONTEXT_LIMIT_EXCEEDED if _context_limit_error(exc) else LLM_REQUEST_INVALID), False
    if isinstance(exc, APIStatusError):
        status = getattr(exc, "status_code", None)
        if status == 429:
            return LLM_RATE_LIMITED, True
        if isinstance(status, int) and 500 <= status <= 599:
            return LLM_PROVIDER_UNAVAILABLE, True
        if status == 401:
            return LLM_AUTHENTICATION_FAILED, False
        if status == 403:
            return LLM_PERMISSION_DENIED, False
        if status == 400:
            return (LLM_CONTEXT_LIMIT_EXCEEDED if _context_limit_error(exc) else LLM_REQUEST_INVALID), False
    return LLM_GENERATION_FAILED, False


class OpenAILLMProvider:
    """Stateless OpenAI Responses adapter with one application-owned retry."""

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
        if self.settings.llm_api_key is None or not self.settings.llm_api_key.get_secret_value().strip():
            raise llm_error(LLM_PROVIDER_NOT_CONFIGURED)
        self._client = AsyncOpenAI(
            api_key=self.settings.llm_api_key.get_secret_value(),
            timeout=self.settings.llm_request_timeout_seconds,
            max_retries=0,
        )
        return self._client

    @staticmethod
    def _response_failure(response: Any) -> tuple[str, str | None]:
        status = getattr(response, "status", None)
        if status == "completed":
            output = getattr(response, "output_text", None)
            if not isinstance(output, str):
                return INVALID_LLM_RESPONSE, None
            if not output.strip():
                return EMPTY_LLM_RESPONSE, None
            return "", None
        if status == "incomplete":
            details = getattr(response, "incomplete_details", None)
            reason = getattr(details, "reason", None) if details is not None else None
            safe_reason = reason if reason in {"max_output_tokens", "content_filter"} else None
            return INVALID_LLM_RESPONSE, safe_reason
        if status == "failed":
            return LLM_GENERATION_FAILED, None
        return INVALID_LLM_RESPONSE, None

    async def generate(self, request: LLMGenerationRequest) -> LLMGenerationResult:
        return await self._generate(request, None)

    async def generate_with_attempt_preparer(
        self,
        request: LLMGenerationRequest,
        prepare_attempt: Callable[[int], Awaitable[LLMGenerationRequest]],
    ) -> LLMGenerationResult:
        return await self._generate(request, prepare_attempt)

    async def _generate(
        self,
        request: LLMGenerationRequest,
        prepare_attempt: Callable[[int], Awaitable[LLMGenerationRequest]] | None,
    ) -> LLMGenerationResult:
        if (
            not isinstance(request, LLMGenerationRequest)
            or not request.system_content.strip()
            or not request.user_content.strip()
            or request.model != self.settings.llm_model
            or type(request.max_output_tokens) is not int
            or request.max_output_tokens < 1
            or request.max_output_tokens > self.settings.llm_max_output_tokens
            or request.reasoning_effort != "none"
            or request.temperature != 0.2
            or request.model_input_limit != 400_000
            or type(request.estimated_input_tokens) is not int
            or request.estimated_input_tokens < 0
            or type(request.memory_input_tokens) is not int
            or request.memory_input_tokens < 0
            or not isinstance(request.historical_messages, tuple)
            or any(not isinstance(message, LLMRoleMessage) for message in request.historical_messages)
            or any(message.role not in {"user", "assistant"} or not message.content.strip() for message in request.historical_messages)
            or len(request.historical_messages) % 2 != 0
            or any(
                message.role != expected
                for index, message in enumerate(request.historical_messages)
                for expected in (("user" if index % 2 == 0 else "assistant"),)
            )
            or bool(request.historical_messages) != (request.memory_input_tokens > 0)
            or request.estimated_input_tokens < request.memory_input_tokens
        ):
            raise llm_error(LLM_REQUEST_INVALID)

        client = self._get_client()
        started = perf_counter()
        max_attempts = self.settings.llm_max_transient_retries + 1
        provider_preflight_count = 0
        memory_dropped_after_exact_preflight = False
        for attempt in range(1, max_attempts + 1):
            if prepare_attempt is not None:
                request = await prepare_attempt(attempt)
            preflight_tokens: int | None = None
            response: Any | None = None
            attempt_memory_dropped = False
            try:
                # Rebuild the normal memory-aware input on every logical attempt.
                # The exact same list is passed to count and create within an attempt.
                effective_input = self._provider_input(request)
                for preflight_index in range(2):
                    provider_preflight_count += 1
                    count_result = await client.responses.input_tokens.count(
                        model=request.model,
                        instructions=request.system_content,
                        input=effective_input,
                        reasoning={"effort": request.reasoning_effort},
                        truncation="disabled",
                    )
                    preflight_tokens = getattr(count_result, "input_tokens", None)
                    if type(preflight_tokens) is not int or preflight_tokens < 0:
                        raise llm_error(INVALID_LLM_RESPONSE)
                    if preflight_tokens + 800 <= request.model_input_limit:
                        break
                    if preflight_index == 0 and request.historical_messages:
                        # D-084 removes optional memory as one unit. Evidence, system
                        # instructions and the current learner payload remain intact.
                        memory_dropped_after_exact_preflight = True
                        attempt_memory_dropped = True
                        effective_input = self._provider_input(request, include_memory=False)
                        continue
                    self._log_failure(
                        request, attempt, started, preflight_tokens,
                        LLM_CONTEXT_LIMIT_EXCEEDED, None, None,
                        provider_preflight_count=provider_preflight_count,
                        memory_dropped_after_exact_preflight=memory_dropped_after_exact_preflight,
                    )
                    raise llm_error(LLM_CONTEXT_LIMIT_EXCEEDED)

                response = await client.responses.create(
                    model=request.model,
                    instructions=request.system_content,
                    input=effective_input,
                    reasoning={"effort": request.reasoning_effort},
                    temperature=request.temperature,
                    max_output_tokens=request.max_output_tokens,
                    truncation="disabled",
                    store=False,
                    stream=False,
                )
                error_code, incomplete_reason = self._response_failure(response)
                if error_code:
                    self._log_failure(
                        request, attempt, started, preflight_tokens, error_code,
                        getattr(response, "status", None), incomplete_reason,
                        provider_preflight_count=provider_preflight_count,
                        memory_dropped_after_exact_preflight=memory_dropped_after_exact_preflight,
                    )
                    raise llm_error(error_code)

                usage = getattr(response, "usage", None)
                input_tokens = getattr(usage, "input_tokens", None) if usage is not None else None
                output_tokens = getattr(usage, "output_tokens", None) if usage is not None else None
                total_tokens = getattr(usage, "total_tokens", None) if usage is not None else None
                for value in (input_tokens, output_tokens, total_tokens):
                    if value is not None and (type(value) is not int or value < 0):
                        raise llm_error(INVALID_LLM_RESPONSE)
                latency_ms = round((perf_counter() - started) * 1000)
                request_id = getattr(response, "_request_id", None)
                if request_id is not None and not isinstance(request_id, str):
                    request_id = None
                result = LLMGenerationResult(
                    text=response.output_text,
                    provider="openai",
                    model=request.model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    provider_preflight_input_tokens=preflight_tokens,
                    latency_ms=latency_ms,
                    attempt_count=attempt,
                    provider_request_id=request_id,
                    provider_preflight_count=provider_preflight_count,
                    memory_dropped_after_exact_preflight=memory_dropped_after_exact_preflight,
                    memory_selected_turn_count=(
                        0 if attempt_memory_dropped else len(request.historical_messages) // 2
                    ),
                )
                logger.info(
                    "llm_generation_completed",
                    extra={
                        "provider": "openai", "model": request.model,
                        "estimated_input_tokens": request.estimated_input_tokens,
                        "provider_preflight_input_tokens": preflight_tokens,
                        "provider_preflight_count": provider_preflight_count,
                        "memory_dropped_after_exact_preflight": memory_dropped_after_exact_preflight,
                        "provider_usage_input_tokens": input_tokens,
                        "output_tokens": output_tokens, "total_tokens": total_tokens,
                        "temperature": request.temperature,
                        "max_output_tokens": request.max_output_tokens,
                        "attempt_count": attempt, "latency_ms": latency_ms,
                        "provider_status": "completed", "error_code": None,
                        "safe_incomplete_reason": None,
                        "provider_request_id": request_id,
                    },
                )
                return result
            except Exception as exc:
                if isinstance(exc, ApplicationError):
                    raise
                code, transient = _provider_error(exc)
                if transient and attempt < max_attempts:
                    logger.warning(
                        "llm_generation_retrying",
                        extra={
                            "provider": "openai", "model": request.model,
                            "attempt_count": attempt, "error_code": code,
                            "provider_preflight_input_tokens": preflight_tokens,
                            "provider_preflight_count": provider_preflight_count,
                            "memory_dropped_after_exact_preflight": memory_dropped_after_exact_preflight,
                        },
                    )
                    await transient_backoff(sleep=self._sleep, uniform=self._uniform)
                    continue
                self._log_failure(
                    request, attempt, started, preflight_tokens, code,
                    getattr(response, "status", None), None,
                    provider_preflight_count=provider_preflight_count,
                    memory_dropped_after_exact_preflight=memory_dropped_after_exact_preflight,
                )
                raise llm_error(code) from None
        raise llm_error(LLM_GENERATION_FAILED)

    @staticmethod
    def _provider_input(request: LLMGenerationRequest, *, include_memory: bool = True) -> list[dict[str, str]]:
        history = request.historical_messages if include_memory else ()
        return [
            *({"role": message.role, "content": message.content} for message in history),
            {"role": "user", "content": request.user_content},
        ]

    @staticmethod
    def _log_failure(
        request: LLMGenerationRequest,
        attempt: int,
        started: float,
        preflight_tokens: int | None,
        error_code: str,
        provider_status: str | None,
        incomplete_reason: str | None,
        *,
        provider_preflight_count: int = 0,
        memory_dropped_after_exact_preflight: bool = False,
    ) -> None:
        logger.warning(
            "llm_generation_failed",
            extra={
                "provider": "openai", "model": request.model,
                "estimated_input_tokens": request.estimated_input_tokens,
                "provider_preflight_input_tokens": preflight_tokens,
                "provider_preflight_count": provider_preflight_count,
                "memory_dropped_after_exact_preflight": memory_dropped_after_exact_preflight,
                "provider_usage_input_tokens": None, "output_tokens": None,
                "total_tokens": None, "temperature": request.temperature,
                "max_output_tokens": request.max_output_tokens,
                "attempt_count": attempt,
                "latency_ms": round((perf_counter() - started) * 1000),
                "provider_status": provider_status, "error_code": error_code,
                "safe_incomplete_reason": incomplete_reason,
                "provider_request_id": None,
            },
        )


__all__ = ["OpenAILLMProvider"]
