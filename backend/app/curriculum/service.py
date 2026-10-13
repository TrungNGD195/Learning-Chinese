"""Curriculum and lesson content use cases."""
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApplicationError
from app.curriculum import repository
from app.curriculum import repository as curriculum_repository
from app.progress import service as progress_service


async def list_hsk_levels(session: AsyncSession,user_id: UUID):
    levels, states, _, _, _ = await progress_service.progression_snapshot(session,user_id)
    return progress_service.learner_hsk_states(levels,states)


async def get_curriculum(session: AsyncSession,user_id: UUID,hsk_id: UUID):
    levels, states, _, _, _ = await progress_service.progression_snapshot(session,user_id)
    level=next((item for item in levels if item.id==hsk_id),None)
    if level is None:
        raise ApplicationError("NOT_FOUND","HSK level was not found",status_code=404)
    units=[]
    for entry in states.get(hsk_id,[]):
        unit,lesson,assessment=entry["unit"],entry["lesson"],entry["assessment"]
        units.append({"id":unit.id,"order_index":unit.order_index,"unit_type":unit.unit_type,"state":entry["state"],
            "lesson":None if lesson is None else {"id":lesson.id,"lesson_number":lesson.lesson_number,"title":lesson.title,"status":lesson.status},
            "assessment":None if assessment is None else {"id":assessment.id,"title":assessment.title,"type":assessment.type,"status":assessment.status}})
    return {"hsk":{"id":level.id,"level_number":level.level_number,"title":level.title},"units":units}


async def get_hsk_progress(session: AsyncSession,user_id: UUID,hsk_id: UUID):
    data=await get_curriculum(session,user_id,hsk_id)
    _,states,_,_,_=await progress_service.progression_snapshot(session,user_id)
    active=[entry for entry in states.get(hsk_id,[]) if entry["active"]]
    completed=sum(1 for entry in active if entry["complete"])
    return {**data,"progress_percentage":round(100*completed/len(active),2) if active else 0.0}


async def get_lesson(session: AsyncSession,user_id: UUID,lesson_id: UUID):
    lesson=await progress_service.require_lesson_access(session,user_id,lesson_id)
    await progress_service.start_lesson(session,user_id,lesson_id)
    vocab=await repository.lesson_vocabulary(session,lesson_id)
    grammar=await repository.lesson_grammar(session,lesson_id)
    assessments=await repository.lesson_assessments(session,lesson_id)
    return {
        "id":lesson.id,"hsk_level_id":lesson.hsk_level_id,"lesson_number":lesson.lesson_number,
        "title":lesson.title,"description":lesson.description,
        "vocabulary":[{"id":link.id,"order_index":link.order_index,"note":link.note,"example":link.example,
            "item":{"id":item.id,"hanzi":item.hanzi,"pinyin":item.pinyin,
                "vietnamese_meaning":item.vietnamese_meaning,"part_of_speech":item.part_of_speech}}
            for link,item in vocab],
        "grammar":[{"id":link.id,"order_index":link.order_index,"note":link.note,"example":link.example,
            "item":{"id":item.id,"name":item.name,"structure":item.structure,
                "explanation":item.explanation,"usage":item.usage}}
            for link,item in grammar],
        "assessment_ids":assessments,
    }


# Admin use cases for HSK, curriculum ordering, lessons, and shared lesson content.

def fail(code: str, message: str, status: int = 404):
    raise ApplicationError(code, message, status_code=status)

def _dump(obj, fields): return {field: getattr(obj, field) for field in fields}

async def admin_get_lesson(session, lesson_id, *, for_update=False):
    return await curriculum_repository.admin_get_lesson(session,lesson_id,for_update=for_update)


