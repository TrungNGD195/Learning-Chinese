from uuid import UUID

from fastapi import APIRouter, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.admin import service
from app.admin.schemas import (AdminCurriculumUnitResponse, AdminStatsResponse, AssessmentAdminPageResponse, AssessmentAdminResponse,
    AssessmentCreateRequest, AssessmentPatchRequest, AssessmentGenerationRequest, AssessmentGenerationDraftResponse,
    GrammarAttachRequest, GrammarPatchRequest,
    HSKPatchRequest, HSKAdminResponse, LessonAdminPageResponse, LessonAdminResponse, LessonContentAdminResponse,
    LessonCreateRequest, LessonPatchRequest, QuestionAdminResponse, QuestionCreateRequest,
    QuestionPatchRequest, VocabularyAttachRequest, VocabularyPatchRequest, CurriculumPutRequest)
from app.database.session import get_db_session
from app.auth.current_user import require_admin
from app.core.config import get_settings
from app.database.models import User
from app.ingestion.schemas import (
    DocumentAdminDetailResponse,
    DocumentAdminPageResponse,
    DocumentRawIngestionResponse,
)
from app.ingestion.service import (
    get_admin_document_detail,
    ingest_document,
    list_admin_documents,
)
from app.ingestion.storage import LocalFileStorage
from app.ingestion.orchestrator import IngestionOrchestrator
from app.ingestion.transformation.models import TransformedDocument
from fastapi import File, Form, UploadFile

router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])


@router.get("/documents", response_model=DocumentAdminPageResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
):
    return await list_admin_documents(session, page=page, page_size=page_size)


