"""Persistence queries for curriculum structure and learning content."""
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (Assessment, CurriculumUnit, Grammar, HSKLevel, Lesson,
    LearnerGrammarProgress, LearnerVocabularyProgress, LessonGrammar, LessonVocabulary,
    PronunciationProgress, PronunciationSection, Vocabulary)


async def catalog_snapshot(session: AsyncSession):
    levels=(await session.execute(select(HSKLevel).order_by(HSKLevel.level_number))).scalars().all()
    units=(await session.execute(select(CurriculumUnit,Lesson,Assessment)
        .outerjoin(Lesson, CurriculumUnit.lesson_id==Lesson.id)
        .outerjoin(Assessment, CurriculumUnit.assessment_id==Assessment.id)
        .order_by(CurriculumUnit.hsk_level_id,CurriculumUnit.order_index))).all()
    return levels,units


async def get_lesson(session: AsyncSession, lesson_id: UUID):
    return (await session.execute(select(Lesson).where(Lesson.id==lesson_id))).scalar_one_or_none()


async def get_pronunciation_section(session: AsyncSession, section_id: UUID):
    return (await session.execute(select(PronunciationSection).where(PronunciationSection.id==section_id))).scalar_one_or_none()


async def pronunciation_rows(session: AsyncSession, user_id: UUID):
    return (await session.execute(select(PronunciationSection,PronunciationProgress)
        .outerjoin(PronunciationProgress,(PronunciationProgress.pronunciation_section_id==PronunciationSection.id)
            &(PronunciationProgress.user_id==user_id))
        .order_by(PronunciationSection.order_index))).all()


async def lesson_vocabulary(session: AsyncSession, lesson_id: UUID):
    return (await session.execute(select(LessonVocabulary,Vocabulary)
        .join(Vocabulary,Vocabulary.id==LessonVocabulary.vocabulary_id)
        .where(LessonVocabulary.lesson_id==lesson_id).order_by(LessonVocabulary.order_index))).all()


async def lesson_grammar(session: AsyncSession, lesson_id: UUID):
    return (await session.execute(select(LessonGrammar,Grammar)
        .join(Grammar,Grammar.id==LessonGrammar.grammar_id)
        .where(LessonGrammar.lesson_id==lesson_id).order_by(LessonGrammar.order_index))).all()


async def lesson_assessments(session: AsyncSession, lesson_id: UUID):
    return (await session.execute(select(Assessment.id).where(Assessment.lesson_id==lesson_id,
        Assessment.type=="LESSON_EXERCISE",Assessment.status=="PUBLISHED").order_by(Assessment.created_at))).scalars().all()


async def lesson_theory_ids(session: AsyncSession, lesson_id: UUID):
    vocabulary=(await session.execute(select(LessonVocabulary.id).where(LessonVocabulary.lesson_id==lesson_id))).scalars().all()
    grammar=(await session.execute(select(LessonGrammar.id).where(LessonGrammar.lesson_id==lesson_id))).scalars().all()
    return vocabulary,grammar


async def get_owned_theory_link(session: AsyncSession, lesson_id: UUID, junction_id: UUID, kind: str):
    model=LessonVocabulary if kind=="vocabulary" else LessonGrammar
    return (await session.execute(select(model).where(model.id==junction_id,model.lesson_id==lesson_id))).scalar_one_or_none()


# Admin curriculum/content persistence operations. These functions never commit.
async def admin_hsk_levels(session:AsyncSession):
    return (await session.execute(select(HSKLevel).order_by(HSKLevel.level_number))).scalars().all()


async def admin_get_hsk(session:AsyncSession,hsk_id:UUID,*,for_update:bool=False):
    statement=select(HSKLevel).where(HSKLevel.id==hsk_id)
    if for_update:statement=statement.with_for_update()
    return (await session.execute(statement)).scalar_one_or_none()


async def admin_update_hsk(session:AsyncSession,hsk_id:UUID,fields:dict):
    row=await admin_get_hsk(session,hsk_id,for_update=True)
    if row:
        for key,value in fields.items():setattr(row,key,value)
    return row


async def admin_curriculum(session:AsyncSession,hsk_id:UUID):
    return (await session.execute(select(CurriculumUnit,Lesson,Assessment)
        .outerjoin(Lesson,Lesson.id==CurriculumUnit.lesson_id)
        .outerjoin(Assessment,Assessment.id==CurriculumUnit.assessment_id)
        .where(CurriculumUnit.hsk_level_id==hsk_id).order_by(CurriculumUnit.order_index))).all()


async def admin_replace_curriculum(session:AsyncSession,hsk_id:UUID,units:list[dict]):
    await session.execute(delete(CurriculumUnit).where(CurriculumUnit.hsk_level_id==hsk_id))
    for item in units:
        target=item["target_id"]
        session.add(CurriculumUnit(hsk_level_id=hsk_id,unit_type=item["unit_type"],order_index=item["order_index"],
            lesson_id=target if item["unit_type"]=="LESSON" else None,
            assessment_id=target if item["unit_type"]=="PERIODIC_TEST" else None))
    await session.flush()


async def admin_lessons(session:AsyncSession,status=None,hsk_level_id=None):
    statement=select(Lesson).order_by(Lesson.hsk_level_id,Lesson.lesson_number)
    if status:statement=statement.where(Lesson.status==status)
    if hsk_level_id:statement=statement.where(Lesson.hsk_level_id==hsk_level_id)
    return (await session.execute(statement)).scalars().all()


