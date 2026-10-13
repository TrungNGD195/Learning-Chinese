from __future__ import annotations

import hashlib
from collections.abc import Callable

from app.ai.llm.schemas import LLMGenerationResult, LLMGenerationRequest

from .contracts import E2EJudgeResult


class DeterministicLLMProvider:
    """Test fake behind LLMProvider; keyed by user request text, never case labels."""

    def __init__(self, answer_for_request: Callable[[LLMGenerationRequest], str]):
        self.answer_for_request = answer_for_request
        self.calls = 0
        self.request_hashes: list[str] = []

    async def generate(self, request: LLMGenerationRequest) -> LLMGenerationResult:
        self.calls += 1
        digest = hashlib.sha256(request.user_content.encode("utf-8")).hexdigest()
        self.request_hashes.append(digest)
        answer = self.answer_for_request(request)
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("FAKE_LLM_EMPTY_ANSWER")
        return LLMGenerationResult(
            text=answer, provider="deterministic-test-fake", model=request.model,
            input_tokens=None, output_tokens=None, total_tokens=None,
            provider_preflight_input_tokens=request.estimated_input_tokens,
            latency_ms=0, attempt_count=1, provider_request_id=None,
            provider_preflight_count=1, memory_dropped_after_exact_preflight=False,
            memory_selected_turn_count=len(request.historical_messages) // 2,
        )


class DeterministicE2EJudge:
    """Offline judge fake behind the Step-7.5 Judge protocol; never self-approves."""

    def __init__(self, result_for_payload: Callable[[dict], E2EJudgeResult]):
        self.result_for_payload = result_for_payload
        self.calls = 0

    async def evaluate(self, payload: dict, *, case_id: str, repeat_index: int,
                       current_citation_labels: set[str], source_map_labels: set[str]) -> E2EJudgeResult:
        self.calls += 1
        if payload.get("case_id") != case_id or payload.get("repeat_index") != repeat_index:
            raise ValueError("JUDGE_REQUEST_IDENTITY_MISMATCH")
        result = self.result_for_payload(payload)
        result.validate_labels(case_id=case_id, repeat_index=repeat_index,
                               current_citation_labels=current_citation_labels,
                               source_map_labels=source_map_labels)
        return result
