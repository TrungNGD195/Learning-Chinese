import asyncio
import copy
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4, UUID
import pytest
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.engine import engine
from app.database.models import User, HSKLevel, HskExamAttempt, Lesson, CurriculumUnit, LearnerLessonProgress
from app.core.errors import ApplicationError
from app.hsk_exam import service
from app.hsk_exam.schemas import ExamSession, SaveAnswer, SelfReview

@pytest.mark.parametrize('level,counts,seconds',[(1,[20,20],[900,1200]),(2,[25,25,10],[1200,1500,600]),(3,[30,30,10],[1680,1800,1200])])
def test_original_papers_match_current_hsk30_structure(level,counts,seconds):
    p=service.load_paper(level)
    assert [len(s['questions']) for s in p['sections']]==counts
    assert [s['duration_seconds'] for s in p['sections']]==seconds
    assert len({q['id'] for s in p['sections'] for q in s['questions']})==sum(counts)
    assert all(q['reference_answer'] and q['explanation'] for s in p['sections'] for q in s['questions'])
    for s in p['sections']:
        for q in s['questions']:
            if q['type']=='choice':assert q['correct_option_id'] in {o['id'] for o in q['options']}
            if level==3:assert not q.get('prompt_pinyin') and not q.get('reading_text_pinyin') and all(not o.get('pinyin') for o in q['options'])
    assert sum(bool(q['phonetic_hint']) for s in p['sections'] for q in s['questions'])==(5 if level>1 else 0)

def test_shuffling_preserves_sections_parts_and_answer_identity():
    p=service.load_paper(3);a=service.shuffled_paper(p,'user1:attempt1');b=service.shuffled_paper(p,'user2:attempt1')
    c=service.shuffled_paper(p,'user1:attempt2')
    orders=lambda paper:[[q['id'] for q in s['questions']] for s in paper['sections']]
    assert orders(a)!=orders(b) and orders(a)!=orders(c)
    assert a==service.shuffled_paper(p,'user1:attempt1')
    for original,shuffled in zip(p['sections'],a['sections']):
        assert original['id']==shuffled['id']
        assert [q['part'] for q in shuffled['questions']]==sorted(q['part'] for q in original['questions'])
        for q in shuffled['questions']:
            expected=next(x for x in original['questions'] if x['id']==q['id'])
            assert set(o['id'] for o in q['options'])==set(o['id'] for o in expected['options'])
            assert q['reference_answer']==expected['reference_answer']

def test_section_weighting_blanks_and_self_assessment_are_explicit():
    p=service.load_paper(3)
    answers={q['id']:q.get('correct_option_id',q['reference_answer']) for s in p['sections'] for q in s['questions']}
    result=service.grade(p,answers)
    assert result['score'] is None and result['pending_self_reviews']==5
    assert result['score_min']==250 and result['score_max']==300
    assert result['passed'] is None and result['includes_self_assessment'] is True
    result=service.grade(p,answers,{q['id']:1 for q in p['sections'][-1]['questions'] if q['type']=='sentence'})
    assert result['score']==300 and result['passed'] is True
    assert service.grade(p,{})['score']==0
    assert service.grade(p,{})['passed'] is False
    q=next(q for q in p['sections'][-1]['questions'] if q['type']=='fill')
    assert service.grade(p,{q['id']:'　'+q['reference_answer']+'。'})['score']==10

async def isolated(work,complete=True):
    async with engine.connect() as connection:
        outer=await connection.begin()
        try:
            async with AsyncSession(bind=connection,expire_on_commit=False,join_transaction_mode='create_savepoint') as session:
                for n in [1,2,3]:
                    if not await session.scalar(select(HSKLevel.id).where(HSKLevel.level_number==n)):
                        session.add(HSKLevel(level_number=n,order_index=n,title=f'HSK {n}'))
                users=[User(id=uuid4(),email=f'exam-{uuid4()}@example.invalid',password_hash='unused',full_name='Exam Test',role='LEARNER') for _ in range(2)]
                session.add_all(users);await session.flush()
                for n,count in service.REQUIRED_LESSONS.items():
                    level_id=await session.scalar(select(HSKLevel.id).where(HSKLevel.level_number==n))
                    for number in range(1,count+1):
                        lesson=await session.scalar(select(Lesson).where(Lesson.hsk_level_id==level_id,Lesson.lesson_number==number))
                        if lesson is None:
                            lesson=Lesson(hsk_level_id=level_id,lesson_number=number,title=f'Exam prerequisite {n}-{number}',status='PUBLISHED')
                            session.add(lesson);await session.flush()
                        lesson.status='PUBLISHED'
                        if not await session.scalar(select(CurriculumUnit.id).where(CurriculumUnit.lesson_id==lesson.id)):
                            order=1+(await session.scalar(select(func.max(CurriculumUnit.order_index)).where(CurriculumUnit.hsk_level_id==level_id)) or 0)
                            session.add(CurriculumUnit(hsk_level_id=level_id,unit_type='LESSON',lesson_id=lesson.id,order_index=order));await session.flush()
                        if complete:
                            for user in users:session.add(LearnerLessonProgress(user_id=user.id,lesson_id=lesson.id,completed_at=datetime.now(UTC),theory_completed_at=datetime.now(UTC)))
                await session.flush()
                await work(session,*[u.id for u in users])
        finally:await outer.rollback()

