from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApplicationError
from app.database.models import Assessment
from app.curriculum import repository as curriculum_repository
from app.exercise import repository as exercise_repository
from app.progress import repository


def _active_target(unit_type: str, lesson, assessment) -> bool:
    if unit_type == "LESSON":
        return lesson is not None and lesson.status == "PUBLISHED"
    return assessment is not None and assessment.status == "PUBLISHED"


async def progression_snapshot(session: AsyncSession, user_id: UUID):
    levels, raw_units = await curriculum_repository.catalog_snapshot(session)
    lesson_done = await repository.learner_completion_snapshot(session,user_id)
    passed_assessments = await exercise_repository.passed_periodic_assessment_ids(session,user_id)
    pronunciation = await curriculum_repository.pronunciation_rows(session,user_id)
    all_sections_complete = bool(pronunciation) and all(progress is not None and progress.completed_at is not None for _, progress in pronunciation)
    per_hsk: dict[UUID, list[dict]] = {level.id: [] for level in levels}
    for unit, lesson, assessment in raw_units:
        complete = (
            unit.lesson_id in lesson_done if unit.unit_type == "LESSON"
            else unit.assessment_id in passed_assessments
        )
        active = _active_target(unit.unit_type, lesson, assessment)
        per_hsk.setdefault(unit.hsk_level_id, []).append({
            "unit": unit,
            "lesson": lesson,
            "assessment": assessment,
            "complete": complete,
            "active": active,
            "state": "COMPLETED" if complete else "LOCKED",
        })

    previous_hsk_complete = True
    for level in levels:
        entries = per_hsk.get(level.id, [])
        active_entries = [entry for entry in entries if entry["active"]]
        hsk_gate = all_sections_complete if level.level_number == 1 else previous_hsk_complete
        prior_complete = True
        for entry in entries:
            if entry["complete"]:
                entry["state"] = "COMPLETED"
            elif not entry["active"]:
                entry["state"] = "LOCKED"
            elif hsk_gate and prior_complete:
                entry["state"] = "AVAILABLE"
            else:
                entry["state"] = "LOCKED"
            if entry["active"] and not entry["complete"]:
                prior_complete = False
        previous_hsk_complete = bool(active_entries) and all(entry["complete"] for entry in active_entries)

    current_level = next(
        (level for level in levels if not (bool([entry for entry in per_hsk.get(level.id, []) if entry["active"]]) and all(entry["complete"] for entry in per_hsk[level.id] if entry["active"]))),
        levels[-1] if levels else None,
    )
    return levels, per_hsk, pronunciation, all_sections_complete, current_level


def learner_hsk_states(levels, states) -> list[dict]:
    result=[]
    for level in levels:
        entries=states.get(level.id,[])
        active=[entry for entry in entries if entry["active"]]
        complete=bool(active) and all(entry["complete"] for entry in active)
        state="COMPLETED" if complete else next((entry["state"] for entry in active if not entry["complete"]),"LOCKED")
        result.append({"id":level.id,"level_number":level.level_number,"title":level.title,"description":level.description,"state":state})
    return result


def _unit_payload(entry: dict) -> dict:
    unit,lesson,assessment=entry["unit"],entry["lesson"],entry["assessment"]
    return {"id":unit.id,"order_index":unit.order_index,"unit_type":unit.unit_type,"state":entry["state"],
        "lesson":None if lesson is None else {"id":lesson.id,"lesson_number":lesson.lesson_number,"title":lesson.title,"status":lesson.status},
        "assessment":None if assessment is None else {"id":assessment.id,"title":assessment.title,"type":assessment.type,"status":assessment.status}}


