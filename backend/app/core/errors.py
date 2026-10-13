from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ApplicationError(Exception):
    """An expected application failure that can be returned to an API client."""

    def __init__(
        self,
        code: str,
        message: str,
        details: Any = None,
        status_code: int = 400,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details
        self.status_code = status_code


async def application_error_handler(
    request: Request, exc: ApplicationError
) -> JSONResponse:
    del request  # The response contract does not depend on request details.
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


def register_application_error_handler(app: FastAPI) -> None:
    """Register the standard response for expected application errors."""
    app.add_exception_handler(ApplicationError, application_error_handler)

    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        del request
        details = [
            {key: value for key, value in error.items() if key not in {"input", "ctx"}}
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "Request validation failed",
                    "details": details,
                }
            },
        )

    app.add_exception_handler(RequestValidationError, validation_error_handler)
