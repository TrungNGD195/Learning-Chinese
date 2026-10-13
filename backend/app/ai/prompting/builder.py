from __future__ import annotations

import logging
from collections.abc import Sequence
from time import perf_counter
from typing import Any
from uuid import UUID

from app.ai.prompting.errors import (
    CONTEXT_BUDGET_EXHAUSTED,
    INVALID_PROMPT_BUDGET,
    NO_RETRIEVAL_CONTEXT,
    PROMPT_CONTEXT_BUILD_FAILED,
    TOKEN_COUNT_FAILED,
    prompt_context_error,
)
from app.ai.prompting.formatter import ContextBlockFormatter, render_learning_context
from app.ai.prompting.instructions import SYSTEM_INSTRUCTIONS
from app.ai.prompting.schemas import (
    BudgetUsage,
    ContextBuildResult,
    LearningContext,
    PromptBudget,
    PromptPackage,
)
from app.ai.prompting.token_counter import TokenCounter
from app.ai.reranking.schemas import RerankedCandidate
from app.ai.prompting.evidence import ContextEvidence, ExternalContextEvidence, InternalContextEvidence

logger = logging.getLogger(__name__)


class PromptContextBuilder:
    def __init__(self, *, token_counter: TokenCounter) -> None:
        self.token_counter = token_counter

    def _count(self, text: str) -> int:
        try:
            count = self.token_counter.count(text)
        except Exception:
            raise prompt_context_error(
                TOKEN_COUNT_FAILED,
                "Prompt token counting failed.",
                status_code=503,
            ) from None
        if type(count) is not int or count < 0:
            raise prompt_context_error(
                TOKEN_COUNT_FAILED,
                "Prompt token counting failed.",
                status_code=503,
            )
        return count

    @staticmethod
    def _validate_inputs(
        user_query: object,
        prompt_budget: object,
        learning_context: object,
    ) -> tuple[str, PromptBudget, LearningContext | None]:
        if not isinstance(prompt_budget, PromptBudget):
            raise prompt_context_error(INVALID_PROMPT_BUDGET, "Prompt budget structure is invalid.")
        if not isinstance(user_query, str) or not user_query.strip():
            raise prompt_context_error(PROMPT_CONTEXT_BUILD_FAILED, "Prompt input is invalid.")
        if learning_context is not None and not isinstance(learning_context, LearningContext):
            raise prompt_context_error(PROMPT_CONTEXT_BUILD_FAILED, "Learning context is invalid.")
        return user_query, prompt_budget, learning_context

    @staticmethod
    def _candidate_sequence(candidates: object) -> list[object]:
        if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes, bytearray)):
            raise prompt_context_error(PROMPT_CONTEXT_BUILD_FAILED, "Prompt evidence is invalid.")
        items = list(candidates)
        if len(items) > 5:
            raise prompt_context_error(PROMPT_CONTEXT_BUILD_FAILED, "Prompt evidence is invalid.")
        return items

    @staticmethod
    def _validate_candidates(candidates: list[Any]) -> list[RerankedCandidate]:
        items: list[RerankedCandidate] = []
        seen: set[UUID] = set()
        for position, candidate in enumerate(candidates, start=1):
            if not isinstance(candidate, RerankedCandidate):
                raise prompt_context_error(PROMPT_CONTEXT_BUILD_FAILED, "Prompt evidence is invalid.")
            if type(candidate.rerank_rank) is not int or candidate.rerank_rank != position:
                raise prompt_context_error(PROMPT_CONTEXT_BUILD_FAILED, "Prompt evidence order is invalid.")
            if not isinstance(candidate.chunk_id, UUID) or candidate.chunk_id in seen:
                raise prompt_context_error(PROMPT_CONTEXT_BUILD_FAILED, "Prompt evidence identity is invalid.")
            seen.add(candidate.chunk_id)
            items.append(candidate)
        return items

    def _log_failure(self, *, started: float, error_code: str, candidate_count: int) -> None:
        logger.warning(
            "prompt_context_build_failed",
            extra={
                "input_candidate_count": candidate_count,
                "selected_context_count": 0,
                "omitted_context_count": 0,
                "build_duration_ms": round((perf_counter() - started) * 1000, 2),
                "status": "FAILED",
                "error_code": error_code,
            },
        )

    def build(
        self,
        *,
        user_query: str,
        candidates: Sequence[RerankedCandidate],
        prompt_budget: PromptBudget,
        learning_context: LearningContext | None = None,
    ) -> ContextBuildResult:
        if isinstance(candidates, Sequence) and not isinstance(candidates, (str, bytes, bytearray)):
            evidence = tuple(InternalContextEvidence(i, candidate) for i, candidate in enumerate(candidates, start=1))
        else:
            evidence = candidates
        return self.build_from_evidence(
            user_query=user_query, evidence=evidence, prompt_budget=prompt_budget,
            learning_context=learning_context,
        )

    @staticmethod
    def _validate_evidence(evidence: list[Any]) -> list[ContextEvidence]:
        validated: list[ContextEvidence] = []
        seen: set[UUID] = set()
        for position, item in enumerate(evidence, start=1):
            if type(getattr(item, "final_order", None)) is not int or item.final_order != position:
                raise prompt_context_error(PROMPT_CONTEXT_BUILD_FAILED, "Prompt evidence order is invalid.")
            if isinstance(item, InternalContextEvidence):
                candidate = item.candidate
                if not isinstance(candidate, RerankedCandidate) or not isinstance(candidate.chunk_id, UUID) or candidate.chunk_id in seen:
                    raise prompt_context_error(PROMPT_CONTEXT_BUILD_FAILED, "Prompt evidence identity is invalid.")
                if type(candidate.rerank_rank) is not int or candidate.rerank_rank != position:
                    raise prompt_context_error(PROMPT_CONTEXT_BUILD_FAILED, "Prompt evidence order is invalid.")
                seen.add(candidate.chunk_id)
            elif not isinstance(item, ExternalContextEvidence):
                raise prompt_context_error(PROMPT_CONTEXT_BUILD_FAILED, "Prompt evidence is invalid.")
            validated.append(item)
        return validated

    def build_from_evidence(
        self,
        *,
        user_query: str,
        evidence: Sequence[ContextEvidence],
        prompt_budget: PromptBudget,
        learning_context: LearningContext | None = None,
    ) -> ContextBuildResult:
        started = perf_counter()
        candidate_count = len(evidence) if isinstance(evidence, (list, tuple)) else 0
        try:
            query, budget, trusted_learning_context = self._validate_inputs(
                user_query, prompt_budget, learning_context
            )

            # 6.6-D1: base-prompt validity takes precedence over evidence-state handling.
            learning_text = render_learning_context(trusted_learning_context)
            system_tokens = self._count(SYSTEM_INSTRUCTIONS)
            learning_tokens = self._count(learning_text) if learning_text is not None else 0
            query_tokens = self._count(query)
            base_input_tokens = (
                system_tokens
                + learning_tokens
                + query_tokens
                + budget.serialization_overhead_tokens
            )
            base_total_tokens = base_input_tokens + budget.reserved_output_tokens
            if base_total_tokens > budget.model_input_limit:
                raise prompt_context_error(
                    CONTEXT_BUDGET_EXHAUSTED,
                    "Prompt input exceeds the configured token budget.",
                    status_code=422,
                )

            raw_candidates = self._candidate_sequence(evidence)
            validated_candidates = self._validate_evidence(raw_candidates)
            available_context_tokens = budget.model_input_limit - base_total_tokens
            blocks = []
            selected_candidates = []
            source_map = {}
            selected_context_tokens = 0
            omitted_chunk_ids = []
            omitted_count = 0

            for item in validated_candidates:
                tentative_label = f"S{len(blocks) + 1}"
                if isinstance(item, InternalContextEvidence):
                    candidate = item.candidate
                    block = ContextBlockFormatter.format(candidate, tentative_label)
                    entry = ContextBlockFormatter.source_map_entry(block)
                else:
                    candidate = None
                    block = ContextBlockFormatter.format_external(item, tentative_label)
                    entry = ContextBlockFormatter.external_source_map_entry(block)
                block_tokens = self._count(block.text)
                if block_tokens <= available_context_tokens - selected_context_tokens:
                    blocks.append(block)
                    if candidate is not None:
                        selected_candidates.append(candidate)
                    source_map[tentative_label] = entry
                    selected_context_tokens += block_tokens
                else:
                    omitted_count += 1
                    if candidate is not None:
                        omitted_chunk_ids.append(candidate.chunk_id)

            if validated_candidates and not blocks:
                raise prompt_context_error(
                    CONTEXT_BUDGET_EXHAUSTED,
                    "No complete evidence block fits the configured token budget.",
                    status_code=422,
                )

            estimated_input_tokens = base_input_tokens + selected_context_tokens
            if estimated_input_tokens + budget.reserved_output_tokens > budget.model_input_limit:
                raise prompt_context_error(
                    PROMPT_CONTEXT_BUILD_FAILED,
                    "Prompt package violates its token budget.",
                    status_code=500,
                )

            usage = BudgetUsage(
                system_tokens=system_tokens,
                learning_context_tokens=learning_tokens,
                user_query_tokens=query_tokens,
                serialization_overhead_tokens=budget.serialization_overhead_tokens,
                reserved_output_tokens=budget.reserved_output_tokens,
                base_input_tokens=base_input_tokens,
                available_context_tokens=available_context_tokens,
                selected_context_tokens=selected_context_tokens,
                estimated_input_tokens=estimated_input_tokens,
                model_input_limit=budget.model_input_limit,
            )
            package = PromptPackage(
                system_instructions=SYSTEM_INSTRUCTIONS,
                learning_context=learning_text,
                context_blocks=tuple(blocks),
                user_query=query,
                selected_chunk_ids=tuple(candidate.chunk_id for candidate in selected_candidates),
                omitted_chunk_ids=tuple(omitted_chunk_ids),
                source_map=source_map,
                budget_usage=usage,
            )
            reason = NO_RETRIEVAL_CONTEXT if not validated_candidates else None
            result = ContextBuildResult(
                status="SUCCEEDED",
                reason=reason,
                selected_count=len(blocks),
                omitted_count=omitted_count,
                package=package,
            )
        except Exception as exc:
            code = getattr(exc, "code", PROMPT_CONTEXT_BUILD_FAILED)
            if code not in {
                INVALID_PROMPT_BUDGET,
                TOKEN_COUNT_FAILED,
                CONTEXT_BUDGET_EXHAUSTED,
                PROMPT_CONTEXT_BUILD_FAILED,
            }:
                code = PROMPT_CONTEXT_BUILD_FAILED
                exc = prompt_context_error(code, "Prompt context construction failed.", 500)
            self._log_failure(started=started, error_code=code, candidate_count=candidate_count)
            if hasattr(exc, "code"):
                raise exc from None
            raise prompt_context_error(
                PROMPT_CONTEXT_BUILD_FAILED,
                "Prompt context construction failed.",
                status_code=500,
            ) from None

        logger.info(
            "prompt_context_build_completed",
            extra={
                "input_candidate_count": len(validated_candidates),
                "selected_context_count": len(blocks),
                "omitted_context_count": omitted_count,
                "context_token_count": selected_context_tokens,
                "estimated_total_input_tokens": estimated_input_tokens,
                "model_input_limit": budget.model_input_limit,
                "reserved_output_tokens": budget.reserved_output_tokens,
                "serialization_overhead_tokens": budget.serialization_overhead_tokens,
                "available_context_tokens": available_context_tokens,
                "learning_context_present": learning_text is not None,
                "source_labels_count": len(source_map),
                "system_token_count": system_tokens,
                "user_query_token_count": query_tokens,
                "learning_context_token_count": learning_tokens,
                "build_duration_ms": round((perf_counter() - started) * 1000, 2),
                "status": "SUCCEEDED",
                "error_code": None,
            },
        )
        return result