async def dashboard(session: AsyncSession, user_id: UUID) -> dict:
    levels, states, pronunciation, pronunciation_complete, current_level = await progression_snapshot(session, user_id)
    section_target = next((section for section, progress in pronunciation if progress is None or progress.completed_at is None), None)
    active = states.get(current_level.id, []) if current_level else []
    required = [entry for entry in active if entry["active"]]
    completed = sum(1 for entry in required if entry["complete"])
    percentage = round((completed / len(required)) * 100, 2) if required else 0.0
    current_entry = next((entry for entry in required if not entry["complete"]), None)
    current_unit = _unit_payload(current_entry) if current_entry else None
    if not pronunciation_complete and section_target:
        continue_learning = {"type": "PRONUNCIATION", "section_id": section_target.id, "code": section_target.code}
    elif current_entry and current_entry["state"] == "AVAILABLE":
        continue_learning = {
            "type": current_entry["unit"].unit_type,
            "lesson_id": current_entry["unit"].lesson_id,
            "assessment_id": current_entry["unit"].assessment_id,
        }
    else:
        continue_learning = None
    return {
        "current_hsk": None if current_level is None else {
            "id": current_level.id,
            "level_number": current_level.level_number,
            "title": current_level.title,
        },
        "current_unit": current_unit,
        "current_lesson": ({"id": current_entry["lesson"].id, "lesson_number": current_entry["lesson"].lesson_number,
                            "title": current_entry["lesson"].title, "description": current_entry["lesson"].description}
                           if current_entry and current_entry["unit"].unit_type == "LESSON" and current_entry["state"] == "AVAILABLE" else None),
        "progress_percentage": percentage,
        "continue_learning": continue_learning,
    }


async def pronunciation_list(session: AsyncSession, user_id: UUID) -> list[dict]:
    rows = await curriculum_repository.pronunciation_rows(session, user_id)
    return [{"id": section.id, "code": section.code, "title": section.title, "description": section.description,
             "order_index": section.order_index, "completed_at": progress.completed_at if progress else None}
            for section, progress in rows]


async def complete_pronunciation(session: AsyncSession, user_id: UUID, section_id: UUID) -> dict:
    section = await curriculum_repository.get_pronunciation_section(session,section_id)
    if section is None:
        raise ApplicationError("NOT_FOUND", "Pronunciation section was not found", status_code=404)
    async with session.begin_nested():
        completed_at = await repository.complete_pronunciation(session, user_id, section_id)
        levels, _, pronunciation, complete, _ = await progression_snapshot(session, user_id)
        if complete and levels:
            await repository.ensure_hsk_started(session, user_id, levels[0].id)
    await session.commit()
    return {"section_id": section_id, "completed_at": completed_at}


async def require_lesson_access(session: AsyncSession, user_id: UUID, lesson_id: UUID):
    lesson = await curriculum_repository.get_lesson(session,lesson_id)
    if lesson is None:
        raise ApplicationError("NOT_FOUND", "Lesson was not found", status_code=404)
    if lesson.status == "ARCHIVED":
        raise ApplicationError("CONTENT_ARCHIVED", "Lesson is archived", status_code=404)
    if lesson.status != "PUBLISHED":
        raise ApplicationError("NOT_FOUND", "Lesson was not found", status_code=404)
    _, states, _, _, _ = await progression_snapshot(session, user_id)
    allowed = any(
        entry["unit"].lesson_id == lesson_id and entry["state"] in {"AVAILABLE", "COMPLETED"}
        for entries in states.values() for entry in entries
    )
    if not allowed:
        raise ApplicationError("LESSON_LOCKED", "Lesson is locked", status_code=403)
    return lesson


async def start_lesson(session: AsyncSession, user_id: UUID, lesson_id: UUID) -> None:
    lesson = await require_lesson_access(session, user_id, lesson_id)
    async with session.begin_nested():
        await repository.ensure_hsk_started(session, user_id, lesson.hsk_level_id)
        await repository.ensure_lesson_started(session, user_id, lesson_id)
        vocabulary_ids,grammar_ids=await curriculum_repository.lesson_theory_ids(session,lesson_id)
        await _converge_theory_completion(session,user_id,lesson_id,vocabulary_ids,grammar_ids)
    await session.commit()


