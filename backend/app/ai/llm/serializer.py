from app.ai.llm.errors import LLM_REQUEST_INVALID, llm_error
from app.ai.llm.schemas import (
    GenerationConfig,
    LLMGenerationRequest,
    serialize_historical_messages,
    serialize_user_content,
)
from app.ai.prompting.schemas import PromptPackage


class LLMRequestSerializer:
    def serialize(self, package: PromptPackage, config: GenerationConfig) -> LLMGenerationRequest:
        if not isinstance(package, PromptPackage) or not isinstance(config, GenerationConfig):
            raise llm_error(LLM_REQUEST_INVALID)
        if (
            not package.system_instructions.strip()
            or not package.user_query.strip()
            or type(package.budget_usage.estimated_input_tokens) is not int
            or package.budget_usage.estimated_input_tokens < 0
        ):
            raise llm_error(LLM_REQUEST_INVALID)
        return LLMGenerationRequest(
            system_content=package.system_instructions,
            user_content=serialize_user_content(package),
            model=config.model,
            temperature=config.temperature,
            max_output_tokens=config.max_output_tokens,
            reasoning_effort=config.reasoning_effort,
            model_input_limit=config.model_input_limit,
            estimated_input_tokens=(
                package.budget_usage.estimated_input_tokens
                + (package.conversation_memory.token_count if package.conversation_memory else 0)
            ),
            historical_messages=serialize_historical_messages(package.conversation_memory),
            memory_input_tokens=(package.conversation_memory.token_count if package.conversation_memory else 0),
        )
