import asyncio

from app.ai.llm.schemas import GenerationConfig
from app.ai.llm.service import LLMGenerationService
from step67_fixtures import prompt_package


class RecordingProvider:
    def __init__(self):
        self.request = None

    async def generate(self, request):
        self.request = request
        return "result"


def test_service_serializes_then_delegates_without_provider_sdk_contracts() -> None:
    provider = RecordingProvider()
    result = asyncio.run(LLMGenerationService(provider).generate(prompt_package(), GenerationConfig()))
    assert result == "result"
    assert provider.request.model == "gpt-5.4-mini-2026-03-17"