async def record_theory_view(session: AsyncSession, user_id: UUID, lesson_id: UUID, junction_id: UUID, kind: str) -> dict:
    async with session.begin_nested():
        await require_lesson_access(session, user_id, lesson_id)
        if kind == "vocabulary":
            junction = await curriculum_repository.get_owned_theory_link(session,lesson_id,junction_id,kind)
            if junction is None:
                raise ApplicationError("NOT_FOUND", "Lesson vocabulary item was not found", status_code=404)
            viewed_at = await repository.mark_vocabulary_viewed(session, user_id, junction_id)
        else:
            junction = await curriculum_repository.get_owned_theory_link(session,lesson_id,junction_id,kind)
            if junction is None:
                raise ApplicationError("NOT_FOUND", "Lesson grammar item was not found", status_code=404)
            viewed_at = await repository.mark_grammar_viewed(session, user_id, junction_id)
        vocabulary_ids,grammar_ids=await curriculum_repository.lesson_theory_ids(session,lesson_id)
        progress = await _converge_theory_completion(session,user_id,lesson_id,vocabulary_ids,grammar_ids)
        result = {"viewed_at": viewed_at, "theory_completed_at": progress.theory_completed_at}
    await session.commit()
    return result


async def lesson_progress(session: AsyncSession, user_id: UUID, lesson_id: UUID) -> dict:
    lesson = await curriculum_repository.get_lesson(session,lesson_id)
    if lesson is None:
        raise ApplicationError("NOT_FOUND", "Lesson was not found", status_code=404)
    if lesson.status == "ARCHIVED":
        # Archival removes active progression access but must not hide the learner's own history.
        pass
    else:
        await require_lesson_access(session, user_id, lesson_id)
    progress = await repository.get_lesson_progress(session, user_id, lesson_id)
    vocabulary_ids,grammar_ids=await curriculum_repository.lesson_theory_ids(session,lesson_id)
    viewed_vocabulary = await repository.viewed_vocabulary_ids(session,user_id,vocabulary_ids)
    viewed_grammar = await repository.viewed_grammar_ids(session,user_id,grammar_ids)
    return {"lesson_id": lesson_id, "started_at": progress.started_at if progress else None,
            "theory_completed_at": progress.theory_completed_at if progress else None,
            "completed_at": progress.completed_at if progress else None,
            "vocabulary": [{"id": item, "viewed": item in viewed_vocabulary} for item in vocabulary_ids],
            "grammar": [{"id": item, "viewed": item in viewed_grammar} for item in grammar_ids]}


async def progress_overview(session: AsyncSession, user_id: UUID) -> dict:
    levels, states, pronunciation, pronunciation_complete, current_level = await progression_snapshot(session, user_id)
    entries = [entry for group in states.values() for entry in group if entry["active"]]
    complete_count = sum(1 for entry in entries if entry["complete"])
    percentage = round(100 * complete_count / len(entries), 2) if entries else 0.0
    return {"current_hsk": current_level.level_number if current_level else None,
            "progress_percentage": percentage,
            "pronunciation_complete": pronunciation_complete,
            "hsk_levels": learner_hsk_states(levels,states)}


async def _converge_theory_completion(session: AsyncSession,user_id: UUID,lesson_id: UUID,vocabulary_ids,grammar_ids):
    progress=await repository.mark_theory_complete_if_ready(session,user_id,lesson_id,vocabulary_ids,grammar_ids)
    if progress.theory_completed_at is not None:
        passed=await exercise_repository.has_passing_lesson_exercise(session,user_id,lesson_id)
        await repository.update_lesson_completion(session,user_id,lesson_id,passed)
        await _materialize_hsk_progress(session,user_id)
    return progress


async def _materialize_hsk_progress(session: AsyncSession, user_id: UUID) -> None:
    # Materialize HSK lifecycle timestamps only after every current required unit is complete.
    levels, states, _, _, _ = await progression_snapshot(session, user_id)
    now = datetime.now(UTC)
    for level in levels:
        active = [entry for entry in states.get(level.id, []) if entry["active"]]
        if active and all(entry["complete"] for entry in active):
            await repository.mark_hsk_completed(session,user_id,level.id,now)
    await session.flush()


async def after_attempt(session: AsyncSession, user_id: UUID, assessment: Assessment) -> None:
    if assessment.type == "LESSON_EXERCISE" and assessment.lesson_id:
        passed=await exercise_repository.has_passing_lesson_exercise(session,user_id,assessment.lesson_id)
        await repository.update_lesson_completion(session, user_id, assessment.lesson_id,passed)
    await _materialize_hsk_progress(session, user_id)
