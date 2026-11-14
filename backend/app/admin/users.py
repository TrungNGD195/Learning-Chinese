"""Read-only account directory. No ORM user entities or secrets leave this module."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.current_user import require_admin
from app.core.errors import ApplicationError
from app.database.models import User, LearnerLessonProgress, PronunciationLessonProgress, Lesson, HSKLevel, AssessmentAttempt
from app.database.session import get_db_session

router = APIRouter(prefix="/admin/users", tags=["admin"], dependencies=[Depends(require_admin)])


class AccountSummary(BaseModel):
    id: UUID
    full_name: str
    email: str
    role: Literal["ADMIN", "LEARNER"]
    is_active: bool
    created_at: datetime
    completed_lessons: int


class AccountPage(BaseModel):
    items: list[AccountSummary]
    total: int
    page: int
    page_size: int


class LessonActivity(BaseModel):
    lesson_id: UUID
    title: str
    lesson_number: int
    hsk_level: int
    started_at: datetime | None
    theory_completed_at: datetime | None
    completed_at: datetime | None


class AccountDetail(AccountSummary):
    pronunciation_completed: bool
    graded_attempts: int
    average_score: float | None
    lesson_activity: list[LessonActivity]


def account_projection():
    completed = (select(func.count()).select_from(LearnerLessonProgress)
                 .where(LearnerLessonProgress.user_id == User.id,
                        LearnerLessonProgress.completed_at.is_not(None)).correlate(User).scalar_subquery())
    return select(User.id, User.full_name, User.email, User.role, User.is_active,
                  User.created_at, completed.label("completed_lessons"))


@router.get("", response_model=AccountPage)
async def list_accounts(
    session: AsyncSession = Depends(get_db_session),
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    search: str = Query("", max_length=100), role: Literal["ADMIN", "LEARNER"] | None = None,
):
    conditions = []
    if search.strip():
        # Escape SQL wildcard characters: user search is literal, not a pattern.
        term = search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        conditions.append(or_(User.full_name.ilike(f"%{term}%", escape="\\"),
                              User.email.ilike(f"%{term}%", escape="\\")))
    if role:
        conditions.append(User.role == role)
    total = (await session.execute(select(func.count()).select_from(User).where(*conditions))).scalar_one()
    rows = (await session.execute(account_projection().where(*conditions)
            .order_by(User.created_at.desc(), User.id.desc()).offset((page-1)*page_size).limit(page_size))).mappings().all()
    return {"items": rows, "total": total, "page": page, "page_size": page_size}


@router.get("/{user_id}", response_model=AccountDetail)
async def account_detail(user_id: UUID, session: AsyncSession = Depends(get_db_session)):
    row = (await session.execute(account_projection().where(User.id == user_id))).mappings().one_or_none()
    if row is None:
        raise ApplicationError("NOT_FOUND", "Không tìm thấy tài khoản.", status_code=404)
    pronunciation = (await session.execute(select(PronunciationLessonProgress.completed_at)
                     .where(PronunciationLessonProgress.user_id == user_id))).scalar_one_or_none()
    attempts, average = (await session.execute(select(func.count(), func.avg(AssessmentAttempt.score))
                         .where(AssessmentAttempt.user_id == user_id, AssessmentAttempt.status == "GRADED"))).one()
    activity = (await session.execute(select(Lesson.id.label("lesson_id"), Lesson.title, Lesson.lesson_number,
                HSKLevel.level_number.label("hsk_level"), LearnerLessonProgress.started_at,
                LearnerLessonProgress.theory_completed_at, LearnerLessonProgress.completed_at)
                .select_from(LearnerLessonProgress).join(Lesson, Lesson.id == LearnerLessonProgress.lesson_id)
                .join(HSKLevel, HSKLevel.id == Lesson.hsk_level_id)
                .where(LearnerLessonProgress.user_id == user_id)
                .order_by(HSKLevel.level_number, Lesson.lesson_number))).mappings().all()
    return {**row, "pronunciation_completed": pronunciation is not None, "graded_attempts": attempts,
            "average_score": float(average) if average is not None else None, "lesson_activity": activity}
