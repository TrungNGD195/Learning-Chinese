"""Persistence access for assessments, questions and attempt outcomes."""
from uuid import UUID

from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (Assessment, AssessmentAttempt, AssessmentGrammar, AssessmentLesson,
    AssessmentVocabulary, AttemptAnswer, Grammar, Lesson, Question, QuestionOption, Vocabulary)


async def passed_periodic_assessment_ids(session: AsyncSession,user_id: UUID) -> set[UUID]:
    return set((await session.execute(select(AssessmentAttempt.assessment_id)
        .join(Assessment,Assessment.id==AssessmentAttempt.assessment_id)
        .where(AssessmentAttempt.user_id==user_id,AssessmentAttempt.status=="GRADED",
            AssessmentAttempt.score.is_not(None),AssessmentAttempt.score>=Assessment.pass_threshold,
            Assessment.type=="PERIODIC_TEST"))).scalars())


async def has_passing_lesson_exercise(session: AsyncSession,user_id: UUID,lesson_id: UUID) -> bool:
    result=(await session.execute(select(AssessmentAttempt.id)
        .join(Assessment,Assessment.id==AssessmentAttempt.assessment_id)
        .where(AssessmentAttempt.user_id==user_id,AssessmentAttempt.status=="GRADED",
            AssessmentAttempt.score.is_not(None),AssessmentAttempt.score>=Assessment.pass_threshold,
            Assessment.type=="LESSON_EXERCISE",Assessment.lesson_id==lesson_id).limit(1))).scalar_one_or_none()
    return result is not None


async def has_active_periodic_test(session: AsyncSession, user_id: UUID) -> bool:
    result = (await session.execute(
        select(AssessmentAttempt.id)
        .join(Assessment, Assessment.id == AssessmentAttempt.assessment_id)
        .where(
            AssessmentAttempt.user_id == user_id,
            AssessmentAttempt.status == "IN_PROGRESS",
            Assessment.type == "PERIODIC_TEST",
        )
        .limit(1)
    )).scalar_one_or_none()
    return result is not None


async def get_assessment(session:AsyncSession,assessment_id:UUID,*,for_update:bool=False):
    statement=select(Assessment).where(Assessment.id==assessment_id)
    if for_update:statement=statement.with_for_update()
    return (await session.execute(statement)).scalar_one_or_none()


async def list_questions(session:AsyncSession,assessment_id:UUID):
    return (await session.execute(select(Question).where(Question.assessment_id==assessment_id).order_by(Question.order_index))).scalars().all()


async def list_question_options(session:AsyncSession,question_id:UUID):
    return (await session.execute(select(QuestionOption).where(QuestionOption.question_id==question_id).order_by(QuestionOption.order_index))).scalars().all()


async def active_attempt(session:AsyncSession,user_id:UUID,assessment_id:UUID):
    return (await session.execute(select(AssessmentAttempt).where(AssessmentAttempt.user_id==user_id,
        AssessmentAttempt.assessment_id==assessment_id,AssessmentAttempt.status=="IN_PROGRESS").with_for_update())).scalar_one_or_none()


async def max_attempt_number(session:AsyncSession,user_id:UUID,assessment_id:UUID):
    return (await session.execute(select(func.max(AssessmentAttempt.attempt_number)).where(
        AssessmentAttempt.user_id==user_id,AssessmentAttempt.assessment_id==assessment_id))).scalar_one()


async def create_attempt(session:AsyncSession,user_id:UUID,assessment_id:UUID,attempt_number:int):
    row=AssessmentAttempt(user_id=user_id,assessment_id=assessment_id,attempt_number=attempt_number,status="IN_PROGRESS")
    session.add(row); await session.flush(); return row


async def get_attempt(session:AsyncSession,attempt_id:UUID,user_id:UUID|None=None,*,for_update:bool=False):
    statement=select(AssessmentAttempt).where(AssessmentAttempt.id==attempt_id)
    if user_id is not None:statement=statement.where(AssessmentAttempt.user_id==user_id)
    if for_update:statement=statement.with_for_update()
    return (await session.execute(statement)).scalar_one_or_none()


async def add_attempt_answers(session:AsyncSession,attempt_id:UUID,answers:list[dict]):
    session.add_all([AttemptAnswer(assessment_attempt_id=attempt_id,**answer) for answer in answers])
    await session.flush()


async def finalize_attempt(session:AsyncSession,attempt_id:UUID,*,submitted_at,status,score,passed):
    attempt=(await get_attempt(session,attempt_id,for_update=True))
    attempt.submitted_at=submitted_at; attempt.status=status; attempt.score=score; attempt.passed=passed
    await session.flush()
    return attempt


