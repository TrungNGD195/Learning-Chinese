from app.core.errors import ApplicationError


_STATUS_CODES = {
    "KNOWLEDGE_VERSION_NOT_PROCESSING": 409,
    "KNOWLEDGE_VERSION_NOT_VECTOR_READY": 409,
    "EMBEDDING_PROFILE_NOT_READY": 409,
    "ACTIVE_EMBEDDING_PROFILE_NOT_FOUND": 409,
    "MULTIPLE_ACTIVE_EMBEDDING_PROFILES": 500,
    "VECTOR_DIMENSION_MISMATCH": 500,
    "VECTOR_QUERY_FAILED": 500,
    "ACTIVATION_CONFLICT": 409,
}


def vector_storage_error(code: str, message: str) -> ApplicationError:
    return ApplicationError(code, message, status_code=_STATUS_CODES[code])
