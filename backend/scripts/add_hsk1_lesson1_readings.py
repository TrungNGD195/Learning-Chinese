"""Add the textbook reading to the existing draft without changing its vocabulary.

Dry run by default. Use --apply to add only missing readings; existing edits win.
"""
import argparse
import asyncio
import json
from uuid import uuid5

from sqlalchemy import select
from app.database.models import HSKLevel, Lesson, LessonReading, LessonVocabulary
from app.database.session import SessionFactory
from scripts.create_hsk1_lesson1_draft import NAMESPACE, load_definition


async def main(apply):
    definition, _ = load_definition()
    async with SessionFactory.begin() as session:
        lesson = (await session.execute(select(Lesson).join(HSKLevel, HSKLevel.id == Lesson.hsk_level_id).where(
            HSKLevel.level_number == 1, Lesson.lesson_number == 1).with_for_update(of=Lesson))).scalar_one()
        if lesson.id != uuid5(NAMESPACE, definition['key'] + ':lesson') or lesson.status != 'DRAFT':
            raise RuntimeError('The reviewed lesson-1 draft is required; nothing was changed.')
        vocabulary_before = (await session.execute(select(LessonVocabulary.id, LessonVocabulary.vocabulary_id, LessonVocabulary.order_index, LessonVocabulary.note, LessonVocabulary.example).where(LessonVocabulary.lesson_id == lesson.id).order_by(LessonVocabulary.order_index))).all()
        existing = (await session.execute(select(LessonReading).where(LessonReading.lesson_id == lesson.id))).scalars().all()
        added = 0
        for reading in definition['readings']:
            ident = uuid5(NAMESPACE, definition['key'] + ':reading:' + str(reading['order_index']))
            if any(row.id == ident or row.order_index == reading['order_index'] for row in existing):
                continue
            added += 1
            if apply:
                session.add(LessonReading(id=ident, lesson_id=lesson.id, **reading))
        await session.flush()
        vocabulary_after = (await session.execute(select(LessonVocabulary.id, LessonVocabulary.vocabulary_id, LessonVocabulary.order_index, LessonVocabulary.note, LessonVocabulary.example).where(LessonVocabulary.lesson_id == lesson.id).order_by(LessonVocabulary.order_index))).all()
        assert vocabulary_after == vocabulary_before
        report = {'applied': apply, 'lesson_id': str(lesson.id), 'status': lesson.status, 'readings_added': added if apply else 0,
                  'readings_to_add': added, 'vocabulary_preserved': len(vocabulary_before)}
    print(json.dumps(report))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    asyncio.run(main(parser.parse_args().apply))
