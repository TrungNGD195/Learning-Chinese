from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.current_user import get_current_user
from app.database.session import get_db_session
from app.database.models import User
from app.exercise import service
from app.exercise.grading import AIGrader, get_ai_grader
from app.exercise.schemas import (AssessmentResponse, AttemptDetailResponse, AttemptHistoryPage,
    AttemptResponse, AttemptSubmissionResponse, SubmitAttemptRequest)

router = APIRouter()


@router.get("/assessments/{assessment_id}",response_model=AssessmentResponse)
async def assessment(assessment_id: UUID, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db_session)):
    return await service.assessment_payload(session, current_user.id, assessment_id)


@router.post("/assessments/{assessment_id}/attempts",response_model=AttemptResponse)
async def start(assessment_id: UUID, response: Response, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db_session)):
    data, response.status_code = await service.start_attempt(session, current_user.id, assessment_id)
    return data


@router.post("/assessment-attempts/{attempt_id}/submit",response_model=AttemptSubmissionResponse)
async def submit(attempt_id: UUID, payload: SubmitAttemptRequest, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db_session), ai_grader: AIGrader = Depends(get_ai_grader)):
    return await service.submit_attempt(session, current_user.id, attempt_id, payload.model_dump(mode="json"), ai_grader)


@router.get("/me/assessment-attempts",response_model=AttemptHistoryPage)
async def history(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), assessment_id: UUID | None = None,
                 lesson_id: UUID | None = None, assessment_type: str | None = None,
                 current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db_session)):
    if assessment_type is not None and assessment_type not in {"LESSON_EXERCISE", "PERIODIC_TEST"}:
        from app.core.errors import ApplicationError
        raise ApplicationError("INVALID_FILTER", "Assessment type filter is invalid", status_code=422)
    return await service.history(session, current_user.id, page, page_size, assessment_id, lesson_id, assessment_type)


@router.get("/me/assessment-attempts/{attempt_id}",response_model=AttemptDetailResponse)
async def detail(attempt_id: UUID, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db_session)):
    return await service.attempt_detail(session, current_user.id, attempt_id)
