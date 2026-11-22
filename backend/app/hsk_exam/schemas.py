from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class Input(BaseModel):
    model_config=ConfigDict(extra='forbid')

class ExamSection(BaseModel):
    id:str
    label:str
    duration_seconds:int
    question_count:int

IllustrationTopic=Literal['moving-home','tennis','reading-library','spring-festival','restaurant-menu',
    'office-documents','high-speed-train','photography','wedding-clothes','recovery','panda-zoo']

class ExamOption(BaseModel):
    id:str
    text:str
    image_hanzi:str|None=None
    pinyin:str|None=None
    illustration_topic:IllustrationTopic|None=None

class ExamQuestion(BaseModel):
    id:str
    part:int
    type:Literal['choice','fill','sentence']
    prompt:str
    prompt_pinyin:str|None=None
    reading_text:str|None=None
    reading_text_pinyin:str|None=None
    audio_text:str|None=None
    image_hanzi:str|None=None
    illustration_topic:IllustrationTopic|None=None
    phonetic_hint:str|None=None
    options:list[ExamOption]

class ExamAccess(BaseModel):
    unlocked:bool
    completed_lessons:int
    total_lessons:int

class ExamInfo(BaseModel):
    level:int
    standard:str
    version:str
    title:str
    pinyin_support:bool
    total_questions:int
    max_score:int
    pass_score:float
    sections:list[ExamSection]
    access:ExamAccess|None=None

class ExamReview(ExamQuestion):
    section_id:str
    section_label:str
    answer:str|None
    answer_text:str|None
    reference_answer:str
    explanation:str
    is_correct:bool|None
    earned_fraction:float|None
    self_rating:float|None=None

class SectionResult(BaseModel):
    id:str
    label:str
    score:float|None
    score_min:float
    score_max:float
    correct:int
    total:int

class ExamResult(BaseModel):
    score:float|None
    score_min:float
    score_max:float
    max_score:int
    pass_score:float
    passed:bool|None
    pending_self_reviews:int
    includes_self_assessment:bool
    sections:list[SectionResult]
    questions:list[ExamReview]

class ExamSession(BaseModel):
    id:UUID
    level:int
    attempt_number:int
    status:Literal['IN_PROGRESS','GRADED']
    info:ExamInfo
    started_at:datetime
    submitted_at:datetime|None
    server_time:datetime
    section_index:int
    section_deadline:datetime|None
    questions:list[ExamQuestion]
    answers:dict[str,str]
    result:ExamResult|None

class SaveAnswer(Input):
    section_index:int=Field(ge=0,le=2)
    question_id:str=Field(max_length=80)
    answer:str=Field(max_length=1000)

class FinishSection(Input):
    section_index:int=Field(ge=0,le=2)

class SelfReview(Input):
    question_id:str=Field(max_length=80)
    rating:Literal[0,0.5,1]

class ExamHistoryItem(BaseModel):
    id:UUID
    attempt_number:int
    status:str
    started_at:datetime
    submitted_at:datetime|None
    score:float|None
    max_score:int
    pending_self_reviews:int
    includes_self_assessment:bool
