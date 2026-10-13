import asyncio
from uuid import uuid4

from app.ai.retrieval.filters import RetrievalFilter
from app.ai.retrieval.scopes import RetrievalScope, build_scope_filter
from app.ai.vector_storage.service import VectorStorageService
from app.database.session import SessionFactory
from step64_test_support import step64_corpus
from step63_test_support import create_profile, make_identity


def _search(corpus, retrieval_filter=None, limit=20):
    async def run():
        async with SessionFactory() as session:
            return await VectorStorageService(session).nearest_vectors(
                [1., 0., 0.], corpus.profile_id, limit,
                retrieval_filter=retrieval_filter,
            )
    return asyncio.run(run())


def test_filters_compose_and_across_dimensions_and_or_within_dimension(step64_corpus):
    async def setup():
        corpus = step64_corpus
        hsk_l1 = 70_000_000 + uuid4().int % 1_000_000
        hsk_l2 = hsk_l1 + 1
        grammar_a = await corpus.create_lesson(
            vector=[1., 0., 0.], content_type="GRAMMAR", hsk_level_number=hsk_l1
        )
        vocab = await corpus.create_lesson(
            vector=[0., 1., 0.], content_type="VOCABULARY",
            hsk_level_id=grammar_a["level_id"],
        )
        wrong_type = await corpus.create_lesson(
            vector=[0., 0., 1.], content_type="DOCUMENT_TEXT",
            hsk_level_id=grammar_a["level_id"],
        )
        wrong_lesson = await corpus.create_lesson(
            vector=[-1., 0., 0.], content_type="GRAMMAR", hsk_level_number=hsk_l2
        )
        return grammar_a, vocab, wrong_type, wrong_lesson, hsk_l1

    grammar_a, vocab, wrong_type, wrong_lesson, hsk_l1 = asyncio.run(setup())
    retrieval_filter = RetrievalFilter(
        lesson_ids={grammar_a["lesson_id"], vocab["lesson_id"]},
        hsk_levels={hsk_l1}, content_types={"GRAMMAR", "VOCABULARY"},
        source_types={"LESSON"},
    )
    rows = _search(step64_corpus, retrieval_filter)
    assert {row.chunk_id for row in rows} == {grammar_a["chunk_id"], vocab["chunk_id"]}
    assert wrong_type["chunk_id"] not in {row.chunk_id for row in rows}
    assert wrong_lesson["chunk_id"] not in {row.chunk_id for row in rows}


def test_filter_is_applied_before_top_k_inside_nearest_vector_sql(step64_corpus):
    async def setup():
        corpus = step64_corpus
        lesson_2 = await corpus.create_lesson(vector=[1., 0., 0.])
        lesson_1 = await corpus.create_lesson(vector=[0.8, 0.6, 0.])
        return lesson_1, lesson_2

    lesson_1, lesson_2 = asyncio.run(setup())
    global_top_one = _search(step64_corpus, limit=1)
    assert global_top_one[0].chunk_id == lesson_2["chunk_id"]

    current_lesson = build_scope_filter(
        RetrievalScope.CURRENT_LESSON, trusted_lesson_id=lesson_1["lesson_id"]
    )
    filtered_top_one = _search(step64_corpus, current_lesson, limit=1)
    assert len(filtered_top_one) == 1
    assert filtered_top_one[0].chunk_id == lesson_1["chunk_id"]


