"""Explicit, backed-up release of the reviewed 40-lesson collection to Hanfolio.

No local database restore or automatic startup import. --inspect reads state.
--apply requires the inspected fingerprint and a verified backup receipt. The
named Railway production project is the only permitted production target.
"""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.curriculum.service import admin_publish_lesson_package
from app.database.engine import engine
from app.database.models import (
    Assessment, AssessmentAttempt, AttemptAnswer, HSKLevel, LearnerGrammarProgress,
    LearnerHSKProgress, LearnerLessonProgress, LearnerReadingProgress,
    LearnerVocabularyProgress, Lesson, PronunciationLessonProgress,
    PronunciationProgress, User,
)
from scripts.import_curriculum_refresh import fingerprint, load_definitions as load_prior, refresh
from scripts.import_hsk3_curriculum import load_definitions as load_hsk3

PROJECT = 'f928bd3a-c3ea-479e-a156-9111e1207b1b'
PROTECTED = (User, LearnerLessonProgress, LearnerHSKProgress, LearnerVocabularyProgress,
             LearnerGrammarProgress, LearnerReadingProgress, PronunciationProgress,
             PronunciationLessonProgress, AssessmentAttempt, AttemptAnswer)


def check_target(settings, project_id=None, environment_name=None):
    if settings.app_env != 'production' or project_id != PROJECT or environment_name != 'production':
        raise RuntimeError('Release requires the named Hanfolio Railway production project/environment.')
    if settings.knowledge_ai_enabled:
        raise RuntimeError('Keep the learning-only configuration; this release does not enable AI.')


def check_backup(path, expected_sha):
    if not path or not path.is_file():
        raise RuntimeError('A verified production database backup receipt is required.')
    data = json.loads(path.read_text(encoding='utf-8'))
    if (data.get('project_id') != PROJECT or data.get('environment') != 'production'
            or data.get('format') != 'PostgreSQL custom dump' or not data.get('verified_toc')
            or data.get('bytes', 0) < 1000 or not expected_sha or len(expected_sha) != 64
            or data.get('sha256') != expected_sha):
        raise RuntimeError('Backup receipt does not match the requested production release.')


async def protected_state(session):
    result = {}
    for model in PROTECTED:
        rows = (await session.execute(select(model.__table__))).mappings().all()
        ordered = sorted([dict(row) for row in rows], key=lambda row: str(row.get('id', row)))
        result[model.__tablename__] = {
            'count': len(ordered),
            'sha256': hashlib.sha256(json.dumps(ordered, sort_keys=True, default=str).encode()).hexdigest(),
        }
    return result


async def release(session, definitions):
    before = await protected_state(session)
    # Prevent a concurrent admin edit to targeted lessons during this transaction.
    await session.execute(select(HSKLevel).where(HSKLevel.level_number.in_([1, 2, 3])).with_for_update())
    result = await refresh(session, definitions)
    for definition in definitions:
        level, number = definition['lesson']['hsk_level'], definition['lesson']['lesson_number']
        lesson_id = await session.scalar(select(Lesson.id).join(HSKLevel, HSKLevel.id == Lesson.hsk_level_id)
            .where(HSKLevel.level_number == level, Lesson.lesson_number == number))
        await admin_publish_lesson_package(session, lesson_id)
    after = await protected_state(session)
    if before != after:
        raise RuntimeError('User or learning-history data changed; rolling back the whole content release.')
    return {'published_lessons': len(result), 'history_preserved': True,
            'protected_counts': {key: value['count'] for key, value in after.items()}}


async def main(args):
    settings = get_settings()
    check_target(settings, os.getenv('RAILWAY_PROJECT_ID'), os.getenv('RAILWAY_ENVIRONMENT_NAME'))
    definitions = load_prior() + load_hsk3()
    if args.apply:
        check_backup(args.backup_receipt, args.backup_sha256)
    async with engine.begin() as connection:
        async with AsyncSession(bind=connection, expire_on_commit=False, join_transaction_mode='create_savepoint') as session:
            current = await fingerprint(session)
            if args.inspect:
                protected = await protected_state(session)
                print(json.dumps({'project': PROJECT, 'environment': 'production', 'fingerprint': current,
                    'target_lessons': len(definitions), 'protected_counts': {key: value['count'] for key, value in protected.items()}}))
                return
            if not args.expected_fingerprint or current != args.expected_fingerprint:
                raise RuntimeError('Production changed since inspect; nothing imported.')
            result = await release(session, definitions)
            await session.commit()
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--inspect', action='store_true')
    mode.add_argument('--apply', action='store_true')
    parser.add_argument('--expected-fingerprint')
    parser.add_argument('--backup-receipt', type=Path)
    parser.add_argument('--backup-sha256')
    asyncio.run(main(parser.parse_args()))
