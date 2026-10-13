import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.ai.citations.schemas import CitationValidationResult, ExternalCitationSource, InternalCitationSource, ValidatedCitation
from app.ai.citations.validator import CitationValidator, TrustedExternalDomains
from app.conversation.citation_finalization import finalize_validated_assistant
from app.conversation import repository as conversation_repository
from app.conversation.service import _finalize_assistant
from app.database.models import Chunk, Conversation, KnowledgeSource, KnowledgeVersion, Message, MessageCitation
from app.database.session import SessionFactory
from tests import conversation_test_support as support


def test_validated_snapshots_commit_atomically_and_survive_chunk_delete():
    user_id, lesson_id = asyncio.run(support.seed_user_lesson())
    try:
        async def run():
            conversation = Conversation(user_id=user_id, lesson_id=lesson_id)
            async with SessionFactory.begin() as session:
                session.add(conversation)
                await session.flush()
                source = KnowledgeSource(source_type="LESSON", lesson_id=lesson_id)
                session.add(source)
                await session.flush()
                version = KnowledgeVersion(knowledge_source_id=source.id, version_number=900000, status="FAILED")
                session.add(version)
                await session.flush()
                chunk = Chunk(
                    knowledge_version_id=version.id, content="grammar", content_type="GRAMMAR",
                    chunk_index=900000, section="Live section", lesson_id=lesson_id,
                )
                session.add(chunk)
                user = Message(conversation_id=conversation.id, sequence_number=1, role="USER", content="question", status="COMPLETED")
                session.add(user)
                await session.flush()
                assistant = Message(conversation_id=conversation.id, sequence_number=2, role="ASSISTANT", content=None, status="PENDING", reply_to_message_id=user.id)
                session.add(assistant)
                await session.flush()
                assistant_id, chunk_id = assistant.id, chunk.id

            result = CitationValidator(TrustedExternalDomains(frozenset({"example.edu"}))).validate(
                text="Answer [S1] and [S1]",
                sources={"S1": InternalCitationSource("S1", chunk_id, "LESSON", "Lesson snapshot", 3, "Snapshot section")},
                citation_required=True,
            )
            async with SessionFactory() as session:
                payload = await _finalize_assistant(
                    session, assistant_id, status="COMPLETED", content=result.text, citation_result=result,
                )
                assert payload["citations"] == [{
                    "label": "S1", "source_kind": "INTERNAL_CHUNK", "title": "Lesson snapshot",
                    "source_type": "LESSON", "section": "Snapshot section", "page_number": 3,
                    "url": None, "domain": None,
                }]

            async with SessionFactory.begin() as session:
                citation = await session.scalar(select(MessageCitation).where(MessageCitation.message_id == assistant_id))
                assert citation is not None and citation.chunk_id == chunk_id
                assert citation.locator == {"page_number": 3, "section": "Snapshot section"}
                chunk = await session.get(Chunk, chunk_id)
                chunk.section = "Changed live section"
                await session.flush()
                assert citation.locator["section"] == "Snapshot section"
                await session.delete(chunk)
            async with SessionFactory() as session:
                citation = await session.scalar(select(MessageCitation).where(MessageCitation.message_id == assistant_id))
                assert citation is not None and citation.chunk_id is None
                assert citation.title == "Lesson snapshot" and citation.locator["section"] == "Snapshot section"
        asyncio.run(run())
    finally:
        async def remove_test_knowledge():
            async with SessionFactory.begin() as session:
                source_ids = select(KnowledgeSource.id).where(KnowledgeSource.lesson_id == lesson_id)
                version_ids = select(KnowledgeVersion.id).where(KnowledgeVersion.knowledge_source_id.in_(source_ids))
                await session.execute(delete(Chunk).where(Chunk.knowledge_version_id.in_(version_ids)))
                await session.execute(delete(KnowledgeVersion).where(KnowledgeVersion.knowledge_source_id.in_(source_ids)))
                await session.execute(delete(KnowledgeSource).where(KnowledgeSource.lesson_id == lesson_id))
        asyncio.run(remove_test_knowledge())
        support.scenario_cleanup(user_id, lesson_id)


def test_failed_finalization_has_no_citation_rows():
    user_id, lesson_id = asyncio.run(support.seed_user_lesson())
    try:
        async def run():
            async with SessionFactory.begin() as session:
                conversation = Conversation(user_id=user_id, lesson_id=lesson_id)
                session.add(conversation)
                await session.flush()
                assistant = Message(conversation_id=conversation.id, sequence_number=1, role="ASSISTANT", content=None, status="PENDING")
                session.add(assistant)
                await session.flush()
                assistant_id = assistant.id
            async with SessionFactory() as session:
                await _finalize_assistant(session, assistant_id, status="FAILED", content=None)
            async with SessionFactory() as session:
                assistant = await session.get(Message, assistant_id)
                citations = list((await session.scalars(select(MessageCitation).where(MessageCitation.message_id == assistant_id))).all())
                assert assistant.status == "FAILED" and assistant.content is None and citations == []
        asyncio.run(run())
    finally:
        support.scenario_cleanup(user_id, lesson_id)


