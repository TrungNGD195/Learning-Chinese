from __future__ import annotations

import logging
from time import perf_counter
from typing import Any
from uuid import UUID

from app.ai.memory.errors import (
    MEMORY_BUILD_FAILED,
    MEMORY_PERSISTENCE_INTEGRITY_FAILED,
    MEMORY_REPOSITORY_FAILED,
    MEMORY_TOKEN_COUNT_FAILED,
    memory_error,
)
from app.ai.memory.sanitizer import sanitize_historical_assistant_text
from app.ai.memory.schemas import ConversationMemory, MemoryTurn, empty_memory
from app.ai.prompting.token_counter import TokenCounter
from app.conversation import repository as conversation_repository

logger = logging.getLogger(__name__)


class ConversationMemoryBuilder:
    def __init__(
        self,
        session: Any,
        *,
        token_counter: TokenCounter,
        repository: Any = conversation_repository,
    ) -> None:
        self.session = session
        self.token_counter = token_counter
        self.repository = repository

    async def build(
        self,
        *,
        conversation_id: UUID,
        current_user_sequence_number: int,
        memory_token_budget: int,
        max_turns: int,
    ) -> ConversationMemory:
        started = perf_counter()
        if (
            not isinstance(conversation_id, UUID)
            or type(current_user_sequence_number) is not int
            or current_user_sequence_number < 1
            or type(memory_token_budget) is not int
            or type(max_turns) is not int
            or not 0 <= max_turns <= 3
        ):
            raise memory_error(MEMORY_BUILD_FAILED)
        if max_turns == 0 or memory_token_budget <= 0:
            return self._log_and_return(
                empty_memory(), conversation_id, started,
                eligible_count=0, disabled=max_turns == 0,
            )

        try:
            if self.session is None:
                rows = await self.repository.list_recent_completed_turn_pairs_for_memory(
                    self.session,
                    conversation_id=conversation_id,
                    before_sequence_number=current_user_sequence_number,
                    limit=max_turns + 1,
                )
            else:
                async with self.session.begin():
                    rows = await self.repository.list_recent_completed_turn_pairs_for_memory(
                        self.session,
                        conversation_id=conversation_id,
                        before_sequence_number=current_user_sequence_number,
                        limit=max_turns + 1,
                    )
        except Exception:
            logger.warning(
                "conversation_memory_build_failed",
                extra={"conversation_id": str(conversation_id), "status": "FAILED", "error_code": MEMORY_REPOSITORY_FAILED},
            )
            raise memory_error(MEMORY_REPOSITORY_FAILED) from None

        try:
            usable = self._validate_and_sanitize(rows, conversation_id, current_user_sequence_number)
        except Exception:
            logger.warning(
                "conversation_memory_build_failed",
                extra={"conversation_id": str(conversation_id), "status": "FAILED", "error_code": MEMORY_PERSISTENCE_INTEGRITY_FAILED},
            )
            raise memory_error(MEMORY_PERSISTENCE_INTEGRITY_FAILED) from None

        # Query order is newest first. Select the most recent usable complete turns,
        # then restore chronological order before token packing/serialization.
        selected = list(reversed(usable[:max_turns]))
        counted: list[tuple[MemoryTurn, int]] = []
        try:
            for turn in selected:
                user_count = self.token_counter.count(turn.user_text)
                assistant_count = self.token_counter.count(turn.assistant_text)
                if type(user_count) is not int or user_count < 0 or type(assistant_count) is not int or assistant_count < 0:
                    raise ValueError("invalid token count")
                counted.append((turn, user_count + assistant_count))
        except Exception:
            logger.warning(
                "conversation_memory_build_failed",
                extra={"conversation_id": str(conversation_id), "status": "FAILED", "error_code": MEMORY_TOKEN_COUNT_FAILED},
            )
            raise memory_error(MEMORY_TOKEN_COUNT_FAILED) from None

        total = sum(count for _, count in counted)
        omitted = 0
        while counted and total > memory_token_budget:
            _, dropped_count = counted.pop(0)
            total -= dropped_count
            omitted += 1

        if not counted:
            result = empty_memory(omitted_turn_count=omitted)
        else:
            result = ConversationMemory(
                turns=tuple(turn for turn, _ in counted),
                selected_turn_count=len(counted),
                omitted_turn_count=omitted,
                token_count=total,
                status="APPLIED",
            )
        return self._log_and_return(
            result, conversation_id, started, eligible_count=len(usable), disabled=False,
        )

    @staticmethod
    def _validate_and_sanitize(rows: object, conversation_id: UUID, before_sequence_number: int) -> list[MemoryTurn]:
        if not isinstance(rows, (tuple, list)) or len(rows) > 4:
            raise ValueError("invalid memory repository result")
        seen: set[UUID] = set()
        turns: list[MemoryTurn] = []
        for row in rows:
            user_id = getattr(row, "user_message_id", None)
            assistant_id = getattr(row, "assistant_message_id", None)
            user_text = getattr(row, "user_text", None)
            assistant_text = getattr(row, "assistant_text", None)
            user_sequence = getattr(row, "user_sequence_number", None)
            assistant_sequence = getattr(row, "assistant_sequence_number", None)
            if (
                not isinstance(user_id, UUID)
                or not isinstance(assistant_id, UUID)
                or user_id in seen
                or getattr(row, "conversation_id", None) != conversation_id
                or not isinstance(user_text, str)
                or not user_text.strip()
                or not isinstance(assistant_text, str)
                or not assistant_text.strip()
                or type(user_sequence) is not int
                or type(assistant_sequence) is not int
                or not 0 < user_sequence < assistant_sequence < before_sequence_number
            ):
                raise ValueError("invalid persisted complete turn")
            seen.add(user_id)
            sanitized = sanitize_historical_assistant_text(assistant_text)
            if not sanitized.strip():
                continue
            turns.append(
                MemoryTurn(
                    user_text=user_text,
                    assistant_text=sanitized,
                    user_message_id=user_id,
                    assistant_message_id=assistant_id,
                    user_sequence_number=user_sequence,
                    assistant_sequence_number=assistant_sequence,
                )
            )
        # Database order must be newest-first; reject malformed repository ordering.
        if any(turns[i].user_sequence_number < turns[i + 1].user_sequence_number for i in range(len(turns) - 1)):
            raise ValueError("memory rows are not ordered newest-first")
        return turns

    @staticmethod
    def _log_and_return(
        result: ConversationMemory,
        conversation_id: UUID,
        started: float,
        *,
        eligible_count: int,
        disabled: bool,
    ) -> ConversationMemory:
        logger.info(
            "conversation_memory_build_completed",
            extra={
                "conversation_id": str(conversation_id),
                "eligible_memory_turns": eligible_count,
                "selected_memory_turns": result.selected_turn_count,
                "omitted_memory_turns": result.omitted_turn_count,
                "memory_token_count": result.token_count,
                "memory_build_duration_ms": round((perf_counter() - started) * 1000, 2),
                "memory_applied": result.status == "APPLIED",
                "memory_disabled_by_config": disabled,
                "status": result.status,
                "error_code": None,
            },
        )
        return result
