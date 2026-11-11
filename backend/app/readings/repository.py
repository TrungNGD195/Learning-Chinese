from sqlalchemy import select

from app.database.models import LearnerReadingProgress, Lesson, LessonReading


async def get_lesson(session, lesson_id, *, for_update=False):
    statement = select(Lesson).where(Lesson.id == lesson_id)
    if for_update:
        statement = statement.with_for_update().execution_options(populate_existing=True)
    return (await session.execute(statement)).scalar_one_or_none()


async def list_readings(session, lesson_id):
    return (await session.execute(select(LessonReading).where(LessonReading.lesson_id == lesson_id)
                                  .order_by(LessonReading.order_index, LessonReading.id))).scalars().all()


async def get_reading(session, lesson_id, reading_id, *, for_update=False):
    statement = select(LessonReading).where(LessonReading.id == reading_id, LessonReading.lesson_id == lesson_id)
    if for_update:
        statement = statement.with_for_update().execution_options(populate_existing=True)
    return (await session.execute(statement)).scalar_one_or_none()


async def order_taken(session, lesson_id, order_index, excluding=None):
    return await session.scalar(select(LessonReading.id).where(
        LessonReading.lesson_id == lesson_id, LessonReading.order_index == order_index,
        LessonReading.id != excluding if excluding else True)) is not None


async def create(session, lesson_id, body):
    row = LessonReading(lesson_id=lesson_id, **body)
    session.add(row)
    await session.flush()
    return row


async def update(session, row, body):
    changed = any(getattr(row, key) != value for key, value in body.items() if key != 'order_index')
    for key, value in body.items():
        setattr(row, key, value)
    if changed:
        row.version += 1
    await session.flush()
    return row


async def has_history(session, reading_id):
    return await session.scalar(select(LearnerReadingProgress.id).where(
        LearnerReadingProgress.lesson_reading_id == reading_id).limit(1)) is not None


async def delete(session, row):
    await session.delete(row)
    await session.flush()
