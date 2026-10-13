from __future__ import annotations

from functools import lru_cache

from app.ai.generation.openai_provider import OpenAIResponsesAssessmentGenerationProvider
from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_assessment_generation_provider() -> OpenAIResponsesAssessmentGenerationProvider:
    return OpenAIResponsesAssessmentGenerationProvider(get_settings())
