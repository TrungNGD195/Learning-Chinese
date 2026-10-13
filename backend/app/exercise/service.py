from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApplicationError
from app.database.models import Assessment
from app.exercise.grading import DeterministicGrader, GradingUnavailable, UnavailableAIGrader
from app.exercise import repository
from app.exercise import repository as exercise_repository
from app.progress import service as progress


def _error(code: str, message: str, status: int):
    return ApplicationError(code, message, status_code=status)


async def _assessment_access(session: AsyncSession, user_id: UUID, assessment: Assessment) -> None:
    if assessment.status != "PUBLISHED":
        raise _error("NOT_FOUND", "Assessment was not found", 404)
    if assessment.type == "LESSON_EXERCISE":
        await progress.require_lesson_access(session, user_id, assessment.lesson_id)
        return
    _, states, _, _, _ = await progress.progression_snapshot(session, user_id)
    if not any(entry["unit"].assessment_id == assessment.id and entry["state"] in {"AVAILABLE", "COMPLETED"}
               for group in states.values() for entry in group):
        raise _error("ASSESSMENT_LOCKED", "Assessment is locked", 403)


async def has_active_periodic_test(session: AsyncSession, user_id: UUID) -> bool:
    """Return whether committed assessment state blocks starting an AI chat turn."""
    return await repository.has_active_periodic_test(session, user_id)


async def assessment_payload(session: AsyncSession, user_id: UUID, assessment_id: UUID, *, reveal: bool = False) -> dict:
    assessment = await repository.get_assessment(session,assessment_id)
    if assessment is None:
        raise _error("NOT_FOUND", "Assessment was not found", 404)
    await _assessment_access(session, user_id, assessment)
    questions = await repository.list_questions(session,assessment.id)
    payload = []
    for q in questions:
        config = dict(q.config or {})
        if q.type == "multiple_choice":
            config = {}
        elif q.type == "fill_blank":
            config = {key: config[key] for key in ("accepted_answers",) if reveal and key in config}
        elif q.type == "matching":
            config = {key: config[key] for key in ("left_items", "right_items", "correct_pairs") if reveal or key != "correct_pairs"}
        elif q.type == "reorder_sentence":
            config = {key: config[key] for key in ("items", "correct_order") if reveal or key != "correct_order"}
        else:
            config = {}
        options = await repository.list_question_options(session,q.id) if q.type == "multiple_choice" else []
        row = {"id": q.id, "type": q.type, "prompt": q.prompt, "order_index": q.order_index, "points": float(q.points), "config": config}
        if q.type == "multiple_choice":
            row["options"] = [{"id": option.id, "option_text": option.option_text, **({"is_correct": option.is_correct} if reveal else {})} for option in options]
        if reveal:
            row.update(reference_answer=q.reference_answer, rubric=q.rubric)
        payload.append(row)
    return {"id": assessment.id, "type": assessment.type, "title": assessment.title, "description": assessment.description,
            "pass_threshold": assessment.pass_threshold, "questions": payload}


async def start_attempt(session: AsyncSession, user_id: UUID, assessment_id: UUID) -> tuple[dict, int]:
    async with session.begin_nested():
        assessment = await repository.get_assessment(session,assessment_id,for_update=True)
        if assessment is None:
            raise _error("NOT_FOUND", "Assessment was not found", 404)
        await _assessment_access(session, user_id, assessment)
        active = await repository.active_attempt(session,user_id,assessment_id)
        if active:
            result, status = active, 200
        else:
            maximum = await repository.max_attempt_number(session,user_id,assessment_id)
            result = await repository.create_attempt(session,user_id,assessment_id,(maximum or 0)+1); status = 201
        data = {"id": result.id, "assessment_id": result.assessment_id, "attempt_number": result.attempt_number,
                "status": result.status, "started_at": result.started_at}
    await session.commit()
    return data, status


