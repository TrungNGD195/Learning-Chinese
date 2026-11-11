import asyncio
from uuid import uuid4

from app.ai.generation.prompt import build_generation_prompt
from app.ai.generation.schemas import LessonExerciseGenerationRequest, MaterializedGenerationScope
from app.curriculum.service import materialize_generation_scope
from app.database.models import HSKLevel, Lesson, LessonVocabulary, Vocabulary
from app.database.session import SessionFactory
from scripts.create_hsk1_lessons_02_05_drafts import load_definitions


def test_updated_vocabulary_and_review_questions_match_requested_curriculum():
    definitions = load_definitions()
    expected = {
        2: '大家 您 们 名字 叫 同学 谢谢 不客气 对不起 没关系 没事 很 高兴 认识 也',
        3: '请问 什么 是 越南 中国 中文 汉语 人 老师 的 这 那 哪 谁 朋友 男 他 她 它 法国 泰国 喂 工作 忙 还 吗 对 太 想 再见',
        4: '有 没有 多 少 多少 学生 二 三 四 六 七 九 十 两 班 爸爸 妈妈 父母 哥哥 姐姐 弟弟 妹妹 家 几 呢 和 老公 丈夫 老婆 妻子 孩子 儿子 女儿 奶奶 爷爷 外公 外婆 结婚 单身 对象 包括 岁',
        5: '天 昨天 年 去年 今年 明年 会 喜欢 做 星期 周末 休息 日 号 月 吃 菜 饭 米饭 饺子 馒头 包子 鸡蛋 面条 酒 啤酒 喝 茶 咖啡 可乐 水',
    }
    for d in definitions:
        n=d['lesson']['lesson_number']
        assert [w['hanzi'] for w in d['vocabulary']] == expected[n].split()
        assert sum('Ôn bài' in q['prompt'] for q in d['questions']) == 6
        assert d['practice_scope']['lesson_numbers'] == list(range(1,n+1))


def test_generation_includes_earlier_material_but_excludes_later_archived_and_other_levels():
    async def run():
        async with SessionFactory() as session:
            try:
                num=30_000_000+uuid4().int%1_000_000
                levels=[HSKLevel(level_number=num+i,order_index=num+i) for i in range(2)]
                session.add_all(levels);await session.flush()
                lessons=[]
                for number,status,level in [(1,'PUBLISHED',0),(2,'DRAFT',0),(3,'DRAFT',0),(4,'ARCHIVED',0),(5,'DRAFT',0),(1,'PUBLISHED',1)]:
                    lesson=Lesson(hsk_level_id=levels[level].id,lesson_number=number,title=f'L{number}',status=status)
                    session.add(lesson);await session.flush()
                    vocab=Vocabulary(hanzi=f'word-{level}-{number}',pinyin='test',vietnamese_meaning='test')
                    session.add(vocab);await session.flush()
                    session.add(LessonVocabulary(lesson_id=lesson.id,vocabulary_id=vocab.id,order_index=1))
                    lessons.append(lesson)
                # Target 5 includes 1–3, excluding archived 4 and the other level.
                await session.flush()
                request=LessonExerciseGenerationRequest(type='LESSON_EXERCISE',lesson_id=lessons[4].id,question_count=30,allowed_types=['multiple_choice','fill_blank','matching'],difficulty='EASY')
                scope=await materialize_generation_scope(session,request)
                assert set(scope['lesson_ids']) == {lessons[i].id for i in (0,1,2,4)}
                assert [v['lesson']['lesson_number'] for v in scope['payload']['vocabulary']] == [5,1,2,3]
                # Target 2 cannot use later lesson 3 or 5.
                request.lesson_id=lessons[1].id
                scope=await materialize_generation_scope(session,request)
                assert scope['lesson_ids'] == (lessons[1].id,lessons[0].id)
                assert len(scope['allowed_source_refs']) == 2
                system,user=build_generation_prompt(MaterializedGenerationScope(**scope),request)
                assert '20%' in system and 'Never draw on later lessons' in system
                assert 'review_lessons' in user
            finally:
                await session.rollback()
    asyncio.run(run())
