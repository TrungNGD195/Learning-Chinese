from functools import lru_cache

from app.ai.llm.openai_provider import OpenAILLMProvider
from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_llm_provider() -> OpenAILLMProvider:
    return OpenAILLMProvider(get_settings())
