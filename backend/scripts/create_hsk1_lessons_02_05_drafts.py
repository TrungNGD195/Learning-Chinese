"""Import HSK1 lessons 2–5 as complete drafts, never overwrite or publish.

Dry run is the default. --apply creates all missing lessons in one transaction.
Existing imports, including administrator edits, are preserved. A conflicting
lesson number or incomplete prior import stops the whole operation.
"""
import argparse
import asyncio
import json
from pathlib import Path
from uuid import UUID, uuid5

from sqlalchemy import func, select

from app.admin.schemas import GrammarAttachRequest, QuestionCreateRequest, VocabularyAttachRequest
from app.database.models import (
    Assessment, CurriculumUnit, Grammar, HSKLevel, Lesson, LessonGrammar,
    LessonReading, LessonVocabulary, Question, QuestionOption, Vocabulary,
)
from app.database.session import SessionFactory
from app.exercise.service import admin_validate_question
from app.readings.schemas import ReadingCreateRequest

NAMESPACE = UUID('23c010fb-f291-4d79-af36-983a116bf02a')
CONTENT = Path(__file__).resolve().parents[1] / 'content' / 'hsk1'


def load_definitions():
    definitions = []
    for number in range(2, 6):
        definition = json.loads((CONTENT / f'lesson-{number:02d}.json').read_text(encoding='utf-8'))
        if definition['lesson']['lesson_number'] != number or definition['lesson']['hsk_level'] != 1:
            raise ValueError('Manifest must target its HSK1 lesson number.')
        vocabulary = definition['vocabulary']
        if not vocabulary or len({word['hanzi'] for word in vocabulary}) != len(vocabulary):
            raise ValueError('Vocabulary must be nonempty and unique within a lesson.')
        for index, word in enumerate(vocabulary, 1):
            VocabularyAttachRequest.model_validate({**word, 'order_index': index})
            lines = word['example'].splitlines()
            if not word['part_of_speech'] or len(lines) != 3 or word['hanzi'] not in lines[0] or not any(char in lines[0] for char in '。！？'):
                raise ValueError('Each word requires a full sentence, pinyin and translation.')
            if word.get('note') and ('Nguồn' in word['note'] or 'PDF' in word['note']):
                raise ValueError('Usage notes must not contain source attribution.')
        for index, item in enumerate(definition['grammar'], 1):
            GrammarAttachRequest.model_validate({**item, 'order_index': index})
        for item in definition['readings']:
            ReadingCreateRequest.model_validate(item)
        questions = definition['questions']
        types = {question['type'] for question in questions}
        if len(questions) != 30 or len(types) < 3 or definition['assessment']['pass_threshold'] != 80:
            raise ValueError('Each lesson requires 30 varied questions and an 80% threshold.')
        if len({question['prompt'] for question in questions}) != 30:
            raise ValueError('Question prompts must be unique.')
        for index, question in enumerate(questions, 1):
            validated = QuestionCreateRequest.model_validate(question)
            admin_validate_question(validated.model_dump(exclude_unset=True))
            if question['order_index'] != index or question['points'] != 1:
                raise ValueError('Questions must be ordered and total exactly 30 points.')
            if question['type'] == 'matching':
                right = question['config']['right_items']
                if len({item['text'] for item in right}) != len(right):
                    raise ValueError('Matching pairs must have distinct meanings.')
        definitions.append(definition)
    return definitions


def identifiers(definition):
    key = definition['key']
    return uuid5(NAMESPACE, key + ':lesson'), uuid5(NAMESPACE, key + ':exercise')