async def materialize_generation_scope(session, request):
    """Copy selected curriculum rows into scalar-only generation DTO data."""
    from app.ai.generation.errors import AssessmentGenerationScopeInvalid
    from app.ai.generation.schemas import LessonExerciseGenerationRequest

    if isinstance(request, LessonExerciseGenerationRequest):
        lesson, vocab_rows, grammar_rows = await curriculum_repository.admin_generation_lesson(session, request.lesson_id)
        if lesson is None or (not vocab_rows and not grammar_rows):
            raise AssessmentGenerationScopeInvalid
        lesson_data = {"id": str(lesson.id), "title": lesson.title, "description": lesson.description,
                       "lesson_number": lesson.lesson_number, "hsk_level_id": str(lesson.hsk_level_id)}
        vocabulary = [{"source_ref": f"vocab:{item.id}", "lesson": lesson_data,
                       "hanzi": item.hanzi, "pinyin": item.pinyin, "vietnamese_meaning": item.vietnamese_meaning,
                       "part_of_speech": item.part_of_speech, "note": link.note, "example": link.example,
                       "order_index": link.order_index} for link, item in vocab_rows]
        grammar = [{"source_ref": f"grammar:{item.id}", "lesson": lesson_data,
                    "name": item.name, "structure": item.structure, "explanation": item.explanation,
                    "usage": item.usage, "note": link.note, "example": link.example,
                    "order_index": link.order_index} for link, item in grammar_rows]
        return {
            "assessment_type": request.type, "lesson_id": request.lesson_id, "lesson_ids": (request.lesson_id,),
            "vocabulary_ids": tuple(item.id for _, item in vocab_rows), "grammar_ids": tuple(item.id for _, item in grammar_rows),
            "title": request.title or f"AI Draft — {lesson.title}", "description": request.description,
            "pass_threshold": request.pass_threshold,
            "payload": {"scope": {"lesson": lesson_data}, "vocabulary": vocabulary, "grammar": grammar},
            "allowed_source_refs": frozenset(item["source_ref"] for item in vocabulary + grammar),
        }

    lesson_rows, vocab_rows, grammar_rows = await curriculum_repository.admin_generation_periodic_scope(
        session, request.lesson_ids, request.vocabulary_ids, request.grammar_ids
    )
    if {row.id for row in lesson_rows} != set(request.lesson_ids):
        raise AssessmentGenerationScopeInvalid
    vocabulary_by_id = {}
    for link, item, lesson in vocab_rows:
        record = vocabulary_by_id.setdefault(item.id, {
            "source_ref": f"vocab:{item.id}", "hanzi": item.hanzi, "pinyin": item.pinyin,
            "vietnamese_meaning": item.vietnamese_meaning, "part_of_speech": item.part_of_speech,
            "lessons": [], "lesson_associations": [],
        })
        record["lessons"].append({"id": str(lesson.id), "title": lesson.title, "lesson_number": lesson.lesson_number})
        record["lesson_associations"].append({"note": link.note, "example": link.example, "order_index": link.order_index})
    grammar_by_id = {}
    for link, item, lesson in grammar_rows:
        record = grammar_by_id.setdefault(item.id, {
            "source_ref": f"grammar:{item.id}", "name": item.name, "structure": item.structure,
            "explanation": item.explanation, "usage": item.usage,
            "lessons": [], "lesson_associations": [],
        })
        record["lessons"].append({"id": str(lesson.id), "title": lesson.title, "lesson_number": lesson.lesson_number})
        record["lesson_associations"].append({"note": link.note, "example": link.example, "order_index": link.order_index})
    if set(vocabulary_by_id) != set(request.vocabulary_ids) or set(grammar_by_id) != set(request.grammar_ids):
        raise AssessmentGenerationScopeInvalid
    lesson_data = [{"id": str(row.id), "title": row.title, "description": row.description,
                    "lesson_number": row.lesson_number, "hsk_level_id": str(row.hsk_level_id)} for row in lesson_rows]
    vocabulary = [vocabulary_by_id[ident] for ident in request.vocabulary_ids]
    grammar = [grammar_by_id[ident] for ident in request.grammar_ids]
    return {
        "assessment_type": request.type, "lesson_id": None, "lesson_ids": tuple(request.lesson_ids),
        "vocabulary_ids": tuple(request.vocabulary_ids), "grammar_ids": tuple(request.grammar_ids),
        "title": request.title or "AI Draft — Periodic Test", "description": request.description,
        "pass_threshold": request.pass_threshold,
        "payload": {"scope": {"lessons": lesson_data}, "vocabulary": vocabulary, "grammar": grammar},
        "allowed_source_refs": frozenset(item["source_ref"] for item in vocabulary + grammar),
    }

