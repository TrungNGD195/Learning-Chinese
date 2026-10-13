from app.core.errors import ApplicationError


EXTERNAL_RETRIEVAL_NOT_CONFIGURED = "EXTERNAL_RETRIEVAL_NOT_CONFIGURED"
EXTERNAL_RETRIEVAL_AUTH_FAILED = "EXTERNAL_RETRIEVAL_AUTH_FAILED"
EXTERNAL_RETRIEVAL_TIMEOUT = "EXTERNAL_RETRIEVAL_TIMEOUT"
EXTERNAL_RETRIEVAL_FAILED = "EXTERNAL_RETRIEVAL_FAILED"


def external_retrieval_error(code: str) -> ApplicationError:
    messages = {
        EXTERNAL_RETRIEVAL_NOT_CONFIGURED: "External retrieval is not configured.",
        EXTERNAL_RETRIEVAL_AUTH_FAILED: "External retrieval authentication failed.",
        EXTERNAL_RETRIEVAL_TIMEOUT: "External retrieval timed out.",
        EXTERNAL_RETRIEVAL_FAILED: "External retrieval failed.",
    }
    return ApplicationError(code, messages.get(code, messages[EXTERNAL_RETRIEVAL_FAILED]), 503)
