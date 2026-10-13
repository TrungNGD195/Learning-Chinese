from __future__ import annotations

from typing import Protocol

from app.ai.grading.schemas import StructuredGradingProviderResult, StructuredGradingRequest


class StructuredGradingProvider(Protocol):
    async def grade(
        self, request: StructuredGradingRequest
    ) -> StructuredGradingProviderResult: ...