async def _require_admin_lesson_content_mutable(session,lesson_id):
    lesson=await curriculum_repository.admin_get_lesson(session,lesson_id,for_update=True)
    if lesson is None:fail("NOT_FOUND","Lesson was not found")
    if lesson.status=="ARCHIVED":fail("LESSON_CONTENT_IMMUTABLE","Archived lesson content cannot be changed",409)
    return lesson

async def admin_levels(session):
    return [_dump(x, ("id", "level_number", "title", "description", "order_index")) for x in await curriculum_repository.admin_hsk_levels(session)]


async def admin_patch_level(session, ident, body):
    if set(body) - {"title", "description"}: fail("INVALID_FIELDS", "Only display metadata may be changed", 422)
    async with session.begin_nested():
        row = await curriculum_repository.admin_update_hsk(session,ident,body)
        if row is None:fail("NOT_FOUND","HSK level was not found")
    await session.commit(); return _dump(row, ("id", "level_number", "title", "description", "order_index"))


async def admin_curriculum(session, hsk_id):
    if await curriculum_repository.admin_get_hsk(session,hsk_id) is None:fail("NOT_FOUND","HSK level was not found")
    rows = await curriculum_repository.admin_curriculum(session,hsk_id)
    return [{"id": u.id, "order_index": u.order_index, "unit_type": u.unit_type,
             "lesson_id": u.lesson_id, "assessment_id": u.assessment_id,
             "lesson_title": lesson.title if lesson else None, "assessment_title": assess.title if assess else None} for u, lesson, assess in rows]


async def admin_replace_curriculum(session, hsk_id, units):
    if not isinstance(units, list) or any(not isinstance(u, dict) or set(u) != {"unit_type", "target_id", "order_index"} for u in units): fail("INVALID_CURRICULUM", "Curriculum payload is invalid", 422)
    if sorted(u["order_index"] for u in units) != list(range(1, len(units)+1)): fail("INVALID_CURRICULUM", "Order indexes must be unique and consecutive", 422)
    try: targets = [(u["unit_type"], UUID(str(u["target_id"]))) for u in units]
    except (ValueError, TypeError, KeyError): fail("INVALID_CURRICULUM", "Curriculum target identifier is invalid", 422)
    if len(set(targets)) != len(targets): fail("INVALID_CURRICULUM", "Duplicate curriculum target", 422)
    async with session.begin_nested():
        if await curriculum_repository.admin_get_hsk(session,hsk_id,for_update=True) is None:fail("NOT_FOUND","HSK level was not found")
        for unit_type, target in targets:
            if unit_type == "LESSON":
                item = await curriculum_repository.get_lesson(session,target)
                if item is None:fail("NOT_FOUND","Lesson target was not found")
                if item.hsk_level_id != hsk_id or item.status == "ARCHIVED": fail("INVALID_CURRICULUM_TARGET", "Lesson target is invalid", 422)
            elif unit_type == "PERIODIC_TEST":
                from app.exercise import service as exercise_service
                item = await exercise_service.admin_get_assessment(session,target)
                if item is None:fail("NOT_FOUND","Assessment target was not found")
                if item.type != "PERIODIC_TEST" or item.status == "ARCHIVED": fail("INVALID_CURRICULUM_TARGET", "Periodic test target is invalid", 422)
            else: fail("INVALID_CURRICULUM", "Unit type is invalid", 422)
        normalized=[{**u,"target_id":UUID(str(u["target_id"]))} for u in units]
        await curriculum_repository.admin_replace_curriculum(session,hsk_id,normalized)
    await session.commit(); return await admin_curriculum(session, hsk_id)


