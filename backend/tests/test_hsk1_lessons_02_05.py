import asyncio
from copy import deepcopy
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from app.curriculum.service import get_curriculum
from app.database.models import Assessment, CurriculumUnit, HSKLevel, Lesson, LessonGrammar, LessonReading, LessonVocabulary, Question, QuestionOption
from app.database.session import SessionFactory
from app.exercise.grading import DeterministicGrader, GradeResult
from app.exercise.service import calculate_score
from scripts.create_hsk1_lessons_02_05_drafts import create_drafts, load_definitions


def test_manifests_cover_textbook_without_source_notes_or_pronunciation_theory():
    definitions = load_definitions()
    assert [len(d['vocabulary']) for d in definitions] == [15, 30, 42, 31]
    assert [len(d['grammar']) for d in definitions] == [4, 6, 8, 6]
    assert [len(d['readings']) for d in definitions] == [4, 3, 3, 3]
    assert [d['lesson']['lesson_number'] for d in definitions] == [2, 3, 4, 5]
    for definition in definitions:
        assert not any('phát âm' in entry['name'].lower() for entry in definition['grammar'])
        assert all(row['content'] and row['pinyin'] and row['vietnamese_translation'] for row in definition['readings'])


def test_import_is_draft_only_idempotent_preserves_edits_and_has_working_answer_keys():
    async def run():
        async with SessionFactory() as session:
            try:
                number = 9_000_000 + uuid4().int % 1_000_000
                level = HSKLevel(level_number=number, order_index=number)
                session.add(level)
                await session.flush()
                definitions = load_definitions()
                report = await create_drafts(session, definitions, level_number=number)
                assert len(report) == 4 and all(item['status'] == 'DRAFT' for item in report)
                assert (await get_curriculum(session, uuid4(), level.id))['units'] == []
                for item, definition in zip(report, definitions):
                    lesson_id, assessment_id = UUID(item['lesson_id']), UUID(item['assessment_id'])
                    assert (await session.get(Assessment, assessment_id)).status == 'DRAFT'
                    for model, expected in [(LessonVocabulary, len(definition['vocabulary'])), (LessonGrammar, len(definition['grammar'])), (LessonReading, len(definition['readings']))]:
                        assert await session.scalar(select(func.count()).select_from(model).where(model.lesson_id == lesson_id)) == expected
                    rows = (await session.execute(select(Question).where(Question.assessment_id == assessment_id).order_by(Question.order_index))).scalars().all()
                    assert len(rows) == 30
                    grading_questions, results = [], {}
                    for row in rows:
                        options = (await session.execute(select(QuestionOption).where(QuestionOption.question_id == row.id))).scalars().all()
                        question = {'id': row.id, 'type': row.type, 'points': row.points, 'config': row.config,
                                    'reference_answer': row.reference_answer, 'correct_option_ids': {str(option.id) for option in options if option.is_correct}}
                        if row.type == 'multiple_choice':
                            answer = {'option_id': next(iter(question['correct_option_ids']))}
                        elif row.type == 'fill_blank':
                            answer = {'text': row.reference_answer}
                        elif row.type == 'matching':
                            answer = {'pairs': row.config['correct_pairs']}
                        else:
                            answer = {'item_ids': row.config['correct_order']}
                        graded = DeterministicGrader().grade(question, answer)
                        assert graded.is_correct and graded.score == 1
                        grading_questions.append(question)
                        results[row.id] = graded
                    for row in rows[:6]:
                        results[row.id] = GradeResult('GRADED', 0, False)
                    assert calculate_score(grading_questions, results, 80) == (80, True)
                    results[rows[6].id] = GradeResult('GRADED', 0, False)
                    assert calculate_score(grading_questions, results, 80) == (76.67, False)
                first = await session.get(Lesson, UUID(report[0]['lesson_id']))
                first.title = 'Administrator-edited draft'
                await session.flush()
                repeated = await create_drafts(session, definitions, level_number=number)
                assert all(not row['created'] for row in repeated)
                assert first.title == 'Administrator-edited draft'
                assert await session.scalar(select(func.count()).select_from(CurriculumUnit).where(CurriculumUnit.hsk_level_id == level.id)) == 4
            finally:
                await session.rollback()
    asyncio.run(run())


def test_conflicting_number_stops_entire_batch_before_creating_other_lessons():
    async def run():
        async with SessionFactory() as session:
            try:
                number = 10_000_000 + uuid4().int % 1_000_000
                level = HSKLevel(level_number=number, order_index=number)
                session.add(level)
                await session.flush()
                session.add(Lesson(hsk_level_id=level.id, lesson_number=4, title='Existing user content', status='DRAFT'))
                await session.flush()
                with pytest.raises(RuntimeError, match='another ID'):
                    await create_drafts(session, deepcopy(load_definitions()), level_number=number)
                assert await session.scalar(select(func.count()).select_from(Lesson).where(Lesson.hsk_level_id == level.id)) == 1
            finally:
                await session.rollback()
    asyncio.run(run())
