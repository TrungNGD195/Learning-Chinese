"""Temporary completed HSK3 catalog for the isolated exam browser test only."""
import asyncio
import sys
from datetime import UTC,datetime
from uuid import NAMESPACE_URL,uuid5
from sqlalchemy import select,delete
from sqlalchemy.engine import make_url
from app.core.config import get_settings
from app.database.session import SessionFactory
from app.database.models import User,HSKLevel,Lesson,CurriculumUnit,LearnerLessonProgress,HskExamAttempt

def ident(n):return uuid5(NAMESPACE_URL,f'hanfolio-exam-browser-prerequisite-{n}')

async def run(action):
    settings=get_settings()
    url=make_url(settings.effective_database_url)
    if settings.app_env!='test' or url.database!='chinese_learning_test' or url.host not in {'localhost','127.0.0.1','::1'}:
        raise RuntimeError('Exam fixture is restricted to the dedicated local test database')
    async with SessionFactory.begin() as session:
        user=await session.scalar(select(User).where(User.email=='step81-learner@example.invalid'))
        level=await session.scalar(select(HSKLevel).where(HSKLevel.level_number==3))
        if not user or not level:raise RuntimeError('Required browser test seed is missing')
        ids=[ident(n) for n in range(1,16)]
        if action=='--complete-test-course':
            if (await session.scalars(select(Lesson.id).where(Lesson.hsk_level_id==level.id))).all():
                raise RuntimeError('Temporary fixture requires the originally empty HSK3 test catalog')
            for n,lesson_id in enumerate(ids,1):
                session.add(Lesson(id=lesson_id,hsk_level_id=level.id,lesson_number=n,title=f'Exam fixture {n}',status='PUBLISHED'))
            await session.flush()
            for n,lesson_id in enumerate(ids,1):
                session.add(CurriculumUnit(hsk_level_id=level.id,unit_type='LESSON',lesson_id=lesson_id,order_index=n))
                session.add(LearnerLessonProgress(user_id=user.id,lesson_id=lesson_id,theory_completed_at=datetime.now(UTC),completed_at=datetime.now(UTC)))
        elif action=='--remove-test-course':
            await session.execute(delete(HskExamAttempt).where(HskExamAttempt.user_id==user.id,HskExamAttempt.hsk_level==3))
            await session.execute(delete(LearnerLessonProgress).where(LearnerLessonProgress.lesson_id.in_(ids)))
            await session.execute(delete(CurriculumUnit).where(CurriculumUnit.lesson_id.in_(ids)))
            await session.execute(delete(Lesson).where(Lesson.id.in_(ids)))
        else:raise RuntimeError('Explicit test-fixture action is required')
    print('Dedicated test-only exam prerequisite fixture updated.')

if __name__=='__main__':asyncio.run(run(sys.argv[1] if len(sys.argv)==2 else ''))
