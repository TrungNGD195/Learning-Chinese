import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app.auth.current_user import get_current_user
from app.database.models import (Assessment, AssessmentAttempt, AttemptAnswer, CurriculumUnit, HSKLevel,
    LearnerHSKProgress, LearnerLessonProgress, Lesson, PronunciationProgress, Question, QuestionOption, User)
from app.database.session import SessionFactory
from app.main import app


def test_empty_theory_historical_pass_converges_and_unlocks_periodic_and_next_hsk():
    user_id,lesson1_id,lesson2_id,exercise_id,periodic_id=uuid4(),uuid4(),uuid4(),uuid4(),uuid4()
    async def setup():
        async with SessionFactory.begin() as session:
            hsk1=(await session.execute(select(HSKLevel).where(HSKLevel.level_number==1))).scalar_one()
            hsk2=(await session.execute(select(HSKLevel).where(HSKLevel.level_number==2))).scalar_one()
            base1=(await session.execute(select(func.max(CurriculumUnit.order_index)).where(CurriculumUnit.hsk_level_id==hsk1.id))).scalar_one() or 0
            base2=(await session.execute(select(func.max(CurriculumUnit.order_index)).where(CurriculumUnit.hsk_level_id==hsk2.id))).scalar_one() or 0
            user=User(id=user_id,email=f"progress-{user_id}@example.invalid",password_hash="test-only",full_name="Progress test",role="LEARNER")
            lesson1=Lesson(id=lesson1_id,hsk_level_id=hsk1.id,lesson_number=700000+user_id.int%100000,title="HSK1",status="PUBLISHED")
            lesson2=Lesson(id=lesson2_id,hsk_level_id=hsk2.id,lesson_number=700000+user_id.int%100000,title="HSK2",status="PUBLISHED")
            exercise=Assessment(id=exercise_id,type="LESSON_EXERCISE",lesson_id=lesson1_id,title="Lesson exercise",status="PUBLISHED",pass_threshold=90)
            periodic=Assessment(id=periodic_id,type="PERIODIC_TEST",title="Periodic",status="PUBLISHED",pass_threshold=90)
            session.add_all([user,lesson1,lesson2]);await session.flush()
            session.add_all([exercise,periodic]);await session.flush()
            session.add_all([CurriculumUnit(hsk_level_id=hsk1.id,unit_type="LESSON",lesson_id=lesson1_id,order_index=base1+1),
                CurriculumUnit(hsk_level_id=hsk1.id,unit_type="PERIODIC_TEST",assessment_id=periodic_id,order_index=base1+2),
                CurriculumUnit(hsk_level_id=hsk2.id,unit_type="LESSON",lesson_id=lesson2_id,order_index=base2+1)])
            exq=Question(assessment_id=exercise_id,type="multiple_choice",prompt="Exercise",order_index=1,points=1)
            perq=Question(assessment_id=periodic_id,type="multiple_choice",prompt="Periodic",order_index=1,points=1)
            session.add_all([exq,perq]);await session.flush()
            exgood=QuestionOption(question_id=exq.id,option_text="good",order_index=1,is_correct=True)
            pergood=QuestionOption(question_id=perq.id,option_text="good",order_index=1,is_correct=True)
            perbad=QuestionOption(question_id=perq.id,option_text="bad",order_index=2,is_correct=False)
            session.add_all([exgood,pergood,perbad]);await session.flush()
            return hsk1.id,hsk2.id,exq.id,exgood.id,perq.id,pergood.id,perbad.id
    hsk1_id,hsk2_id,exq_id,exgood_id,perq_id,pergood_id,perbad_id=asyncio.run(setup())
    async def current_user():
        async with SessionFactory() as session:
            return await session.get(User, user_id)
    app.dependency_overrides[get_current_user]=current_user
    try:
        with TestClient(app) as client:
            for section in client.get("/api/v1/pronunciation").json():
                assert client.post(f"/api/v1/pronunciation/{section['id']}/complete").status_code==200
            exercise_attempt=client.post(f"/api/v1/assessments/{exercise_id}/attempts").json()
            passed=client.post(f"/api/v1/assessment-attempts/{exercise_attempt['id']}/submit",json={"answers":[{"question_id":str(exq_id),"answer":{"option_id":str(exgood_id)}}]})
            assert passed.status_code==200 and passed.json()["passed"] is True
            before_start=client.get(f"/api/v1/me/progress/lessons/{lesson1_id}").json()
            assert before_start["theory_completed_at"] is None and before_start["completed_at"] is None
            assert client.get(f"/api/v1/lessons/{lesson1_id}").status_code==200
            after_start=client.get(f"/api/v1/me/progress/lessons/{lesson1_id}").json()
            assert after_start["theory_completed_at"] is not None and after_start["completed_at"] is not None
            state=client.get(f"/api/v1/hsk-levels/{hsk1_id}/curriculum").json()["units"]
            assert state[0]["state"]=="COMPLETED" and state[1]["state"]=="AVAILABLE"
            assert client.get(f"/api/v1/hsk-levels/{hsk2_id}/curriculum").json()["units"][0]["state"]=="LOCKED"

            first=client.post(f"/api/v1/assessments/{periodic_id}/attempts").json()
            failed=client.post(f"/api/v1/assessment-attempts/{first['id']}/submit",json={"answers":[{"question_id":str(perq_id),"answer":{"option_id":str(perbad_id)}}]})
            assert failed.status_code==200 and failed.json()["passed"] is False
            assert client.get(f"/api/v1/hsk-levels/{hsk2_id}/curriculum").json()["units"][0]["state"]=="LOCKED"

            retry=client.post(f"/api/v1/assessments/{periodic_id}/attempts").json()
            assert retry["attempt_number"]==2
            successful=client.post(f"/api/v1/assessment-attempts/{retry['id']}/submit",json={"answers":[{"question_id":str(perq_id),"answer":{"option_id":str(pergood_id)}}]})
            assert successful.status_code==200 and successful.json()["passed"] is True
            assert client.get(f"/api/v1/hsk-levels/{hsk2_id}/curriculum").json()["units"][0]["state"]=="AVAILABLE"
    finally:
        app.dependency_overrides.pop(get_current_user,None)
        async def cleanup():
            async with SessionFactory.begin() as session:
                assessment_ids=(exercise_id,periodic_id)
                attempts=select(AssessmentAttempt.id).where(AssessmentAttempt.assessment_id.in_(assessment_ids))
                await session.execute(delete(AttemptAnswer).where(AttemptAnswer.assessment_attempt_id.in_(attempts)))
                await session.execute(delete(AssessmentAttempt).where(AssessmentAttempt.assessment_id.in_(assessment_ids)))
                questions=select(Question.id).where(Question.assessment_id.in_(assessment_ids))
                await session.execute(delete(QuestionOption).where(QuestionOption.question_id.in_(questions)))
                await session.execute(delete(Question).where(Question.assessment_id.in_(assessment_ids)))
                await session.execute(delete(CurriculumUnit).where(CurriculumUnit.lesson_id.in_((lesson1_id,lesson2_id))))
                await session.execute(delete(CurriculumUnit).where(CurriculumUnit.assessment_id==periodic_id))
                await session.execute(delete(Assessment).where(Assessment.id.in_(assessment_ids)))
                await session.execute(delete(LearnerLessonProgress).where(LearnerLessonProgress.user_id==user_id))
                await session.execute(delete(LearnerHSKProgress).where(LearnerHSKProgress.user_id==user_id))
                await session.execute(delete(PronunciationProgress).where(PronunciationProgress.user_id==user_id))
                await session.execute(delete(Lesson).where(Lesson.id.in_((lesson1_id,lesson2_id))))
                await session.execute(delete(User).where(User.id==user_id))
        asyncio.run(cleanup())