def _validate_answer(question: dict, answer: object) -> dict:
    if not isinstance(answer, dict):
        raise _error("INVALID_ANSWER", "Answer payload is invalid", 422)
    kind = question["type"]
    fields = {"multiple_choice": {"option_id"}, "fill_blank": {"text"}, "matching": {"pairs"},
              "reorder_sentence": {"item_ids"}, "translate_vi_zh": {"text"}, "translate_zh_vi": {"text"}, "sentence_writing": {"text"}}[kind]
    if set(answer) != fields:
        raise _error("INVALID_ANSWER", "Answer payload is invalid", 422)
    if kind == "multiple_choice":
        try: option_id = UUID(str(answer["option_id"]))
        except (ValueError, TypeError): raise _error("INVALID_ANSWER", "Answer option is invalid", 422)
        if option_id not in question["option_ids"]: raise _error("INVALID_ANSWER", "Answer option is invalid", 422)
        return {"option_id": str(option_id)}
    if kind in {"fill_blank", "translate_vi_zh", "translate_zh_vi", "sentence_writing"}:
        if not isinstance(answer["text"], str): raise _error("INVALID_ANSWER", "Answer text must be a string", 422)
    elif kind == "matching":
        if not isinstance(answer["pairs"], list) or any(not isinstance(p, dict) or set(p) != {"left_id", "right_id"} or not all(isinstance(p[k], str) for k in p) for p in answer["pairs"]):
            raise _error("INVALID_ANSWER", "Matching answer is invalid", 422)
        cfg = question["config"] or {}; left = {x.get("id") for x in cfg.get("left_items", []) if isinstance(x, dict)}; right = {x.get("id") for x in cfg.get("right_items", []) if isinstance(x, dict)}
        pairs=answer["pairs"]
        left_ids=[p["left_id"] for p in pairs]; right_ids=[p["right_id"] for p in pairs]
        pair_keys=[(p["left_id"],p["right_id"]) for p in pairs]
        if (any(left_id not in left or right_id not in right for left_id,right_id in pair_keys)
                or len(set(left_ids))!=len(left_ids) or len(set(right_ids))!=len(right_ids)
                or len(set(pair_keys))!=len(pair_keys)):
            raise _error("INVALID_ANSWER", "Matching answer contains invalid or duplicate pairs", 422)
    else:
        cfg = question["config"] or {}; items = cfg.get("items")
        if not isinstance(answer["item_ids"], list) or not all(isinstance(x, str) for x in answer["item_ids"]): raise _error("INVALID_ANSWER", "Ordering answer is invalid", 422)
        valid = {x.get("id") for x in items if isinstance(x, dict)} if isinstance(items, list) else set()
        if len(answer["item_ids"]) != len(valid) or set(answer["item_ids"]) != valid: raise _error("INVALID_ANSWER", "Ordering answer is invalid", 422)
    return answer


