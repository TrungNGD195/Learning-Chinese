from app.core.errors import ApplicationError
from app.readings import repository


def fail(code, message, status=409):
    raise ApplicationError(code, message, status_code=status)


async def list_readings(session, lesson_id):
    return await repository.list_readings(session, lesson_id)


async def lesson_for_edit(session, lesson_id):
    lesson = await repository.get_lesson(session, lesson_id, for_update=True)
    if lesson is None:
        fail('NOT_FOUND', 'Lesson was not found', 404)
    if lesson.status == 'ARCHIVED':
        fail('LESSON_IMMUTABLE', 'Archived lesson content is read only')
    return lesson


async def admin_list(session, lesson_id):
    if await repository.get_lesson(session, lesson_id) is None:
        fail('NOT_FOUND', 'Lesson was not found', 404)
    return await list_readings(session, lesson_id)


async def save_reading(session, lesson_id, body, reading_id=None):
    async with session.begin_nested():
        await lesson_for_edit(session, lesson_id)
        row = None
        if reading_id is not None:
            row = await repository.get_reading(session, lesson_id, reading_id, for_update=True)
            if row is None:
                fail('NOT_FOUND', 'Reading was not found in this lesson', 404)
        duplicate = await repository.order_taken(session, lesson_id, body['order_index'], reading_id)
        if duplicate:
            fail('READING_ORDER_CONFLICT', 'A reading already uses this order index')
        if row is None:
            row = await repository.create(session, lesson_id, body)
        else:
            # Completion refers to the version actually read, not an older open page.
            row = await repository.update(session, row, body)
    await session.commit()
    return row


async def delete_reading(session, lesson_id, reading_id):
    async with session.begin_nested():
        lesson = await lesson_for_edit(session, lesson_id)
        if lesson.status != 'DRAFT':
            fail('LESSON_CONTENT_DETACH_DRAFT_ONLY', 'Readings can only be removed from draft lessons')
        row = await repository.get_reading(session, lesson_id, reading_id, for_update=True)
        if row is None:
            fail('NOT_FOUND', 'Reading was not found in this lesson', 404)
        if await repository.has_history(session, row.id):
            fail('ITEM_HAS_LEARNER_HISTORY', 'Reading has learner completion history')
        await repository.delete(session, row)
    await session.commit()
    return {'deleted': True}
