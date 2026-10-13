import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.admin import repository as admin_repository
from app.curriculum import service as curriculum_service
from app.exercise import service as exercise_service
from app.ai.generation.errors import (
    AI_GENERATION_INPUT_TOO_LARGE,
    AI_GENERATION_INVALID_RESPONSE,
    AI_GENERATION_SCHEMA_INVALID,
    AssessmentGenerationInvalidOutput,
    AssessmentGenerationScopeInvalid,
    StructuredAssessmentGenerationProviderError,
)
from app.ai.generation.factory import get_assessment_generation_provider
from app.ai.generation.schemas import MaterializedGenerationScope
from app.ai.generation.service import AssessmentGenerationService, validate_and_map_output
from app.core.config import get_settings
from app.core.errors import ApplicationError

logger = logging.getLogger("app.admin.assessment_generation")


async def levels(session): return await curriculum_service.admin_levels(session)
async def patch_level(session, ident, body): return await curriculum_service.admin_patch_level(session,ident,body)
async def curriculum(session, hsk_id): return await curriculum_service.admin_curriculum(session,hsk_id)
async def replace_curriculum(session, hsk_id, units): return await curriculum_service.admin_replace_curriculum(session,hsk_id,units)
async def lessons(session, page=1, page_size=20, status=None, hsk_level_id=None): return await curriculum_service.admin_lessons(session,page,page_size,status,hsk_level_id)
async def lesson_detail(session, lesson_id):
    lesson = await curriculum_service.admin_get_lesson(session, lesson_id)
    if lesson is None: curriculum_service.fail("NOT_FOUND", "Lesson was not found")
    return {field: getattr(lesson, field) for field in ("id", "hsk_level_id", "lesson_number", "title", "description", "status", "published_at")}
async def create_lesson(session, body): return await curriculum_service.admin_create_lesson(session,body)
async def patch_lesson(session, ident, body): return await curriculum_service.admin_patch_lesson(session,ident,body)
async def lesson_transition(session, ident, action):
    # The curriculum use case commits PUBLISHED before this post-commit pipeline starts.
    result = await curriculum_service.admin_lesson_transition(session, ident, action)
    if action == "publish":
        from app.core.config import get_settings
        from app.ingestion.orchestrator import process_published_lesson
        from app.ingestion.storage import LocalFileStorage
        settings = get_settings()
        await process_published_lesson(
            session, ident, LocalFileStorage(settings.document_storage_root)
        )
    return result
async def lesson_items(session, lesson_id, kind): return await curriculum_service.admin_lesson_items(session,lesson_id,kind)
async def attach_item(session, lesson_id, kind, body): return await curriculum_service.admin_attach_item(session,lesson_id,kind,body)
async def patch_item(session, lesson_id, link_id, kind, body): return await curriculum_service.admin_patch_item(session,lesson_id,link_id,kind,body)
async def detach_item(session, lesson_id, link_id, kind): return await curriculum_service.admin_detach_item(session,lesson_id,link_id,kind)
async def assessments(session, page=1, page_size=20, status=None, assessment_type=None): return await exercise_service.admin_assessments(session,page,page_size,status,assessment_type)
async def assessment_detail(session, assessment_id):
    assessment = await exercise_service.admin_get_assessment(session, assessment_id)
    if assessment is None: exercise_service.fail("NOT_FOUND", "Assessment was not found")
    return {field: getattr(assessment, field) for field in ("id", "type", "lesson_id", "title", "description", "status", "pass_threshold", "published_at")}
async def create_assessment(session, body): return await exercise_service.admin_create_assessment(session,body)
async def patch_assessment(session, ident, body): return await exercise_service.admin_patch_assessment(session,ident,body)
async def assessment_transition(session, ident, action): return await exercise_service.admin_assessment_transition(session,ident,action)
async def questions(session, assessment_id): return await exercise_service.admin_questions(session,assessment_id)
async def create_question(session, assessment_id, body): return await exercise_service.admin_create_question(session,assessment_id,body)
async def patch_question(session, assessment_id, question_id, body): return await exercise_service.admin_patch_question(session,assessment_id,question_id,body)
async def delete_question(session, assessment_id, question_id): return await exercise_service.admin_delete_question(session,assessment_id,question_id)


