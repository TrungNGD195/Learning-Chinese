from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from app.ai.memory.errors import MEMORY_PERSISTENCE_INTEGRITY_FAILED, memory_error


@dataclass(frozen=True)
class MemoryTurn:
    user_text: str
    assistant_text: str
    user_message_id: UUID
    assistant_message_id: UUID
    user_sequence_number: int
    assistant_sequence_number: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.user_text, str)
            or not self.user_text.strip()
            or not isinstance(self.assistant_text, str)
            or not self.assistant_text.strip()
            or not isinstance(self.user_message_id, UUID)
            or not isinstance(self.assistant_message_id, UUID)
            or self.user_message_id == self.assistant_message_id
            or type(self.user_sequence_number) is not int
            or type(self.assistant_sequence_number) is not int
            or not 0 < self.user_sequence_number < self.assistant_sequence_number
        ):
            raise memory_error(MEMORY_PERSISTENCE_INTEGRITY_FAILED)


@dataclass(frozen=True)
class ConversationMemory:
    turns: tuple[MemoryTurn, ...]
    selected_turn_count: int
    omitted_turn_count: int
    token_count: int
    status: Literal["APPLIED", "EMPTY"]

    def __post_init__(self) -> None:
        if (
            self.status not in {"APPLIED", "EMPTY"}
            or not isinstance(self.turns, tuple)
            or any(not isinstance(turn, MemoryTurn) for turn in self.turns)
            or any(type(value) is not int or value < 0 for value in (
                self.selected_turn_count, self.omitted_turn_count, self.token_count,
            ))
        ):
            raise memory_error(MEMORY_PERSISTENCE_INTEGRITY_FAILED)
        if self.status == "EMPTY":
            if self.turns or self.selected_turn_count != 0 or self.token_count != 0:
                raise memory_error(MEMORY_PERSISTENCE_INTEGRITY_FAILED)
        elif not self.turns or self.selected_turn_count != len(self.turns) or self.token_count < 1:
            raise memory_error(MEMORY_PERSISTENCE_INTEGRITY_FAILED)


def empty_memory(*, omitted_turn_count: int = 0) -> ConversationMemory:
    return ConversationMemory((), 0, omitted_turn_count, 0, "EMPTY")