def _validate_stored_question(question: dict) -> None:
    """Reject invalid persisted answer keys as server data errors before learner input is graded."""
    kind, config = question["type"], question["config"]
    if config is None: config = {}
    if not isinstance(config,dict):
        raise ApplicationError("INVALID_QUESTION_CONFIGURATION", "Assessment question configuration is invalid", status_code=500)
    if kind == "multiple_choice":
        if not question["option_ids"]: raise ApplicationError("INVALID_QUESTION_CONFIGURATION", "Assessment question configuration is invalid", status_code=500)
    elif kind == "fill_blank":
        accepted=config.get("accepted_answers", [])
        if not isinstance(question["reference_answer"],str) or not isinstance(accepted,list) or not all(isinstance(item,str) for item in accepted):
            raise ApplicationError("INVALID_QUESTION_CONFIGURATION", "Assessment question configuration is invalid", status_code=500)
    elif kind == "matching":
        left,right,pairs=config.get("left_items"),config.get("right_items"),config.get("correct_pairs")
        valid_items=lambda rows: isinstance(rows,list) and rows and all(isinstance(x,dict) and isinstance(x.get("id"),str) and isinstance(x.get("text"),str) for x in rows)
        if not valid_items(left) or not valid_items(right) or not isinstance(pairs,list):
            raise ApplicationError("INVALID_QUESTION_CONFIGURATION", "Assessment question configuration is invalid", status_code=500)
        lids=[x["id"] for x in left]; rids=[x["id"] for x in right]
        if len(set(lids))!=len(lids) or len(set(rids))!=len(rids) or len(pairs)!=len(lids):
            raise ApplicationError("INVALID_QUESTION_CONFIGURATION", "Assessment question configuration is invalid", status_code=500)
        if any(not isinstance(p,dict) or set(p)!={"left_id","right_id"} or p["left_id"] not in lids or p["right_id"] not in rids for p in pairs):
            raise ApplicationError("INVALID_QUESTION_CONFIGURATION", "Assessment question configuration is invalid", status_code=500)
        if len({p["left_id"] for p in pairs})!=len(pairs) or len({p["right_id"] for p in pairs})!=len(pairs):
            raise ApplicationError("INVALID_QUESTION_CONFIGURATION", "Assessment question configuration is invalid", status_code=500)
    elif kind == "reorder_sentence":
        items,order=config.get("items"),config.get("correct_order")
        if not isinstance(items,list) or not items or not isinstance(order,list) or any(not isinstance(x,dict) or not isinstance(x.get("id"),str) or not isinstance(x.get("text"),str) for x in items):
            raise ApplicationError("INVALID_QUESTION_CONFIGURATION", "Assessment question configuration is invalid", status_code=500)
        item_ids=[x["id"] for x in items]
        if len(set(item_ids))!=len(item_ids) or len(order)!=len(item_ids) or set(order)!=set(item_ids):
            raise ApplicationError("INVALID_QUESTION_CONFIGURATION", "Assessment question configuration is invalid", status_code=500)


def calculate_score(questions: list[dict],results: dict,pass_threshold:int) -> tuple[float|None,bool|None]:
    gradable=[q for q in questions if results[q["id"]] is not None and results[q["id"]].grading_status=="GRADED"]
    maximum=sum(float(q["points"]) for q in gradable)
    if maximum==0:return None,None
    earned=sum(float(results[q["id"]].score or 0) for q in gradable)
    score=round(earned/maximum*100,2)
    return score,score>=pass_threshold


