from __future__ import annotations


AI_GENERATION_PROVIDER_NOT_CONFIGURED = "AI_GENERATION_PROVIDER_NOT_CONFIGURED"
AI_GENERATION_AUTHENTICATION_FAILED = "AI_GENERATION_AUTHENTICATION_FAILED"
AI_GENERATION_PERMISSION_DENIED = "AI_GENERATION_PERMISSION_DENIED"
AI_GENERATION_TIMEOUT = "AI_GENERATION_TIMEOUT"
AI_GENERATION_RATE_LIMITED = "AI_GENERATION_RATE_LIMITED"
AI_GENERATION_PROVIDER_UNAVAILABLE = "AI_GENERATION_PROVIDER_UNAVAILABLE"
AI_GENERATION_INPUT_TOO_LARGE = "AI_GENERATION_INPUT_TOO_LARGE"
AI_GENERATION_REQUEST_INVALID = "AI_GENERATION_REQUEST_INVALID"
AI_GENERATION_INVALID_RESPONSE = "AI_GENERATION_INVALID_RESPONSE"
AI_GENERATION_SCHEMA_INVALID = "AI_GENERATION_SCHEMA_INVALID"


class StructuredAssessmentGenerationProviderError(Exception):
    """Safe internal classification for a structured generation failure."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class AssessmentGenerationInvalidOutput(Exception):
    """The complete model proposal failed programmatic validation."""


class AssessmentGenerationScopeInvalid(Exception):
    """The Admin-selected curriculum scope is invalid or empty."""
