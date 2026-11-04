"""The last two theory views must converge even in overlapping transactions."""
import asyncio
from uuid import uuid4

from sqlalchemy import delete, select, text

from app.database.models import (
    Grammar, HSKLevel, LearnerGrammarProgress, LearnerLessonProgress,
    LearnerVocabularyProgress, Lesson, LessonGrammar, LessonVocabulary, User, Vocabulary,
)
from app.database.seeds.required import seed_required_data
from app.database.session import SessionFactory
from app.progress import repository


def test_simultaneous_last_vocabulary_and_grammar_views_complete_theory():
    async def scenario():
        user_id, lesson_id, word_id, grammar_id, word_link, grammar_link = [uuid4() for _ in range(6)]
        await seed_required_data()
        async with SessionFactory.begin() as session:
            hsk_id = await session.scalar(select(HSKLevel.id).where(HSKLevel.level_number == 1))
            session.add(User(id=user_id, email=f'{user_id}@example.invalid', password_hash='test-only', full_name='Concurrent learner', role='LEARNER'))
            session.add(Lesson(id=lesson_id, hsk_level_id=hsk_id, lesson_number=1_900_000 + user_id.int % 100_000, title='Concurrent theory', status='PUBLISHED'))
            session.add(Vocabulary(id=word_id, hanzi='并', pinyin='bìng', vietnamese_meaning='cùng lúc'))
            session.add(Grammar(id=grammar_id, name='Concurrent grammar', explanation='Test theory point'))
            await session.flush()
            session.add_all([
                LessonVocabulary(id=word_link, lesson_id=lesson_id, vocabulary_id=word_id, order_index=1),
                LessonGrammar(id=grammar_link, lesson_id=lesson_id, grammar_id=grammar_id, order_index=1),
                LearnerLessonProgress(user_id=user_id, lesson_id=lesson_id),
            ])

        first_checked, release_first, second_started = asyncio.Event(), asyncio.Event(), asyncio.Event()
        second_pid = []

        async def view_word():
            async with SessionFactory.begin() as session:
                await repository.mark_vocabulary_viewed(session, user_id, word_link)
                progress = await repository.mark_theory_complete_if_ready(session, user_id, lesson_id, [word_link], [grammar_link])
                assert progress.theory_completed_at is None
                first_checked.set()
                await release_first.wait()

        async def view_grammar():
            await first_checked.wait()
            async with SessionFactory.begin() as session:
                second_pid.append(await session.scalar(text('SELECT pg_backend_pid()')))
                await repository.mark_grammar_viewed(session, user_id, grammar_link)
                second_started.set()
                progress = await repository.mark_theory_complete_if_ready(session, user_id, lesson_id, [word_link], [grammar_link])
                return progress.theory_completed_at

        tasks = [asyncio.create_task(view_word()), asyncio.create_task(view_grammar())]
        try:
            await asyncio.wait_for(second_started.wait(), 10)
            # Release the first transaction only once the second either finishes
            # its check or waits on a database lock. No fixed timing assumption.
            async with SessionFactory() as monitor:
                async with asyncio.timeout(10):
                    while not tasks[1].done():
                        waiting = await monitor.scalar(text('SELECT EXISTS (SELECT 1 FROM pg_locks WHERE pid = :pid AND NOT granted)'), {'pid': second_pid[0]})
                        if waiting:
                            break
                        await asyncio.sleep(0.01)
            release_first.set()
            _, completed_at = await asyncio.wait_for(asyncio.gather(*tasks), 10)
            assert completed_at is not None
            async with SessionFactory() as session:
                progress = await repository.get_lesson_progress(session, user_id, lesson_id)
                assert progress.theory_completed_at is not None
                assert await repository.viewed_vocabulary_ids(session, user_id, [word_link]) == {word_link}
                assert await repository.viewed_grammar_ids(session, user_id, [grammar_link]) == {grammar_link}
        finally:
            release_first.set()
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            async with SessionFactory.begin() as session:
                for model in (LearnerVocabularyProgress, LearnerGrammarProgress, LearnerLessonProgress):
                    await session.execute(delete(model).where(model.user_id == user_id))
                await session.execute(delete(LessonVocabulary).where(LessonVocabulary.lesson_id == lesson_id))
                await session.execute(delete(LessonGrammar).where(LessonGrammar.lesson_id == lesson_id))
                await session.execute(delete(Vocabulary).where(Vocabulary.id == word_id))
                await session.execute(delete(Grammar).where(Grammar.id == grammar_id))
                await session.execute(delete(Lesson).where(Lesson.id == lesson_id))
                await session.execute(delete(User).where(User.id == user_id))

    asyncio.run(scenario())