async def submit_attempt(session: AsyncSession, user_id: UUID, attempt_id: UUID, body: dict, ai_grader=None) -> dict:
    if ai_grader is None:
        ai_grader = UnavailableAIGrader()
    attempt = await repository.get_attempt(session,attempt_id,for_update=True)
    if attempt is None or attempt.user_id != user_id: raise _error("NOT_FOUND", "Assessment attempt was not found", 404)
    if attempt.status != "IN_PROGRESS": raise _error("ATTEMPT_ALREADY_SUBMITTED", "Assessment attempt has already been submitted", 409)
    assessment = await repository.get_assessment(session,attempt.assessment_id)
    await _assessment_access(session, user_id, assessment)
    pass_threshold = assessment.pass_threshold
    qs = await repository.list_questions(session,assessment.id)
    if not isinstance(body, dict) or set(body) != {"answers"} or not isinstance(body["answers"], list): raise _error("INVALID_SUBMISSION", "Submission is invalid", 422)
    raw = body["answers"]
    ids = []
    for item in raw:
        if not isinstance(item, dict) or set(item) != {"question_id", "answer"}: raise _error("INVALID_SUBMISSION", "Submission is invalid", 422)
        try: ids.append(UUID(str(item["question_id"])))
        except (ValueError, TypeError): raise _error("INVALID_SUBMISSION", "Submission is invalid", 422)
    if len(set(ids)) != len(ids) or set(ids) != {q.id for q in qs}: raise _error("INVALID_SUBMISSION", "Provide one answer for every question", 422)
    questions = []
    for q in qs:
        options = await repository.list_question_options(session,q.id)
        questions.append({"id": q.id, "type": q.type, "prompt": q.prompt, "config": q.config or {}, "reference_answer": q.reference_answer,
                          "rubric": q.rubric, "points": q.points, "option_ids": {o.id for o in options},
                          "correct_option_ids": {str(o.id) for o in options if o.is_correct}})
    for q in questions: _validate_stored_question(q)
    answer_map = dict(zip(ids, [item["answer"] for item in raw]))
    validated = {q["id"]: _validate_answer(q, answer_map[q["id"]]) for q in questions}
    # Materialize the grading inputs, then release all read locks/transactions before the AI boundary.
    await session.rollback()
    grader = DeterministicGrader(); results = {}; ai_failed = False
    for q in questions:
        answer = validated[q["id"]]
        if q["type"] in {"multiple_choice", "fill_blank", "matching", "reorder_sentence"}:
            try: results[q["id"]] = grader.grade(q, answer)
            except (ValueError, KeyError, TypeError): raise ApplicationError("INVALID_QUESTION_CONFIGURATION", "Assessment question configuration is invalid", status_code=500)
        else:
            try:
                grading_question = {key: q[key] for key in ("type", "prompt", "reference_answer", "rubric", "points")}
                results[q["id"]] = await ai_grader.grade(question=grading_question, answer=answer)
            except GradingUnavailable: ai_failed = True; results[q["id"]] = None
    async with session.begin():
        locked = await repository.get_attempt(session,attempt_id,for_update=True)
        if locked.user_id != user_id or locked.status != "IN_PROGRESS": raise _error("ATTEMPT_ALREADY_SUBMITTED", "Assessment attempt has already been submitted", 409)
        now = datetime.now(UTC)
        score,passed=calculate_score(questions,results,pass_threshold)
        answer_rows=[{"question_id":q["id"],"user_answer":validated[q["id"]],
                      "score":results[q["id"]].score if results[q["id"]] else None,
                      "is_correct":results[q["id"]].is_correct if results[q["id"]] else None,
                      "grading_status":results[q["id"]].grading_status if results[q["id"]] else "FAILED",
                      "feedback":results[q["id"]].feedback if results[q["id"]] else None} for q in questions]
        await repository.add_attempt_answers(session,attempt_id,answer_rows)
        assessment_for_progress = await repository.get_assessment(session,locked.assessment_id)
        if ai_failed:
            await repository.finalize_attempt(session,attempt_id,submitted_at=now,status="GRADING_FAILED",score=None,passed=None)
        else:
            await repository.finalize_attempt(session,attempt_id,submitted_at=now,status="GRADED",score=score,passed=passed)
            if score is not None: await progress.after_attempt(session, user_id, assessment_for_progress)
    if ai_failed: raise ApplicationError("AI_GRADING_UNAVAILABLE", "AI grading is not available", status_code=503)
    return {"attempt_id": attempt_id, "status": "GRADED", "score": score, "passed": (score >= assessment_for_progress.pass_threshold) if score is not None else None}


async def history(session: AsyncSession, user_id: UUID, page: int, page_size: int, assessment_id=None, lesson_id=None, assessment_type=None):
    total,rows=await repository.history_rows(session,user_id,page,page_size,assessment_id,lesson_id,assessment_type)
    return {"items": [{"id": a.id, "assessment_id": ass.id, "assessment_title": ass.title, "assessment_type": ass.type,
                        "attempt_number": a.attempt_number, "status": a.status, "started_at": a.started_at, "submitted_at": a.submitted_at,
                        "score": float(a.score) if a.score is not None else None, "passed": a.passed} for a, ass in rows],
            "page": page, "page_size": page_size, "total": total}


