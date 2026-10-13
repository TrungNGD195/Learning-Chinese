from __future__ import annotations

from functools import lru_cache

from app.ai.grading.openai_provider import OpenAIResponsesGradingProvider
from app.ai.grading.service import LLMGradingService
from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_structured_grading_provider() -> OpenAIResponsesGradingProvider:
    return OpenAIResponsesGradingProvider(get_settings())


def get_grading_service() -> LLMGradingService:
    return LLMGradingService(get_structured_grading_provider(), get_settings())