@router.get("/documents/{document_id}", response_model=DocumentAdminDetailResponse)
async def get_document_detail(
    document_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    return await get_admin_document_detail(session, document_id)


@router.post("/documents", status_code=201, response_model=DocumentRawIngestionResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    source_category: str = Form(...),
    source_origin: str = Form(...),
    source_language: str = Form(...),
    usage_rights_note: str | None = Form(default=None),
    domain_allowed: bool = Form(...),
    current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
):
    settings = get_settings()
    return await ingest_document(
        session=session, settings=settings,
        storage=LocalFileStorage(settings.document_storage_root),
        admin_id=current_admin.id, upload=file, title=title,
        source_category=source_category, source_origin=source_origin,
        source_language=source_language, usage_rights_note=usage_rights_note,
        domain_allowed=domain_allowed,
    )


@router.post("/documents/{document_id}/process")
async def process_document(document_id: UUID, session: AsyncSession = Depends(get_db_session)):
    settings = get_settings()
    return await IngestionOrchestrator(
        session, LocalFileStorage(settings.document_storage_root)
    ).process_document(document_id)


@router.get("/documents/{document_id}/preview", response_model=TransformedDocument)
async def preview_document(document_id: UUID, session: AsyncSession = Depends(get_db_session)):
    settings = get_settings()
    return await IngestionOrchestrator(
        session, LocalFileStorage(settings.document_storage_root)
    ).preview_document(document_id)


@router.post("/documents/{document_id}/approve")
async def approve_document(
    document_id: UUID, current_admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
):
    settings = get_settings()
    return await IngestionOrchestrator(
        session, LocalFileStorage(settings.document_storage_root)
    ).approve_document(document_id, current_admin.id)


@router.post("/documents/{document_id}/reject")
async def reject_document(document_id: UUID, session: AsyncSession = Depends(get_db_session)):
    settings = get_settings()
    return await IngestionOrchestrator(
        session, LocalFileStorage(settings.document_storage_root)
    ).reject_document(document_id)


@router.post("/documents/{document_id}/knowledge/retry")
async def retry_document_knowledge(document_id: UUID, session: AsyncSession = Depends(get_db_session)):
    settings = get_settings()
    return await IngestionOrchestrator(
        session, LocalFileStorage(settings.document_storage_root)
    ).retry_document_knowledge(document_id)


@router.get("/hsk-levels",response_model=list[HSKAdminResponse])
async def hsk_levels(session: AsyncSession = Depends(get_db_session)): return await service.levels(session)

@router.patch("/hsk-levels/{hsk_id}",response_model=HSKAdminResponse)
async def patch_hsk(hsk_id: UUID, payload: HSKPatchRequest, session: AsyncSession = Depends(get_db_session)): return await service.patch_level(session,hsk_id,payload.model_dump(exclude_unset=True))

@router.get("/hsk-levels/{hsk_id}/curriculum",response_model=list[AdminCurriculumUnitResponse])
async def get_curriculum(hsk_id: UUID, session: AsyncSession = Depends(get_db_session)): return await service.curriculum(session,hsk_id)

@router.put("/hsk-levels/{hsk_id}/curriculum",response_model=list[AdminCurriculumUnitResponse])
async def put_curriculum(hsk_id: UUID, payload: CurriculumPutRequest, session: AsyncSession = Depends(get_db_session)):
    return await service.replace_curriculum(session,hsk_id,[unit.model_dump(mode="json") for unit in payload.units])

@router.get("/lessons",response_model=LessonAdminPageResponse)
async def lessons(status: str | None = None, hsk_level_id: UUID | None = None,
                  page: int = Query(1,ge=1), page_size: int = Query(20,ge=1,le=100),
                  session: AsyncSession = Depends(get_db_session)):
    return await service.lessons(session,page,page_size,status,hsk_level_id)

@router.get("/lessons/{lesson_id}",response_model=LessonAdminResponse)
async def get_lesson(lesson_id: UUID, session: AsyncSession = Depends(get_db_session)):
    return await service.lesson_detail(session, lesson_id)

@router.post("/lessons",status_code=201,response_model=LessonAdminResponse)
async def create_lesson(payload: LessonCreateRequest,session: AsyncSession=Depends(get_db_session)): return await service.create_lesson(session,payload.model_dump(mode="json"))

@router.patch("/lessons/{lesson_id}",response_model=LessonAdminResponse)
async def patch_lesson(lesson_id:UUID,payload:LessonPatchRequest,session:AsyncSession=Depends(get_db_session)): return await service.patch_lesson(session,lesson_id,payload.model_dump(exclude_unset=True))

@router.post("/lessons/{lesson_id}/publish",response_model=LessonAdminResponse)
async def publish_lesson(lesson_id:UUID,session:AsyncSession=Depends(get_db_session)): return await service.lesson_transition(session,lesson_id,"publish")


@router.post("/lessons/{lesson_id}/knowledge/retry")
async def retry_lesson_knowledge(lesson_id: UUID, session: AsyncSession = Depends(get_db_session)):
    settings = get_settings()
    return await IngestionOrchestrator(
        session, LocalFileStorage(settings.document_storage_root)
    ).retry_lesson_knowledge(lesson_id)

@router.post("/lessons/{lesson_id}/archive",response_model=LessonAdminResponse)
async def archive_lesson(lesson_id:UUID,session:AsyncSession=Depends(get_db_session)): return await service.lesson_transition(session,lesson_id,"archive")

def _lesson_item_routes(kind: str):
    request_model=VocabularyAttachRequest if kind=="vocabulary" else GrammarAttachRequest
    patch_model=VocabularyPatchRequest if kind=="vocabulary" else GrammarPatchRequest
    @router.get(f"/lessons/{{lesson_id}}/{kind}",response_model=list[LessonContentAdminResponse])
    async def get_items(lesson_id:UUID,session:AsyncSession=Depends(get_db_session)): return await service.lesson_items(session,lesson_id,kind)
    @router.post(f"/lessons/{{lesson_id}}/{kind}",status_code=201,response_model=LessonContentAdminResponse)
    async def attach(lesson_id:UUID,payload:request_model,session:AsyncSession=Depends(get_db_session)): return await service.attach_item(session,lesson_id,kind,payload.model_dump(exclude_unset=True,mode="json"))
    @router.patch(f"/lessons/{{lesson_id}}/{kind}/{{item_id}}",response_model=LessonContentAdminResponse)
    async def patch(lesson_id:UUID,item_id:UUID,payload:patch_model,session:AsyncSession=Depends(get_db_session)): return await service.patch_item(session,lesson_id,item_id,kind,payload.model_dump(exclude_unset=True,mode="json"))
    @router.delete(f"/lessons/{{lesson_id}}/{kind}/{{item_id}}")
    async def detach(lesson_id:UUID,item_id:UUID,session:AsyncSession=Depends(get_db_session)): return await service.detach_item(session,lesson_id,item_id,kind)

_lesson_item_routes("vocabulary")
_lesson_item_routes("grammar")

@router.get("/assessments",response_model=AssessmentAdminPageResponse)
async def assessments(status:str|None=None,assessment_type:str|None=None,
                      page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),
                      session:AsyncSession=Depends(get_db_session)):
    return await service.assessments(session,page,page_size,status,assessment_type)


