from typing import Protocol

from app.ai.llm.schemas import LLMGenerationRequest, LLMGenerationResult


class LLMProvider(Protocol):
    async def generate(self, request: LLMGenerationRequest) -> LLMGenerationResult: ...
