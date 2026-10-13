from app.core.errors import ApplicationError

LLM_PROVIDER_NOT_CONFIGURED = "LLM_PROVIDER_NOT_CONFIGURED"
LLM_CONFIGURATION_INVALID = "LLM_CONFIGURATION_INVALID"
LLM_REQUEST_INVALID = "LLM_REQUEST_INVALID"
LLM_TIMEOUT = "LLM_TIMEOUT"
LLM_RATE_LIMITED = "LLM_RATE_LIMITED"
LLM_PROVIDER_UNAVAILABLE = "LLM_PROVIDER_UNAVAILABLE"
LLM_AUTHENTICATION_FAILED = "LLM_AUTHENTICATION_FAILED"
LLM_PERMISSION_DENIED = "LLM_PERMISSION_DENIED"
LLM_CONTEXT_LIMIT_EXCEEDED = "LLM_CONTEXT_LIMIT_EXCEEDED"
EMPTY_LLM_RESPONSE = "EMPTY_LLM_RESPONSE"
INVALID_LLM_RESPONSE = "INVALID_LLM_RESPONSE"
LLM_GENERATION_FAILED = "LLM_GENERATION_FAILED"


_MESSAGES = {
    LLM_PROVIDER_NOT_CONFIGURED: "The language model provider is not configured.",
    LLM_CONFIGURATION_INVALID: "The language model configuration is invalid.",
    LLM_REQUEST_INVALID: "The language model request is invalid.",
    LLM_TIMEOUT: "The language model provider timed out.",
    LLM_RATE_LIMITED: "The language model provider is rate limited.",
    LLM_PROVIDER_UNAVAILABLE: "The language model provider is unavailable.",
    LLM_AUTHENTICATION_FAILED: "The language model provider rejected authentication.",
    LLM_PERMISSION_DENIED: "The language model provider denied the request.",
    LLM_CONTEXT_LIMIT_EXCEEDED: "The language model context limit was exceeded.",
    EMPTY_LLM_RESPONSE: "The language model returned an empty response.",
    INVALID_LLM_RESPONSE: "The language model returned an invalid response.",
    LLM_GENERATION_FAILED: "Language model generation failed.",
}


def llm_error(code: str, status_code: int | None = None) -> ApplicationError:
    statuses = {
        LLM_PROVIDER_NOT_CONFIGURED: 503,
        LLM_CONFIGURATION_INVALID: 500,
        LLM_REQUEST_INVALID: 400,
        LLM_TIMEOUT: 503,
        LLM_RATE_LIMITED: 503,
        LLM_PROVIDER_UNAVAILABLE: 503,
        LLM_AUTHENTICATION_FAILED: 502,
        LLM_PERMISSION_DENIED: 502,
        LLM_CONTEXT_LIMIT_EXCEEDED: 422,
        EMPTY_LLM_RESPONSE: 502,
        INVALID_LLM_RESPONSE: 502,
        LLM_GENERATION_FAILED: 502,
    }
    return ApplicationError(
        code,
        _MESSAGES.get(code, _MESSAGES[LLM_GENERATION_FAILED]),
        status_code=status_code or statuses.get(code, 502),
    )