async def generate_assessment_draft(session, request):
    settings = get_settings()
    try:
        scope_data = await curriculum_service.materialize_generation_scope(session, request)
    except AssessmentGenerationScopeInvalid:
        await session.rollback()
        logger.warning("ai_assessment_generation_scope_rejected", extra={
            "feature": "ai_assessment_generation", "generation_kind": request.type,
            "requested_question_count": request.question_count, "allowed_types": tuple(request.allowed_types),
            "difficulty": request.difficulty, "error_code": "INVALID_GENERATION_SCOPE",
        })
        raise ApplicationError("INVALID_GENERATION_SCOPE", "Assessment generation scope is invalid", status_code=422) from None
    except Exception:
        await session.rollback()
        raise
    # Authentication and the materialization reads share the request-scoped session.
    # End that read transaction before crossing the provider boundary.
    await session.rollback()
    if session.in_transaction():
        raise RuntimeError("generation provider cannot run inside a database transaction")
    scope = MaterializedGenerationScope(
        assessment_type=scope_data["assessment_type"], lesson_id=scope_data["lesson_id"],
        lesson_ids=scope_data["lesson_ids"], vocabulary_ids=scope_data["vocabulary_ids"],
        grammar_ids=scope_data["grammar_ids"], title=scope_data["title"],
        description=scope_data["description"], pass_threshold=scope_data["pass_threshold"],
        payload=scope_data["payload"], allowed_source_refs=scope_data["allowed_source_refs"],
    )
    provider_result = None
    try:
        generation = AssessmentGenerationService(get_assessment_generation_provider(), settings)
        provider_result = await generation.generate(request, scope)
        mapped = validate_and_map_output(
            provider_result, request=request, scope=scope,
            domain_validator=exercise_service.admin_validate_generated_question,
        )
    except AssessmentGenerationInvalidOutput:
        logger.warning("ai_assessment_generation_output_rejected", extra={
            "feature": "ai_assessment_generation", "generation_kind": request.type,
            "requested_question_count": request.question_count, "allowed_types": tuple(request.allowed_types),
            "difficulty": request.difficulty, "prompt_version": "v1",
            "error_code": "AI_GENERATION_INVALID_OUTPUT",
        })
        raise ApplicationError("AI_GENERATION_INVALID_OUTPUT", "AI assessment generation returned an invalid result", status_code=502) from None
    except StructuredAssessmentGenerationProviderError as exc:
        if exc.code == AI_GENERATION_INPUT_TOO_LARGE:
            raise ApplicationError("AI_GENERATION_INPUT_TOO_LARGE", "Assessment generation input is too large", status_code=422) from None
        if exc.code in {AI_GENERATION_INVALID_RESPONSE, AI_GENERATION_SCHEMA_INVALID}:
            raise ApplicationError("AI_GENERATION_INVALID_OUTPUT", "AI assessment generation returned an invalid result", status_code=502) from None
        raise ApplicationError("AI_GENERATION_UNAVAILABLE", "AI assessment generation is not available", status_code=503) from None

    assessment_fields = {
        "type": scope.assessment_type, "lesson_id": scope.lesson_id, "title": scope.title,
        "description": scope.description, "pass_threshold": scope.pass_threshold,
    }
    persistence_scope = {"type": scope.assessment_type, "lesson_ids": scope.lesson_ids,
                         "vocabulary_ids": scope.vocabulary_ids, "grammar_ids": scope.grammar_ids}
    try:
        response = await exercise_service.persist_generated_assessment_draft(
            session, assessment_fields=assessment_fields, scope=persistence_scope, questions=mapped
        )
    except Exception:
        await session.rollback()
        logger.error("ai_assessment_generation_persistence_failed", extra={
            "feature": "ai_assessment_generation", "provider": "openai", "model": settings.llm_model,
            "prompt_version": "v1", "generation_kind": request.type,
            "requested_question_count": request.question_count, "allowed_types": tuple(request.allowed_types),
            "difficulty": request.difficulty, "error_code": "AI_GENERATION_PERSISTENCE_FAILED",
        })
        raise ApplicationError("AI_GENERATION_PERSISTENCE_FAILED", "Generated assessment draft could not be saved", status_code=500) from None
    logger.info("ai_assessment_generation_draft_persisted", extra={
        "feature": "ai_assessment_generation", "provider": provider_result.provider,
        "model": provider_result.model, "prompt_version": "v1", "generation_kind": request.type,
        "requested_question_count": request.question_count, "allowed_types": tuple(request.allowed_types),
        "difficulty": request.difficulty, "attempt_count": provider_result.attempt_count,
        "latency_ms": provider_result.latency_ms,
        "provider_preflight_input_tokens": provider_result.provider_preflight_input_tokens,
        "provider_usage_input_tokens": provider_result.input_tokens,
        "provider_usage_output_tokens": provider_result.output_tokens,
        "provider_usage_total_tokens": provider_result.total_tokens,
        "provider_request_id": provider_result.provider_request_id, "error_code": None,
    })
    return response


async def statistics(session):
    total,learners,avg=await admin_repository.statistics_inputs(session)
    from app.progress.service import progression_snapshot
    hsk_counts={}
    for user_id in learners:
        levels, states, _, _, current = await progression_snapshot(session,user_id)
        if current: hsk_counts[str(current.level_number)]=hsk_counts.get(str(current.level_number),0)+1
    return {"total_users":total,"users_by_current_hsk":[{"hsk_level":int(level),"users":count} for level,count in sorted(hsk_counts.items(),key=lambda x:int(x[0]))],"average_exercise_score":float(avg) if avg is not None else None}
