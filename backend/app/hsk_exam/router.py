from uuid import UUID
from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.current_user import require_learner
from app.database.models import User
from app.database.session import get_db_session
from app.hsk_exam import service
from app.hsk_exam.schemas import ExamInfo, ExamSession, SaveAnswer, FinishSection, SelfReview, ExamHistoryItem

router=APIRouter()

@router.get('/hsk-mock-exams/{level}',response_model=ExamInfo)
async def exam_info(level:int=Path(ge=1,le=3),user:User=Depends(require_learner),session:AsyncSession=Depends(get_db_session)):
    return await service.exam_info(session,user.id,level)

@router.post('/hsk-mock-exams/{level}/attempts',response_model=ExamSession)
async def start(level:int=Path(ge=1,le=3),user:User=Depends(require_learner),session:AsyncSession=Depends(get_db_session)):
    return await service.start(session,user.id,level)

@router.get('/hsk-mock-exams/{level}/attempts',response_model=list[ExamHistoryItem])
async def history(level:int=Path(ge=1,le=3),user:User=Depends(require_learner),session:AsyncSession=Depends(get_db_session)):
    return await service.history(session,user.id,level)

@router.get('/hsk-mock-exam-attempts/{attempt_id}',response_model=ExamSession)
async def attempt(attempt_id:UUID,user:User=Depends(require_learner),session:AsyncSession=Depends(get_db_session)):
    return await service.get_session(session,user.id,attempt_id)

@router.put('/hsk-mock-exam-attempts/{attempt_id}/answer',response_model=ExamSession)
async def save(attempt_id:UUID,body:SaveAnswer,user:User=Depends(require_learner),session:AsyncSession=Depends(get_db_session)):
    return await service.save(session,user.id,attempt_id,body)

@router.post('/hsk-mock-exam-attempts/{attempt_id}/next-section',response_model=ExamSession)
async def advance(attempt_id:UUID,body:FinishSection,user:User=Depends(require_learner),session:AsyncSession=Depends(get_db_session)):
    return await service.next_section(session,user.id,attempt_id,body.section_index)

@router.post('/hsk-mock-exam-attempts/{attempt_id}/self-review',response_model=ExamSession)
async def review(attempt_id:UUID,body:SelfReview,user:User=Depends(require_learner),session:AsyncSession=Depends(get_db_session)):
    return await service.self_review(session,user.id,attempt_id,body)
