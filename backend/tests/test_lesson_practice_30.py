import asyncio
import json
from collections import Counter
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.ai.generation.errors import AssessmentGenerationInvalidOutput
from app.ai.generation.schemas import (
    GeneratedFillBlankQuestion, GeneratedMatchingQuestion, GeneratedMultipleChoiceQuestion,
    GeneratedReorderSentenceQuestion, LessonExerciseGenerationRequest, MaterializedGenerationScope,
    StructuredAssessmentGenerationOutput, StructuredAssessmentGenerationProviderResult,
)
from app.ai.generation.service import AssessmentGenerationService, validate_and_map_output
from app.core.config import Settings
from app.exercise.service import admin_validate_generated_question


class FakeProvider:
    def __init__(self, *, duplicate=False, fail_at=None):
        self.calls=[]
        self.duplicate=duplicate
        self.fail_at=fail_at

    async def generate(self, request):
        self.calls.append(request)
        if len(self.calls)==self.fail_at:
            raise RuntimeError('provider unavailable')
        kind=request.allowed_types[0]
        questions=[]
        for index in range(request.requested_question_count):
            common=dict(type=kind, prompt='Repeat' if self.duplicate else f'{kind} batch {len(self.calls)} item {index}', source_refs=['vocab:word'])
            if kind=='multiple_choice':
                item=GeneratedMultipleChoiceQuestion(**common, options=[dict(option_text='好', is_correct=True),dict(option_text='不', is_correct=False)])
            elif kind=='fill_blank':
                item=GeneratedFillBlankQuestion(**common, reference_answer='好', accepted_answers=['好'])
            elif kind=='matching':
                item=GeneratedMatchingQuestion(**common,left_items=[dict(id='a',text='好')],right_items=[dict(id='b',text='tốt')],correct_pairs=[dict(left_id='a',right_id='b')])
            else:
                item=GeneratedReorderSentenceQuestion(**common,items=[dict(id='a',text='你'),dict(id='b',text='好')],correct_order=['a','b'])
            questions.append(item)
        return StructuredAssessmentGenerationProviderResult(StructuredAssessmentGenerationOutput(questions=questions),'fake','fake-model',10,20,30,9,100,1,None)


def request_and_scope():
    request=LessonExerciseGenerationRequest(type='LESSON_EXERCISE', lesson_id=uuid4(), allowed_types=['multiple_choice','fill_blank','matching','reorder_sentence'], difficulty='EASY')
    scope=MaterializedGenerationScope(request.type,request.lesson_id,(request.lesson_id,),(),(),'Practice',None,80,{'vocabulary':[],'grammar':[]},frozenset({'vocab:word'}))
    return request, scope


def test_full_lesson_default_is_30_with_varied_bounded_batches_and_valid_answer_keys():
    request,scope=request_and_scope()
    assert request.question_count==30 and request.pass_threshold==80
    provider=FakeProvider()
    settings=Settings(_env_file=None, app_env='test', debug=False, test_database_url='postgresql+psycopg://u:p@localhost/chinese_learning_test')
    result=asyncio.run(AssessmentGenerationService(provider,settings).generate(request,scope))
    assert len(result.output.questions)==30
    assert Counter(item.type for item in result.output.questions)==dict(multiple_choice=8,fill_blank=8,matching=7,reorder_sentence=7)
    assert all(call.requested_question_count<=10 for call in provider.calls)
    assert len(json.loads(provider.calls[-1].user_content)['previous_question_prompts_to_avoid'])==23
    assert result.total_tokens==120 and result.attempt_count==4
    mapped=validate_and_map_output(result,request=request,scope=scope,domain_validator=admin_validate_generated_question)
    assert [item['order_index'] for item in mapped]==list(range(1,31))
    assert sum(item['points'] for item in mapped)==30


def test_full_lesson_rejects_single_format_and_out_of_range_count():
    request,_=request_and_scope()
    for changes in ({'allowed_types':['multiple_choice']},{'question_count':31}):
        with pytest.raises(ValidationError):
            LessonExerciseGenerationRequest.model_validate({**request.model_dump(),**changes})


def test_batch_duplicate_or_provider_failure_does_not_return_a_partial_exercise():
    request,scope=request_and_scope()
    settings=Settings(_env_file=None, app_env='test',debug=False,test_database_url='postgresql+psycopg://u:p@localhost/chinese_learning_test')
    with pytest.raises(AssessmentGenerationInvalidOutput):
        asyncio.run(AssessmentGenerationService(FakeProvider(duplicate=True),settings).generate(request,scope))
    provider=FakeProvider(fail_at=2)
    with pytest.raises(RuntimeError,match='provider unavailable'):
        asyncio.run(AssessmentGenerationService(provider,settings).generate(request,scope))
    assert len(provider.calls)==2
