from __future__ import annotations

import logging
from time import perf_counter
from typing import Callable, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select

from app.ai.citations.validator import CitationValidator, TrustedExternalDomains, sources_from_prompt_package
from app.ai.embeddings.provider import get_embedding_provider
from app.ai.external_retrieval.reranking import ExternalRerankingService
from app.ai.external_retrieval.service import ExternalRetrievalService
from app.ai.external_retrieval.tavily_provider import TavilyExternalRetrievalProvider
from app.ai.llm.factory import get_llm_provider
from app.ai.llm.schemas import GenerationConfig
from app.ai.llm.serializer import LLMRequestSerializer
from app.ai.llm.service import LLMGenerationService
from app.ai.memory.builder import ConversationMemoryBuilder
from app.ai.memory.composition import derive_memory_token_budget, with_conversation_memory
from app.ai.prompting.builder import PromptContextBuilder
from app.ai.prompting.evidence import ExternalContextEvidence
from app.ai.prompting.schemas import PromptBudget
from app.ai.prompting.token_counter import TiktokenTokenCounter
from app.ai.rag.errors import RAG_CONFIGURATION_INVALID, rag_error
from app.ai.rag.schemas import (
    NO_EVIDENCE_CONTENT,
    CalibrationCandidateTrace,
    CalibrationScoreRequest,
    CalibrationScoreTrace,
    CalibrationTierTrace,
    RagInternalTier,
    RagRunResult,
    RagRunStatus,
    RagTierUsed,
    RetrievalTraceEntry,
)
from app.ai.reranking.service import RerankingService
from app.ai.retrieval.scopes import RetrievalScope, build_scope_filter
from app.ai.retrieval.service import SemanticRetrievalService
from app.ai.retrieval.query_preprocessor import QueryPreprocessor
from app.core.config import Settings, get_settings
from app.database.models import Conversation, Message
from app.database.session import SessionFactory

if TYPE_CHECKING:
    from app.conversation.ai_chat import ChatRequest

logger = logging.getLogger("app.ai.rag")