async def attempt_detail(session: AsyncSession, user_id: UUID, attempt_id: UUID):
    attempt,assessment,answers=await repository.attempt_detail_rows(session,attempt_id,user_id)
    if attempt is None: raise _error("NOT_FOUND", "Assessment attempt was not found", 404)
    submitted = attempt.status in {"GRADED", "GRADING_FAILED"}
    return {"id": attempt.id, "assessment_id": assessment.id, "attempt_number": attempt.attempt_number, "status": attempt.status,
            "score": float(attempt.score) if attempt.score is not None else None, "passed": attempt.passed, "submitted_at": attempt.submitted_at,
            "answers": [{"question_id": q.id, "type": q.type, "prompt": q.prompt, "answer": a.user_answer,
                         "grading_status": a.grading_status, "score": float(a.score) if a.score is not None else None,
                         "is_correct": a.is_correct, "feedback": a.feedback,
                         **({"reference_answer": q.reference_answer, "rubric": q.rubric, "config": q.config} if submitted else {})} for a, q in answers]}


# Admin use cases for assessment and question lifecycle and validation.

def fail(code: str, message: str, status: int = 404):
    raise ApplicationError(code, message, status_code=status)

def _dump(obj, fields): return {field: getattr(obj, field) for field in fields}

async def admin_get_assessment(session, assessment_id, *, for_update=False):
    return await exercise_repository.get_assessment(session,assessment_id,for_update=for_update)

async def admin_assessments(session, page=1, page_size=20, status=None, assessment_type=None):
    total,rows=await exercise_repository.admin_assessments_page(session,page,page_size,status,assessment_type)
    return {"items":[_dump(a,("id","type","lesson_id","title","description","status","pass_threshold","published_at")) for a in rows],
        "page":page,"page_size":page_size,"total":total}


async def admin_create_assessment(session, body):
    scope_fields={"lesson_ids","vocabulary_ids","grammar_ids"}
    allowed={"type","lesson_id","title","description","pass_threshold"}|scope_fields
    if set(body)-allowed or not {"type","title"}<=set(body): fail("INVALID_FIELDS","Assessment payload is invalid",422)
    if body["type"] not in {"LESSON_EXERCISE","PERIODIC_TEST"} or (body["type"]=="LESSON_EXERCISE") != bool(body.get("lesson_id")): fail("INVALID_ASSESSMENT_TARGET","Assessment target is invalid",422)
    if "pass_threshold" in body and (not isinstance(body["pass_threshold"],int) or not 0<=body["pass_threshold"]<=100): fail("INVALID_ASSESSMENT","Pass threshold must be from 0 through 100",422)
    if body["type"]=="LESSON_EXERCISE" and any(body.get(k) for k in scope_fields): fail("INVALID_ASSESSMENT_SCOPE","Lesson exercises use lesson_id scope",422)
    async with session.begin_nested():
        fields={k:v for k,v in body.items() if k not in scope_fields}
        if body.get("lesson_id"):
            try: fields["lesson_id"]=UUID(str(body["lesson_id"]))
            except (ValueError,TypeError): fail("INVALID_ASSESSMENT_TARGET","Lesson identifier is invalid",422)
        if body.get("lesson_id"):
            from app.curriculum import service as curriculum_service
            if await curriculum_service.admin_get_lesson(session,fields["lesson_id"]) is None:fail("NOT_FOUND","Lesson was not found")
        row=await exercise_repository.admin_create_assessment(session,fields)
        await admin__replace_assessment_scope(session,row.id,body)
    await session.commit(); return _dump(row,("id","type","lesson_id","title","description","status","pass_threshold","published_at"))


async def admin_patch_assessment(session, ident, body):
    if set(body)-{"title","description","pass_threshold","lesson_ids","vocabulary_ids","grammar_ids"}: fail("INVALID_FIELDS","Assessment status/target cannot be changed with PATCH",422)
    async with session.begin_nested():
        row=await exercise_repository.get_assessment(session,ident,for_update=True)
        if row is None:fail("NOT_FOUND","Assessment was not found")
        if row.status not in {"DRAFT","REVIEW"}: fail("ASSESSMENT_IMMUTABLE","Assessment is immutable after publication",409)
        if "pass_threshold" in body and (not isinstance(body["pass_threshold"],int) or not 0<=body["pass_threshold"]<=100): fail("INVALID_ASSESSMENT","Pass threshold must be from 0 through 100",422)
        await exercise_repository.admin_update_assessment(session,row,{k:v for k,v in body.items() if k not in {"lesson_ids","vocabulary_ids","grammar_ids"}})
        if any(k in body for k in ("lesson_ids","vocabulary_ids","grammar_ids")):
            if row.type!="PERIODIC_TEST": fail("INVALID_ASSESSMENT_SCOPE","Lesson exercises use lesson_id scope",422)
            await admin__replace_assessment_scope(session,row.id,body)
    await session.commit(); return _dump(row,("id","type","lesson_id","title","description","status","pass_threshold","published_at"))


