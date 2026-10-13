import asyncio

from app.ai.retrieval.service import SemanticRetrievalService
from app.database.session import SessionFactory
from step62_test_support import step62_state
from step63_test_support import FakeProvider, create_profile, make_identity, settings_with_candidate_k


def test_deterministic_chinese_learning_semantic_retrieval_smoke(step62_state):
    async def run():
        identity = make_identity()
        profile_id = await create_profile(step62_state, identity)
        source_id = await step62_state.create_source()
        _, chunk_ids = await step62_state.create_version(
            source_id,
            status="ACTIVE",
            vectors=[
                [1., 0., 0.],  # deterministic semantic match for 了 usage
                [0., 1., 0.],  # unrelated tone-mark reference
            ],
            profile_vectors={profile_id: [[1., 0., 0.], [0., 1., 0.]]},
        )
        # Give the persisted chunks Chinese-learning corpus content.
        from app.database.models import Chunk
        async with SessionFactory.begin() as session:
            relevant = await session.get(Chunk, chunk_ids[0])
            unrelated = await session.get(Chunk, chunk_ids[1])
            relevant.content = "了解 ‘了’ 的变化和用法。"
            unrelated.content = "四声的标记与发音练习。"
        async with SessionFactory() as session:
            candidates = await SemanticRetrievalService(
                session,
                provider=FakeProvider(identity, vector=[1., 0., 0.]),
                settings=settings_with_candidate_k(1),
            ).retrieve("怎么用 了")
        assert len(candidates) == 1
        assert candidates[0].chunk_id == chunk_ids[0]
        assert "了" in candidates[0].content
        assert candidates[0].rank == 1
        assert candidates[0].retrieval_score == 1.0

    asyncio.run(run())