@router.post("/assessments/generate-draft", status_code=201, response_model=AssessmentGenerationDraftResponse)
async def generate_assessment_draft(payload: AssessmentGenerationRequest, session: AsyncSession = Depends(get_db_session)):
    return await service.generate_assessment_draft(session, payload)

@router.get("/assessments/{assessment_id}",response_model=AssessmentAdminResponse)
async def get_assessment(assessment_id: UUID, session: AsyncSession = Depends(get_db_session)):
    return await service.assessment_detail(session, assessment_id)

@router.post("/assessments",status_code=201,response_model=AssessmentAdminResponse)
async def create_assessment(payload:AssessmentCreateRequest,session:AsyncSession=Depends(get_db_session)): return await service.create_assessment(session,payload.model_dump(exclude_unset=True,mode="json"))

@router.patch("/assessments/{assessment_id}",response_model=AssessmentAdminResponse)
async def patch_assessment(assessment_id:UUID,payload:AssessmentPatchRequest,session:AsyncSession=Depends(get_db_session)): return await service.patch_assessment(session,assessment_id,payload.model_dump(exclude_unset=True,mode="json"))

@router.get("/assessments/{assessment_id}/questions",response_model=list[QuestionAdminResponse])
async def questions(assessment_id:UUID,session:AsyncSession=Depends(get_db_session)): return await service.questions(session,assessment_id)

@router.post("/assessments/{assessment_id}/questions",status_code=201,response_model=QuestionAdminResponse)
async def create_question(assessment_id:UUID,payload:QuestionCreateRequest,session:AsyncSession=Depends(get_db_session)): return await service.create_question(session,assessment_id,payload.model_dump(exclude_unset=True,mode="json"))

@router.patch("/assessments/{assessment_id}/questions/{question_id}",response_model=QuestionAdminResponse)
async def patch_question(assessment_id:UUID,question_id:UUID,payload:QuestionPatchRequest,session:AsyncSession=Depends(get_db_session)): return await service.patch_question(session,assessment_id,question_id,payload.model_dump(exclude_unset=True,mode="json"))

@router.delete("/assessments/{assessment_id}/questions/{question_id}")
async def delete_question(assessment_id:UUID,question_id:UUID,session:AsyncSession=Depends(get_db_session)): return await service.delete_question(session,assessment_id,question_id)

@router.post("/assessments/{assessment_id}/submit-review",response_model=AssessmentAdminResponse)
async def submit_review(assessment_id:UUID,session:AsyncSession=Depends(get_db_session)): return await service.assessment_transition(session,assessment_id,"submit-review")

@router.post("/assessments/{assessment_id}/publish",response_model=AssessmentAdminResponse)
async def publish_assessment(assessment_id:UUID,session:AsyncSession=Depends(get_db_session)): return await service.assessment_transition(session,assessment_id,"publish")

@router.post("/assessments/{assessment_id}/archive",response_model=AssessmentAdminResponse)
async def archive_assessment(assessment_id:UUID,session:AsyncSession=Depends(get_db_session)): return await service.assessment_transition(session,assessment_id,"archive")

@router.get("/stats",response_model=AdminStatsResponse)
async def stats(session:AsyncSession=Depends(get_db_session)): return await service.statistics(session)
