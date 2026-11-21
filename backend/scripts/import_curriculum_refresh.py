"""Validate curriculum manifests; explicitly import drafts into local development only.

No network generation, publication, user deletion or assessment-history deletion.
Default is offline validation. --inspect prints a content fingerprint; --apply
requires that exact fingerprint and a nonempty pg_dump backup file.
"""
import argparse
import asyncio
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from uuid import UUID, uuid5

from sqlalchemy import select
from sqlalchemy.engine import make_url

from app.admin.schemas import GrammarAttachRequest, QuestionCreateRequest, VocabularyAttachRequest
from app.core.config import get_settings
from app.database.models import (
    Assessment, CurriculumUnit, Grammar, HSKLevel, LearnerGrammarProgress,
    LearnerReadingProgress, LearnerVocabularyProgress, Lesson, LessonGrammar,
    LessonReading, LessonVocabulary, Question, QuestionOption, Vocabulary,
)
from app.database.session import SessionFactory
from app.exercise.service import admin_validate_question
from app.readings.schemas import ReadingCreateRequest

CONTENT = Path(__file__).resolve().parents[1] / 'content' / 'curriculum-refresh'
NAMESPACE = UUID('5ad85ba0-40d8-4632-8fb3-4e6d378f713a')


def normalized(value):
    return ' '.join(unicodedata.normalize('NFC', value).split()).casefold()


def word_key(word):
    get = word.get if isinstance(word, dict) else lambda key: getattr(word, key)
    return (normalized(get('hanzi')), re.sub(r"[\s·’'-]", '', normalized(get('pinyin'))), normalized(get('vietnamese_meaning')))


def load_definitions():
    definitions = [json.loads(path.read_text(encoding='utf-8')) for path in sorted(CONTENT.glob('hsk*-lesson-*.json'))]
    expected = {(1, n) for n in range(1, 16)} | {(2, n) for n in range(1, 11)}
    return validate_definitions(definitions, expected)


def validate_definitions(definitions, expected, existing_words=()):
    if {(d['lesson']['hsk_level'], d['lesson']['lesson_number']) for d in definitions} != expected or len(definitions) != len(expected):
        raise ValueError('Lesson manifests do not exactly match the requested curriculum scope.')
    seen = {word_key(word) for word in existing_words}
    for d in definitions:
        current = (d['lesson']['hsk_level'], d['lesson']['lesson_number'])
        for index, word in enumerate(d['vocabulary'], 1):
            VocabularyAttachRequest.model_validate({k: v for k, v in word.items() if k != 'source_key'})
            key = word_key(word)
            if key in seen or word['order_index'] != index:
                raise ValueError(f'Duplicate vocabulary or ordering error: {current} {key}')
            seen.add(key)
            if len(word['example'].splitlines()) != 3 or not word['part_of_speech']:
                raise ValueError('Each word needs a sentence, pinyin, translation and word class.')
        for item in d['grammar']:
            GrammarAttachRequest.model_validate(item)
        for item in d['readings']:
            ReadingCreateRequest.model_validate(item)
        if len(d['questions']) != 30 or d['assessment']['pass_threshold'] != 80:
            raise ValueError('Every lesson needs 30 questions and an 80% pass threshold.')
        if len({q['type'] for q in d['questions']}) < 4:
            raise ValueError('Expected four exercise formats.')
        for index, question in enumerate(d['questions'], 1):
            data = {k: v for k, v in question.items() if k != 'knowledge_origins'}
            parsed = QuestionCreateRequest.model_validate(data)
            admin_validate_question(parsed.model_dump(exclude_unset=True))
            if question['order_index'] != index or question['points'] != 1 or not question['rubric']:
                raise ValueError('Invalid scoring, ordering or missing explanation.')
            if not question.get('knowledge_origins') or any((o['hsk'], o['lesson']) > current for o in question['knowledge_origins']):
                raise ValueError('Exercises must not draw on later lessons.')
    return definitions


