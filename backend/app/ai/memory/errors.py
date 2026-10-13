from app.core.errors import ApplicationError

MEMORY_REPOSITORY_FAILED = "MEMORY_REPOSITORY_FAILED"
MEMORY_TOKEN_COUNT_FAILED = "MEMORY_TOKEN_COUNT_FAILED"
MEMORY_PERSISTENCE_INTEGRITY_FAILED = "MEMORY_PERSISTENCE_INTEGRITY_FAILED"
MEMORY_BUILD_FAILED = "MEMORY_BUILD_FAILED"

_MESSAGES = {
    MEMORY_REPOSITORY_FAILED: "Conversation memory could not be loaded.",
    MEMORY_TOKEN_COUNT_FAILED: "Conversation memory could not be measured.",
    MEMORY_PERSISTENCE_INTEGRITY_FAILED: "Conversation memory data is inconsistent.",
    MEMORY_BUILD_FAILED: "Conversation memory could not be built.",
}


def memory_error(code: str) -> ApplicationError:
    return ApplicationError(code, _MESSAGES.get(code, _MESSAGES[MEMORY_BUILD_FAILED]), 500)
