"""Apply a reviewed content revision to drafts, with snapshot and history guards.

Import apply_revision in maintenance tooling; caller owns the single transaction.
Existing reading passages, lesson identities, publication state and learner data
are preserved. A changed snapshot or any attempt/progress aborts before writes.
"""
import json
from uuid import UUID

from sqlalchemy import delete, func, select

from app.admin.schemas import GrammarAttachRequest, QuestionCreateRequest, VocabularyAttachRequest
from app.database.models import (
    Assessment, AssessmentAttempt, Grammar, LearnerGrammarProgress,
    LearnerLessonProgress, LearnerReadingProgress, LearnerVocabularyProgress,
    Lesson, LessonGrammar, LessonReading, LessonVocabulary, Question,
    QuestionOption, Vocabulary,
)
from app.exercise.service import admin_validate_question


def scalar_row(row):
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


def equal_snapshot(actual, expected):
    return json.loads(json.dumps(actual, default=str)) == expected


async def apply_revision(session, definitions, expected):
    targets = []
    for definition in definitions:
        n = definition['lesson']['lesson_number']
        if n not in (2, 3, 4, 5):
            raise ValueError('Revision is restricted to lessons 2–5.')
        snapshot = next(x for x in expected if x['lesson']['lesson_number'] == n)
        lesson = await session.get(Lesson, UUID(snapshot['lesson']['id']), with_for_update=True)
        if not lesson or lesson.status != 'DRAFT' or not equal_snapshot(scalar_row(lesson), snapshot['lesson']):
            raise RuntimeError(f'Lesson {n} changed or is not a draft; export a fresh snapshot.')
        words = (await session.execute(select(LessonVocabulary, Vocabulary).join(Vocabulary, Vocabulary.id == LessonVocabulary.vocabulary_id).where(LessonVocabulary.lesson_id == lesson.id).order_by(LessonVocabulary.order_index))).all()
        grammar = (await session.execute(select(LessonGrammar, Grammar).join(Grammar, Grammar.id == LessonGrammar.grammar_id).where(LessonGrammar.lesson_id == lesson.id).order_by(LessonGrammar.order_index))).all()
        if not equal_snapshot([dict(link=scalar_row(l), word=scalar_row(v)) for l,v in words], snapshot['vocabulary']):
            raise RuntimeError(f'Lesson {n} vocabulary changed since review.')
        if not equal_snapshot([dict(link=scalar_row(l), grammar=scalar_row(g)) for l,g in grammar], snapshot['grammar']):
            raise RuntimeError(f'Lesson {n} grammar changed since review.')
        readings = (await session.scalars(select(LessonReading).where(LessonReading.lesson_id == lesson.id).order_by(LessonReading.order_index))).all()
        if not equal_snapshot([scalar_row(r) for r in readings], snapshot['readings']):
            raise RuntimeError(f'Lesson {n} readings changed since review.')
        for model,condition in (
            (LearnerLessonProgress, LearnerLessonProgress.lesson_id == lesson.id),
            (LearnerVocabularyProgress, LearnerVocabularyProgress.lesson_vocabulary_id.in_([l.id for l,_ in words])),
            (LearnerGrammarProgress, LearnerGrammarProgress.lesson_grammar_id.in_([l.id for l,_ in grammar])),
            (LearnerReadingProgress, LearnerReadingProgress.lesson_reading_id.in_([r.id for r in readings])),
        ):
            if await session.scalar(select(func.count()).select_from(model).where(condition)):
                raise RuntimeError(f'Lesson {n} has learner history; manual versioning required.')
        assessments = (await session.scalars(select(Assessment).where(Assessment.lesson_id == lesson.id).with_for_update())).all()
        if len(assessments) != 1 or assessments[0].status != 'DRAFT':
            raise RuntimeError(f'Lesson {n} requires exactly one draft exercise.')
        assessment = assessments[0]
        old_a = snapshot['assessments'][0]
        if any(str(getattr(assessment,k)) != str(old_a[k]) for k in scalar_row(assessment)):
            raise RuntimeError('Assessment changed since review.')
        if await session.scalar(select(func.count()).select_from(AssessmentAttempt).where(AssessmentAttempt.assessment_id == assessment.id)):
            raise RuntimeError('Cannot replace questions with attempt history.')
        actual_questions=[]
        for q in await session.scalars(select(Question).where(Question.assessment_id == assessment.id).order_by(Question.order_index)):
            qr=scalar_row(q)
            qr['options']=[scalar_row(o) for o in await session.scalars(select(QuestionOption).where(QuestionOption.question_id == q.id).order_by(QuestionOption.order_index))]
            actual_questions.append(qr)
        if not equal_snapshot(actual_questions,old_a['questions']):
            raise RuntimeError('Exercise questions changed since review.')
        for i,w in enumerate(definition['vocabulary'],1):
            VocabularyAttachRequest.model_validate(dict(w,order_index=i))
        for i,g in enumerate(definition['grammar'],1):
            GrammarAttachRequest.model_validate(dict(g,order_index=i))
        if len(definition['questions']) != 30 or definition['assessment']['pass_threshold'] != 80:
            raise ValueError('Expected 30 questions and an 80% threshold.')
        for q in definition['questions']:
            admin_validate_question(QuestionCreateRequest.model_validate(q).model_dump(exclude_unset=True))
        targets.append((definition, lesson, words, grammar, assessment))

    for d,lesson,words,grammar,assessment in targets:
        # Move existing indexes aside before applying the requested ordering.
        for link,_ in words + grammar:
            link.order_index += 10000
        await session.flush()
        by_hanzi = {v.hanzi:(l,v) for l,v in words}
        keep=set()
        for i,w in enumerate(d['vocabulary'],1):
            if w['hanzi'] in by_hanzi:
                link,item=by_hanzi[w['hanzi']]
                # Avoid modifying a canonical record used in another lesson.
                shared=await session.scalar(select(func.count()).select_from(LessonVocabulary).where(LessonVocabulary.vocabulary_id == item.id,LessonVocabulary.lesson_id != lesson.id))
                if shared:
                    item=Vocabulary(**{k:w[k] for k in ('hanzi','pinyin','vietnamese_meaning','part_of_speech')})
                    session.add(item);await session.flush();link.vocabulary_id=item.id
                keep.add(link.id)
            else:
                item=Vocabulary(**{k:w[k] for k in ('hanzi','pinyin','vietnamese_meaning','part_of_speech')})
                session.add(item);await session.flush()
                link=LessonVocabulary(lesson_id=lesson.id,vocabulary_id=item.id)
                session.add(link)
            for k in ('pinyin','vietnamese_meaning','part_of_speech'):
                setattr(item,k,w[k])
            link.order_index=i;link.example=w['example'];link.note=w.get('note')
        for link,_ in words:
            if link.id not in keep:await session.delete(link)
        for i,g in enumerate(d['grammar'],1):
            if i <= len(grammar):
                link,item=grammar[i-1]
                shared=await session.scalar(select(func.count()).select_from(LessonGrammar).where(LessonGrammar.grammar_id == item.id,LessonGrammar.lesson_id != lesson.id))
                if shared:
                    item=Grammar(name=g['name'],explanation=g['explanation']);session.add(item);await session.flush();link.grammar_id=item.id
            else:
                item=Grammar(name=g['name'],explanation=g['explanation']);session.add(item);await session.flush()
                link=LessonGrammar(lesson_id=lesson.id,grammar_id=item.id);session.add(link)
            for k in ('name','structure','explanation','usage'):setattr(item,k,g.get(k))
            link.order_index=i;link.example=g['example'];link.note=g.get('note')
        for link,_ in grammar[len(d['grammar']):]:await session.delete(link)
        qids=select(Question.id).where(Question.assessment_id == assessment.id)
        await session.execute(delete(QuestionOption).where(QuestionOption.question_id.in_(qids)))
        await session.execute(delete(Question).where(Question.assessment_id == assessment.id))
        for q in d['questions']:
            item=Question(assessment_id=assessment.id,**{k:v for k,v in q.items() if k != 'options'})
            session.add(item);await session.flush()
            for i,o in enumerate(q.get('options',[]),1):session.add(QuestionOption(question_id=item.id,order_index=i,**o))
        assessment.description=d['assessment']['description'];assessment.pass_threshold=80
        await session.flush()
    return [{'lesson':d['lesson']['lesson_number'],'vocabulary':len(d['vocabulary']),'grammar':len(d['grammar']),'questions':30,'status':'DRAFT'} for d in definitions]
