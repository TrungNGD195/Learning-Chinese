import asyncio
from copy import deepcopy
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.curriculum.service import admin_publish_lesson_package
from app.database.engine import engine
from app.database.models import Assessment, HSKLevel, Lesson, LessonReading, Question
from app.exercise.grading import DeterministicGrader, GradeResult
from app.exercise.service import calculate_score
from scripts.import_curriculum_refresh import load_definitions as load_prior, refresh, word_key
from scripts.import_hsk3_curriculum import load_definitions


def test_hsk3_covers_the_docx_including_both_parts_of_lesson_3_without_duplicates():
    definitions = load_definitions()
    assert len(definitions) == 15
    assert sum(len(d['readings']) for d in definitions) == 60
    all_words = [word_key(w) for d in load_prior() + definitions for w in d['vocabulary']]
    assert len(all_words) == len(set(all_words))
    third = definitions[2]
    assert {'草原', '迪士尼乐园', '海鲜'} <= {w['hanzi'] for w in third['vocabulary']}
    assert len({r['content'] for r in third['readings']}) == 4
    for d in definitions:
        for word in d['vocabulary']:
            assert word['example'] and len(word['example'].splitlines()) == 3
            assert len(word['example'].splitlines()[0]) <= 110
        assert all(r['content'] and r['pinyin'] and r['vietnamese_translation'] for r in d['readings'])
        assert d['grammar'] and len(d['questions']) == 30
        assert all(q['rubric'] for q in d['questions'])
        assert all((o['hsk'], o['lesson']) <= (3, d['lesson']['lesson_number']) for q in d['questions'] for o in q['knowledge_origins'])
    for lesson, word, pronunciation in [(2, '着', 'zháo'), (2, '还', 'huán'), (8, '了', 'liǎo'), (8, '得', 'dé')]:
        entry = next(w for w in definitions[lesson - 1]['vocabulary'] if w['hanzi'] == word)
        assert entry['pinyin'] == pronunciation and entry['note']
    repayment = next(line for line in definitions[1]['readings'][2]['pinyin'].splitlines() if 'màn màn' in line)
    assert 'màn màn huán' in repayment
    snow = next(line for line in definitions[10]['readings'][2]['pinyin'].splitlines() if 'xuě' in line and 'shàng' in line)
    assert 'xuě dì shàng' in snow


def test_all_450_answer_keys_grade_and_80_percent_boundary_is_exact():
    grader = DeterministicGrader()
    for definition in load_definitions():
        questions, results = [], {}
        for index, entry in enumerate(definition['questions']):
            q = {**entry, 'id': str(index), 'correct_option_ids': {str(i) for i, o in enumerate(entry.get('options', [])) if o['is_correct']}}
            if q['type'] == 'multiple_choice':
                answer = {'option_id': next(iter(q['correct_option_ids']))}
            elif q['type'] == 'fill_blank':
                answer = {'text': q['reference_answer']}
            elif q['type'] == 'matching':
                answer = {'pairs': q['config']['correct_pairs']}
            else:
                answer = {'item_ids': q['config']['correct_order']}
            result = grader.grade(q, answer)
            assert result.is_correct and result.score == 1
            questions.append(q)
            results[q['id']] = result
        assert calculate_score(questions, results, 80) == (100, True)
        for q in questions[:6]:
            results[q['id']] = GradeResult('GRADED', 0, False)
        assert calculate_score(questions, results, 80) == (80, True)
        results[questions[6]['id']] = GradeResult('GRADED', 0, False)
        assert calculate_score(questions, results, 80) == (76.67, False)


def test_hsk3_import_publish_is_atomic_and_reimport_preserves_admin_edits():
    async def run():
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                async with AsyncSession(bind=connection, expire_on_commit=False, join_transaction_mode='create_savepoint') as session:
                    number = 30_000_000 + uuid4().int % 1_000_000
                    level = HSKLevel(level_number=number, order_index=number)
                    session.add(level)
                    await session.flush()
                    definitions = deepcopy(load_definitions())
                    for d in definitions:
                        d['lesson']['hsk_level'] = number
                        d['key'] += f'-test-{number}'
                    result = await refresh(session, definitions)
                    assert len(result) == 15 and all(r['status'] == 'DRAFT' for r in result)
                    rows = (await session.scalars(select(Lesson).where(Lesson.hsk_level_id == level.id).order_by(Lesson.lesson_number))).all()
                    for lesson in rows:
                        await admin_publish_lesson_package(session, lesson.id)
                    assert all(lesson.status == 'PUBLISHED' for lesson in rows)
                    assert await session.scalar(select(func.count()).select_from(Assessment).where(Assessment.lesson_id.in_([r.id for r in rows]), Assessment.status == 'PUBLISHED')) == 15
                    assert await session.scalar(select(func.count()).select_from(LessonReading).where(LessonReading.lesson_id.in_([r.id for r in rows]))) == 60
                    q_count = await session.scalar(select(func.count()).select_from(Question))
                    rows[0].title = 'Edited by admin'
                    await session.flush()
                    again = await refresh(session, definitions)
                    assert all(r['action'] == 'already_imported_preserved' for r in again)
                    assert rows[0].title == 'Edited by admin' and rows[0].status == 'PUBLISHED'
                    assert await session.scalar(select(func.count()).select_from(Question)) == q_count
                    await session.commit()
            finally:
                await transaction.rollback()
    asyncio.run(run())