def test_current_lesson_uses_knowledge_source_not_chunk_lesson_id(step64_corpus):
    async def setup():
        corpus = step64_corpus
        lesson_1 = await corpus.create_lesson(vector=[0., 1., 0.], chunk_lesson_id=None)
        lesson_2 = await corpus.create_lesson(
            vector=[1., 0., 0.], chunk_lesson_id=lesson_1["lesson_id"]
        )
        curriculum_document = await corpus.create_document(
            vector=[0.9, 0.1, 0.], category="CURRICULUM_MATERIAL"
        )
        authored_document = await corpus.create_document(
            vector=[0.7, 0.3, 0.], category="INTERNAL_AUTHORED"
        )
        return lesson_1, lesson_2, curriculum_document, authored_document

    lesson_1, lesson_2, curriculum_document, authored_document = asyncio.run(setup())
    current_lesson = build_scope_filter(
        RetrievalScope.CURRENT_LESSON, trusted_lesson_id=lesson_1["lesson_id"]
    )
    rows = _search(step64_corpus, current_lesson)
    assert [row.chunk_id for row in rows] == [lesson_1["chunk_id"]]
    assert lesson_2["chunk_id"] not in {row.chunk_id for row in rows}
    assert curriculum_document["chunk_id"] not in {row.chunk_id for row in rows}
    assert authored_document["chunk_id"] not in {row.chunk_id for row in rows}


def test_lesson_id_single_multiple_and_missing_ids(step64_corpus):
    async def setup():
        first = await step64_corpus.create_lesson(vector=[1., 0., 0.])
        second = await step64_corpus.create_lesson(vector=[0., 1., 0.])
        third = await step64_corpus.create_lesson(vector=[0., 0., 1.])
        return first, second, third

    first, second, third = asyncio.run(setup())
    one = _search(step64_corpus, RetrievalFilter(lesson_ids={first["lesson_id"]}))
    several = _search(step64_corpus, RetrievalFilter(lesson_ids={first["lesson_id"], second["lesson_id"]}))
    missing = _search(step64_corpus, RetrievalFilter(lesson_ids={uuid4()}))
    assert {row.chunk_id for row in one} == {first["chunk_id"]}
    assert {row.chunk_id for row in several} == {first["chunk_id"], second["chunk_id"]}
    assert third["chunk_id"] not in {row.chunk_id for row in several}
    assert missing == []


def test_hsk_level_numbers_filter_lesson_knowledge(step64_corpus):
    async def setup():
        level_a_number = 80_000_000 + uuid4().int % 1_000_000
        level_b_number = level_a_number + 1
        level_a = await step64_corpus.create_lesson(
            vector=[1., 0., 0.], hsk_level_number=level_a_number
        )
        level_b = await step64_corpus.create_lesson(
            vector=[0., 1., 0.], hsk_level_number=level_b_number
        )
        return level_a, level_b, level_a_number, level_b_number

    level_a, level_b, level_a_number, level_b_number = asyncio.run(setup())
    one = _search(step64_corpus, RetrievalFilter(hsk_levels={level_a_number}))
    both = _search(step64_corpus, RetrievalFilter(hsk_levels={level_a_number, level_b_number}))
    assert {row.chunk_id for row in one} == {level_a["chunk_id"]}
    assert {row.chunk_id for row in both} == {level_a["chunk_id"], level_b["chunk_id"]}


def test_content_type_and_source_type_dimensions(step64_corpus):
    async def setup():
        grammar = await step64_corpus.create_lesson(vector=[1., 0., 0.], content_type="GRAMMAR")
        vocab = await step64_corpus.create_lesson(vector=[0., 1., 0.], content_type="VOCABULARY")
        doc = await step64_corpus.create_document(vector=[0., 0., 1.])
        return grammar, vocab, doc

    grammar, vocab, doc = asyncio.run(setup())
    grammar_only = _search(step64_corpus, RetrievalFilter(content_types={"GRAMMAR"}))
    grammar_or_vocab = _search(
        step64_corpus, RetrievalFilter(content_types={"GRAMMAR", "VOCABULARY"})
    )
    docs = _search(step64_corpus, RetrievalFilter(source_types={"DOCUMENT"}))
    lessons = _search(step64_corpus, RetrievalFilter(source_types={"LESSON"}))
    assert {row.chunk_id for row in grammar_only} == {grammar["chunk_id"]}
    assert {row.chunk_id for row in grammar_or_vocab} == {grammar["chunk_id"], vocab["chunk_id"]}
    assert {row.chunk_id for row in docs} == {doc["chunk_id"]}
    assert {row.chunk_id for row in lessons} == {grammar["chunk_id"], vocab["chunk_id"]}


