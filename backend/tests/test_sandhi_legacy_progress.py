import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import delete, select

from app.database.models import PronunciationLessonProgress, PronunciationProgress, PronunciationSection, User
from app.database.seeds.required import seed_required_data
from app.database.session import SessionFactory
from app.progress import service


def test_existing_graduate_can_study_sandhi_without_losing_original_completion():
    async def run():
        await seed_required_data()
        ident, completed_at = uuid4(), datetime.now(UTC)
        async with SessionFactory.begin() as session:
            sections = (await session.execute(select(PronunciationSection))).scalars().all()
            session.add(User(id=ident, email=f'{ident}@example.invalid', password_hash='test-only', full_name='Legacy graduate', role='LEARNER'))
            await session.flush()
            session.add(PronunciationLessonProgress(user_id=ident, section_index=3, step_index=0, completed_at=completed_at))
            for section in sections:
                if section.code in {'INITIALS', 'FINALS', 'TONES'}:
                    session.add(PronunciationProgress(user_id=ident, pronunciation_section_id=section.id, completed_at=completed_at))
        try:
            async with SessionFactory() as session:
                state = await service.pronunciation_lesson(session, ident)
                assert state['current_section'] == 'SANDHI' and state['step_index'] == 0
                assert state['completed_at'] == completed_at and not state['can_finish']
                assert (await service.progression_snapshot(session, ident))[3] is True
                assert (await service.finish_pronunciation(session, ident))['completed_at'] == completed_at
                for step in range(12):
                    result = await service.advance_pronunciation(session, ident, 'SANDHI', step)
                    assert result['step_index'] == step + 1
                sandhi = next(section for section in sections if section.code == 'SANDHI')
                await service.complete_pronunciation(session, ident, sandhi.id)
                final = await service.pronunciation_lesson(session, ident)
                assert final['current_section'] is None and final['completed_at'] == completed_at
                assert all(section['completed_at'] for section in final['sections'])
        finally:
            async with SessionFactory.begin() as session:
                await session.execute(delete(PronunciationProgress).where(PronunciationProgress.user_id == ident))
                await session.execute(delete(PronunciationLessonProgress).where(PronunciationLessonProgress.user_id == ident))
                await session.execute(delete(User).where(User.id == ident))
    asyncio.run(run())
