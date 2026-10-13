from dataclasses import replace

from app.ai.memory.schemas import ConversationMemory
from app.ai.prompting.schemas import PromptPackage


def derive_memory_token_budget(package: PromptPackage) -> int:
    usage = package.budget_usage
    return max(0, usage.model_input_limit - usage.reserved_output_tokens - usage.estimated_input_tokens)


def with_conversation_memory(package: PromptPackage, memory: ConversationMemory) -> PromptPackage:
    if not isinstance(package, PromptPackage) or not isinstance(memory, ConversationMemory):
        raise TypeError("Prompt package and conversation memory are required")
    return replace(package, conversation_memory=memory)