async def admin_lessons(session, page=1, page_size=20, status=None, hsk_level_id=None):
    total,rows=await curriculum_repository.admin_lessons_page(session,page,page_size,status,hsk_level_id)
    return {"items":[_dump(x,("id","hsk_level_id","lesson_number","title","description","status","published_at")) for x in rows],
        "page":page,"page_size":page_size,"total":total}


async def admin_create_lesson(session, body):
    if set(body) - {"hsk_level_id", "lesson_number", "title", "description"} or not {"hsk_level_id", "lesson_number", "title"} <= set(body): fail("INVALID_FIELDS", "Lesson payload is invalid", 422)
    async with session.begin_nested():
        try: hsk_id=UUID(str(body["hsk_level_id"]))
        except (ValueError,TypeError): fail("INVALID_LESSON","HSK identifier is invalid",422)
        if await curriculum_repository.admin_get_hsk(session,hsk_id) is None:fail("NOT_FOUND","HSK level was not found")
        fields=dict(body); fields["hsk_level_id"]=hsk_id
        row = await curriculum_repository.admin_create_lesson(session,fields)
    await session.commit(); return _dump(row, ("id", "hsk_level_id", "lesson_number", "title", "description", "status", "published_at"))


async def admin_patch_lesson(session, ident, body):
    if set(body) - {"title", "description"}: fail("INVALID_FIELDS", "Only lesson display content may be edited", 422)
    async with session.begin_nested():
        row = await curriculum_repository.admin_get_lesson(session,ident,for_update=True)
        if row is None:fail("NOT_FOUND","Lesson was not found")
        if row.status == "ARCHIVED": fail("LESSON_IMMUTABLE", "Archived lesson metadata cannot be edited", 409)
        row=await curriculum_repository.admin_update_lesson(session,row,body)
    await session.commit(); return _dump(row, ("id", "hsk_level_id", "lesson_number", "title", "description", "status", "published_at"))


async def admin_lesson_transition(session, ident, action):
    async with session.begin_nested():
        row = await curriculum_repository.admin_get_lesson(session,ident,for_update=True)
        if row is None:fail("NOT_FOUND","Lesson was not found")
        expected, target = (("DRAFT", "PUBLISHED") if action == "publish" else ("PUBLISHED", "ARCHIVED"))
        if row.status != expected: fail("INVALID_LIFECYCLE_TRANSITION", "Lesson lifecycle transition is invalid", 409)
        row=await curriculum_repository.admin_transition_lesson(session,row,target,datetime.now(UTC) if action=="publish" else None)
    await session.commit(); return _dump(row, ("id", "hsk_level_id", "lesson_number", "title", "description", "status", "published_at"))


async def admin_lesson_items(session, lesson_id, kind):
    if await curriculum_repository.get_lesson(session,lesson_id) is None:fail("NOT_FOUND","Lesson was not found")
    if kind == "vocabulary":
        rows = await curriculum_repository.admin_list_lesson_content(session,lesson_id,kind)
        return [{"id": a.id, "order_index": a.order_index, "note": a.note, "example": a.example, "vocabulary_id": v.id, "hanzi": v.hanzi, "pinyin": v.pinyin, "vietnamese_meaning": v.vietnamese_meaning, "part_of_speech": v.part_of_speech} for a,v in rows]
    rows = await curriculum_repository.admin_list_lesson_content(session,lesson_id,kind)
    return [{"id": a.id, "order_index": a.order_index, "note": a.note, "example": a.example, "grammar_id": g.id, "name": g.name, "structure": g.structure, "explanation": g.explanation, "usage": g.usage} for a,g in rows]