def test_exam_sessions_own_keys_save_drafts_and_never_leak_results_before_submission():
    async def run(s,u,other):
        first=await service.start(s,u,1);ident=first['id']
        safe=ExamSession.model_validate(first).model_dump_json()
        for forbidden in ['reference_answer','correct_option_id','accepted_answers','explanation']:
            assert forbidden not in safe
        again=await service.start(s,u,1)
        assert again['id']==ident and again['questions']==first['questions']
        with pytest.raises(ApplicationError):await service.get_session(s,other,ident)
        question=first['questions'][0]
        saved=await service.save(s,u,ident,SaveAnswer(section_index=0,question_id=question['id'],answer=question['options'][0]['id']))
        assert saved['answers'][question['id']]==question['options'][0]['id'] and saved['result'] is None
        assert (await service.get_session(s,u,ident))['questions']==first['questions']
        with pytest.raises(ApplicationError):await service.save(s,u,ident,SaveAnswer(section_index=0,question_id=question['id'],answer='foreign-option'))
        next_=await service.next_section(s,u,ident,0)
        assert next_['section_index']==1 and next_['result'] is None
        assert (await service.next_section(s,u,ident,0))['section_index']==1
        with pytest.raises(ApplicationError):await service.save(s,u,ident,SaveAnswer(section_index=0,question_id=question['id'],answer='o1'))
        completed=await service.next_section(s,u,ident,1)
        assert completed['status']=='GRADED' and len(completed['result']['questions'])==40
        assert all(q['reference_answer'] and q['explanation'] for q in completed['result']['questions'])
        second=await service.start(s,u,1)
        assert second['attempt_number']==2 and second['id']!=ident
        assert second['questions']!=first['questions']
        assert len(await service.history(s,u,1))==2
    asyncio.run(isolated(run))

@pytest.mark.parametrize('level',[1,2,3])
def test_exam_requires_every_lesson_of_its_own_level(level):
    async def run(s,u,other):
        count=service.REQUIRED_LESSONS[level]
        access=await service.availability(s,u,level)
        assert access=={'unlocked':False,'completed_lessons':0,'total_lessons':count}
        with pytest.raises(ApplicationError) as error:await service.start(s,u,level)
        assert error.value.code=='HSK_EXAM_LOCKED' and error.value.status_code==403
        rows=await service.repository.lesson_completions(s,u,level)
        for row in rows[:-1]:s.add(LearnerLessonProgress(user_id=u,lesson_id=row.id,completed_at=datetime.now(UTC),theory_completed_at=datetime.now(UTC)))
        await s.flush()
        assert (await service.availability(s,u,level))['completed_lessons']==count-1
        with pytest.raises(ApplicationError):await service.start(s,u,level)
        # Merely starting/viewing theory is not a completed lesson.
        last=LearnerLessonProgress(user_id=u,lesson_id=rows[-1].id,theory_completed_at=datetime.now(UTC))
        s.add(last);await s.flush()
        with pytest.raises(ApplicationError):await service.start(s,u,level)
        last.completed_at=datetime.now(UTC);await s.flush()
        assert (await service.start(s,u,level))['status']=='IN_PROGRESS'
        other_level=2 if level==1 else 1
        assert not (await service.availability(s,u,other_level))['unlocked']
    asyncio.run(isolated(run,complete=False))