class RagOrchestrator:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        session_factory=SessionFactory,
        retrieval_factory: Callable | None = None,
        reranker=None,
        prompt_builder=None,
        token_counter=None,
        generation_service=None,
        citation_validator=None,
        memory_builder_factory=None,
        external_retrieval_service=None,
        external_reranking_service=None,
    ) -> None:
        self.settings = settings or get_settings()
        self.session_factory = session_factory
        self.retrieval_factory = retrieval_factory or (
            lambda session: SemanticRetrievalService(
                session, provider=get_embedding_provider(), settings=self.settings
            )
        )
        self.reranker = reranker or RerankingService(settings=self.settings)
        self.token_counter = token_counter or TiktokenTokenCounter()
        self.prompt_builder = prompt_builder or PromptContextBuilder(token_counter=self.token_counter)
        self.generation_config = GenerationConfig.from_settings(self.settings)
        self.generation_service = generation_service or LLMGenerationService(
            get_llm_provider(), serializer=LLMRequestSerializer()
        )
        self.citation_validator = citation_validator or CitationValidator(
            TrustedExternalDomains(frozenset(self.settings.external_retrieval_allowed_domains))
        )
        self.external_retrieval_service = external_retrieval_service or ExternalRetrievalService(
            TavilyExternalRetrievalProvider(self.settings), self.settings
        )
        self.external_reranking_service = external_reranking_service or ExternalRerankingService(self.settings)
        self.memory_builder_factory = memory_builder_factory or (
            lambda session: ConversationMemoryBuilder(session, token_counter=self.token_counter)
        )

    def _validate_learner_config(self) -> None:
        threshold = self.settings.rag_min_rerank_score
        if (
            self.settings.rag_evidence_calibration_mode
            or threshold is None
            or isinstance(threshold, bool)
        ):
            raise rag_error(RAG_CONFIGURATION_INVALID)

    def _has_usable_evidence(self, result) -> bool:
        return any(
            candidate.rerank_score >= self.settings.rag_min_rerank_score
            for candidate in result.scored_candidates
        )

    async def _score_tier(self, query: str, lesson_id: UUID, tier: RagInternalTier):
        started = perf_counter()
        retrieval_filter = build_scope_filter(
            RetrievalScope.CURRENT_LESSON if tier is RagInternalTier.CURRENT_LESSON else RetrievalScope.INTERNAL_KB,
            trusted_lesson_id=lesson_id if tier is RagInternalTier.CURRENT_LESSON else None,
        )
        async with self.session_factory() as session:
            candidates = await self.retrieval_factory(session).retrieve(
                query, retrieval_filter=retrieval_filter
            )
        retrieval_duration = round((perf_counter() - started) * 1000, 2)
        rerank_started = perf_counter()
        result = await self.reranker.rerank(query, candidates)
        rerank_duration = round((perf_counter() - rerank_started) * 1000, 2)
        logger.info("rag_tier_scored", extra={
            "tier": tier.value,
            "candidate_count": len(candidates),
            "scored_count": len(result.scored_candidates),
            "retrieval_duration_ms": retrieval_duration,
            "rerank_duration_ms": rerank_duration,
            "status": "SCORED" if result.scored_candidates else "EMPTY",
            "error_code": None,
        })
        return tuple(candidates), result, retrieval_duration, rerank_duration

    async def run(self, request: ChatRequest) -> RagRunResult:
        started = perf_counter()
        self._validate_learner_config()
        tiers: list[RagTierUsed] = []
        try:
            current_candidates, current_result, _, _ = await self._score_tier(
                request.content, request.lesson_id, RagInternalTier.CURRENT_LESSON
            )
            tiers.append(RagTierUsed.CURRENT_LESSON)
            current_usable = self._has_usable_evidence(current_result)
            selected_tier = RagTierUsed.CURRENT_LESSON if current_usable else RagTierUsed.INTERNAL_KB
            kb_candidates = ()
            kb_result = None
            if not current_usable:
                kb_candidates, kb_result, _, _ = await self._score_tier(
                    request.content, request.lesson_id, RagInternalTier.INTERNAL_KB
                )
                tiers.append(RagTierUsed.INTERNAL_KB)
                if not self._has_usable_evidence(kb_result):
                    tiers.append(RagTierUsed.TRUSTED_EXTERNAL)
                    normalized_query = QueryPreprocessor.preprocess(request.content)
                    external_candidates = await self.external_retrieval_service.search(normalized_query)
                    external_result = await self.external_reranking_service.rerank(normalized_query, external_candidates)
                    logger.info("external_tier_completed", extra={
                        "external_provider": "tavily", "external_requested_count": 10,
                        "external_returned_count": len(external_candidates),
                        "external_trusted_count": len(external_candidates),
                        "external_scored_count": len(external_result.scored_candidates),
                        "external_eligible_count": len(external_result.eligible_top_candidates),
                        "tier_used": "TRUSTED_EXTERNAL", "status": "SUCCEEDED",
                        "error_stage": None, "error_code": None,
                    })
                    if not external_result.eligible_top_candidates:
                        result = RagRunResult(
                            assistant_message_id=request.assistant_message_id,
                            status=RagRunStatus.NO_EVIDENCE,
                            assistant_content=NO_EVIDENCE_CONTENT,
                            tiers_attempted=tuple(tiers), tier_used=RagTierUsed.NONE,
                            current_lesson_candidate_count=len(current_candidates),
                            current_lesson_scored_count=len(current_result.scored_candidates),
                            internal_kb_candidate_count=len(kb_candidates),
                            internal_kb_scored_count=len(kb_result.scored_candidates),
                            selected_context_count=0, memory_selected_turn_count=0,
                            retrieval_trace=(), validated_citations=(),
                            external_candidate_count=len(external_candidates),
                            external_scored_count=len(external_result.scored_candidates),
                        )
                        self._log_result(result, request.conversation_id, started)
                        return result
                    selected_tier = RagTierUsed.TRUSTED_EXTERNAL
                else:
                    external_candidates = ()
                    external_result = None
            else:
                external_candidates = ()
                external_result = None

            context_started = perf_counter()
            prompt_budget = PromptBudget(
                    model_input_limit=self.generation_config.model_input_limit,
                    reserved_output_tokens=self.generation_config.max_output_tokens,
                    serialization_overhead_tokens=0,
                )
            if selected_tier is RagTierUsed.TRUSTED_EXTERNAL:
                external_evidence = tuple(ExternalContextEvidence(
                    final_order=index, title=item.title, url=item.url, domain=item.domain,
                    content=item.content, rerank_score=item.rerank_score,
                ) for index, item in enumerate(external_result.eligible_top_candidates, start=1))
                built = self.prompt_builder.build_from_evidence(
                    user_query=request.content, evidence=external_evidence,
                    prompt_budget=prompt_budget, learning_context=None,
                )
            else:
                selected = current_result if selected_tier is RagTierUsed.CURRENT_LESSON else kb_result
                built = self.prompt_builder.build(
                    user_query=request.content, candidates=selected.top_candidates,
                    prompt_budget=prompt_budget, learning_context=None,
                )
            if built.status != "SUCCEEDED":
                raise rag_error("RAG_ORCHESTRATION_FAILED")
            package = built.package
            context_duration = round((perf_counter() - context_started) * 1000, 2)
            memory_budget = derive_memory_token_budget(package)
            memory_eligible = self.settings.rag_memory_max_turns > 0 and memory_budget > 0
            current_sequence = await self._current_user_sequence(request) if memory_eligible else None
            async def prepare_attempt(_attempt: int):
                if not memory_eligible:
                    return package
                async with self.session_factory() as memory_session:
                    memory = await self.memory_builder_factory(memory_session).build(
                        conversation_id=request.conversation_id,
                        current_user_sequence_number=current_sequence,
                        memory_token_budget=memory_budget,
                        max_turns=self.settings.rag_memory_max_turns,
                    )
                return with_conversation_memory(package, memory)

            llm_started = perf_counter()
            generated = await self.generation_service.generate_with_attempt_preparer(
                package, self.generation_config, prepare_attempt
            )
            llm_duration = round((perf_counter() - llm_started) * 1000, 2)
            # Provider metadata accounts for D-084 removing memory after exact preflight.
            memory_count = generated.memory_selected_turn_count
            # Memory never changes the evidence source map used for citations.
            sources = sources_from_prompt_package(package)
            citation_started = perf_counter()
            validation = self.citation_validator.validate(
                text=generated.text, sources=sources, citation_required=True
            )
            citation_duration = round((perf_counter() - citation_started) * 1000, 2)
            if selected_tier is RagTierUsed.TRUSTED_EXTERNAL:
                trace = ()
            else:
                selected_candidates = selected.scored_candidates
                trace = tuple(RetrievalTraceEntry(
                    chunk_id=item.chunk_id, rank=item.rank,
                    retrieval_score=item.retrieval_score, rerank_score=item.rerank_score,
                ) for item in selected_candidates)
            result = RagRunResult(
                assistant_message_id=request.assistant_message_id,
                status=RagRunStatus.GROUNDED_ANSWER,
                assistant_content=validation.text,
                tiers_attempted=tuple(tiers), tier_used=selected_tier,
                current_lesson_candidate_count=len(current_candidates),
                current_lesson_scored_count=len(current_result.scored_candidates),
                internal_kb_candidate_count=len(kb_candidates),
                internal_kb_scored_count=len(kb_result.scored_candidates) if kb_result else 0,
                selected_context_count=built.selected_count,
                memory_selected_turn_count=memory_count,
                retrieval_trace=trace,
                validated_citations=validation.citations,
                external_candidate_count=len(external_candidates),
                external_scored_count=len(external_result.scored_candidates) if external_result else 0,
            )
            self._log_result(result, request.conversation_id, started, extra={
                "context_build_duration_ms": context_duration,
                "llm_duration_ms": llm_duration,
                "citation_validation_duration_ms": citation_duration,
            })
            return result
        except Exception as exc:
            logger.warning("rag_orchestration_failed", extra={
                "conversation_id": str(request.conversation_id),
                "assistant_message_id": str(request.assistant_message_id),
                "retrieval_tiers_attempted": tuple(t.value for t in tiers),
                "status": "FAILED",
                "error_stage": "ORCHESTRATION",
                "error_code": getattr(exc, "code", "RAG_ORCHESTRATION_FAILED"),
            })
            raise

    async def _current_user_sequence(self, request: ChatRequest) -> int:
        async with self.session_factory() as session:
            async with session.begin():
                row = await session.execute(
                    select(Message.sequence_number, Message.role, Message.status)
                    .join(Conversation, Conversation.id == Message.conversation_id)
                    .where(
                        Message.id == request.user_message_id,
                        Message.conversation_id == request.conversation_id,
                        Conversation.user_id == request.user_id,
                    )
                )
                result = row.one_or_none()
        if result is None or result.role != "USER" or result.status != "COMPLETED":
            raise rag_error("RAG_ORCHESTRATION_FAILED")
        return result.sequence_number

    async def collect_calibration_scores(
        self, request: CalibrationScoreRequest
    ) -> CalibrationScoreTrace:
        if not self.settings.rag_evidence_calibration_mode:
            raise rag_error(RAG_CONFIGURATION_INVALID)
        traces = []
        for tier in (RagInternalTier.CURRENT_LESSON, RagInternalTier.INTERNAL_KB):
            retrieved, result, _, _ = await self._score_tier(request.query, request.lesson_id, tier)
            candidate_traces = tuple(CalibrationCandidateTrace(
                chunk_id=item.chunk_id, retrieval_rank=item.rank,
                retrieval_score=item.retrieval_score, rerank_rank=item.rerank_rank,
                rerank_score=item.rerank_score, knowledge_source_id=item.knowledge_source_id,
                source_type=item.source_type, source_lesson_id=item.source_lesson_id,
                content_type=item.content_type,
            ) for item in result.scored_candidates)
            traces.append(CalibrationTierTrace(
                tier=tier, status="SCORED" if candidate_traces else "EMPTY",
                retrieval_candidate_count=len(retrieved), scored_count=len(candidate_traces), candidates=candidate_traces,
            ))
        return CalibrationScoreTrace(current_lesson=traces[0], internal_kb=traces[1])

    @staticmethod
    def _log_result(result: RagRunResult, conversation_id: UUID, started: float, extra: dict | None = None) -> None:
        logger.info("rag_orchestration_completed", extra={
            "conversation_id": str(conversation_id),
            "assistant_message_id": str(result.assistant_message_id),
            "calibration_mode": False,
            "retrieval_tiers_attempted": tuple(t.value for t in result.tiers_attempted),
            "tier_used": result.tier_used.value,
            "current_lesson_candidate_count": result.current_lesson_candidate_count,
            "current_lesson_scored_count": result.current_lesson_scored_count,
            "internal_kb_candidate_count": result.internal_kb_candidate_count,
            "internal_kb_scored_count": result.internal_kb_scored_count,
            "selected_context_count": result.selected_context_count,
            "memory_selected_turn_count": result.memory_selected_turn_count,
            "citation_count": len(result.validated_citations),
            "total_rag_duration_ms": round((perf_counter() - started) * 1000, 2),
            "status": result.status.value,
            "error_stage": None,
            "error_code": None,
            **(extra or {}),
        })
