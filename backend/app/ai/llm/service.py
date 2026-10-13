from app.ai.llm.provider import LLMProvider
from app.ai.llm.schemas import GenerationConfig, LLMGenerationResult
from app.ai.llm.serializer import LLMRequestSerializer
from app.ai.prompting.schemas import PromptPackage
from collections.abc import Awaitable, Callable
from app.ai.llm.schemas import LLMGenerationRequest


class LLMGenerationService:
    def __init__(self, provider: LLMProvider, *, serializer: LLMRequestSerializer | None = None) -> None:
        self.provider = provider
        self.serializer = serializer or LLMRequestSerializer()

    async def generate(
        self, package: PromptPackage, config: GenerationConfig
    ) -> LLMGenerationResult:
        request = self.serializer.serialize(package, config)
        return await self.provider.generate(request)

    async def generate_with_attempt_preparer(
        self,
        package: PromptPackage,
        config: GenerationConfig,
        prepare_attempt: Callable[[int], Awaitable[PromptPackage]],
    ) -> LLMGenerationResult:
        """Let the accepted retry owner rebuild optional memory per logical attempt."""
        if not hasattr(self.provider, "generate_with_attempt_preparer"):
            prepared = await prepare_attempt(1)
            return await self.provider.generate(self.serializer.serialize(prepared, config))

        base_request = self.serializer.serialize(package, config)

        async def request_for_attempt(attempt: int) -> LLMGenerationRequest:
            prepared = await prepare_attempt(attempt)
            return self.serializer.serialize(prepared, config)

        return await self.provider.generate_with_attempt_preparer(base_request, request_for_attempt)