def test_reusable_success_finalizer_does_not_commit():
    user_id, lesson_id = asyncio.run(support.seed_user_lesson())
    try:
        async def run():
            async with SessionFactory.begin() as session:
                conversation = Conversation(user_id=user_id, lesson_id=lesson_id)
                session.add(conversation)
                await session.flush()
                assistant = Message(conversation_id=conversation.id, sequence_number=1, role="ASSISTANT", content=None, status="PENDING")
                session.add(assistant)
                await session.flush()
                assistant_id = assistant.id
            result = CitationValidator(TrustedExternalDomains(frozenset({"example.edu"}))).validate(
                text="[S1]",
                sources={"S1": ExternalCitationSource("S1", "Title", "https://example.edu/page")},
                citation_required=True,
            )
            async with SessionFactory() as session:
                assistant = await session.get(Message, assistant_id)
                await finalize_validated_assistant(session, assistant_message=assistant, content=result.text, validation=result)
                assert assistant.status == "COMPLETED"
                assert await session.scalar(select(MessageCitation.id).where(MessageCitation.message_id == assistant_id)) is not None
                await session.rollback()
            async with SessionFactory() as session:
                assistant = await session.get(Message, assistant_id)
                assert assistant.status == "PENDING" and assistant.content is None
                assert await session.scalar(select(MessageCitation.id).where(MessageCitation.message_id == assistant_id)) is None
        asyncio.run(run())
    finally:
        support.scenario_cleanup(user_id, lesson_id)


def test_constraint_failure_rolls_back_completion_and_partial_citations():
    user_id, lesson_id = asyncio.run(support.seed_user_lesson())
    try:
        async def run():
            async with SessionFactory.begin() as session:
                conversation = Conversation(user_id=user_id, lesson_id=lesson_id)
                session.add(conversation)
                await session.flush()
                assistant = Message(conversation_id=conversation.id, sequence_number=1, role="ASSISTANT", content=None, status="PENDING")
                session.add(assistant)
                await session.flush()
                assistant_id = assistant.id
            repeated = ValidatedCitation(label="S1", source_kind="EXTERNAL_URL", title="test", url="https://example.edu", domain="example.edu")
            result = CitationValidationResult("[S1]", ("S1", "S1"), (repeated, repeated), 2, 2)
            with pytest.raises(IntegrityError):
                async with SessionFactory() as session:
                    await _finalize_assistant(session, assistant_id, status="COMPLETED", content="[S1]", citation_result=result)
            async with SessionFactory() as session:
                assistant = await session.get(Message, assistant_id)
                citations = list((await session.scalars(select(MessageCitation).where(MessageCitation.message_id == assistant_id))).all())
                assert assistant.status == "PENDING" and assistant.content is None and citations == []
        asyncio.run(run())
    finally:
        support.scenario_cleanup(user_id, lesson_id)


def test_validator_and_finalizer_logs_redact_answer_source_url_and_database_error(caplog, monkeypatch):
    import logging

    caplog.set_level(logging.INFO, logger="app.ai.citations")
    caplog.set_level(logging.INFO, logger="app.conversation")
    user_id, lesson_id = asyncio.run(support.seed_user_lesson())
    try:
        async def run():
            result = CitationValidator(TrustedExternalDomains(frozenset({"example.edu"}))).validate(
                text="SENTINEL_GENERATED_ANSWER [S1]",
                sources={"S1": ExternalCitationSource(
                    "S1", "SENTINEL_SOURCE_CONTENT", "https://example.edu/?key=SENTINEL_URL_SECRET",
                )},
                citation_required=True,
            )
            async with SessionFactory.begin() as session:
                conversation = Conversation(user_id=user_id, lesson_id=lesson_id)
                session.add(conversation)
                await session.flush()
                good = Message(conversation_id=conversation.id, sequence_number=1, role="ASSISTANT", content=None, status="PENDING")
                bad = Message(conversation_id=conversation.id, sequence_number=2, role="ASSISTANT", content=None, status="PENDING")
                session.add_all([good, bad])
                await session.flush()
                good_id, bad_id = good.id, bad.id
            async with SessionFactory() as session:
                await _finalize_assistant(
                    session, good_id, status="COMPLETED", content=result.text, citation_result=result,
                )

            async def fail_insert(*_args, **_kwargs):
                raise RuntimeError("SENTINEL_DB_EXCEPTION")
            monkeypatch.setattr(conversation_repository, "add_message_citations", fail_insert)
            with pytest.raises(RuntimeError):
                async with SessionFactory() as session:
                    await _finalize_assistant(
                        session, bad_id, status="COMPLETED", content=result.text, citation_result=result,
                    )
        asyncio.run(run())
        for sentinel in (
            "SENTINEL_GENERATED_ANSWER", "SENTINEL_SOURCE_CONTENT",
            "SENTINEL_DB_EXCEPTION", "SENTINEL_URL_SECRET",
        ):
            assert sentinel not in caplog.text
        assert "assistant_message_finalized" in caplog.text
        assert "citation_validation_completed" in caplog.text
    finally:
        support.scenario_cleanup(user_id, lesson_id)
