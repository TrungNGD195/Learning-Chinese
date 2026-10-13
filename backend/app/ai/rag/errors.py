from app.core.errors import ApplicationError

RAG_CONFIGURATION_INVALID = "RAG_CONFIGURATION_INVALID"
RAG_ORCHESTRATION_FAILED = "RAG_ORCHESTRATION_FAILED"
DUPLICATE_RAG_GENERATION = "DUPLICATE_RAG_GENERATION"


def rag_error(code: str) -> ApplicationError:
    messages = {
        RAG_CONFIGURATION_INVALID: "RAG runtime configuration is not ready.",
        RAG_ORCHESTRATION_FAILED: "RAG response processing failed.",
        DUPLICATE_RAG_GENERATION: "This assistant response is already being processed.",
    }
    status = 409 if code == DUPLICATE_RAG_GENERATION else 503
    return ApplicationError(code, messages.get(code, messages[RAG_ORCHESTRATION_FAILED]), status_code=status)