async def history_rows(session:AsyncSession,user_id:UUID,page:int,page_size:int,assessment_id=None,lesson_id=None,assessment_type=None):
    query=select(AssessmentAttempt,Assessment).join(Assessment,Assessment.id==AssessmentAttempt.assessment_id).where(AssessmentAttempt.user_id==user_id)
    if assessment_id is not None:query=query.where(Assessment.id==assessment_id)
    if lesson_id is not None:query=query.where(Assessment.lesson_id==lesson_id)
    if assessment_type is not None:query=query.where(Assessment.type==assessment_type)
    total=(await session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    rows=(await session.execute(query.order_by(AssessmentAttempt.started_at.desc(),AssessmentAttempt.id)
        .offset((page-1)*page_size).limit(page_size))).all()
    return total,rows


async def attempt_detail_rows(session:AsyncSession,attempt_id:UUID,user_id:UUID):
    attempt=await get_attempt(session,attempt_id,user_id)
    if attempt is None:return None,None,[]
    assessment=await get_assessment(session,attempt.assessment_id)
    answers=(await session.execute(select(AttemptAnswer,Question).join(Question,Question.id==AttemptAnswer.question_id)
        .where(AttemptAnswer.assessment_attempt_id==attempt.id).order_by(Question.order_index))).all()
    return attempt,assessment,answers


async def admin_list_assessments(session:AsyncSession,status=None,assessment_type=None):
    statement=select(Assessment).order_by(Assessment.created_at)
    if status:statement=statement.where(Assessment.status==status)
    if assessment_type:statement=statement.where(Assessment.type==assessment_type)
    return (await session.execute(statement)).scalars().all()


async def admin_assessments_page(session:AsyncSession,page:int,page_size:int,status=None,assessment_type=None):
    filters=[]
    if status:filters.append(Assessment.status==status)
    if assessment_type:filters.append(Assessment.type==assessment_type)
    total=(await session.execute(select(func.count()).select_from(Assessment).where(*filters))).scalar_one()
    rows=(await session.execute(select(Assessment).where(*filters).order_by(Assessment.created_at,Assessment.id)
        .offset((page-1)*page_size).limit(page_size))).scalars().all()
    return total,rows


async def admin_create_assessment(session:AsyncSession,fields:dict):
    row=Assessment(**fields,status="DRAFT");session.add(row);await session.flush();return row


async def admin_update_assessment(session:AsyncSession,row:Assessment,fields:dict):
    for key,value in fields.items():setattr(row,key,value)
    await session.flush();return row


async def admin_transition_assessment(session:AsyncSession,row:Assessment,status:str,published_at=None):
    row.status=status
    if published_at is not None:row.published_at=published_at
    await session.flush();return row


async def admin_replace_assessment_scope(session:AsyncSession,assessment_id:UUID,scope:dict):
    for key,table,model,column in (("lesson_ids",AssessmentLesson,Lesson,"lesson_id"),
        ("vocabulary_ids",AssessmentVocabulary,Vocabulary,"vocabulary_id"),
        ("grammar_ids",AssessmentGrammar,Grammar,"grammar_id")):
        if key not in scope:continue
        ids=scope[key]
        if ids:
            found=set((await session.execute(select(model.id).where(model.id.in_(ids)))).scalars())
            if found!=set(ids):return False
        await session.execute(delete(table).where(table.c.assessment_id==assessment_id))
        if ids:await session.execute(insert(table),[{"assessment_id":assessment_id,column:ident} for ident in ids])
    return True


async def admin_question_count(session:AsyncSession,assessment_id:UUID):
    return (await session.execute(select(func.count()).select_from(Question).where(Question.assessment_id==assessment_id))).scalar_one()


async def admin_questions(session:AsyncSession,assessment_id:UUID):
    questions=(await session.execute(select(Question).where(Question.assessment_id==assessment_id).order_by(Question.order_index))).scalars().all()
    return [(q,await list_question_options(session,q.id)) for q in questions]


async def admin_get_question(session:AsyncSession,assessment_id:UUID,question_id:UUID,*,for_update=False):
    statement=select(Question).where(Question.id==question_id,Question.assessment_id==assessment_id)
    if for_update:statement=statement.with_for_update()
    return (await session.execute(statement)).scalar_one_or_none()


async def admin_create_question(session:AsyncSession,assessment_id:UUID,fields:dict,options:list[dict]):
    question=Question(assessment_id=assessment_id,**fields);session.add(question);await session.flush()
    await admin_replace_question_options(session,question.id,options)
    return question


async def admin_question_options(session:AsyncSession,question_id:UUID):
    return (await session.execute(select(QuestionOption).where(QuestionOption.question_id==question_id).order_by(QuestionOption.order_index))).scalars().all()


async def admin_replace_question_options(session:AsyncSession,question_id:UUID,options:list[dict]):
    await session.execute(delete(QuestionOption).where(QuestionOption.question_id==question_id))
    session.add_all([QuestionOption(question_id=question_id,order_index=i,**option) for i,option in enumerate(options,1)])
    await session.flush()


async def admin_update_question(session:AsyncSession,question:Question,fields:dict):
    for key,value in fields.items():setattr(question,key,value)
    await session.flush();return question


async def admin_question_has_history(session:AsyncSession,question_id:UUID):
    return (await session.execute(select(AttemptAnswer.id).where(AttemptAnswer.question_id==question_id).limit(1))).scalar_one_or_none() is not None


async def admin_delete_question(session:AsyncSession,question:Question):
    await session.execute(delete(QuestionOption).where(QuestionOption.question_id==question.id))
    await session.delete(question);await session.flush()