async def create_drafts(session, definitions, *, level_number=1):
    level = await session.scalar(select(HSKLevel).where(HSKLevel.level_number == level_number).with_for_update())
    if level is None:
        raise RuntimeError('Target HSK level must already exist.')
    existing = (await session.execute(select(Lesson).where(
        Lesson.hsk_level_id == level.id, Lesson.lesson_number.in_([2, 3, 4, 5]),
    ).with_for_update())).scalars().all()
    by_number = {lesson.lesson_number: lesson for lesson in existing}
    # Preflight every target before staging any new content.
    for definition in definitions:
        number = definition['lesson']['lesson_number']
        lesson_id, exercise_id = identifiers(definition)
        if number in by_number:
            if by_number[number].id != lesson_id:
                raise RuntimeError(f'Lesson {number} already exists with another ID; nothing overwritten.')
            exercise = await session.get(Assessment, exercise_id)
            if exercise is None or exercise.lesson_id != lesson_id:
                raise RuntimeError(f'Lesson {number} has an incomplete prior import; manual review required.')
    highest = await session.scalar(select(func.max(CurriculumUnit.order_index)).where(CurriculumUnit.hsk_level_id == level.id)) or 0
    result = []
    for definition in definitions:
        number = definition['lesson']['lesson_number']
        lesson_id, exercise_id = identifiers(definition)
        if number in by_number:
            result.append(dict(number=number, lesson_id=str(lesson_id), created=False, status=by_number[number].status, note='Existing content preserved.'))
            continue
        lesson = Lesson(id=lesson_id, hsk_level_id=level.id, lesson_number=number,
                        title=definition['lesson']['title'], description=definition['lesson']['description'], status='DRAFT')
        session.add(lesson)
        await session.flush()
        for index, word in enumerate(definition['vocabulary'], 1):
            # Separate canonical records prevent changing Lesson 1 or other lessons.
            item = Vocabulary(id=uuid5(NAMESPACE, definition['key'] + ':vocabulary:' + word['hanzi']),
                              **{key: word[key] for key in ('hanzi', 'pinyin', 'vietnamese_meaning', 'part_of_speech')})
            session.add(item)
            await session.flush()
            session.add(LessonVocabulary(lesson_id=lesson_id, vocabulary_id=item.id, order_index=index,
                                         example=word['example'], note=word.get('note')))
        for index, entry in enumerate(definition['grammar'], 1):
            item = Grammar(id=uuid5(NAMESPACE, definition['key'] + ':grammar:' + str(index)),
                           **{key: entry.get(key) for key in ('name', 'structure', 'explanation', 'usage')})
            session.add(item)
            await session.flush()
            session.add(LessonGrammar(lesson_id=lesson_id, grammar_id=item.id, order_index=index,
                                      example=entry['example'], note=entry.get('note')))
        for entry in definition['readings']:
            session.add(LessonReading(id=uuid5(NAMESPACE, definition['key'] + ':reading:' + str(entry['order_index'])), lesson_id=lesson_id, **entry))
        assessment = Assessment(id=exercise_id, type='LESSON_EXERCISE', lesson_id=lesson_id, status='DRAFT', **definition['assessment'])
        session.add(assessment)
        await session.flush()
        for entry in definition['questions']:
            fields = {key: value for key, value in entry.items() if key != 'options'}
            question = Question(assessment_id=exercise_id, **fields)
            session.add(question)
            await session.flush()
            for index, option in enumerate(entry.get('options', []), 1):
                session.add(QuestionOption(question_id=question.id, order_index=index, **option))
        highest += 1
        session.add(CurriculumUnit(hsk_level_id=level.id, unit_type='LESSON', lesson_id=lesson_id, order_index=highest))
        await session.flush()
        result.append(dict(number=number, lesson_id=str(lesson_id), assessment_id=str(exercise_id), created=True,
                           status='DRAFT', vocabulary=len(definition['vocabulary']), grammar=len(definition['grammar']),
                           readings=len(definition['readings']), questions=30, pass_threshold=80))
    return result


async def main(apply):
    definitions = load_definitions()
    if not apply:
        print(json.dumps({'dry_run': True, 'lessons': [dict(number=d['lesson']['lesson_number'], vocabulary=len(d['vocabulary']), grammar=len(d['grammar']), readings=len(d['readings']), questions=30, pass_threshold=80) for d in definitions]}))
        return
    async with SessionFactory.begin() as session:
        report = await create_drafts(session, definitions)
    print(json.dumps({'applied': True, 'lessons': report}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    asyncio.run(main(parser.parse_args().apply))