def test_document_category_and_language_filter_dimensions(step64_corpus):
    async def setup():
        curriculum_zh = await step64_corpus.create_document(
            vector=[1., 0., 0.], category="CURRICULUM_MATERIAL", language="zh"
        )
        authored_vi = await step64_corpus.create_document(
            vector=[0., 1., 0.], category="INTERNAL_AUTHORED", language="vi"
        )
        authored_en = await step64_corpus.create_document(
            vector=[0., 0., 1.], category="INTERNAL_AUTHORED", language="en"
        )
        lesson = await step64_corpus.create_lesson(vector=[-1., 0., 0.])
        return curriculum_zh, authored_vi, authored_en, lesson

    curriculum_zh, authored_vi, authored_en, lesson = asyncio.run(setup())
    curriculum = _search(step64_corpus, RetrievalFilter(source_categories={"CURRICULUM_MATERIAL"}))
    authored = _search(step64_corpus, RetrievalFilter(source_categories={"INTERNAL_AUTHORED"}))
    zh = _search(step64_corpus, RetrievalFilter(source_languages={"zh"}))
    vi = _search(step64_corpus, RetrievalFilter(source_languages={"vi"}))
    en = _search(step64_corpus, RetrievalFilter(source_languages={"en"}))
    all_languages = _search(step64_corpus)
    assert {row.chunk_id for row in curriculum} == {curriculum_zh["chunk_id"]}
    assert {row.chunk_id for row in authored} == {authored_vi["chunk_id"], authored_en["chunk_id"]}
    assert {row.chunk_id for row in zh} == {curriculum_zh["chunk_id"]}
    assert {row.chunk_id for row in vi} == {authored_vi["chunk_id"]}
    assert {row.chunk_id for row in en} == {authored_en["chunk_id"]}
    assert len(all_languages) == 4
    assert lesson["chunk_id"] in {row.chunk_id for row in all_languages}


def test_active_lifecycle_gates_remain_mandatory_when_filtered(step64_corpus):
    async def setup():
        corpus = step64_corpus
        active = await corpus.create_lesson(vector=[1., 0., 0.])
        processing = await corpus.create_lesson(
            vector=[0., 1., 0.], version_status="PROCESSING"
        )
        failed = await corpus.create_lesson(vector=[0., 0., 1.], version_status="FAILED")
        superseded = await corpus.create_lesson(vector=[-1., 0., 0.], version_status="SUPERSEDED")
        inactive_profile_id = await create_profile(
            corpus.state, make_identity(), status="INACTIVE"
        )
        inactive_only = await corpus.create_lesson(
            vector=[0.7, 0.7, 0.], embedding_profile_id=inactive_profile_id
        )
        return active, processing, failed, superseded, inactive_only

    active, processing, failed, superseded, inactive_only = asyncio.run(setup())
    rows = _search(step64_corpus, RetrievalFilter(source_types={"LESSON"}))
    assert [row.chunk_id for row in rows] == [active["chunk_id"]]
    assert all(item["chunk_id"] not in {row.chunk_id for row in rows} for item in (
        processing, failed, superseded, inactive_only,
    ))


def test_active_version_with_inactive_profile_vector_stays_excluded(step64_corpus):
    async def setup():
        corpus = step64_corpus
        active = await corpus.create_lesson(vector=[0., 1., 0.])
        inactive_profile_id = await create_profile(
            corpus.state, make_identity(), status="INACTIVE"
        )
        await corpus.add_profile_vector(active["chunk_id"], inactive_profile_id, [1., 0., 0.])
        return active

    active = asyncio.run(setup())
    rows = _search(
        step64_corpus,
        RetrievalFilter(lesson_ids={active["lesson_id"]}),
    )
    assert {row.chunk_id for row in rows} == {active["chunk_id"]}
    assert rows[0].distance == 1.0
