import asyncio
from uuid import uuid4
from sqlalchemy import select
from app.database.models import Lesson, Assessment, AssessmentAttempt, Question, QuestionOption, PracticeResponse
from app.exercise import service, feedback
from app.exercise.schemas import SubmissionAnswer
from app.core.errors import ApplicationError
from tests.test_hsk_mock_exams import isolated
import pytest

def test_feedback_is_first_answer_only_owned_and_cannot_be_used_for_tests(monkeypatch):
    async def allow(*args):pass
    monkeypatch.setattr(service,'_assessment_access',allow)
    monkeypatch.setattr(service.progress,'after_attempt',allow)
    async def run(s,u,other):
        from app.database.models import HSKLevel
        level=await s.scalar(select(HSKLevel.id).where(HSKLevel.level_number==3))
        lesson=Lesson(hsk_level_id=level,lesson_number=10000+uuid4().int%1000000,title='Feedback test',status='PUBLISHED')
        s.add(lesson);await s.flush()
        assessment=Assessment(type='LESSON_EXERCISE',lesson_id=lesson.id,title='Feedback',status='PUBLISHED',pass_threshold=80)
        s.add(assessment);await s.flush()
        q=Question(assessment_id=assessment.id,type='multiple_choice',prompt='你好',order_index=1,points=1,rubric='你好 nghĩa là xin chào.',config={})
        s.add(q);await s.flush()
        correct=QuestionOption(question_id=q.id,option_text='Xin chào',order_index=1,is_correct=True)
        wrong=QuestionOption(question_id=q.id,option_text='Tạm biệt',order_index=2,is_correct=False)
        a=AssessmentAttempt(user_id=u,assessment_id=assessment.id,attempt_number=1,status='IN_PROGRESS')
        s.add_all([correct,wrong,a]);await s.flush()
        aid,qid,cid,wid=a.id,q.id,correct.id,wrong.id
        payload=SubmissionAnswer(question_id=q.id,answer={'option_id':wrong.id})
        with pytest.raises(ApplicationError):await feedback.check_answer(s,other,a.id,payload)
        result=await feedback.check_answer(s,u,a.id,payload)
        assert result['is_correct'] is False and result['reference_answer']=='Xin chào' and result['feedback']
        result2=await feedback.check_answer(s,u,a.id,SubmissionAnswer(question_id=q.id,answer={'option_id':correct.id}))
        assert result2==result
        assert len(await feedback.responses(s,a.id))==1
        with pytest.raises(ApplicationError):await service.submit_attempt(s,u,aid,{'answers':[{'question_id':str(qid),'answer':{'option_id':str(cid)}}]})
        assert (await s.get(AssessmentAttempt,aid)).status=='IN_PROGRESS'
        submitted=await service.submit_attempt(s,u,aid,{'answers':[{'question_id':str(qid),'answer':{'option_id':str(wid)}}]})
        assert submitted['score']==0 and submitted['passed'] is False
        periodic=Assessment(type='PERIODIC_TEST',title='Do not reveal',status='PUBLISHED',pass_threshold=60)
        s.add(periodic);await s.flush()
        exam=AssessmentAttempt(user_id=u,assessment_id=periodic.id,attempt_number=1,status='IN_PROGRESS')
        s.add(exam);await s.flush()
        with pytest.raises(ApplicationError) as caught:await feedback.check_answer(s,u,exam.id,payload)
        assert caught.value.status_code==403
    asyncio.run(isolated(run))
