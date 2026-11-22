"""Server-timed, per-attempt shuffled original HSK3.0 practice exams.

Exam snapshots are private JSON, never returned directly. Existing curriculum,
assessment DTOs, thresholds and completion rules are deliberately independent.
"""
import copy
import hashlib
import json
import random
import unicodedata
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from uuid import UUID
from app.core.errors import ApplicationError
from app.hsk_exam import repository
from app.hsk_exam.schemas import ExamInfo, ExamQuestion

CONTENT=Path(__file__).resolve().parents[2]/'content'/'hsk-exams'
REQUIRED_LESSONS={1:15,2:10,3:15}

def fail(code,message,status=409):raise ApplicationError(code,message,status_code=status)

@lru_cache(maxsize=3)
def load_paper(level):
    if level not in {1,2,3}:fail('NOT_FOUND','HSK mock exam not found',404)
    raw=(CONTENT/f'hsk-{level}.json').read_bytes()
    paper=json.loads(raw)
    expected={1:[20,20],2:[25,25,10],3:[30,30,10]}[level]
    if [len(s['questions']) for s in paper['sections']]!=expected:
        raise RuntimeError('Invalid HSK exam manifest')
    paper['version']+='-'+hashlib.sha256(raw).hexdigest()[:12]
    return paper

def info(paper):
    return ExamInfo.model_validate({**paper,'sections':[{**s,'question_count':len(s['questions'])} for s in paper['sections']]}).model_dump()

async def availability(session,user_id,level):
    if level not in REQUIRED_LESSONS:fail('NOT_FOUND','HSK mock exam not found',404)
    rows=await repository.lesson_completions(session,user_id,level)
    # Planned slots still count when missing/draft/archived. An incomplete
    # published catalog must never turn into an early exam unlock.
    missing=set(range(1,REQUIRED_LESSONS[level]+1))-{row.lesson_number for row in rows}
    total=len(rows)+len(missing)
    completed=sum(row.completed_at is not None for row in rows)
    return {'unlocked':completed==total and total>0,'completed_lessons':completed,'total_lessons':total}

async def require_completion(session,user_id,level):
    access=await availability(session,user_id,level)
    if not access['unlocked']:
        fail('HSK_EXAM_LOCKED',f'Hoàn thành tất cả bài học HSK {level} trước khi mở bài thi ({access["completed_lessons"]}/{access["total_lessons"]} bài).',403)

async def exam_info(session,user_id,level):
    return {**info(load_paper(level)),'access':await availability(session,user_id,level)}

def shuffled_paper(paper, seed):
    result=copy.deepcopy(paper)
    # Keep official section/part boundaries; shuffle only independent questions
    # inside each part. Option IDs stay attached to their original answer keys.
    rng=random.Random(seed)
    for section in result['sections']:
        rows=[]
        for part in sorted({q['part'] for q in section['questions']}):
            group=[q for q in section['questions'] if q['part']==part]
            rng.shuffle(group);rows.extend(group)
        section['questions']=rows
        for q in rows:rng.shuffle(q['options'])
    return result

def safe_question(q):return ExamQuestion.model_validate(q).model_dump()

def normalized(value):
    return ''.join(c for c in unicodedata.normalize('NFKC',value or '') if not c.isspace() and not unicodedata.category(c).startswith('P'))

def grade(paper,answers,ratings=None):
    ratings=ratings or {};sections=[];reviews=[];pending=0
    for section in paper['sections']:
        fractions=[]
        for q in section['questions']:
            answer=answers.get(q['id']) or None
            fraction=0.0;self_rating=None
            if q['type']=='choice':fraction=float(answer==q['correct_option_id'])
            elif q['type']=='fill':fraction=float(bool(answer) and normalized(answer) in {normalized(q['reference_answer']),*(normalized(a) for a in q['accepted_answers'])})
            elif answer:
                self_rating=ratings.get(q['id'])
                fraction=self_rating
                if fraction is None:pending+=1
            fractions.append(fraction)
            answer_text=next((o['text'] or o['image_hanzi'] for o in q['options'] if o['id']==answer),answer)
            reviews.append({**safe_question(q),'section_id':section['id'],'section_label':section['label'],
                'answer':answer,'answer_text':answer_text,'reference_answer':q['reference_answer'],
                'explanation':q['explanation'],'is_correct':fraction==1 if fraction is not None else None,
                'earned_fraction':fraction,'self_rating':self_rating})
        low=100*sum(x or 0 for x in fractions)/len(fractions)
        high=low+100*sum(x is None for x in fractions)/len(fractions)
        sections.append({'id':section['id'],'label':section['label'],'score':round(low,2) if None not in fractions else None,
            'score_min':round(low,2),'score_max':round(high,2),'correct':sum(x==1 for x in fractions),'total':len(fractions)})
    low=round(sum(s['score_min'] for s in sections),2);high=round(sum(s['score_max'] for s in sections),2)
    return {'score':low if not pending else None,'score_min':low,'score_max':high,'max_score':paper['max_score'],
        'pass_score':paper['pass_score'],'passed':low>=paper['pass_score'] if not pending else None,
        'pending_self_reviews':pending,'includes_self_assessment':any(q['type']=='sentence' for q in reviews),
        'sections':sections,'questions':reviews}

def deadline(attempt):
    if attempt.status!='IN_PROGRESS':return None
    return attempt.section_started_at+timedelta(seconds=attempt.paper['sections'][attempt.section_index]['duration_seconds'])

