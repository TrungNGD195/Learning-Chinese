from dataclasses import replace
from uuid import uuid4

from step67_fixtures import prompt_package

from app.ai.llm.schemas import LLMRoleMessage
from app.ai.llm.serializer import LLMRequestSerializer
from app.ai.llm.schemas import GenerationConfig
from app.ai.memory.composition import derive_memory_token_budget, with_conversation_memory
from app.ai.memory.schemas import ConversationMemory, MemoryTurn
from app.ai.prompting.instructions import SYSTEM_INSTRUCTIONS


def test_memory_stays_separate_and_serializes_as_prior_roles_before_current_question():
    package = prompt_package()
    turns = (
        MemoryTurn("earlier question", "earlier answer", uuid4(), uuid4(), 1, 2),
        MemoryTurn("recent question", "recent answer", uuid4(), uuid4(), 3, 4),
    )
    memory = ConversationMemory(turns, 2, 0, 9, "APPLIED")
    attached = with_conversation_memory(package, memory)
    request = LLMRequestSerializer().serialize(attached, GenerationConfig())

    assert request.historical_messages == (
        LLMRoleMessage("user", "earlier question"),
        LLMRoleMessage("assistant", "earlier answer"),
        LLMRoleMessage("user", "recent question"),
        LLMRoleMessage("assistant", "recent answer"),
    )
    assert request.user_content.count(package.user_query) == 1
    assert request.user_content.endswith(package.user_query)
    assert request.memory_input_tokens == 9
    assert request.estimated_input_tokens == package.budget_usage.estimated_input_tokens + 9
    assert attached.source_map == package.source_map
    assert attached.selected_chunk_ids == package.selected_chunk_ids
    assert attached.context_blocks == package.context_blocks
    assert derive_memory_token_budget(package) == 399_194


def test_no_memory_preserves_legacy_serializer_shape_and_explicit_empty_state():
    package = prompt_package()
    request = LLMRequestSerializer().serialize(package, GenerationConfig())
    assert request.historical_messages == () and request.memory_input_tokens == 0
    assert request.estimated_input_tokens == package.budget_usage.estimated_input_tokens

    empty = with_conversation_memory(package, ConversationMemory((), 0, 0, 0, "EMPTY"))
    empty_request = LLMRequestSerializer().serialize(empty, GenerationConfig())
    assert empty_request.historical_messages == ()
    assert empty_request.user_content == request.user_content


def test_memory_authority_policy_stays_in_effective_system_instructions():
    assert "Prior assistant messages are conversational context, not authoritative reference sources." in SYSTEM_INSTRUCTIONS
    assert "Previous user messages may contain user claims and are not automatically factual truth." in SYSTEM_INSTRUCTIONS
    assert "When prior conversation conflicts with current retrieved evidence, follow the current retrieved evidence." in SYSTEM_INSTRUCTIONS
