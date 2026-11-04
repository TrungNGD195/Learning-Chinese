from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.current_user import require_learner
from app.curriculum import service as curriculum_service
from app.database.session import get_db_session
from app.database.models import User
from app.progress import service
from app.progress.schemas import (DashboardResponse, HSKProgressResponse, LessonProgressResponse,
    ProgressOverviewResponse, PronunciationAdvanceRequest, PronunciationLessonResponse,
    PronunciationSectionResponse, ViewProgressResponse)


router = APIRouter()


@router.get("/me/dashboard",response_model=DashboardResponse)
async def dashboard(current_user: User = Depends(require_learner), session: AsyncSession = Depends(get_db_session)):
    return await service.dashboard(session, current_user.id)


@router.get("/pronunciation",response_model=list[PronunciationSectionResponse])
async def pronunciation(current_user: User = Depends(require_learner), session: AsyncSession = Depends(get_db_session)):
    return await service.pronunciation_list(session, current_user.id)


@router.get("/pronunciation/lesson", response_model=PronunciationLessonResponse)
async def pronunciation_lesson(current_user: User = Depends(require_learner), session: AsyncSession = Depends(get_db_session)):
    return await service.pronunciation_lesson(session, current_user.id)


@router.post("/pronunciation/lesson/advance", response_model=PronunciationLessonResponse)
async def pronunciation_advance(body: PronunciationAdvanceRequest, current_user: User = Depends(require_learner), session: AsyncSession = Depends(get_db_session)):
    return await service.advance_pronunciation(session, current_user.id, body.section_code, body.step_index)


@router.post("/pronunciation/lesson/complete", response_model=PronunciationLessonResponse)
async def pronunciation_lesson_complete(current_user: User = Depends(require_learner), session: AsyncSession = Depends(get_db_session)):
    return await service.finish_pronunciation(session, current_user.id)


@router.post("/pronunciation/{section_id}/complete",response_model=dict)
async def pronunciation_complete(section_id: UUID, current_user: User = Depends(require_learner), session: AsyncSession = Depends(get_db_session)):
    return await service.complete_pronunciation(session, current_user.id, section_id)


@router.post("/lessons/{lesson_id}/theory/vocabulary/{lesson_vocabulary_id}/view",response_model=ViewProgressResponse)
async def vocabulary_view(lesson_id: UUID, lesson_vocabulary_id: UUID, current_user: User = Depends(require_learner), session: AsyncSession = Depends(get_db_session)):
    return await service.record_theory_view(session, current_user.id, lesson_id, lesson_vocabulary_id, "vocabulary")


@router.post("/lessons/{lesson_id}/theory/grammar/{lesson_grammar_id}/view",response_model=ViewProgressResponse)
async def grammar_view(lesson_id: UUID, lesson_grammar_id: UUID, current_user: User = Depends(require_learner), session: AsyncSession = Depends(get_db_session)):
    return await service.record_theory_view(session, current_user.id, lesson_id, lesson_grammar_id, "grammar")


@router.get("/me/progress",response_model=ProgressOverviewResponse)
async def progress(current_user: User = Depends(require_learner), session: AsyncSession = Depends(get_db_session)):
    return await service.progress_overview(session, current_user.id)


@router.get("/me/progress/hsk/{hsk_id}",response_model=HSKProgressResponse)
async def hsk_progress(hsk_id: UUID, current_user: User = Depends(require_learner), session: AsyncSession = Depends(get_db_session)):
    return await curriculum_service.get_hsk_progress(session, current_user.id, hsk_id)


@router.get("/me/progress/lessons/{lesson_id}",response_model=LessonProgressResponse)
async def lesson_progress(lesson_id: UUID, current_user: User = Depends(require_learner), session: AsyncSession = Depends(get_db_session)):
    return await service.lesson_progress(session, current_user.id, lesson_id)