async def admin__replace_assessment_scope(session, assessment_id, body):
    for key in ("lesson_ids","vocabulary_ids","grammar_ids"):
        if key not in body: continue
        raw=body[key]
        if not isinstance(raw,list): fail("INVALID_ASSESSMENT_SCOPE","Assessment scope must be a list",422)
        try: values=[UUID(str(value)) for value in raw]
        except (ValueError,TypeError): fail("INVALID_ASSESSMENT_SCOPE","Assessment scope contains an invalid identifier",422)
        if len(set(values))!=len(values): fail("INVALID_ASSESSMENT_SCOPE","Assessment scope contains duplicates",422)
        if not await exercise_repository.admin_replace_assessment_scope(session,assessment_id,{key:values}):
            fail("INVALID_ASSESSMENT_SCOPE","Assessment scope target was not found",422)


async def admin_assessment_transition(session, ident, action):
    transitions={"submit-review":("DRAFT","REVIEW"),"publish":("REVIEW","PUBLISHED"),"archive":("PUBLISHED","ARCHIVED")}
    async with session.begin_nested():
        row=await exercise_repository.get_assessment(session,ident,for_update=True)
        if row is None:fail("NOT_FOUND","Assessment was not found")
        source,target=transitions[action]
        if row.status!=source: fail("INVALID_LIFECYCLE_TRANSITION","Assessment lifecycle transition is invalid",409)
        if action=="submit-review":
            count=await exercise_repository.admin_question_count(session,ident)
            if count==0: fail("ASSESSMENT_HAS_NO_QUESTIONS","Assessment requires questions",409)
        row=await exercise_repository.admin_transition_assessment(session,row,target,datetime.now(UTC) if action=="publish" else None)
    await session.commit(); return _dump(row,("id","type","lesson_id","title","description","status","pass_threshold","published_at"))


async def admin_questions(session, assessment_id):
    if await exercise_repository.get_assessment(session,assessment_id) is None:fail("NOT_FOUND","Assessment was not found")
    qs=await exercise_repository.admin_questions(session,assessment_id)
    result=[]
    for q,options in qs:
        result.append({"id":q.id,"assessment_id":q.assessment_id,"type":q.type,"prompt":q.prompt,"order_index":q.order_index,"reference_answer":q.reference_answer,"rubric":q.rubric,"config":q.config,"points":float(q.points),"options":[{"id":o.id,"option_text":o.option_text,"order_index":o.order_index,"is_correct":o.is_correct} for o in options]})
    return result