def content_hash(d):
    return hashlib.sha256(json.dumps(d, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def identifier(key):
    return uuid5(NAMESPACE, key)


async def fingerprint(session):
    # Include content and progress tables: stop if anybody edits/studies after inspect.
    from app.database.models import AssessmentAttempt, LearnerLessonProgress
    tables = [HSKLevel, Lesson, CurriculumUnit, Vocabulary, LessonVocabulary, Grammar,
              LessonGrammar, LessonReading, Assessment, Question, QuestionOption,
              LearnerVocabularyProgress, LearnerGrammarProgress, LearnerReadingProgress,
              LearnerLessonProgress, AssessmentAttempt]
    payload = {}
    for model in tables:
        rows = (await session.execute(select(model.__table__))).mappings().all()
        payload[model.__tablename__] = sorted([dict(row) for row in rows], key=lambda row: str(row.get('id', row)))
    return hashlib.sha256(json.dumps(payload, default=str, sort_keys=True).encode()).hexdigest()


async def refresh(session, definitions):
    report = []
    for d in definitions:
        h, number = d['lesson']['hsk_level'], d['lesson']['lesson_number']
        level = await session.scalar(select(HSKLevel).where(HSKLevel.level_number == h).with_for_update())
        if level is None:
            raise RuntimeError(f'HSK {h} is missing; refusing to create a new level.')
        lesson = await session.scalar(select(Lesson).where(Lesson.hsk_level_id == level.id, Lesson.lesson_number == number).with_for_update())
        digest = content_hash(d)
        exercise_id = identifier(f'{d["key"]}:exercise:{digest}')
        if await session.get(Assessment, exercise_id):
            report.append({'hsk': h, 'lesson': number, 'action': 'already_imported_preserved'})
            continue  # Never overwrite subsequent admin edits on a repeated run.
        if lesson is None:
            lesson = Lesson(id=identifier(d['key'] + ':lesson'), hsk_level_id=level.id,
                            lesson_number=number, title=d['lesson']['title'], status='DRAFT')
            session.add(lesson)
            await session.flush()
        lesson.title, lesson.description, lesson.status = d['lesson']['title'], d['lesson']['description'], 'DRAFT'
        # Keep published_at as historical metadata; DRAFT controls student access.
        old_links = list((await session.scalars(select(LessonVocabulary).where(LessonVocabulary.lesson_id == lesson.id))).all())
        old_words = {link.id: await session.get(Vocabulary, link.vocabulary_id) for link in old_links}
        for i, link in enumerate(old_links, 1):
            link.order_index = 1000000 + i
        await session.flush()
        remaining = list(old_links)
        for word in d['vocabulary']:
            match = next((link for link in remaining if word_key(old_words[link.id]) == word_key(word)), None)
            if match is None:
                match = next((link for link in remaining if old_words[link.id].hanzi == word['hanzi']), None)
            vocabulary_id = identifier('vocabulary:' + '\0'.join(word_key(word)))
            vocabulary = await session.get(Vocabulary, vocabulary_id)
            if vocabulary is None:
                vocabulary = Vocabulary(id=vocabulary_id, **{k: word[k] for k in ('hanzi', 'pinyin', 'vietnamese_meaning', 'part_of_speech')})
                session.add(vocabulary)
                await session.flush()
            if match is None:
                match = LessonVocabulary(lesson_id=lesson.id, vocabulary_id=vocabulary.id)
                session.add(match)
            else:
                remaining.remove(match)
                match.vocabulary_id = vocabulary.id
            match.order_index, match.example, match.note = word['order_index'], word['example'], word.get('note')
        for link in remaining:
            if await session.scalar(select(LearnerVocabularyProgress.id).where(LearnerVocabularyProgress.lesson_vocabulary_id == link.id).limit(1)):
                raise RuntimeError('An obsolete vocabulary link has study history; manual mapping required. No changes committed.')
            await session.delete(link)
        old_grammar = list((await session.scalars(select(LessonGrammar).where(LessonGrammar.lesson_id == lesson.id).order_by(LessonGrammar.order_index))).all())
        for i, link in enumerate(old_grammar, 1):
            link.order_index = 1000000 + i
        await session.flush()
        for i, entry in enumerate(d['grammar']):
            gid = identifier(d['key'] + ':grammar:' + str(i))
            grammar = await session.get(Grammar, gid)
            if grammar is None:
                grammar = Grammar(id=gid, **{k: entry.get(k) for k in ('name', 'structure', 'explanation', 'usage')})
                session.add(grammar)
                await session.flush()
            link = old_grammar[i] if i < len(old_grammar) else LessonGrammar(lesson_id=lesson.id, grammar_id=gid)
            if i >= len(old_grammar):
                session.add(link)
            link.grammar_id, link.order_index, link.example, link.note = gid, i + 1, entry['example'], entry.get('note')
        for link in old_grammar[len(d['grammar']):]:
            if await session.scalar(select(LearnerGrammarProgress.id).where(LearnerGrammarProgress.lesson_grammar_id == link.id).limit(1)):
                raise RuntimeError('An obsolete grammar link has study history; no changes committed.')
            await session.delete(link)
        old_readings = list((await session.scalars(select(LessonReading).where(LessonReading.lesson_id == lesson.id).order_by(LessonReading.order_index))).all())
        for i, entry in enumerate(d['readings']):
            reading = old_readings[i] if i < len(old_readings) else LessonReading(lesson_id=lesson.id, version=1)
            if i >= len(old_readings):
                session.add(reading)
            # Preserve historical reading completion/version; do not force relearning.
            for k, value in entry.items():
                setattr(reading, k, value)
        for reading in old_readings[len(d['readings']):]:
            if await session.scalar(select(LearnerReadingProgress.id).where(LearnerReadingProgress.lesson_reading_id == reading.id).limit(1)):
                raise RuntimeError('An obsolete reading has study history; no changes committed.')
            await session.delete(reading)
        # Archive superseded assessments, retaining every question, answer and attempt.
        for old in (await session.scalars(select(Assessment).where(Assessment.lesson_id == lesson.id, Assessment.type == 'LESSON_EXERCISE'))).all():
            old.status = 'ARCHIVED'
        session.add(Assessment(id=exercise_id, lesson_id=lesson.id, type='LESSON_EXERCISE', status='DRAFT', **d['assessment']))
        await session.flush()
        for entry in d['questions']:
            question = Question(assessment_id=exercise_id, **{k: v for k, v in entry.items() if k not in ('options', 'knowledge_origins')})
            session.add(question)
            await session.flush()
            for index, option in enumerate(entry.get('options', []), 1):
                session.add(QuestionOption(question_id=question.id, order_index=index, **option))
        if not await session.scalar(select(CurriculumUnit.id).where(CurriculumUnit.lesson_id == lesson.id)):
            # Preserve all existing unit positions and periodic tests.
            orders = (await session.scalars(select(CurriculumUnit.order_index).where(CurriculumUnit.hsk_level_id == level.id))).all()
            session.add(CurriculumUnit(hsk_level_id=level.id, lesson_id=lesson.id, unit_type='LESSON', order_index=max(orders, default=0) + 1))
        await session.flush()
        report.append({'hsk': h, 'lesson': number, 'id': str(lesson.id), 'status': lesson.status, 'vocabulary': len(d['vocabulary']), 'questions': 30})
    return report


async def main(args):
    definitions = load_definitions()
    if not (args.apply or args.inspect):
        print(json.dumps({'validated_lessons': len(definitions), 'vocabulary': sum(len(d['vocabulary']) for d in definitions), 'questions': 750}))
        return
    settings = get_settings()
    url = make_url(settings.effective_database_url)
    if settings.app_env != 'development' or url.host not in ('localhost', '127.0.0.1', 'db') or url.database != 'chinese_learning':
        raise RuntimeError('Only the named local development database is allowed.')
    if args.apply and (not args.backup or not args.backup.is_file() or args.backup.stat().st_size < 1000):
        raise RuntimeError('Apply requires an existing database backup file.')
    async with SessionFactory.begin() as session:
        before = await fingerprint(session)
        if args.inspect:
            print(json.dumps({'fingerprint': before, 'target_lessons': len(definitions)}))
            return
        if args.expected_fingerprint != before:
            raise RuntimeError('Local data changed since inspect; nothing imported.')
        result = await refresh(session, definitions)
    print(json.dumps({'applied': True, 'lessons': result}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--inspect', action='store_true')
    mode.add_argument('--apply', action='store_true')
    parser.add_argument('--expected-fingerprint')
    parser.add_argument('--backup', type=Path)
    asyncio.run(main(parser.parse_args()))