async def admin_attach_item(session, lesson_id, kind, body):
    allowed_shared = {"vocabulary": {"hanzi", "pinyin", "vietnamese_meaning", "part_of_speech"}, "grammar": {"name", "structure", "explanation", "usage"}}[kind]
    required_shared = {"vocabulary": {"hanzi", "pinyin", "vietnamese_meaning"}, "grammar": {"name", "explanation"}}[kind]
    shared_key = "vocabulary_id" if kind == "vocabulary" else "grammar_id"
    assoc_fields = {"order_index", "note", "example"}
    if set(body) - (assoc_fields | allowed_shared | {shared_key}) or "order_index" not in body: fail("INVALID_FIELDS", "Association payload is invalid", 422)
    has_id = shared_key in body and body[shared_key] is not None
    supplied_shared = set(body) & allowed_shared
    has_new = bool(supplied_shared)
    if has_id == has_new or (shared_key in body and body[shared_key] is None) or (has_new and not required_shared <= supplied_shared):
        fail("INVALID_ITEM_MODE", "Provide exactly one existing-item or new-item mode", 422)
    async with session.begin_nested():
        await _require_admin_lesson_content_mutable(session,lesson_id)
        shared_id=None
        if has_id:
            try:shared_id=UUID(str(body[shared_key]))
            except (ValueError,TypeError):fail("INVALID_ITEM_MODE","Shared item identifier is invalid",422)
        link,shared=await curriculum_repository.admin_attach_lesson_content(session,lesson_id,kind,shared_id,
            {k:body[k] for k in allowed_shared if k in body} if has_new else {},{k:body[k] for k in assoc_fields if k in body})
        if shared is None:fail("NOT_FOUND","Shared item was not found")
    await session.commit(); return {"id": link.id, "lesson_id": lesson_id, shared_key: shared.id, **{k: getattr(link,k) for k in assoc_fields}, **{k: getattr(shared,k) for k in allowed_shared}}


async def admin_patch_item(session, lesson_id, link_id, kind, body):
    shared_key = "vocabulary_id" if kind=="vocabulary" else "grammar_id"
    shared_fields = {"hanzi", "pinyin", "vietnamese_meaning", "part_of_speech"} if kind == "vocabulary" else {"name", "structure", "explanation", "usage"}
    if set(body) - ({"order_index", "note", "example"} | shared_fields): fail("INVALID_FIELDS", "Item update fields are invalid", 422)
    async with session.begin_nested():
        await _require_admin_lesson_content_mutable(session,lesson_id)
        link = await curriculum_repository.admin_get_lesson_content_link(session,lesson_id,link_id,kind,for_update=True)
        if link is None: fail("NOT_FOUND", "Lesson item was not found")
        shared = await curriculum_repository.admin_get_shared_content(session,getattr(link,shared_key),kind)
        association_fields={key:value for key,value in body.items() if key not in shared_fields}
        canonical_fields={key:value for key,value in body.items() if key in shared_fields}
        await curriculum_repository.admin_update_lesson_content(session,link,shared,kind,association_fields,canonical_fields)
    await session.commit(); return {"id": link.id, "lesson_id": lesson_id, shared_key: shared.id, **{k: getattr(link,k) for k in ("order_index", "note", "example")}, **{k: getattr(shared,k) for k in shared_fields}}


async def admin_detach_item(session, lesson_id, link_id, kind):
    async with session.begin_nested():
        lesson=await _require_admin_lesson_content_mutable(session,lesson_id)
        if lesson.status!="DRAFT":fail("LESSON_CONTENT_DETACH_DRAFT_ONLY","Lesson content can only be detached from draft lessons",409)
        link = await curriculum_repository.admin_get_lesson_content_link(session,lesson_id,link_id,kind,for_update=True)
        if link is None: fail("NOT_FOUND", "Lesson item was not found")
        historical = await curriculum_repository.admin_content_has_history(session,link_id,kind)
        if historical: fail("ITEM_HAS_LEARNER_HISTORY", "Lesson item has learner progress history", 409)
        await curriculum_repository.admin_delete_lesson_content(session,link)
    await session.commit(); return {"detached": True}


