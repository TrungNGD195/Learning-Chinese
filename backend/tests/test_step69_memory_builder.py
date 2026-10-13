import asyncio
import logging
from uuid import uuid4

import pytest

from app.ai.memory.builder import ConversationMemoryBuilder
from app.ai.memory.errors import (
    MEMORY_PERSISTENCE_INTEGRITY_FAILED,
    MEMORY_REPOSITORY_FAILED,
    MEMORY_TOKEN_COUNT_FAILED,
)
from app.conversation.repository import MemoryTurnRow


class MemoryRepository:
    def __init__(self, rows=(), failure=None):
        self.rows = tuple(rows)
        self.failure = failure
        self.calls = []

    async def list_recent_completed_turn_pairs_for_memory(self, session, **kwargs):
        self.calls.append(kwargs)
        if self.failure:
            raise self.failure
        return self.rows[:kwargs["limit"]]


class Counter:
    def __init__(self, counts=None, failure=None):
        self.counts = counts or {}
        self.failure = failure
        self.calls = []

    def count(self, text):
        self.calls.append(text)
        if self.failure:
            raise self.failure
        return self.counts.get(text, 1)


def row(conversation_id, user_sequence, assistant_sequence, *, user_text=None, assistant_text=None, user_id=None):
    return MemoryTurnRow(
        user_message_id=user_id or uuid4(), assistant_message_id=uuid4(),
        user_text=user_text or f"question {user_sequence}",
        assistant_text=assistant_text or f"answer {assistant_sequence}",
        user_sequence_number=user_sequence, assistant_sequence_number=assistant_sequence,
        conversation_id=conversation_id,
    )


def test_builder_selects_recent_turns_and_packs_oldest_first_chronologically():
    conversation_id = uuid4()
    rows = [row(conversation_id, 7, 8), row(conversation_id, 5, 6), row(conversation_id, 3, 4)]
    counter = Counter({"question 7": 2, "answer 8": 2, "question 5": 1, "answer 6": 1})
    repository = MemoryRepository(rows)
    memory = asyncio.run(ConversationMemoryBuilder(None, token_counter=counter, repository=repository).build(
        conversation_id=conversation_id, current_user_sequence_number=9,
        memory_token_budget=4, max_turns=2,
    ))
    assert [turn.user_sequence_number for turn in memory.turns] == [7]
    assert memory.token_count == 4 and memory.selected_turn_count == 1
    assert memory.omitted_turn_count == 1 and memory.status == "APPLIED"
    assert repository.calls == [{"conversation_id": conversation_id, "before_sequence_number": 9, "limit": 3}]


@pytest.mark.parametrize("reason", ["disabled", "no_budget"])
def test_empty_without_repository_lookup_when_disabled_or_no_budget(reason):
    repository = MemoryRepository([row(uuid4(), 1, 2)])
    memory = asyncio.run(ConversationMemoryBuilder(None, token_counter=Counter(), repository=repository).build(
        conversation_id=uuid4(), current_user_sequence_number=3,
        memory_token_budget=0 if reason == "no_budget" else 10,
        max_turns=0 if reason == "disabled" else 3,
    ))
    assert memory.status == "EMPTY" and memory.turns == ()
    assert memory.selected_turn_count == 0 and memory.token_count == 0
    assert not repository.calls


def test_builder_strips_only_exact_historical_citation_markers_and_drops_blank_turn():
    conversation_id = uuid4()
    rows = [
        row(conversation_id, 5, 6, assistant_text=" [S1][S12] \t"),
        row(conversation_id, 3, 4, user_text="keep [S0] [S01]", assistant_text="valid [S1] answer"),
    ]
    memory = asyncio.run(ConversationMemoryBuilder(None, token_counter=Counter(), repository=MemoryRepository(rows)).build(
        conversation_id=conversation_id, current_user_sequence_number=7,
        memory_token_budget=10, max_turns=3,
    ))
    assert len(memory.turns) == 1
    assert memory.turns[0].user_text == "keep [S0] [S01]"
    assert memory.turns[0].assistant_text == "valid  answer"


def test_builder_fails_on_duplicate_completed_assistant_for_user():
    conversation_id, user_id = uuid4(), uuid4()
    rows = [row(conversation_id, 1, 2, user_id=user_id), row(conversation_id, 1, 3, user_id=user_id)]
    builder = ConversationMemoryBuilder(None, token_counter=Counter(), repository=MemoryRepository(rows))
    with pytest.raises(Exception) as caught:
        asyncio.run(builder.build(conversation_id=conversation_id, current_user_sequence_number=4, memory_token_budget=10, max_turns=3))
    assert caught.value.code == MEMORY_PERSISTENCE_INTEGRITY_FAILED


