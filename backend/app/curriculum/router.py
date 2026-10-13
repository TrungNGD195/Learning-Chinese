from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.current_user import get_current_user
from app.database.models import User
from app.curriculum import service
from app.database.session import get_db_session
from app.progress.schemas import CurriculumResponse, HSKLevelResponse, LessonResponse

router=APIRouter()


@router.get("/hsk-levels",response_model=list[HSKLevelResponse])
async def hsk_levels(current_user:User=Depends(get_current_user),session:AsyncSession=Depends(get_db_session)):
    return await service.list_hsk_levels(session,current_user.id)


@router.get("/hsk-levels/{hsk_id}/curriculum",response_model=CurriculumResponse)
async def curriculum(hsk_id:UUID,current_user:User=Depends(get_current_user),session:AsyncSession=Depends(get_db_session)):
    return await service.get_curriculum(session,current_user.id,hsk_id)


@router.get("/lessons/{lesson_id}",response_model=LessonResponse)
async def lesson(lesson_id:UUID,current_user:User=Depends(get_current_user),session:AsyncSession=Depends(get_db_session)):
    return await service.get_lesson(session,current_user.id,lesson_id)
