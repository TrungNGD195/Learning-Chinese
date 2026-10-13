"""Admin-only aggregate reads that span multiple bounded product domains."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Assessment, AssessmentAttempt, User


async def statistics_inputs(session:AsyncSession):
    total=(await session.execute(select(func.count()).select_from(User))).scalar_one()
    learner_ids=(await session.execute(select(User.id).where(User.role=="LEARNER"))).scalars().all()
    average=(await session.execute(select(func.avg(AssessmentAttempt.score)).select_from(AssessmentAttempt)
        .join(Assessment,Assessment.id==AssessmentAttempt.assessment_id)
        .where(Assessment.type=="LESSON_EXERCISE",AssessmentAttempt.status=="GRADED",
            AssessmentAttempt.score.is_not(None)))).scalar_one()
    return total,learner_ids,average
