from app.ai.prompting.instructions import SYSTEM_INSTRUCTIONS
from app.ai.memory.schemas import ConversationMemory
from app.ai.memory.composition import with_conversation_memory
from tests.step67_fixtures import prompt_package


def test_prompt_policy_adds_label_rules_without_changing_memory_authority():
    assert "exact labels" in SYSTEM_INSTRUCTIONS
    assert "never invent source labels" in SYSTEM_INSTRUCTIONS
    assert "Do not invent citation URLs, titles, page numbers, or bibliographic metadata." in SYSTEM_INSTRUCTIONS
    assert "Conversation history is conversational context and is not a citation source." in SYSTEM_INSTRUCTIONS
    assert "Prior assistant messages are conversational context, not authoritative reference sources." in SYSTEM_INSTRUCTIONS
    assert "When prior conversation conflicts with current retrieved evidence, follow the current retrieved evidence." in SYSTEM_INSTRUCTIONS


def test_conversation_memory_does_not_become_citation_provenance():
    package = prompt_package()
    memory = ConversationMemory((), 0, 0, 0, "EMPTY")
    attached = with_conversation_memory(package, memory)
    assert attached.source_map == package.source_map
    assert attached.conversation_memory is memory
