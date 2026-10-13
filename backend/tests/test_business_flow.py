import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app.auth.current_user import get_current_user
from app.database.models import (Assessment, AssessmentAttempt, AttemptAnswer, CurriculumUnit, HSKLevel,
    Chunk, Grammar, KnowledgeSource, KnowledgeVersion, LearnerGrammarProgress, LearnerHSKProgress, LearnerLessonProgress, LearnerVocabularyProgress,
    Lesson, LessonGrammar, LessonVocabulary, PronunciationProgress, PronunciationSection, Question,
    QuestionOption, User, Vocabulary)
from app.database.session import SessionFactory
from app.exercise.grading import GradeResult, get_ai_grader
from app.exercise import service as exercise_service
from app.main import app


def test_postgres_learner_lesson_and_attempt_flow(monkeypatch):
    user_id, outsider_id, lesson_id, next_lesson_id, archived_lesson_id, curriculum_candidate_id, assessment_id, unavailable_assessment_id, uncertain_assessment_id = uuid4(), uuid4(), uuid4(), uuid4(), uuid4(), uuid4(), uuid4(), uuid4(), uuid4()
    vocab_link_id, grammar_link_id = uuid4(), uuid4()
    async def seed():
        async with SessionFactory.begin() as session:
            hsk = (await session.execute(select(HSKLevel).where(HSKLevel.level_number == 1))).scalar_one()
            index = (await session.execute(select(func.max(CurriculumUnit.order_index)).where(CurriculumUnit.hsk_level_id == hsk.id))).scalar_one() or 0
            user = User(id=user_id, email=f"step34-{user_id}@example.invalid", password_hash="test-only", full_name="Step 3.4 Test", role="ADMIN")
            outsider = User(id=outsider_id,email=f"step34-outsider-{outsider_id}@example.invalid",password_hash="test-only",full_name="Other Test",role="LEARNER")
            lesson = Lesson(id=lesson_id, hsk_level_id=hsk.id, lesson_number=900000 + user_id.int % 100000,
                            title="Integration lesson", description="Test", status="PUBLISHED")
            next_lesson = Lesson(id=next_lesson_id,hsk_level_id=hsk.id,lesson_number=800000 + user_id.int % 100000,
                                 title="Locked lesson",description="Test",status="PUBLISHED")
            session.add_all([user, outsider, lesson, next_lesson]); await session.flush()
            session.add_all([CurriculumUnit(hsk_level_id=hsk.id, unit_type="LESSON", lesson_id=lesson.id, order_index=index + 1),
                             CurriculumUnit(hsk_level_id=hsk.id, unit_type="LESSON", lesson_id=next_lesson.id, order_index=index + 2)])
            vocab=Vocabulary(hanzi="你",pinyin="nǐ",vietnamese_meaning="bạn",part_of_speech="pronoun")
            grammar=Grammar(name="Test grammar",structure="A",explanation="Test",usage="Test")
            session.add_all([vocab,grammar]); await session.flush()
            session.add_all([LessonVocabulary(id=vocab_link_id,lesson_id=lesson.id,vocabulary_id=vocab.id,order_index=1),
                             LessonGrammar(id=grammar_link_id,lesson_id=lesson.id,grammar_id=grammar.id,order_index=1)])
            session.add(Assessment(id=assessment_id, type="LESSON_EXERCISE", lesson_id=lesson.id, title="Exercise", status="DRAFT", pass_threshold=90))
            session.add(Assessment(id=unavailable_assessment_id, type="LESSON_EXERCISE", lesson_id=lesson.id, title="Writing", status="DRAFT", pass_threshold=90))
            session.add(Assessment(id=uncertain_assessment_id,type="LESSON_EXERCISE",lesson_id=lesson.id,title="Uncertain",status="DRAFT",pass_threshold=90))
            await session.flush()
            q=Question(assessment_id=assessment_id,type="multiple_choice",prompt="Pick",order_index=1,points=1)
            session.add(q); await session.flush()
            correct=QuestionOption(question_id=q.id,option_text="correct",order_index=1,is_correct=True)
            wrong=QuestionOption(question_id=q.id,option_text="wrong",order_index=2,is_correct=False)
            session.add_all([correct,wrong]); await session.flush()
            free=Question(assessment_id=unavailable_assessment_id,type="sentence_writing",prompt="Write",order_index=1,points=1,reference_answer="你好",rubric="Meaning")
            session.add(free); await session.flush()
            deterministic=Question(assessment_id=unavailable_assessment_id,type="multiple_choice",prompt="Pick",order_index=2,points=1)
            session.add(deterministic); await session.flush()
            deterministic_option=QuestionOption(question_id=deterministic.id,option_text="correct",order_index=1,is_correct=True)
            session.add(deterministic_option); await session.flush()
            uncertain_free=Question(assessment_id=uncertain_assessment_id,type="sentence_writing",prompt="Write",order_index=1,points=1)
            uncertain_mcq=Question(assessment_id=uncertain_assessment_id,type="multiple_choice",prompt="Pick",order_index=2,points=1)
            session.add_all([uncertain_free,uncertain_mcq]); await session.flush()
            uncertain_option=QuestionOption(question_id=uncertain_mcq.id,option_text="correct",order_index=1,is_correct=True)
            session.add(uncertain_option); await session.flush()
            return hsk.id, q.id, correct.id, free.id, deterministic.id, deterministic_option.id, uncertain_free.id, uncertain_mcq.id, uncertain_option.id
    hsk_id, question_id, correct_option_id, free_question_id, deterministic_question_id, deterministic_option_id, uncertain_free_id, uncertain_mcq_id, uncertain_option_id = asyncio.run(seed())
    active_user={"id":user_id}
    async def current_user():
        async with SessionFactory() as session:
            return await session.get(User, active_user["id"])
    app.dependency_overrides[get_current_user] = current_user
    try:
        with TestClient(app,raise_server_exceptions=False) as client:
            empty_stats=client.get("/api/v1/admin/stats")
            assert empty_stats.status_code==200 and empty_stats.json()["average_exercise_score"] is None
            assert client.get(f"/api/v1/hsk-levels/{hsk_id}/curriculum").json()["units"][0]["state"] == "LOCKED"
            dashboard_before=client.get("/api/v1/me/dashboard")
            assert dashboard_before.status_code==200
            before_data=dashboard_before.json()
            assert before_data["current_hsk"]["id"]==str(hsk_id)
            assert before_data["current_unit"]["state"]=="LOCKED" and before_data["current_lesson"] is None
            assert before_data["progress_percentage"]==0 and before_data["continue_learning"]["type"]=="PRONUNCIATION"
            assert before_data["continue_learning"]["section_id"]
            overview_before=client.get("/api/v1/me/progress")
            assert overview_before.status_code==200 and overview_before.json()["current_hsk"]==1
            hsk_progress_before=client.get(f"/api/v1/me/progress/hsk/{hsk_id}")
            assert hsk_progress_before.status_code==200 and hsk_progress_before.json()["progress_percentage"]==0
            sections = client.get("/api/v1/pronunciation").json()
            for section in sections:
                assert client.post(f"/api/v1/pronunciation/{section['id']}/complete").status_code == 200
                assert client.post(f"/api/v1/pronunciation/{section['id']}/complete").status_code == 200
            persisted_sections = client.get("/api/v1/pronunciation")
            assert persisted_sections.status_code == 200
            assert {row["id"] for row in persisted_sections.json()} == {row["id"] for row in sections}
            assert all(row["completed_at"] is not None for row in persisted_sections.json())
            unit = client.get(f"/api/v1/hsk-levels/{hsk_id}/curriculum").json()["units"][0]
            assert unit["state"] == "AVAILABLE"
            dashboard_after=client.get("/api/v1/me/dashboard").json()
            assert dashboard_after["current_hsk"]["id"]==str(hsk_id)
            assert dashboard_after["current_unit"]["state"]=="AVAILABLE"
            assert dashboard_after["current_lesson"]["id"]==str(lesson_id)
            assert dashboard_after["continue_learning"]["type"]=="LESSON"
            overview_after=client.get("/api/v1/me/progress")
            assert overview_after.status_code==200 and overview_after.json()["hsk_levels"][0]["state"]=="AVAILABLE"
            assert client.get(f"/api/v1/me/progress/hsk/{hsk_id}").status_code==200
            lesson = client.get(f"/api/v1/lessons/{lesson_id}")
            assert lesson.status_code == 200 and lesson.json()["id"] == str(lesson_id)
            assert client.get(f"/api/v1/lessons/{next_lesson_id}").status_code == 403
            vocab_first=client.post(f"/api/v1/lessons/{lesson_id}/theory/vocabulary/{vocab_link_id}/view").json()
            vocab_repeat=client.post(f"/api/v1/lessons/{lesson_id}/theory/vocabulary/{vocab_link_id}/view").json()
            assert vocab_first["viewed_at"]==vocab_repeat["viewed_at"]
            assert client.delete(f"/api/v1/admin/lessons/{lesson_id}/vocabulary/{vocab_link_id}").status_code==409
            assert client.get(f"/api/v1/me/progress/lessons/{lesson_id}").json()["theory_completed_at"] is None

            assert client.post(f"/api/v1/admin/assessments/{assessment_id}/submit-review").status_code == 200
            assert client.post(f"/api/v1/admin/assessments/{assessment_id}/publish").status_code == 200
            assert client.post(f"/api/v1/admin/assessments/{assessment_id}/publish").status_code == 409
            assert client.patch(f"/api/v1/admin/assessments/{assessment_id}",json={"status":"ARCHIVED"}).status_code == 422
            assert client.patch(f"/api/v1/admin/assessments/{assessment_id}/questions/{question_id}",json={"prompt":"Changed"}).status_code == 409

            public = client.get(f"/api/v1/assessments/{assessment_id}")
            assert public.status_code == 200
            assert "is_correct" not in public.json()["questions"][0]["options"][0]
            started = client.post(f"/api/v1/assessments/{assessment_id}/attempts")
            assert started.status_code == 201
            attempt_id = started.json()["id"]
            active_user["id"]=outsider_id
            assert client.get(f"/api/v1/me/assessment-attempts/{attempt_id}").status_code==404
            assert client.get("/api/v1/me/assessment-attempts").json()["total"]==0
            active_user["id"]=user_id
            resumed = client.post(f"/api/v1/assessments/{assessment_id}/attempts")
            assert resumed.status_code == 200 and resumed.json()["id"] == attempt_id
            original_after_attempt=exercise_service.progress.after_attempt
            async def fail_progress(*args,**kwargs):raise RuntimeError("injected progress write failure")
            monkeypatch.setattr(exercise_service.progress,"after_attempt",fail_progress)
            rollback=client.post(f"/api/v1/assessment-attempts/{attempt_id}/submit",json={"answers":[{"question_id":str(question_id),"answer":{"option_id":str(correct_option_id)}}]})
            assert rollback.status_code==500
            monkeypatch.setattr(exercise_service.progress,"after_attempt",original_after_attempt)
            submitted = client.post(f"/api/v1/assessment-attempts/{attempt_id}/submit", json={"answers":[{"question_id":str(question_id),"answer":{"option_id":str(correct_option_id)}}]})
            assert submitted.status_code == 200 and submitted.json()["passed"] is True
            unfinished=client.get(f"/api/v1/me/progress/lessons/{lesson_id}").json()
            assert unfinished["theory_completed_at"] is None and unfinished["completed_at"] is None
            assert client.get(f"/api/v1/lessons/{next_lesson_id}").status_code == 403
            grammar_seen=client.post(f"/api/v1/lessons/{lesson_id}/theory/grammar/{grammar_link_id}/view").json()
            assert grammar_seen["theory_completed_at"] is not None
            assert client.get(f"/api/v1/me/progress/lessons/{lesson_id}").json()["completed_at"] is not None
            assert client.get(f"/api/v1/lessons/{next_lesson_id}").status_code == 200
            assert client.patch(f"/api/v1/admin/lessons/{lesson_id}",json={"title":"Edited after completion"}).status_code==200
            assert client.get(f"/api/v1/me/progress/lessons/{lesson_id}").json()["completed_at"] is not None
            admin_units=client.get(f"/api/v1/admin/hsk-levels/{hsk_id}/curriculum").json()
            reordered=list(reversed(admin_units))
            changed=client.put(f"/api/v1/admin/hsk-levels/{hsk_id}/curriculum",json={"units":[
                {"unit_type":"LESSON","target_id":str(item["lesson_id"]),"order_index":index}
                for index,item in enumerate(reordered,start=1)]})
            assert changed.status_code==200 and changed.json()[0]["lesson_id"]==str(next_lesson_id)
            invalid=client.put(f"/api/v1/admin/hsk-levels/{hsk_id}/curriculum",json={"units":[
                {"unit_type":"LESSON","target_id":str(lesson_id),"order_index":1},
                {"unit_type":"LESSON","target_id":str(lesson_id),"order_index":2}]})
            assert invalid.status_code==422
            assert client.get(f"/api/v1/me/progress/lessons/{lesson_id}").json()["completed_at"] is not None

            # Publishing a Lesson does not create curriculum membership. The
            # existing complete-membership PUT is the only membership change.
            published_candidate = client.post("/api/v1/admin/lessons", json={
                "hsk_level_id": str(hsk_id),
                "lesson_number": 700000 + (user_id.int % 100000),
                "title": "Published but not assigned",
            })
            assert published_candidate.status_code == 201
            curriculum_candidate_id = published_candidate.json()["id"]
            assert published_candidate.json()["status"] == "DRAFT"
            assert client.post(f"/api/v1/admin/lessons/{curriculum_candidate_id}/publish").status_code == 200
            published_admin = client.get(f"/api/v1/admin/lessons/{curriculum_candidate_id}")
            assert published_admin.status_code == 200 and published_admin.json()["status"] == "PUBLISHED"
            before_membership = client.get(f"/api/v1/admin/hsk-levels/{hsk_id}/curriculum")
            assert before_membership.status_code == 200
            assert all(row["lesson_id"] != curriculum_candidate_id for row in before_membership.json())
            active_user["id"] = outsider_id
            learner_before_membership = client.get(f"/api/v1/hsk-levels/{hsk_id}/curriculum")
            assert learner_before_membership.status_code == 200
            assert all(row["lesson"] is None or row["lesson"]["id"] != curriculum_candidate_id for row in learner_before_membership.json()["units"])
            active_user["id"] = user_id

            full_membership = before_membership.json()
            desired_membership = [
                {"unit_type": row["unit_type"], "target_id": row["lesson_id"] if row["unit_type"] == "LESSON" else row["assessment_id"], "order_index": index}
                for index, row in enumerate(full_membership, start=1)
            ]
            desired_membership.append({"unit_type": "LESSON", "target_id": curriculum_candidate_id, "order_index": len(desired_membership) + 1})
            added = client.put(f"/api/v1/admin/hsk-levels/{hsk_id}/curriculum", json={"units": desired_membership})
            assert added.status_code == 200
            assert added.json()[-1]["lesson_id"] == curriculum_candidate_id
            active_user["id"] = outsider_id
            learner_after_add = client.get(f"/api/v1/hsk-levels/{hsk_id}/curriculum")
            assert learner_after_add.status_code == 200
            assert learner_after_add.json()["units"][-1]["lesson"]["id"] == curriculum_candidate_id
            active_user["id"] = user_id

            # A replacement PUT can detach the Lesson and reorder the remaining
            # units while leaving the independently published Lesson intact.
            detached_order = [
                {"unit_type": row["unit_type"], "target_id": row["lesson_id"] if row["unit_type"] == "LESSON" else row["assessment_id"], "order_index": index}
                for index, row in enumerate(reversed(added.json()[:-1]), start=1)
            ]
            detached = client.put(f"/api/v1/admin/hsk-levels/{hsk_id}/curriculum", json={"units": detached_order})
            assert detached.status_code == 200
            assert all(row["lesson_id"] != curriculum_candidate_id for row in detached.json())
            assert client.get(f"/api/v1/admin/lessons/{curriculum_candidate_id}").json()["status"] == "PUBLISHED"
            active_user["id"] = outsider_id
            learner_after_remove = client.get(f"/api/v1/hsk-levels/{hsk_id}/curriculum")
            assert learner_after_remove.status_code == 200
            assert all(row["lesson"] is None or row["lesson"]["id"] != curriculum_candidate_id for row in learner_after_remove.json()["units"])
            active_user["id"] = user_id

            assert client.post(f"/api/v1/assessment-attempts/{attempt_id}/submit", json={"answers":[{"question_id":str(question_id),"answer":{"option_id":str(correct_option_id)}}]}).status_code == 409
            assert client.get("/api/v1/me/assessment-attempts").json()["total"] == 1

            assert client.post(f"/api/v1/admin/assessments/{unavailable_assessment_id}/submit-review").status_code == 200
            assert client.post(f"/api/v1/admin/assessments/{unavailable_assessment_id}/publish").status_code == 200
            free_attempt=client.post(f"/api/v1/assessments/{unavailable_assessment_id}/attempts").json()
            failed=client.post(f"/api/v1/assessment-attempts/{free_attempt['id']}/submit",json={"answers":[
                {"question_id":str(free_question_id),"answer":{"text":"我喜欢中文"}},
                {"question_id":str(deterministic_question_id),"answer":{"option_id":str(deterministic_option_id)}}]})
            assert failed.status_code==503
            assert failed.json()=={"error":{"code":"AI_GRADING_UNAVAILABLE","message":"AI grading is not available","details":None}}
            result=client.get(f"/api/v1/me/assessment-attempts/{free_attempt['id']}").json()
            assert result["status"]=="GRADING_FAILED" and result["score"] is None and result["passed"] is None
            by_question={item["question_id"]:item for item in result["answers"]}
            assert by_question[str(free_question_id)]["answer"]=={"text":"我喜欢中文"} and by_question[str(free_question_id)]["grading_status"]=="FAILED"
            assert by_question[str(deterministic_question_id)]["grading_status"]=="GRADED" and by_question[str(deterministic_question_id)]["is_correct"] is True

            class FakeAIGrader:
                async def grade(self, *, question, answer): return GradeResult("UNCERTAIN",None,None,"Needs review")
            app.dependency_overrides[get_ai_grader]=lambda: FakeAIGrader()
            assert client.post(f"/api/v1/admin/assessments/{uncertain_assessment_id}/submit-review").status_code==200
            assert client.post(f"/api/v1/admin/assessments/{uncertain_assessment_id}/publish").status_code==200
            uncertain_attempt=client.post(f"/api/v1/assessments/{uncertain_assessment_id}/attempts").json()
            uncertain_result=client.post(f"/api/v1/assessment-attempts/{uncertain_attempt['id']}/submit",json={"answers":[
                {"question_id":str(uncertain_free_id),"answer":{"text":"answer"}},
                {"question_id":str(uncertain_mcq_id),"answer":{"option_id":str(uncertain_option_id)}}]})
            assert uncertain_result.status_code==200 and uncertain_result.json()["score"]==100.0
            app.dependency_overrides.pop(get_ai_grader,None)
            assert client.post(f"/api/v1/admin/assessments/{assessment_id}/archive").status_code == 200
            assert client.post(f"/api/v1/admin/assessments/{assessment_id}/archive").status_code == 409
            levels=client.get("/api/v1/admin/hsk-levels").json()
            level2=next(row["id"] for row in levels if row["level_number"]==2)
            created_lesson=client.post("/api/v1/admin/lessons",json={"hsk_level_id":level2,"lesson_number":900000+(user_id.int%100000),"title":"Lifecycle lesson"})
            assert created_lesson.status_code==201
            archived_lesson_id=created_lesson.json()["id"]
            assert created_lesson.json()["status"]=="DRAFT"
            assert client.post(f"/api/v1/admin/lessons/{archived_lesson_id}/publish").status_code==200
            assert client.post(f"/api/v1/admin/lessons/{archived_lesson_id}/publish").status_code==409
            assert client.post(f"/api/v1/admin/lessons/{archived_lesson_id}/archive").status_code==200
            assert client.get(f"/api/v1/lessons/{archived_lesson_id}").status_code==404
            stats=client.get("/api/v1/admin/stats")
            assert stats.status_code==200 and stats.json()["total_users"]>=2 and stats.json()["average_exercise_score"] is not None
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_ai_grader, None)
        async def cleanup():
            async with SessionFactory.begin() as session:
                source_ids = select(KnowledgeSource.id).where(KnowledgeSource.lesson_id == archived_lesson_id)
                version_ids = select(KnowledgeVersion.id).where(KnowledgeVersion.knowledge_source_id.in_(source_ids))
                await session.execute(delete(Chunk).where(Chunk.knowledge_version_id.in_(version_ids)))
                await session.execute(delete(KnowledgeVersion).where(KnowledgeVersion.knowledge_source_id.in_(source_ids)))
                await session.execute(delete(KnowledgeSource).where(KnowledgeSource.lesson_id == archived_lesson_id))
                assessment_ids=(assessment_id,unavailable_assessment_id,uncertain_assessment_id)
                attempt_ids = select(AssessmentAttempt.id).where(AssessmentAttempt.assessment_id.in_(assessment_ids))
                await session.execute(delete(AttemptAnswer).where(AttemptAnswer.assessment_attempt_id.in_(attempt_ids)))
                await session.execute(delete(AssessmentAttempt).where(AssessmentAttempt.assessment_id.in_(assessment_ids)))
                qids = select(Question.id).where(Question.assessment_id.in_(assessment_ids))
                await session.execute(delete(QuestionOption).where(QuestionOption.question_id.in_(qids)))
                await session.execute(delete(Question).where(Question.assessment_id.in_(assessment_ids)))
                await session.execute(delete(Assessment).where(Assessment.id.in_(assessment_ids)))
                await session.execute(delete(CurriculumUnit).where(CurriculumUnit.lesson_id == lesson_id))
                await session.execute(delete(LearnerLessonProgress).where(LearnerLessonProgress.user_id == user_id))
                await session.execute(delete(LearnerVocabularyProgress).where(LearnerVocabularyProgress.user_id == user_id))
                await session.execute(delete(LearnerGrammarProgress).where(LearnerGrammarProgress.user_id == user_id))
                await session.execute(delete(LearnerHSKProgress).where(LearnerHSKProgress.user_id == user_id))
                await session.execute(delete(PronunciationProgress).where(PronunciationProgress.user_id == user_id))
                await session.execute(delete(LessonVocabulary).where(LessonVocabulary.id == vocab_link_id))
                test_vocabulary_ids = select(Vocabulary.id).where(
                    Vocabulary.hanzi == "你", Vocabulary.pinyin == "nǐ"
                )
                shared_vocab_link_ids = select(LessonVocabulary.id).where(
                    LessonVocabulary.vocabulary_id.in_(test_vocabulary_ids)
                )
                await session.execute(delete(LearnerVocabularyProgress).where(
                    LearnerVocabularyProgress.lesson_vocabulary_id.in_(shared_vocab_link_ids)
                ))
                await session.execute(delete(LessonVocabulary).where(
                    LessonVocabulary.vocabulary_id.in_(test_vocabulary_ids)
                ))
                await session.execute(delete(LessonGrammar).where(LessonGrammar.id == grammar_link_id))
                await session.execute(delete(Vocabulary).where(Vocabulary.hanzi == "你",Vocabulary.pinyin == "nǐ"))
                await session.execute(delete(Grammar).where(Grammar.name == "Test grammar"))
                await session.execute(delete(CurriculumUnit).where(CurriculumUnit.lesson_id == lesson_id))
                await session.execute(delete(Lesson).where(Lesson.id == lesson_id))
                await session.execute(delete(CurriculumUnit).where(CurriculumUnit.lesson_id == next_lesson_id))
                await session.execute(delete(Lesson).where(Lesson.id == next_lesson_id))
                await session.execute(delete(CurriculumUnit).where(CurriculumUnit.lesson_id == curriculum_candidate_id))
                candidate_source_ids = select(KnowledgeSource.id).where(KnowledgeSource.lesson_id == curriculum_candidate_id)
                candidate_version_ids = select(KnowledgeVersion.id).where(KnowledgeVersion.knowledge_source_id.in_(candidate_source_ids))
                await session.execute(delete(Chunk).where(Chunk.knowledge_version_id.in_(candidate_version_ids)))
                await session.execute(delete(KnowledgeVersion).where(KnowledgeVersion.knowledge_source_id.in_(candidate_source_ids)))
                await session.execute(delete(KnowledgeSource).where(KnowledgeSource.lesson_id == curriculum_candidate_id))
                await session.execute(delete(Lesson).where(Lesson.id == curriculum_candidate_id))
                await session.execute(delete(Lesson).where(Lesson.id == archived_lesson_id))
                await session.execute(delete(User).where(User.id == user_id))
                await session.execute(delete(User).where(User.id == outsider_id))
        asyncio.run(cleanup())
