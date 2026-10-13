from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class ProviderGradingStatus(StrEnum):
    GRADED = "GRADED"
    UNCERTAIN = "UNCERTAIN"


class StructuredGradingOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grading_status: ProviderGradingStatus
    score: float | None
    feedback: str

    @field_validator("score", mode="before")
    @classmethod
    def reject_boolean_score(cls, value: Any) -> Any:
        if isinstance(value, bool):
            raise ValueError("score must be numeric, not boolean")
        return value


@dataclass(frozen=True)
class StructuredGradingRequest:
    question_type: str
    system_content: str
    user_content: str
    model: str
    temperature: float
    max_output_tokens: int
    reasoning_effort: str
    model_input_limit: int
    request_timeout_seconds: float
    max_transient_retries: int


@dataclass(frozen=True)
class StructuredGradingProviderResult:
    output: StructuredGradingOutput
    provider: str
    model: str
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    provider_preflight_input_tokens: int
    latency_ms: int
    attempt_count: int
    provider_request_id: str | None
