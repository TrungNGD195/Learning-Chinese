from app.core.errors import ApplicationError


def embedding_error(code: str, message: str, status_code: int, **details) -> ApplicationError:
    return ApplicationError(code, message, status_code=status_code, details=details or None)
