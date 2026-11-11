from app.core.config import Settings, get_settings
from app.core.errors import ApplicationError


def require_knowledge_ai(settings: Settings | None = None) -> None:
    if not (settings or get_settings()).knowledge_ai_enabled:
        raise ApplicationError(
            'KNOWLEDGE_AI_DISABLED',
            'Xử lý và tìm kiếm tài liệu bằng AI đang tạm tắt trên bản triển khai này.',
            status_code=503,
        )