def admin_validate_question(body, partial=False):
    keys={"type","prompt","order_index","reference_answer","rubric","config","points","options"}
    required={"type","prompt","order_index"}
    if set(body)-keys or (not partial and not required<=set(body)): fail("INVALID_QUESTION","Question payload is invalid",422)
    kind=body.get("type")
    if kind is not None and kind not in {"multiple_choice","fill_blank","matching","reorder_sentence","translate_vi_zh","translate_zh_vi","sentence_writing"}: fail("INVALID_QUESTION","Question type is invalid",422)
    if "options" in body:
        opts=body["options"]
        if (kind not in {None,"multiple_choice"}) or not isinstance(opts,list) or len(opts)<2 or any(not isinstance(o,dict) or set(o)!={"option_text","is_correct"} or not isinstance(o["option_text"],str) or not isinstance(o["is_correct"],bool) for o in opts) or sum(bool(o["is_correct"]) for o in opts)!=1: fail("INVALID_QUESTION","Multiple-choice options are invalid",422)
    cfg=body.get("config")
    if kind=="multiple_choice" and cfg not in (None,{}): fail("INVALID_QUESTION","Multiple-choice answers are stored in question options",422)
    if kind=="multiple_choice" and not partial and "options" not in body: fail("INVALID_QUESTION","Multiple-choice questions require options",422)
    if kind=="fill_blank" and not partial and not isinstance(body.get("reference_answer"),str): fail("INVALID_QUESTION","Fill-blank questions require a reference answer",422)
    if kind=="fill_blank" and cfg is not None and (not isinstance(cfg,dict) or ("accepted_answers" in cfg and (not isinstance(cfg["accepted_answers"],list) or not all(isinstance(x,str) for x in cfg["accepted_answers"])))): fail("INVALID_QUESTION","Fill-blank config is invalid",422)
    if kind=="matching" and not partial and cfg is None: fail("INVALID_QUESTION","Matching questions require configuration",422)
    if kind=="matching" and cfg is not None and set(cfg)!={"left_items","right_items","correct_pairs"}: fail("INVALID_QUESTION","Matching config fields are invalid",422)
    if kind=="matching" and cfg is not None:
        if not isinstance(cfg,dict) or not all(k in cfg for k in ("left_items","right_items","correct_pairs")): fail("INVALID_QUESTION","Matching config is invalid",422)
        left,right,pairs=cfg["left_items"],cfg["right_items"],cfg["correct_pairs"]
        if not isinstance(left,list) or not isinstance(right,list) or not isinstance(pairs,list) or not left or not right: fail("INVALID_QUESTION","Matching config is invalid",422)
        if any(not isinstance(items,list) for items in (left,right)) or any(not isinstance(x,dict) or set(x)!={"id","text"} or not all(isinstance(x[k],str) for k in ("id","text")) for x in [*left,*right]): fail("INVALID_QUESTION","Matching config is invalid",422)
        lids={x["id"] for x in left}; rids={x["id"] for x in right}
        if len(lids)!=len(left) or len(rids)!=len(right) or len(pairs)!=len(left) or any(not isinstance(p,dict) or set(p)!={"left_id","right_id"} or p["left_id"] not in lids or p["right_id"] not in rids for p in pairs) or len({p["left_id"] for p in pairs})!=len(pairs) or len({p["right_id"] for p in pairs})!=len(pairs): fail("INVALID_QUESTION","Matching config is invalid",422)
    if kind=="reorder_sentence" and not partial and cfg is None: fail("INVALID_QUESTION","Reorder questions require configuration",422)
    if kind=="reorder_sentence" and cfg is not None and set(cfg)!={"items","correct_order"}: fail("INVALID_QUESTION","Reorder config fields are invalid",422)
    if kind=="reorder_sentence" and cfg is not None:
        if not isinstance(cfg,dict) or not all(k in cfg for k in ("items","correct_order")) or not isinstance(cfg["items"],list) or not isinstance(cfg["correct_order"],list): fail("INVALID_QUESTION","Reorder config is invalid",422)
        items,order=cfg["items"],cfg["correct_order"]
        if any(not isinstance(x,dict) or set(x)!={"id","text"} or not isinstance(x["id"],str) or not isinstance(x["text"],str) for x in items): fail("INVALID_QUESTION","Reorder config is invalid",422)
        ids=[x["id"] for x in items]
        if not ids or len(set(ids))!=len(ids) or len(order)!=len(ids) or set(order)!=set(ids): fail("INVALID_QUESTION","Reorder config is invalid",422)


def admin_validate_generated_question(body):
    """Apply the existing D-009 contract to a generated, untrusted proposal."""
    return admin_validate_question(body)


