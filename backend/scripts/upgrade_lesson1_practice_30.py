"""Append the reviewed ten questions to the existing lesson-1 draft.

Dry run by default. Existing questions, options, lesson content and status are
preserved. Refuse changed content, published assessments or any attempt history.
"""
import argparse
import asyncio
import json
from pathlib import Path
from uuid import uuid5

from sqlalchemy import select, func

from app.database.models import Assessment, AssessmentAttempt, Question, QuestionOption
from app.database.session import SessionFactory
from app.exercise.service import admin_validate_question
from scripts.create_hsk1_lesson1_draft import NAMESPACE, load_definition


async def upgrade(session, definition, questions):
    assessment_id = uuid5(NAMESPACE, definition['key'] + ':exercise')
    row = (await session.execute(select(Assessment).where(Assessment.id == assessment_id).with_for_update())).scalar_one_or_none()
    if row is None:
        return {'updated': False, 'reason': 'not_imported'}
    if row.status not in {'DRAFT', 'REVIEW'}:
        raise RuntimeError('Only an unpublished assessment can be expanded in place.')
    if await session.scalar(select(func.count()).select_from(AssessmentAttempt).where(AssessmentAttempt.assessment_id == row.id)):
        raise RuntimeError('Attempt history exists; preserve this assessment and create a new draft instead.')
    stored = (await session.execute(select(Question).where(Question.assessment_id == row.id).order_by(Question.order_index))).scalars().all()
    if len(stored) not in {20, 30}:
        raise RuntimeError('Unexpected question count; nothing was changed.')
    before = []
    for actual, expected in zip(stored, questions, strict=False):
        options = (await session.execute(select(QuestionOption).where(QuestionOption.question_id == actual.id).order_by(QuestionOption.order_index))).scalars().all()
        snapshot = {field: getattr(actual, field) for field in ('type', 'prompt', 'order_index', 'reference_answer', 'rubric', 'config')}
        snapshot['points'] = float(actual.points)
        expected_data = expected.model_dump(mode='json', exclude={'options'})
        expected_data['points'] = float(expected_data['points'])
        actual_options = [{'option_text': option.option_text, 'is_correct': option.is_correct} for option in options]
        expected_options = [option.model_dump() for option in expected.options or []]
        if snapshot != expected_data or actual_options != expected_options:
            raise RuntimeError('Existing edited question detected; nothing was changed.')
        before.append({'id': str(actual.id), **snapshot, 'options': [{'id': str(option.id), **value} for option, value in zip(options, actual_options, strict=True)]})
    if len(stored) == 30:
        return {'updated': False, 'assessment_id': str(row.id), 'questions': 30, 'status': row.status}
    for question in questions[20:]:
        fields = question.model_dump(mode='json', exclude={'options'})
        admin_validate_question({**fields, **({'options': [item.model_dump() for item in question.options]} if question.options else {})})
        created = Question(assessment_id=row.id, **fields)
        session.add(created)
        await session.flush()
        for index, option in enumerate(question.options or [], 1):
            session.add(QuestionOption(question_id=created.id, order_index=index, **option.model_dump()))
    await session.flush()
    return {'updated': True, 'assessment_id': str(row.id), 'questions': 30, 'added': 10, 'status': row.status, 'before': before}


async def main(apply, backup):
    definition, questions = load_definition()
    async with SessionFactory() as session:
        try:
            result = await upgrade(session, definition, questions)
            before = result.pop('before', None)
            if apply and before:
                if not backup:
                    raise RuntimeError('--backup is required when applying this content update.')
                target = Path(backup)
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('x', encoding='utf-8') as stream:
                    json.dump({'assessment_id': result['assessment_id'], 'questions': before}, stream, ensure_ascii=False, indent=2)
            if apply:
                await session.commit()
            else:
                await session.rollback()
            print(json.dumps({'dry_run': not apply, **result}, ensure_ascii=True))
        except BaseException:
            await session.rollback()
            raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--backup')
    args = parser.parse_args()
    asyncio.run(main(args.apply, args.backup))
