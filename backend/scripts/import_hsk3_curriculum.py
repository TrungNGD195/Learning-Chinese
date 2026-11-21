"""Validate or explicitly import the supplied-DOCX HSK3 collection locally.

Default: offline validation. --inspect reads a local content fingerprint.
--apply requires that fingerprint and a pg_dump backup. --publish additionally
publishes the 15 lesson packages in the same outer transaction. No remote APIs.
HSK1–2 lessons, attempts, users and pronunciation are not import targets.
"""
import argparse
import asyncio
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.curriculum.service import admin_publish_lesson_package
from app.database.engine import engine
from app.database.models import Lesson, HSKLevel
from scripts.import_curriculum_refresh import (
    fingerprint, load_definitions as load_prior, refresh, validate_definitions,
)

CONTENT = Path(__file__).resolve().parents[1] / 'content' / 'hsk3'


def load_definitions():
    definitions = [json.loads(path.read_text(encoding='utf-8')) for path in sorted(CONTENT.glob('lesson-*.json'))]
    prior = [word for d in load_prior() for word in d['vocabulary']]
    result = validate_definitions(definitions, {(3, n) for n in range(1, 16)}, prior)
    for definition in result:
        if definition['source_documents'] != {'vocabulary': 'DOCX', 'theory': 'DOCX'}:
            raise ValueError('HSK3 must be sourced only from the supplied DOCX.')
        if len(definition['readings']) != 4:
            raise ValueError('Every HSK3 lesson must retain its four distinct source readings.')
    return result


async def main(args):
    definitions = load_definitions()
    if args.publish and not args.apply:
        raise RuntimeError('--publish requires explicit --apply.')
    if not (args.apply or args.inspect):
        print(json.dumps({'validated_lessons': 15, 'vocabulary': sum(len(d['vocabulary']) for d in definitions), 'questions': 450}))
        return
    settings = get_settings()
    url = make_url(settings.effective_database_url)
    if settings.app_env != 'development' or url.host not in ('localhost', '127.0.0.1', 'db') or url.database != 'chinese_learning':
        raise RuntimeError('Only the named local development database is allowed.')
    if args.apply and (not args.backup or not args.backup.is_file() or args.backup.stat().st_size < 1000):
        raise RuntimeError('A nonempty pg_dump backup file is required.')
    async with engine.begin() as connection:
        async with AsyncSession(bind=connection, expire_on_commit=False, join_transaction_mode='create_savepoint') as session:
            before = await fingerprint(session)
            if args.inspect:
                print(json.dumps({'fingerprint': before, 'target_lessons': 15}))
                return
            if before != args.expected_fingerprint:
                raise RuntimeError('Local content changed after inspect; nothing imported.')
            report = await refresh(session, definitions)
            if args.publish:
                for number in range(1, 16):
                    ident = await session.scalar(select(Lesson.id).join(HSKLevel, HSKLevel.id == Lesson.hsk_level_id).where(HSKLevel.level_number == 3, Lesson.lesson_number == number))
                    await admin_publish_lesson_package(session, ident)
                for entry in report:
                    entry['status'] = 'PUBLISHED'
            await session.commit()
    print(json.dumps({'applied': True, 'published': args.publish, 'lessons': report}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--inspect', action='store_true')
    mode.add_argument('--apply', action='store_true')
    parser.add_argument('--publish', action='store_true')
    parser.add_argument('--expected-fingerprint')
    parser.add_argument('--backup', type=Path)
    asyncio.run(main(parser.parse_args()))
