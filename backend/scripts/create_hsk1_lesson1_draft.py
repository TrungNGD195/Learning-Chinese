"""Create the reviewed HSK1 lesson-1 draft, without publishing or overwriting.

Run from backend: python -m scripts.create_hsk1_lesson1_draft --apply
Without --apply, validates and describes the import without touching the database.
The caller owns the transaction so lesson, content and exercise are atomic.
"""
import argparse
import asyncio
import json
from pathlib import Path
from uuid import UUID, uuid5

from sqlalchemy import select, func

from app.admin.schemas import QuestionCreateRequest, VocabularyAttachRequest
from app.database.models import (
    Assessment, CurriculumUnit, HSKLevel, Lesson, LessonVocabulary,
    Question, QuestionOption, Vocabulary,
)
from app.database.session import SessionFactory

NAMESPACE = UUID("23c010fb-f291-4d79-af36-983a116bf02a")
DEFINITION_PATH = Path(__file__).resolve().parents[1] / "content/hsk1/lesson-01.json"


def load_definition():
    definition = json.loads(DEFINITION_PATH.read_text(encoding="utf-8"))
    assert len(definition["vocabulary"]) == 12
    assert len({v["hanzi"] for v in definition["vocabulary"]}) == 12
    for index, item in enumerate(definition["vocabulary"], 1):
        VocabularyAttachRequest.model_validate({
            **{k: v for k, v in item.items() if k != "illustration"}, "order_index": index,
        })
        assert item["illustration"] and item["example"] and item["part_of_speech"]
    questions = [QuestionCreateRequest.model_validate({
        **question, "order_index": index, "points": 1,
    }) for index, question in enumerate(definition["questions"], 1)]
    assert len(questions) == 20 and sum(q.points for q in questions) == 20
    assert {q.type for q in questions} == {"multiple_choice", "fill_blank", "matching", "reorder_sentence"}
    assert definition["assessment"]["pass_threshold"] == 80
    return definition, questions


async def create_draft(session, definition, questions):
    lesson_id = uuid5(NAMESPACE, definition["key"] + ":lesson")
    assessment_id = uuid5(NAMESPACE, definition["key"] + ":exercise")
    level = (await session.execute(select(HSKLevel).where(HSKLevel.level_number == definition["lesson"]["hsk_level"]).with_for_update())).scalar_one_or_none()
    if level is None:
        raise RuntimeError("HSK1 must exist before importing its lesson.")
    existing = (await session.execute(select(Lesson).where(
        Lesson.hsk_level_id == level.id, Lesson.lesson_number == 1,
    ))).scalar_one_or_none()
    if existing is not None:
        if existing.id != lesson_id:
            raise RuntimeError("A different HSK1 lesson 1 already exists; it has not been overwritten.")
        exercise = await session.get(Assessment, assessment_id)
        if exercise is None or exercise.lesson_id != existing.id:
            raise RuntimeError("Existing import is incomplete; manual review is required.")
        return {"created": False, "lesson_id": str(existing.id), "lesson_status": existing.status,
                "assessment_id": str(exercise.id), "assessment_status": exercise.status,
                "note": "Existing draft or subsequently edited content preserved."}
    lesson = Lesson(id=lesson_id, hsk_level_id=level.id, lesson_number=1,
                    title=definition["lesson"]["title"], description=definition["lesson"]["description"], status="DRAFT")
    session.add(lesson)
    await session.flush()
    for index, item in enumerate(definition["vocabulary"], 1):
        vocab = Vocabulary(id=uuid5(NAMESPACE, definition["key"] + ":vocabulary:" + item["hanzi"]),
                           **{key: item[key] for key in ("hanzi", "pinyin", "vietnamese_meaning", "part_of_speech")})
        session.add(vocab)
        await session.flush()
        session.add(LessonVocabulary(lesson_id=lesson.id, vocabulary_id=vocab.id, order_index=index,
                                     example=item["example"], note=item.get("note")))
    exercise = Assessment(id=assessment_id, type="LESSON_EXERCISE", lesson_id=lesson.id,
                          status="DRAFT", **definition["assessment"])
    session.add(exercise)
    await session.flush()
    for question in questions:
        data = question.model_dump(mode="json", exclude={"options"})
        row = Question(assessment_id=exercise.id, **data)
        session.add(row)
        await session.flush()
        for index, option in enumerate(question.options or [], 1):
            session.add(QuestionOption(question_id=row.id, order_index=index, **option.model_dump()))
    highest = await session.scalar(select(func.max(CurriculumUnit.order_index)).where(CurriculumUnit.hsk_level_id == level.id))
    session.add(CurriculumUnit(hsk_level_id=level.id, unit_type="LESSON", lesson_id=lesson.id, order_index=(highest or 0) + 1))
    await session.flush()
    return {"created": True, "lesson_id": str(lesson.id), "lesson_status": lesson.status,
            "assessment_id": str(exercise.id), "assessment_status": exercise.status,
            "vocabulary": 12, "grammar": 0, "questions": len(questions), "pass_threshold": exercise.pass_threshold}


async def main(apply):
    definition, questions = load_definition()
    if not apply:
        print(json.dumps({"dry_run": True, "title": definition["lesson"]["title"],
                          "vocabulary": 12, "grammar": 0, "questions": len(questions), "pass_threshold": 80}, ensure_ascii=True))
        return
    async with SessionFactory.begin() as session:
        result = await create_draft(session, definition, questions)
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    asyncio.run(main(parser.parse_args().apply))
