from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings
from app.ai.llm.errors import LLM_CONFIGURATION_INVALID, llm_error
from app.ai.memory.schemas import ConversationMemory


@dataclass(frozen=True)
class GenerationConfig:
    model: str = "gpt-5.4-mini-2026-03-17"
    temperature: float = 0.2
    max_output_tokens: int = 800
    reasoning_effort: str = "none"
    model_input_limit: int = 400_000
    request_timeout_seconds: float = 60
    max_transient_retries: int = 1

    def __post_init__(self) -> None:
        if (
            self.model != "gpt-5.4-mini-2026-03-17"
            or self.temperature != 0.2
            or self.reasoning_effort != "none"
            or self.model_input_limit != 400_000
            or type(self.max_output_tokens) is not int
            or not 1 <= self.max_output_tokens <= 800
            or type(self.max_transient_retries) is not int
            or not 0 <= self.max_transient_retries <= 1
            or not isinstance(self.request_timeout_seconds, (int, float))
            or self.request_timeout_seconds <= 0
        ):
            raise llm_error(LLM_CONFIGURATION_INVALID)

    @classmethod
    def from_settings(cls, settings: Settings) -> "GenerationConfig":
        return cls(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            max_output_tokens=settings.llm_max_output_tokens,
            reasoning_effort=settings.llm_reasoning_effort,
            model_input_limit=settings.llm_model_input_limit,
            request_timeout_seconds=settings.llm_request_timeout_seconds,
            max_transient_retries=settings.llm_max_transient_retries,
        )


@dataclass(frozen=True)
class LLMGenerationRequest:
    system_content: str
    user_content: str
    model: str
    temperature: float
    max_output_tokens: int
    reasoning_effort: str
    model_input_limit: int
    estimated_input_tokens: int
    historical_messages: tuple["LLMRoleMessage", ...] = ()
    memory_input_tokens: int = 0


@dataclass(frozen=True)
class LLMRoleMessage:
    role: str
    content: str

    def __post_init__(self) -> None:
        if self.role not in {"user", "assistant"} or not isinstance(self.content, str) or not self.content.strip():
            raise llm_error("LLM_REQUEST_INVALID")


@dataclass(frozen=True)
class LLMGenerationResult:
    text: str
    provider: str
    model: str
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    provider_preflight_input_tokens: int
    latency_ms: int
    attempt_count: int
    provider_request_id: str | None
    provider_preflight_count: int = 1
    memory_dropped_after_exact_preflight: bool = False
    memory_selected_turn_count: int = 0


def _reference_block(label: str, text: str) -> str:
    return f'<reference source="{label}">\n{text}\n</reference>'


def serialize_user_content(package) -> str:
    sections: list[str] = []
    if package.learning_context is not None:
        sections.append(f"[Learning context]\n{package.learning_context}")
    if package.context_blocks:
        references = "\n\n".join(
            _reference_block(f"S{index}", block.text)
            for index, block in enumerate(package.context_blocks, start=1)
        )
        sections.append(f"[References]\n\n{references}")
    sections.append(f"[Question]\n{package.user_query}")
    return "\n\n".join(sections)


def serialize_historical_messages(memory: ConversationMemory | None) -> tuple[LLMRoleMessage, ...]:
    if memory is None or not memory.turns:
        return ()
    return tuple(
        message
        for turn in memory.turns
        for message in (
            LLMRoleMessage("user", turn.user_text),
            LLMRoleMessage("assistant", turn.assistant_text),
        )
    )
