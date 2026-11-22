from sqlalchemy import select, func, and_
from app.database.models import HskExamAttempt, HSKLevel, User, Lesson, CurriculumUnit, LearnerLessonProgress

async def lesson_completions(session,user_id,level):
    return (await session.execute(select(Lesson.id,Lesson.lesson_number,LearnerLessonProgress.completed_at)
        .join(HSKLevel,HSKLevel.id==Lesson.hsk_level_id)
        .join(CurriculumUnit,and_(CurriculumUnit.lesson_id==Lesson.id,CurriculumUnit.hsk_level_id==HSKLevel.id))
        .outerjoin(LearnerLessonProgress,and_(LearnerLessonProgress.lesson_id==Lesson.id,LearnerLessonProgress.user_id==user_id))
        .where(HSKLevel.level_number==level,Lesson.status=='PUBLISHED',CurriculumUnit.unit_type=='LESSON')
        .distinct())).all()

async def level_exists(session,level):
    return await session.scalar(select(HSKLevel.id).where(HSKLevel.level_number==level)) is not None

async def lock_user(session,user_id):
    return await session.scalar(select(User.id).where(User.id==user_id).with_for_update())

async def active_attempt(session,user_id,level):
    return await session.scalar(select(HskExamAttempt).where(HskExamAttempt.user_id==user_id,
        HskExamAttempt.hsk_level==level,HskExamAttempt.status=='IN_PROGRESS').with_for_update())

async def next_number(session,user_id,level):
    return 1+(await session.scalar(select(func.max(HskExamAttempt.attempt_number)).where(
        HskExamAttempt.user_id==user_id,HskExamAttempt.hsk_level==level)) or 0)

async def get_owned(session,user_id,attempt_id):
    return await session.scalar(select(HskExamAttempt).where(HskExamAttempt.id==attempt_id,
        HskExamAttempt.user_id==user_id).with_for_update())

async def create(session,**fields):
    row=HskExamAttempt(**fields);session.add(row);await session.flush();return row

async def history(session,user_id,level):
    return (await session.scalars(select(HskExamAttempt).where(HskExamAttempt.user_id==user_id,
        HskExamAttempt.hsk_level==level).order_by(HskExamAttempt.attempt_number.desc()).limit(50))).all()
