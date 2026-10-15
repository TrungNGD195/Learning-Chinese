from __future__ import annotations

from uuid import uuid4

from app.ai.embeddings.schemas import EmbeddingProviderIdentity
from app.core.config import Settings
from app.database.models import EmbeddingProfile
from app.database.session import SessionFactory


def make_identity(*, dimensions: int = 3) -> EmbeddingProviderIdentity:
    nonce = uuid4().hex
    return EmbeddingProviderIdentity(
        provider="LOCAL",
        provider_version=f"step63-provider-{nonce}",
        model_name=f"step63-model-{nonce}",
        model_version="test-revision",
        dimensions=dimensions,
        embedding_input_version="step63-input-v1",
        normalize_embeddings=True,
    )


async def create_profile(state, identity: EmbeddingProviderIdentity, *, status="ACTIVE"):
    profile_id = await state.create_profile(status=status, dimensions=identity.dimensions)
    async with SessionFactory.begin() as session:
        profile = await session.get(EmbeddingProfile, profile_id)
        profile.provider = identity.provider
        profile.provider_version = identity.provider_version
        profile.model_name = identity.model_name
        profile.model_version = identity.model_version
        profile.embedding_input_version = identity.embedding_input_version
        profile.normalize_embeddings = identity.normalize_embeddings
    return profile_id


def settings_with_candidate_k(candidate_k: int = 20) -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        debug=False,
        test_database_url="postgresql+psycopg://test:test@localhost/chinese_learning_test",
        secret_key="step63-test-only-signing-key",
        rag_retrieval_candidate_k=candidate_k,
    )


_DEFAULT_VECTOR = object()


class FakeProvider:
    def __init__(self, identity, vector=_DEFAULT_VECTOR, *, error=None, on_embed=None):
        self.identity = identity
        self.vector = [1.0, 0.0, 0.0] if vector is _DEFAULT_VECTOR else vector
        self.error = error
        self.on_embed = on_embed
        self.queries = []
        self.documents_calls = 0

    async def embed_query(self, text: str):
        self.queries.append(text)
        if self.on_embed:
            self.on_embed()
        if self.error:
            raise self.error
        return self.vector

    async def embed_documents(self, texts, *, batch_size: int):
        self.documents_calls += 1
        raise AssertionError("retrieval must not call embed_documents")
