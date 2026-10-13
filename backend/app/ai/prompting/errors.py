from app.core.errors import ApplicationError


INVALID_PROMPT_BUDGET = "INVALID_PROMPT_BUDGET"
TOKEN_COUNT_FAILED = "TOKEN_COUNT_FAILED"
CONTEXT_BUDGET_EXHAUSTED = "CONTEXT_BUDGET_EXHAUSTED"
PROMPT_CONTEXT_BUILD_FAILED = "PROMPT_CONTEXT_BUILD_FAILED"
NO_RETRIEVAL_CONTEXT = "NO_RETRIEVAL_CONTEXT"


def prompt_context_error(code: str, message: str, status_code: int = 422) -> ApplicationError:
    """Create a safe normalized error without caller-provided details."""
    return ApplicationError(code, message, status_code=status_code)
