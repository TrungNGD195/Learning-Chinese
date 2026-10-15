from __future__ import annotations

import asyncio
import math
from uuid import UUID

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.database.models import HSKLevel, Lesson
from app.database.session import SessionFactory
from app.ai.embeddings.sentence_transformer_provider import SentenceTransformerEmbeddingProvider
from app.ai.reranking.transformers_provider import TransformersRerankerProvider
from app.ai.reranking.service import RerankingService
from app.ai.retrieval.filters import RetrievalFilter
from app.ai.retrieval.service import SemanticRetrievalService
from app.evaluation.step73.fixtures import EVALUATION_LESSON_NUMBER_BASE


def test_step73_wires_real_retrieval_and_reranking_services_without_llm():
    async def run():
        settings = get_settings().model_copy(update={"rag_evidence_calibration_mode": True,
                                                       "rag_min_rerank_score": None})
        async with SessionFactory() as session:
            lesson = await session.scalar(select(Lesson).where(
                Lesson.lesson_number > EVALUATION_LESSON_NUMBER_BASE,
                Lesson.lesson_number <= EVALUATION_LESSON_NUMBER_BASE + 3,
                Lesson.status == "PUBLISHED",
            ).order_by(Lesson.lesson_number).limit(1))
            if lesson is None:
                pytest.skip("Run the Step 7.3 --ensure bootstrap before this integration check")
            hsk = await session.get(HSKLevel, lesson.hsk_level_id)
            lesson_id = UUID(str(lesson.id))
            hsk_number = hsk.level_number
            await session.rollback()
            embedding = SentenceTransformerEmbeddingProvider(settings)
            reranker = TransformersRerankerProvider(settings)
            candidates = await SemanticRetrievalService(
                session, provider=embedding, settings=settings,
            ).retrieve("你好 means hello; what does 你好 mean?", retrieval_filter=RetrievalFilter(
                lesson_ids=frozenset({lesson_id}), hsk_levels=frozenset({hsk_number}),
                source_types=frozenset({"LESSON"}),
            ))
            result = await RerankingService(provider=reranker, settings=settings).rerank(
                "你好 means hello; what does 你好 mean?", candidates,
            )
            assert embedding.identity.model_version == "5617a9f61b028005a4858fdac845db406aefb181"
            assert reranker.identity.model_revision == "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"
            assert result.scored_candidates
            assert all(candidate.source_lesson_id == lesson_id for candidate in candidates)
            assert all(math.isfinite(candidate.rerank_score) for candidate in result.scored_candidates)
            await session.rollback()
    asyncio.run(run())
