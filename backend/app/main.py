from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI

from app.core.config import Settings, configure_application_logging, get_settings
from app.core.errors import register_application_error_handler
from app.database.readiness import check_database_readiness
from app.progress.router import router as progress_router
from app.exercise.router import router as exercise_router
from app.admin.router import router as admin_router
from app.curriculum.router import router as curriculum_router
from app.auth.router import router as auth_router
from app.conversation.router import router as conversation_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_application_logging(settings)

    application = FastAPI(title=settings.app_name, debug=settings.debug)
    application.state.api_v1_prefix = settings.api_v1_prefix
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )
    register_application_error_handler(application)
    application.include_router(auth_router, prefix=settings.api_v1_prefix)
    application.include_router(conversation_router, prefix=settings.api_v1_prefix)
    application.include_router(progress_router, prefix=settings.api_v1_prefix)
    application.include_router(curriculum_router, prefix=settings.api_v1_prefix)
    application.include_router(exercise_router, prefix=settings.api_v1_prefix)
    application.include_router(admin_router, prefix=settings.api_v1_prefix)

    @application.get("/health")
    def health() -> dict[str, str]:
        """Report that the backend process is alive."""
        return {"status": "ok"}

    @application.get("/ready")
    async def readiness() -> dict[str, str]:
        """Report whether the database dependency answers a lightweight probe."""
        await check_database_readiness()
        return {"status": "ready"}

    return application


app = create_app()