async def admin_create_question(session, assessment_id, body):
    admin_validate_question(body)
    async with session.begin_nested():
        assessment=await exercise_repository.get_assessment(session,assessment_id,for_update=True)
        if assessment is None:fail("NOT_FOUND","Assessment was not found")
        if assessment.status not in {"DRAFT","REVIEW"}: fail("QUESTIONS_IMMUTABLE","Questions are immutable after publication",409)
        fields={k:v for k,v in body.items() if k!="options"}
        q=await exercise_repository.admin_create_question(session,assessment_id,fields,body.get("options",[]))
        question_id=q.id
    await session.commit(); return next(item for item in await admin_questions(session,assessment_id) if item["id"]==question_id)


async def persist_generated_assessment_draft(session, *, assessment_fields, scope, questions):
    """Persist a generated DRAFT and materialize its response before committing."""
    async with session.begin():
        assessment = await exercise_repository.admin_create_assessment(session, assessment_fields)
        if scope.get("type") == "PERIODIC_TEST":
            persisted = await exercise_repository.admin_replace_assessment_scope(
                session, assessment.id,
                {"lesson_ids": scope["lesson_ids"], "vocabulary_ids": scope["vocabulary_ids"], "grammar_ids": scope["grammar_ids"]},
            )
            if not persisted:
                raise ValueError("selected scope changed during persistence")
        for question in questions:
            item = dict(question)
            options = item.pop("options", [])
            await exercise_repository.admin_create_question(session, assessment.id, item, options)
        assessment_id = assessment.id
        # Materialize all database-backed response fields while the transaction
        # is still open. Any read/serialization failure must roll back the draft.
        persisted_assessment = await exercise_repository.get_assessment(session, assessment_id)
        question_rows = await admin_questions(session, assessment_id)
        response = {
            "assessment": {field: getattr(persisted_assessment, field) for field in
                           ("id", "type", "lesson_id", "title", "description", "status", "pass_threshold", "published_at")},
            "questions": question_rows,
        }
    return response


async def admin_patch_question(session, assessment_id, question_id, body):
    if "type" in body: fail("QUESTION_TYPE_IMMUTABLE","Question type cannot be changed after creation",422)
    admin_validate_question(body,True)
    async with session.begin_nested():
        assessment=await exercise_repository.get_assessment(session,assessment_id,for_update=True)
        if assessment is None:fail("NOT_FOUND","Assessment was not found")
        q=await exercise_repository.admin_get_question(session,assessment_id,question_id,for_update=True)
        if q is None: fail("NOT_FOUND","Question was not found")
        if assessment.status not in {"DRAFT","REVIEW"}: fail("QUESTIONS_IMMUTABLE","Questions are immutable after publication",409)
        current={"type":q.type,"prompt":q.prompt,"order_index":q.order_index,"reference_answer":q.reference_answer,
                 "rubric":q.rubric,"config":q.config,"points":q.points}
        if q.type=="multiple_choice":
            current["options"]=[{"option_text":o.option_text,"is_correct":o.is_correct} for o in await exercise_repository.admin_question_options(session,q.id)]
        admin_validate_question({**current,**body},False)
        options=body.pop("options",None)
        await exercise_repository.admin_update_question(session,q,body)
        if options is not None:await exercise_repository.admin_replace_question_options(session,q.id,options)
    await session.commit(); return next(x for x in await admin_questions(session,assessment_id) if x["id"]==question_id)


async def admin_delete_question(session, assessment_id, question_id):
    async with session.begin_nested():
        assessment=await exercise_repository.get_assessment(session,assessment_id,for_update=True)
        if assessment is None:fail("NOT_FOUND","Assessment was not found")
        q=await exercise_repository.admin_get_question(session,assessment_id,question_id,for_update=True)
        if q is None: fail("NOT_FOUND","Question was not found")
        if assessment.status not in {"DRAFT","REVIEW"}: fail("QUESTIONS_IMMUTABLE","Questions are immutable after publication",409)
        if await exercise_repository.admin_question_has_history(session,question_id): fail("QUESTION_HAS_HISTORY","Question has historical answers",409)
        await exercise_repository.admin_delete_question(session,q)
    await session.commit(); return {"deleted":True}