def test_builder_fails_on_impossible_pair_relationship_and_token_counter_failure():
    conversation_id = uuid4()
    malformed = [row(conversation_id, 4, 3)]
    with pytest.raises(Exception) as caught:
        asyncio.run(ConversationMemoryBuilder(None, token_counter=Counter(), repository=MemoryRepository(malformed)).build(
            conversation_id=conversation_id, current_user_sequence_number=5, memory_token_budget=10, max_turns=3,
        ))
    assert caught.value.code == MEMORY_PERSISTENCE_INTEGRITY_FAILED

    with pytest.raises(Exception) as caught:
        asyncio.run(ConversationMemoryBuilder(None, token_counter=Counter(failure=RuntimeError()), repository=MemoryRepository([row(conversation_id, 1, 2)])).build(
            conversation_id=conversation_id, current_user_sequence_number=3, memory_token_budget=10, max_turns=3,
        ))
    assert caught.value.code == MEMORY_TOKEN_COUNT_FAILED


def test_repository_failure_is_normalized_and_never_converted_to_empty_memory(caplog):
    conversation_id = uuid4()
    repository = MemoryRepository(failure=RuntimeError("SENTINEL_DATABASE_FAILURE"))
    builder = ConversationMemoryBuilder(None, token_counter=Counter(), repository=repository)
    caplog.set_level(logging.INFO, logger="app.ai.memory.builder")

    with pytest.raises(Exception) as caught:
        asyncio.run(builder.build(
            conversation_id=conversation_id,
            current_user_sequence_number=3,
            memory_token_budget=10,
            max_turns=3,
        ))

    assert caught.value.code == MEMORY_REPOSITORY_FAILED
    assert "SENTINEL_DATABASE_FAILURE" not in str(caught.value)
    assert "SENTINEL_DATABASE_FAILURE" not in caplog.text
    assert "conversation_memory_build_completed" not in caplog.text


def test_cross_conversation_repository_row_fails_closed_without_empty_fallback():
    requested_conversation_id = uuid4()
    row_from_other_conversation = row(uuid4(), 1, 2)
    builder = ConversationMemoryBuilder(
        None,
        token_counter=Counter(),
        repository=MemoryRepository([row_from_other_conversation]),
    )

    with pytest.raises(Exception) as caught:
        asyncio.run(builder.build(
            conversation_id=requested_conversation_id,
            current_user_sequence_number=3,
            memory_token_budget=10,
            max_turns=3,
        ))

    assert caught.value.code == MEMORY_PERSISTENCE_INTEGRITY_FAILED
    assert row_from_other_conversation.conversation_id != requested_conversation_id


def test_memory_builder_logs_safe_counts_but_never_historical_content(caplog):
    conversation_id = uuid4()
    repository = MemoryRepository([
        row(
            conversation_id,
            1,
            2,
            user_text="SENTINEL_USER_MEMORY",
            assistant_text="SENTINEL_ASSISTANT_MEMORY",
        )
    ])
    caplog.set_level(logging.INFO, logger="app.ai.memory.builder")

    memory = asyncio.run(ConversationMemoryBuilder(
        None, token_counter=Counter(), repository=repository,
    ).build(
        conversation_id=conversation_id,
        current_user_sequence_number=3,
        memory_token_budget=10,
        max_turns=3,
    ))

    assert memory.status == "APPLIED"
    assert "SENTINEL_USER_MEMORY" not in caplog.text
    assert "SENTINEL_ASSISTANT_MEMORY" not in caplog.text
    completed = next(record for record in caplog.records if record.message == "conversation_memory_build_completed")
    assert completed.eligible_memory_turns == 1
    assert completed.selected_memory_turns == 1
    assert completed.omitted_memory_turns == 0
    assert completed.memory_token_count == memory.token_count
    assert completed.status == "APPLIED"
    assert completed.memory_applied is True


def test_repository_failure_log_does_not_expose_raw_exception(caplog):
    repository = MemoryRepository(failure=RuntimeError("SENTINEL_DATABASE_FAILURE"))
    caplog.set_level(logging.WARNING, logger="app.ai.memory.builder")

    with pytest.raises(Exception) as caught:
        asyncio.run(ConversationMemoryBuilder(
            None, token_counter=Counter(), repository=repository,
        ).build(
            conversation_id=uuid4(),
            current_user_sequence_number=3,
            memory_token_budget=10,
            max_turns=3,
        ))

    assert caught.value.code == MEMORY_REPOSITORY_FAILED
    assert "SENTINEL_DATABASE_FAILURE" not in caplog.text
    failed = next(record for record in caplog.records if record.message == "conversation_memory_build_failed")
    assert failed.error_code == MEMORY_REPOSITORY_FAILED
    assert failed.status == "FAILED"
