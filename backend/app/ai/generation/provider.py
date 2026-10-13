from __future__ import annotations

from typing import Protocol

from app.ai.generation.schemas import (
    StructuredAssessmentGenerationProviderResult,
    StructuredAssessmentGenerationRequest,
)


class StructuredAssessmentGenerationProvider(Protocol):
    async def generate(
        self, request: StructuredAssessmentGenerationRequest
    ) -> StructuredAssessmentGenerationProviderResult: ...
