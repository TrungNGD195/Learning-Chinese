from app.core.errors import ApplicationError

CITATION_MISSING = "CITATION_MISSING"
CITATION_FORMAT_INVALID = "CITATION_FORMAT_INVALID"
CITATION_UNKNOWN_SOURCE = "CITATION_UNKNOWN_SOURCE"
CITATION_SOURCE_RESOLUTION_FAILED = "CITATION_SOURCE_RESOLUTION_FAILED"
CITATION_EXTERNAL_URL_INVALID = "CITATION_EXTERNAL_URL_INVALID"
CITATION_VALIDATION_FAILED = "CITATION_VALIDATION_FAILED"


def citation_error(code: str) -> ApplicationError:
    messages = {
        CITATION_MISSING: "A citation is required for this response.",
        CITATION_FORMAT_INVALID: "Citation format is invalid.",
        CITATION_UNKNOWN_SOURCE: "A cited source is unavailable.",
        CITATION_SOURCE_RESOLUTION_FAILED: "Citation source could not be resolved.",
        CITATION_EXTERNAL_URL_INVALID: "External citation source is not trusted.",
        CITATION_VALIDATION_FAILED: "Citation validation failed.",
    }
    return ApplicationError(code, messages.get(code, messages[CITATION_VALIDATION_FAILED]), status_code=502)
