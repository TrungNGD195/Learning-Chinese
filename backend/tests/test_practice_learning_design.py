import json
from collections import Counter
from pathlib import Path
from uuid import uuid4
import pytest
from app.admin.schemas import QuestionCreateRequest
from app.exercise.grading import DeterministicGrader
from app.exercise.schemas import AssessmentResponse
from app.exercise.service import admin_validate_question

CONTENT=Path(__file__).resolve().parents[1]/'content/hsk1'


@pytest.mark.parametrize('number',range(1,6))
def test_reviewed_practice_blueprint_has_graded_explanations_and_varied_skills(number):
    pack=json.loads((CONTENT/f'lesson-{number:02}-practice.json').read_text(encoding='utf-8'))
    qs=pack['questions'];assert len(qs)==30
    presentations=[q['config']['presentation'] for q in qs]
    assert Counter(p['difficulty'] for p in presentations)=={'easy':10,'medium':14,'challenge':6}
    assert sum(bool(p.get('audio_text')) for p in presentations)==4
    assert sum(bool(p.get('image_hanzi')) for p in presentations)==4
    assert sum(bool(p.get('reading_text')) for p in presentations)==4
    assert sum(p['review'] for p in presentations)==(0 if number==1 else 6)
    if number>1:assert sum(p['focus']=='grammar' for p in presentations)==15
    for q in qs:
        assert q['rubric'].strip()
        admin_validate_question(QuestionCreateRequest.model_validate(q).model_dump(exclude_unset=True))
        if q['type']=='multiple_choice':
            answer={'option_id':'right'};correct_ids={'right'}
        elif q['type']=='fill_blank':answer={'text':q['reference_answer']};correct_ids=set()
        elif q['type']=='matching':answer={'pairs':q['config']['correct_pairs']};correct_ids=set()
        else:answer={'item_ids':q['config']['correct_order']};correct_ids=set()
        result=DeterministicGrader().grade(dict(q,correct_option_ids=correct_ids),answer)
        assert result.is_correct and result.score==1 and result.feedback==q['rubric']


def test_public_presentation_does_not_accept_answer_keys():
    from app.exercise.schemas import PracticePresentation
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        PracticePresentation(skill='grammar',focus='grammar',difficulty='easy',correct_answer='是')


def test_matching_awards_partial_credit_and_explains_the_missed_pairs():
    q={'type':'matching','points':1,'rubric':'A đi với a; B đi với b; C đi với c.',
       'config':{'left_items':[{'id':x} for x in 'ABC'],'right_items':[{'id':x} for x in 'abc'],
                 'correct_pairs':[{'left_id':x,'right_id':y} for x,y in zip('ABC','abc')]}}
    result=DeterministicGrader().grade(q,{'pairs':[{'left_id':x,'right_id':y} for x,y in zip('ABC','acb')]})
    assert result.score==pytest.approx(1/3,abs=0.0001) and not result.is_correct
    assert '1/3' in result.feedback and q['rubric'] in result.feedback


def test_public_question_metadata_never_leaks_explanations_or_answer_keys(monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from app.exercise import repository,service
    pack=json.loads((CONTENT/'lesson-04-practice.json').read_text(encoding='utf-8'))
    assessment=SimpleNamespace(id=uuid4(),type='LESSON_EXERCISE',title='Test',description=None,pass_threshold=80)
    questions=[SimpleNamespace(**dict(q,id=uuid4(),reference_answer=q.get('reference_answer'))) for q in pack['questions']]
    monkeypatch.setattr(repository,'get_assessment',AsyncMock(return_value=assessment))
    monkeypatch.setattr(service,'_assessment_access',AsyncMock())
    monkeypatch.setattr(repository,'list_questions',AsyncMock(return_value=questions))
    monkeypatch.setattr(repository,'list_question_options',AsyncMock(return_value=[SimpleNamespace(id=uuid4(),option_text='Option',is_correct=True)]))
    data=asyncio.run(service.assessment_payload(None,uuid4(),assessment.id))
    AssessmentResponse.model_validate(data)
    for q in data['questions']:
        assert q['config']['presentation']
        assert not set(q['config']) & {'accepted_answers','correct_pairs','correct_order'}
        assert 'rubric' not in q and 'reference_answer' not in q
        assert all('is_correct' not in option for option in q.get('options',[]))
