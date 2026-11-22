"""One immutable answer per practice question. Never reveal periodic-test keys."""
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.current_user import require_learner
from app.database.models import User
from app.database.session import get_db_session
from app.exercise import repository, service
from app.exercise.grading import DeterministicGrader, GradeResult
from app.exercise.schemas import SubmissionAnswer, AttemptAnswerResult

router = APIRouter()

async def require_practice(session, user_id, attempt_id, *, lock=False):
    attempt = await repository.get_attempt(session, attempt_id, user_id, for_update=lock)
    if attempt is None: raise service._error('NOT_FOUND', 'Attempt not found', 404)
    assessment = await repository.get_assessment(session, attempt.assessment_id)
    if assessment.type != 'LESSON_EXERCISE':
        raise service._error('PRACTICE_FEEDBACK_ONLY', 'Exam answers are revealed only after submission', 403)
    await service._assessment_access(session, user_id, assessment)
    return attempt

async def responses(session, attempt_id):
    return await repository.practice_responses(session,attempt_id)

async def check_answer(session, user_id, attempt_id, payload):
    attempt = await require_practice(session, user_id, attempt_id, lock=True)
    if attempt.status != 'IN_PROGRESS': raise service._error('ATTEMPT_ALREADY_SUBMITTED', 'Attempt already submitted', 409)
    existing = await repository.practice_response(session,attempt_id,payload.question_id)
    if existing:
        # Return the first answer, even if another tab tries to replace it.
        return existing.result
    q = await repository.admin_get_question(session, attempt.assessment_id, payload.question_id)
    if q is None: raise service._error('NOT_FOUND', 'Question not found in this attempt', 404)
    options = await repository.list_question_options(session, q.id)
    question = {'id': q.id, 'type': q.type, 'prompt': q.prompt, 'config': q.config or {},
        'reference_answer': q.reference_answer, 'rubric': q.rubric, 'points': q.points,
        'option_ids': {o.id for o in options}, 'correct_option_ids': {str(o.id) for o in options if o.is_correct}}
    service._validate_stored_question(question)
    answer = service._validate_answer(question, payload.answer.model_dump(mode='json'))
    if 'text' in answer and len(answer['text'])>4000:
        raise service._error('INVALID_ANSWER','Practice answer text is too long',422)
    grade = (DeterministicGrader().grade(question, answer) if q.type in {'multiple_choice','fill_blank','matching','reorder_sentence'}
             else GradeResult('PENDING', None, None, q.rubric))
    result = {'question_id': str(q.id), 'type': q.type, 'prompt': q.prompt, 'answer': answer,
        'grading_status': grade.grading_status, 'score': grade.score, 'is_correct': grade.is_correct,
        'feedback': grade.feedback, 'reference_answer': q.reference_answer, 'rubric': q.rubric, 'config': q.config or {}}
    if q.type == 'multiple_choice':
        result['reference_answer'] = next((o.option_text for o in options if o.is_correct), None)
        result['selected_option_text'] = next((o.option_text for o in options if str(o.id) == answer['option_id']), None)
        result['config'] = {'presentation': q.config['presentation']} if (q.config or {}).get('presentation') else {}
    await repository.add_practice_response(session,attempt_id,q.id,answer,result)
    await session.commit()
    return result

@router.get('/assessment-attempts/{attempt_id}/practice-feedback', response_model=list[AttemptAnswerResult])
async def saved_feedback(attempt_id: UUID, user: User = Depends(require_learner), session: AsyncSession = Depends(get_db_session)):
    await require_practice(session, user.id, attempt_id)
    return [row.result for row in await responses(session, attempt_id)]

@router.post('/assessment-attempts/{attempt_id}/practice-feedback', response_model=AttemptAnswerResult)
async def answer_feedback(attempt_id: UUID, payload: SubmissionAnswer, user: User = Depends(require_learner), session: AsyncSession = Depends(get_db_session)):
    return await check_answer(session, user.id, attempt_id, payload)