def test_empty_missing_draft_catalogs_and_new_published_lessons_do_not_unlock_early():
    async def run(s,u,other):
        level_id=await s.scalar(select(HSKLevel.id).where(HSKLevel.level_number==3))
        core=await s.scalar(select(Lesson).where(Lesson.hsk_level_id==level_id,Lesson.lesson_number==15))
        core.status='DRAFT';await s.flush()
        access=await service.availability(s,u,3)
        assert access=={'unlocked':False,'completed_lessons':14,'total_lessons':15}
        core.status='PUBLISHED';await s.flush()
        extra=Lesson(hsk_level_id=level_id,lesson_number=16,title='Optional draft',status='DRAFT')
        s.add(extra);await s.flush()
        order=1+(await s.scalar(select(func.max(CurriculumUnit.order_index)).where(CurriculumUnit.hsk_level_id==level_id)) or 0)
        s.add(CurriculumUnit(hsk_level_id=level_id,unit_type='LESSON',lesson_id=extra.id,order_index=order));await s.flush()
        assert (await service.availability(s,u,3))['unlocked']
        extra.status='PUBLISHED';await s.flush()
        assert (await service.availability(s,u,3))=={'unlocked':False,'completed_lessons':15,'total_lessons':16}
        await s.execute(delete(CurriculumUnit).where(CurriculumUnit.hsk_level_id==level_id))
        assert (await service.availability(s,u,3))=={'unlocked':False,'completed_lessons':0,'total_lessons':15}
    asyncio.run(isolated(run))

def test_existing_active_attempt_cannot_bypass_gate_and_submitted_results_are_preserved():
    async def run(s,u,other):
        old=await service.start(s,u,3)
        for index in range(3):await service.next_section(s,u,old['id'],index)
        current=await service.start(s,u,3)
        progress=await s.scalar(select(LearnerLessonProgress).join(Lesson,Lesson.id==LearnerLessonProgress.lesson_id)
            .join(HSKLevel,HSKLevel.id==Lesson.hsk_level_id).where(LearnerLessonProgress.user_id==u,HSKLevel.level_number==3,Lesson.lesson_number==15))
        progress.completed_at=None;await s.commit()
        for action in [lambda:service.start(s,u,3),lambda:service.get_session(s,u,current['id']),
            lambda:service.next_section(s,u,current['id'],0),lambda:service.save(s,u,current['id'],SaveAnswer(section_index=0,question_id=current['questions'][0]['id'],answer='o1'))]:
            with pytest.raises(ApplicationError) as error:await action()
            assert error.value.code=='HSK_EXAM_LOCKED'
        assert (await service.get_session(s,u,old['id']))['status']=='GRADED'
        assert len(await service.history(s,u,3))==2
    asyncio.run(isolated(run))

def test_server_deadlines_cannot_be_extended_by_reload_or_writing_old_sections():
    async def run(s,u,other):
        first=await service.start(s,u,2);a=await s.get(HskExamAttempt,first['id'])
        a.section_started_at=datetime.now(UTC)-timedelta(minutes=21);await s.commit()
        state=await service.get_session(s,u,a.id)
        assert state['section_index']==1
        old=state['section_deadline'];assert (await service.get_session(s,u,a.id))['section_deadline']==old
        a.section_started_at=datetime.now(UTC)-timedelta(hours=3);await s.commit()
        state=await service.get_session(s,u,a.id)
        assert state['status']=='GRADED' and state['result']['score']==0
        with pytest.raises(ApplicationError):await service.save(s,u,a.id,SaveAnswer(section_index=2,question_id='h2-writing-01',answer='o1'))
    asyncio.run(isolated(run))

def test_self_review_is_owner_only_after_submit_and_stays_labelled_self_assessed():
    async def run(s,u,other):
        state=await service.start(s,u,3);ident=state['id']
        await service.next_section(s,u,ident,0);state=await service.next_section(s,u,ident,1)
        q=next(q for q in state['questions'] if q['type']=='sentence')
        await service.save(s,u,ident,SaveAnswer(section_index=2,question_id=q['id'],answer='他们一起搬家。'))
        with pytest.raises(ApplicationError):await service.self_review(s,u,ident,SelfReview(question_id=q['id'],rating=1))
        state=await service.next_section(s,u,ident,2)
        assert state['result']['pending_self_reviews']==1
        with pytest.raises(ApplicationError):await service.self_review(s,other,ident,SelfReview(question_id=q['id'],rating=1))
        state=await service.self_review(s,u,ident,SelfReview(question_id=q['id'],rating=0.5))
        assert state['result']['score']==5 and state['result']['includes_self_assessment'] is True
        assert (await service.get_session(s,u,ident))['result']==state['result']
    asyncio.run(isolated(run))
