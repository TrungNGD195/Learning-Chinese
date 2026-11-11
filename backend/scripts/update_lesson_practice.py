"""Replace reviewed practice packs atomically without changing lesson theory.

Caller supplies a fresh content-only snapshot and owns the transaction. This
maintenance operation refuses any exercise with attempt history or changed
questions. It preserves IDs/status of lessons and assessments, including an
already published lesson. It never deletes attempts or learning progress.
"""
import json
from uuid import UUID
from sqlalchemy import select, delete, func
from app.admin.schemas import QuestionCreateRequest
from app.database.models import Assessment, AssessmentAttempt, HSKLevel, Lesson, Question, QuestionOption
from app.exercise.service import admin_validate_question


def scalar_row(item):
    return {c.name:getattr(item,c.name) for c in item.__table__.columns}


async def question_snapshot(session, assessment_id):
    rows=[]
    for q in await session.scalars(select(Question).where(Question.assessment_id==assessment_id).order_by(Question.order_index)):
        row=scalar_row(q)
        row['options']=[scalar_row(o) for o in await session.scalars(select(QuestionOption).where(QuestionOption.question_id==q.id).order_by(QuestionOption.order_index))]
        rows.append(row)
    return json.loads(json.dumps(rows,default=str))


async def update_practice(session, packs, expected):
    targets=[]
    for pack in packs:
        n=pack['lesson_number']
        if n not in range(1,6):raise ValueError('Only reviewed HSK1 lessons 1–5 are supported.')
        prior=next(row for row in expected if row['lesson']['lesson_number']==n)
        lesson=await session.get(Lesson,UUID(prior['lesson']['id']),with_for_update=True)
        if not lesson or lesson.status not in {'DRAFT','PUBLISHED'}:raise RuntimeError('Lesson is unavailable.')
        level=await session.get(HSKLevel,lesson.hsk_level_id)
        if level.level_number!=1 or lesson.lesson_number!=n:raise RuntimeError('Lesson identity mismatch.')
        exercises=(await session.scalars(select(Assessment).where(Assessment.lesson_id==lesson.id,Assessment.type=='LESSON_EXERCISE').with_for_update())).all()
        if len(exercises)!=1:raise RuntimeError('Expected one lesson exercise.')
        exercise=exercises[0]
        old=prior['assessments'][0]
        if str(exercise.id)!=old['id'] or exercise.status!=old['status'] or exercise.status not in {'DRAFT','PUBLISHED'}:raise RuntimeError('Exercise status changed; export a new snapshot.')
        if await session.scalar(select(func.count()).select_from(AssessmentAttempt).where(AssessmentAttempt.assessment_id==exercise.id)):
            raise RuntimeError(f'Lesson {n} has attempt history. A new exercise version is required; no data changed.')
        if await question_snapshot(session,exercise.id)!=old['questions']:raise RuntimeError('Questions changed since review; nothing overwritten.')
        qs=pack['questions']
        if len(qs)!=30 or pack['pass_threshold']!=80:raise ValueError('Expected 30 questions and an 80% threshold.')
        if len({q['prompt'] for q in qs})!=30:raise ValueError('Repeated prompt.')
        for i,q in enumerate(qs,1):
            if q['order_index']!=i or q['points']!=1 or not q.get('rubric','').strip():raise ValueError('Every question needs an explanation and one point.')
            validated=QuestionCreateRequest.model_validate(q)
            admin_validate_question(validated.model_dump(exclude_unset=True))
        targets.append((pack,exercise))
    for pack,exercise in targets:
        ids=select(Question.id).where(Question.assessment_id==exercise.id)
        await session.execute(delete(QuestionOption).where(QuestionOption.question_id.in_(ids)))
        await session.execute(delete(Question).where(Question.assessment_id==exercise.id))
        for q in pack['questions']:
            row=Question(assessment_id=exercise.id,**{k:v for k,v in q.items() if k!='options'})
            session.add(row);await session.flush()
            for i,o in enumerate(q.get('options',[]),1):session.add(QuestionOption(question_id=row.id,order_index=i,**o))
        exercise.description=pack['description'];exercise.pass_threshold=80
    await session.flush()
    return [{'lesson':p['lesson_number'],'questions':30,'status':a.status,'pass_threshold':a.pass_threshold} for p,a in targets]
