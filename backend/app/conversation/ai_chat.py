from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from functools import lru_cache

from app.ai.rag.orchestrator import RagOrchestrator
from app.ai.rag.schemas import RagRunResult


@dataclass(frozen=True)
class ChatRequest:
    user_id: UUID
    conversation_id: UUID
    lesson_id: UUID
    user_message_id: UUID
    assistant_message_id: UUID
    content: str


class AIChatProcessingError(Exception):
    """Safe internal signal that an Assistant processing attempt failed."""


class AIChatService(Protocol):
    async def generate_reply(self, request: ChatRequest) -> RagRunResult:
        """Return typed internal RAG output or raise a safe processing error."""


class RAGAIChatService:
    def __init__(self, orchestrator: RagOrchestrator | None = None) -> None:
        self.orchestrator = orchestrator or RagOrchestrator()

    async def generate_reply(self, request: ChatRequest) -> RagRunResult:
        return await self.orchestrator.run(request)


@lru_cache(maxsize=1)
def get_ai_chat_service() -> AIChatService:
    return RAGAIChatService()