async def admin_lessons_page(session:AsyncSession,page:int,page_size:int,status=None,hsk_level_id=None):
    filters=[]
    if status:filters.append(Lesson.status==status)
    if hsk_level_id:filters.append(Lesson.hsk_level_id==hsk_level_id)
    total=(await session.execute(select(func.count()).select_from(Lesson).where(*filters))).scalar_one()
    rows=(await session.execute(select(Lesson).where(*filters).order_by(Lesson.hsk_level_id,Lesson.lesson_number,Lesson.id)
        .offset((page-1)*page_size).limit(page_size))).scalars().all()
    return total,rows


async def admin_create_lesson(session:AsyncSession,fields:dict):
    lesson=Lesson(**fields,status="DRAFT");session.add(lesson);await session.flush();return lesson


async def admin_get_lesson(session:AsyncSession,lesson_id:UUID,*,for_update:bool=False):
    statement=select(Lesson).where(Lesson.id==lesson_id)
    if for_update:statement=statement.with_for_update()
    return (await session.execute(statement)).scalar_one_or_none()


async def admin_generation_lesson(session:AsyncSession, lesson_id:UUID):
    lesson = await admin_get_lesson(session, lesson_id)
    if lesson is None:
        return None, [], []
    return lesson, await lesson_vocabulary(session, lesson_id), await lesson_grammar(session, lesson_id)


async def admin_generation_periodic_scope(session:AsyncSession, lesson_ids:list[UUID], vocabulary_ids:list[UUID], grammar_ids:list[UUID]):
    lessons = (await session.execute(
        select(Lesson).where(Lesson.id.in_(lesson_ids)).order_by(Lesson.lesson_number, Lesson.id)
    )).scalars().all()
    vocabulary = []
    if vocabulary_ids:
        vocabulary = (await session.execute(
            select(LessonVocabulary, Vocabulary, Lesson)
            .join(Vocabulary, Vocabulary.id == LessonVocabulary.vocabulary_id)
            .join(Lesson, Lesson.id == LessonVocabulary.lesson_id)
            .where(Lesson.id.in_(lesson_ids), Vocabulary.id.in_(vocabulary_ids))
            .order_by(Lesson.lesson_number, Lesson.id, LessonVocabulary.order_index, Vocabulary.id)
        )).all()
    grammar = []
    if grammar_ids:
        grammar = (await session.execute(
            select(LessonGrammar, Grammar, Lesson)
            .join(Grammar, Grammar.id == LessonGrammar.grammar_id)
            .join(Lesson, Lesson.id == LessonGrammar.lesson_id)
            .where(Lesson.id.in_(lesson_ids), Grammar.id.in_(grammar_ids))
            .order_by(Lesson.lesson_number, Lesson.id, LessonGrammar.order_index, Grammar.id)
        )).all()
    return lessons, vocabulary, grammar


async def admin_update_lesson(session:AsyncSession,lesson:Lesson,fields:dict):
    for key,value in fields.items():setattr(lesson,key,value)
    await session.flush();return lesson


async def admin_transition_lesson(session:AsyncSession,lesson:Lesson,status:str,published_at=None):
    lesson.status=status
    if published_at is not None:lesson.published_at=published_at
    await session.flush();return lesson


async def admin_list_lesson_content(session:AsyncSession,lesson_id:UUID,kind:str):
    if kind=="vocabulary":
        return (await session.execute(select(LessonVocabulary,Vocabulary).join(Vocabulary,Vocabulary.id==LessonVocabulary.vocabulary_id)
            .where(LessonVocabulary.lesson_id==lesson_id).order_by(LessonVocabulary.order_index))).all()
    return (await session.execute(select(LessonGrammar,Grammar).join(Grammar,Grammar.id==LessonGrammar.grammar_id)
        .where(LessonGrammar.lesson_id==lesson_id).order_by(LessonGrammar.order_index))).all()


async def admin_attach_lesson_content(session:AsyncSession,lesson_id:UUID,kind:str,shared_id:UUID|None,shared_fields:dict,association_fields:dict):
    if kind=="vocabulary":model,link_model,key=Vocabulary,LessonVocabulary,"vocabulary_id"
    else:model,link_model,key=Grammar,LessonGrammar,"grammar_id"
    shared=(await session.execute(select(model).where(model.id==shared_id))).scalar_one_or_none() if shared_id else None
    if shared_id and shared is None:return None,None
    if shared is None:shared=model(**shared_fields);session.add(shared);await session.flush()
    link=link_model(lesson_id=lesson_id,**{key:shared.id},**association_fields);session.add(link);await session.flush()
    return link,shared


async def admin_get_lesson_content_link(session:AsyncSession,lesson_id:UUID,link_id:UUID,kind:str,*,for_update:bool=False):
    model=LessonVocabulary if kind=="vocabulary" else LessonGrammar
    statement=select(model).where(model.id==link_id,model.lesson_id==lesson_id)
    if for_update:statement=statement.with_for_update()
    return (await session.execute(statement)).scalar_one_or_none()


async def admin_get_shared_content(session:AsyncSession,shared_id:UUID,kind:str):
    model=Vocabulary if kind=="vocabulary" else Grammar
    return (await session.execute(select(model).where(model.id==shared_id))).scalar_one_or_none()


async def admin_update_lesson_content(session:AsyncSession,link,shared,kind:str,association_fields:dict,shared_fields:dict):
    for key,value in association_fields.items():setattr(link,key,value)
    for key,value in shared_fields.items():setattr(shared,key,value)
    await session.flush()


async def admin_content_has_history(session:AsyncSession,link_id:UUID,kind:str):
    progress_model= LearnerVocabularyProgress if kind=="vocabulary" else LearnerGrammarProgress
    fk="lesson_vocabulary_id" if kind=="vocabulary" else "lesson_grammar_id"
    return (await session.execute(select(progress_model.id).where(getattr(progress_model,fk)==link_id).limit(1))).scalar_one_or_none() is not None


async def admin_delete_lesson_content(session:AsyncSession,link):
    await session.delete(link);await session.flush()