def finish(attempt,now):
    attempt.status='GRADED';attempt.submitted_at=now
    attempt.result=grade(attempt.paper,attempt.answers)

def synchronise(attempt,now):
    # Background tabs and offline clients do not pause or reset server deadlines.
    while attempt.status=='IN_PROGRESS' and now>=deadline(attempt):
        end=deadline(attempt)
        if attempt.section_index+1==len(attempt.paper['sections']):finish(attempt,end)
        else:attempt.section_index+=1;attempt.section_started_at=end

async def get_owned(session,user_id,attempt_id):
    attempt=await repository.get_owned(session,user_id,attempt_id)
    if attempt is None:fail('NOT_FOUND','Exam attempt not found',404)
    synchronise(attempt,datetime.now(UTC))
    if attempt.status=='IN_PROGRESS':await require_completion(session,user_id,attempt.hsk_level)
    return attempt

def payload(attempt):
    questions=attempt.paper['sections'][attempt.section_index]['questions'] if attempt.status=='IN_PROGRESS' else []
    return {'id':attempt.id,'level':attempt.hsk_level,'attempt_number':attempt.attempt_number,'status':attempt.status,
        'info':info(attempt.paper),'started_at':attempt.started_at,'submitted_at':attempt.submitted_at,
        'server_time':datetime.now(UTC),'section_index':attempt.section_index,'section_deadline':deadline(attempt),
        'questions':[safe_question(q) for q in questions],
        'answers':{q['id']:attempt.answers[q['id']] for q in questions if q['id'] in attempt.answers},
        'result':attempt.result if attempt.status=='GRADED' else None}

async def start(session,user_id,level):
    paper=load_paper(level)
    if not await repository.level_exists(session,level):
        fail('NOT_FOUND','HSK level not found',404)
    await repository.lock_user(session,user_id)
    await require_completion(session,user_id,level)
    active=await repository.active_attempt(session,user_id,level)
    if active:
        synchronise(active,datetime.now(UTC))
        if active.status=='IN_PROGRESS':
            data=payload(active);await session.commit();return data
        await session.flush()
    number=await repository.next_number(session,user_id,level)
    from uuid import uuid4
    ident=uuid4();now=datetime.now(UTC)
    active=await repository.create(session,id=ident,user_id=user_id,hsk_level=level,attempt_number=number,status='IN_PROGRESS',
        content_version=paper['version'],paper=shuffled_paper(paper,f'{user_id}:{ident}'),answers={},section_index=0,section_started_at=now,started_at=now)
    data=payload(active);await session.commit();return data

async def get_session(session,user_id,attempt_id):
    attempt=await get_owned(session,user_id,attempt_id)
    data=payload(attempt);await session.commit();return data

async def save(session,user_id,attempt_id,body):
    attempt=await get_owned(session,user_id,attempt_id)
    if attempt.status!='IN_PROGRESS' or body.section_index!=attempt.section_index:
        await session.commit();fail('EXAM_SECTION_CLOSED','This section is already closed')
    q=next((q for q in attempt.paper['sections'][attempt.section_index]['questions'] if q['id']==body.question_id),None)
    if q is None:fail('INVALID_ANSWER','Question is not in the current section',422)
    if q['type']=='choice' and body.answer and body.answer not in {o['id'] for o in q['options']}:
        fail('INVALID_ANSWER','Option does not belong to this question',422)
    attempt.answers={**attempt.answers,body.question_id:body.answer}
    data=payload(attempt);await session.commit();return data

async def next_section(session,user_id,attempt_id,index):
    attempt=await get_owned(session,user_id,attempt_id)
    if attempt.status!='IN_PROGRESS' or attempt.section_index!=index:
        data=payload(attempt);await session.commit();return data
    now=datetime.now(UTC)
    if index+1==len(attempt.paper['sections']):finish(attempt,now)
    else:attempt.section_index+=1;attempt.section_started_at=now
    data=payload(attempt);await session.commit();return data

async def self_review(session,user_id,attempt_id,body):
    attempt=await get_owned(session,user_id,attempt_id)
    if attempt.status!='GRADED':fail('EXAM_NOT_SUBMITTED','Submit the exam before reviewing answers')
    q=next((q for s in attempt.paper['sections'] for q in s['questions'] if q['id']==body.question_id and q['type']=='sentence'),None)
    if q is None or not attempt.answers.get(q['id']):fail('INVALID_SELF_REVIEW','Only answered open writing questions can be self-assessed',422)
    ratings={q['id']:q['self_rating'] for q in attempt.result['questions'] if q['self_rating'] is not None}
    ratings[q['id']]=float(body.rating)
    attempt.result=grade(attempt.paper,attempt.answers,ratings)
    data=payload(attempt);await session.commit();return data

async def history(session,user_id,level):
    rows=await repository.history(session,user_id,level)
    for row in rows:synchronise(row,datetime.now(UTC))
    data=[{'id':r.id,'attempt_number':r.attempt_number,'status':r.status,'started_at':r.started_at,'submitted_at':r.submitted_at,
        'score':(r.result or {}).get('score'),'max_score':r.paper['max_score'],
        'pending_self_reviews':(r.result or {}).get('pending_self_reviews',0),
        'includes_self_assessment':(r.result or {}).get('includes_self_assessment',False)} for r in rows]
    await session.commit();return data
