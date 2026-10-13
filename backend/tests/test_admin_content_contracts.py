import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.database.models import (Chunk, Grammar, HSKLevel, KnowledgeSource, KnowledgeVersion,
                                 Lesson, LessonGrammar, LessonVocabulary, Vocabulary)
from app.database.session import SessionFactory
from app.main import app


def test_admin_vocabulary_and_grammar_attach_contracts(persisted_admin_override):
    lesson_id, vocabulary_id, grammar_id = uuid4(), uuid4(), uuid4()

    async def seed():
        async with SessionFactory.begin() as session:
            hsk = (await session.execute(select(HSKLevel).where(HSKLevel.level_number == 1))).scalar_one()
            lesson = Lesson(id=lesson_id, hsk_level_id=hsk.id, lesson_number=950000 + lesson_id.int % 50000,
                            title="Admin contract lesson", status="DRAFT")
            vocabulary = Vocabulary(id=vocabulary_id, hanzi="字-test", pinyin="zì", vietnamese_meaning="chữ",
                                    part_of_speech="noun")
            grammar = Grammar(id=grammar_id, name="Shared grammar", structure="A", explanation="Shared explanation",
                              usage="Shared usage")
            session.add_all([lesson, vocabulary, grammar])

    asyncio.run(seed())
    try:
        with TestClient(app) as client:
            no_mode = client.post(f"/api/v1/admin/lessons/{lesson_id}/vocabulary", json={"order_index": 1})
            assert no_mode.status_code == 422
            mixed_mode = client.post(f"/api/v1/admin/lessons/{lesson_id}/vocabulary", json={
                "vocabulary_id": str(vocabulary_id), "hanzi": "also new", "pinyin": "x", "vietnamese_meaning": "x",
                "order_index": 1})
            assert mixed_mode.status_code == 422
            existing_vocab = client.post(f"/api/v1/admin/lessons/{lesson_id}/vocabulary",
                                         json={"vocabulary_id": str(vocabulary_id), "order_index": 1})
            assert existing_vocab.status_code == 201, existing_vocab.text
            new_vocab = client.post(f"/api/v1/admin/lessons/{lesson_id}/vocabulary",
                                    json={"hanzi": "新字", "pinyin": "xīn zì", "vietnamese_meaning": "chữ mới",
                                          "order_index": 2})
            assert new_vocab.status_code == 201 and new_vocab.json()["part_of_speech"] is None
            vocab_link = new_vocab.json()["id"]
            patched_vocab = client.patch(f"/api/v1/admin/lessons/{lesson_id}/vocabulary/{vocab_link}",
                                         json={"note": "association update", "order_index": 3})
            assert patched_vocab.status_code == 200 and patched_vocab.json()["note"] == "association update"
            assert client.delete(f"/api/v1/admin/lessons/{lesson_id}/vocabulary/{existing_vocab.json()['id']}").status_code == 200
            assert client.delete(f"/api/v1/admin/lessons/{lesson_id}/vocabulary/{vocab_link}").status_code == 200

            existing_grammar = client.post(f"/api/v1/admin/lessons/{lesson_id}/grammar",
                                           json={"grammar_id": str(grammar_id), "order_index": 1})
            assert existing_grammar.status_code == 201
            new_grammar = client.post(f"/api/v1/admin/lessons/{lesson_id}/grammar",
                                      json={"name": "New grammar", "explanation": "Required explanation",
                                            "order_index": 2})
            assert new_grammar.status_code == 201
            assert new_grammar.json()["structure"] is None and new_grammar.json()["usage"] is None
            grammar_link = new_grammar.json()["id"]
            patched_grammar = client.patch(f"/api/v1/admin/lessons/{lesson_id}/grammar/{grammar_link}",
                                          json={"name": "Updated grammar", "note": "association update"})
            assert patched_grammar.status_code == 200 and patched_grammar.json()["name"] == "Updated grammar"
            assert client.delete(f"/api/v1/admin/lessons/{lesson_id}/grammar/{existing_grammar.json()['id']}").status_code == 200
            assert client.delete(f"/api/v1/admin/lessons/{lesson_id}/grammar/{grammar_link}").status_code == 200

            archived_vocab = client.post(f"/api/v1/admin/lessons/{lesson_id}/vocabulary",
                                         json={"vocabulary_id": str(vocabulary_id), "order_index": 4}).json()
            archived_grammar = client.post(f"/api/v1/admin/lessons/{lesson_id}/grammar",
                                           json={"grammar_id": str(grammar_id), "order_index": 4}).json()
            assert client.post(f"/api/v1/admin/lessons/{lesson_id}/publish").status_code == 200
            assert client.delete(f"/api/v1/admin/lessons/{lesson_id}/vocabulary/{archived_vocab['id']}").status_code == 409
            assert client.delete(f"/api/v1/admin/lessons/{lesson_id}/grammar/{archived_grammar['id']}").status_code == 409
            assert client.post(f"/api/v1/admin/lessons/{lesson_id}/archive").status_code == 200
            assert client.post(f"/api/v1/admin/lessons/{lesson_id}/vocabulary",
                               json={"vocabulary_id": str(vocabulary_id), "order_index": 5}).status_code == 409
            assert client.patch(f"/api/v1/admin/lessons/{lesson_id}/vocabulary/{archived_vocab['id']}",
                                json={"note": "no"}).status_code == 409
            assert client.delete(f"/api/v1/admin/lessons/{lesson_id}/vocabulary/{archived_vocab['id']}").status_code == 409
            assert client.post(f"/api/v1/admin/lessons/{lesson_id}/grammar",
                               json={"grammar_id": str(grammar_id), "order_index": 5}).status_code == 409
            assert client.patch(f"/api/v1/admin/lessons/{lesson_id}/grammar/{archived_grammar['id']}",
                                json={"note": "no"}).status_code == 409
            assert client.delete(f"/api/v1/admin/lessons/{lesson_id}/grammar/{archived_grammar['id']}").status_code == 409
    finally:
        async def cleanup():
            async with SessionFactory.begin() as session:
                source_ids = select(KnowledgeSource.id).where(KnowledgeSource.lesson_id == lesson_id)
                version_ids = select(KnowledgeVersion.id).where(KnowledgeVersion.knowledge_source_id.in_(source_ids))
                await session.execute(delete(Chunk).where(Chunk.knowledge_version_id.in_(version_ids)))
                await session.execute(delete(KnowledgeVersion).where(KnowledgeVersion.knowledge_source_id.in_(source_ids)))
                await session.execute(delete(KnowledgeSource).where(KnowledgeSource.lesson_id == lesson_id))
                vocab_ids = (await session.execute(select(LessonVocabulary.vocabulary_id).where(LessonVocabulary.lesson_id == lesson_id))).scalars().all()
                grammar_ids = (await session.execute(select(LessonGrammar.grammar_id).where(LessonGrammar.lesson_id == lesson_id))).scalars().all()
                await session.execute(delete(LessonVocabulary).where(LessonVocabulary.lesson_id == lesson_id))
                await session.execute(delete(LessonGrammar).where(LessonGrammar.lesson_id == lesson_id))
                if vocab_ids: await session.execute(delete(Vocabulary).where(Vocabulary.id.in_(vocab_ids)))
                if grammar_ids: await session.execute(delete(Grammar).where(Grammar.id.in_(grammar_ids)))
                await session.execute(delete(Vocabulary).where(Vocabulary.id == vocabulary_id))
                await session.execute(delete(Grammar).where(Grammar.id == grammar_id))
                await session.execute(delete(Lesson).where(Lesson.id == lesson_id))
        asyncio.run(cleanup())
