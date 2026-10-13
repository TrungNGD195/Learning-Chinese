from app.core.errors import ApplicationError


def reranking_error(code: str, message: str, status_code: int = 500) -> ApplicationError:
    return ApplicationError(code, message, status_code=status_code)
