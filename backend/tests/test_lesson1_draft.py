import asyncio
from uuid import uuid4

from sqlalchemy import select, text, func

from app.admin.schemas import AssessmentCreateRequest
from app.ai.generation.schemas import LessonExerciseGenerationRequest, PeriodicTestGenerationRequest
from app.database.models import Assessment, HSKLevel, LessonVocabulary, Question, QuestionOption
from app.database.session import SessionFactory
from app.exercise.grading import DeterministicGrader, GradeResult
from app.exercise.service import calculate_score
from scripts.create_hsk1_lesson1_draft import create_draft, load_definition


def test_type_defaults_preserve_explicit_values():
    lesson_id = uuid4()
    assert AssessmentCreateRequest(type="LESSON_EXERCISE", lesson_id=lesson_id, title="Practice").pass_threshold == 80
    assert AssessmentCreateRequest(type="PERIODIC_TEST", title="Test").pass_threshold == 90
    assert AssessmentCreateRequest(type="LESSON_EXERCISE", lesson_id=lesson_id, title="Custom", pass_threshold=85).pass_threshold == 85
    common = {"question_count": 3, "allowed_types": ["multiple_choice"], "difficulty": "EASY"}
    assert LessonExerciseGenerationRequest(type="LESSON_EXERCISE", lesson_id=lesson_id, **common).pass_threshold == 80
    assert PeriodicTestGenerationRequest(type="PERIODIC_TEST", lesson_ids=[lesson_id], vocabulary_ids=[uuid4()], **common).pass_threshold == 90


def test_draft_import_and_sql_defaults_with_real_answer_keys():
    async def run():
        definition, questions = load_definition()
        number = 8_000_000 + uuid4().int % 1_000_000
        definition["lesson"]["hsk_level"] = number
        async with SessionFactory() as session:
            try:
                level = HSKLevel(level_number=number, order_index=number)
                session.add(level)
                await session.flush()
                imported = await create_draft(session, definition, questions)
                assert imported["lesson_status"] == imported["assessment_status"] == "DRAFT"
                assert imported["pass_threshold"] == 80
                from app.curriculum.service import get_curriculum
                assert (await get_curriculum(session, uuid4(), level.id))["units"] == []
                repeated = await create_draft(session, definition, questions)
                assert repeated["created"] is False
                assert repeated["lesson_id"] == imported["lesson_id"]
                assert await session.scalar(select(func.count()).select_from(LessonVocabulary).where(LessonVocabulary.lesson_id == imported["lesson_id"])) == 12
                assessment_id = imported["assessment_id"]
                stored = (await session.execute(select(Question).where(Question.assessment_id == assessment_id).order_by(Question.order_index))).scalars().all()
                assert len(stored) == 20
                grading_questions, results = [], {}
                for row in stored:
                    options = (await session.execute(select(QuestionOption).where(QuestionOption.question_id == row.id))).scalars().all()
                    question = {"id": row.id, "type": row.type, "points": row.points, "config": row.config,
                                "reference_answer": row.reference_answer, "correct_option_ids": {str(o.id) for o in options if o.is_correct}}
                    if row.type == "multiple_choice":
                        assert len([o for o in options if o.is_correct]) == 1
                        answer = {"option_id": next(iter(question["correct_option_ids"]))}
                    elif row.type == "fill_blank": answer = {"text": row.reference_answer}
                    elif row.type == "matching": answer = {"pairs": row.config["correct_pairs"]}
                    else: answer = {"item_ids": row.config["correct_order"]}
                    grading_questions.append(question)
                    results[row.id] = DeterministicGrader().grade(question, answer)
                    assert results[row.id].is_correct is True
                assert calculate_score(grading_questions, results, 80) == (100, True)
                for row in stored[:4]: results[row.id] = GradeResult("GRADED", 0, False)
                assert calculate_score(grading_questions, results, 80) == (80, True)
                results[stored[4].id] = GradeResult("GRADED", 0, False)
                assert calculate_score(grading_questions, results, 80) == (75, False)
                for kind, expected in (("LESSON_EXERCISE", 80), ("PERIODIC_TEST", 90)):
                    value = await session.scalar(text("INSERT INTO assessments (id,type,lesson_id,title,status) VALUES (:id,:kind,:lesson,'SQL default','DRAFT') RETURNING pass_threshold"),
                                                 {"id": uuid4(), "kind": kind, "lesson": imported["lesson_id"] if kind == "LESSON_EXERCISE" else None})
                    assert value == expected
                    row = Assessment(type=kind, lesson_id=imported["lesson_id"] if kind == "LESSON_EXERCISE" else None, title="ORM default", status="DRAFT")
                    session.add(row)
                    await session.flush()
                    assert row.pass_threshold == expected
            finally:
                await session.rollback()
    asyncio.run(run())
