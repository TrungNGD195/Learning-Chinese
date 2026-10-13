from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import ApplicationError, register_application_error_handler


def test_application_error_uses_standard_response_shape() -> None:
    test_app = FastAPI()
    register_application_error_handler(test_app)

    @test_app.get("/expected-error")
    def raise_application_error() -> None:
        raise ApplicationError("INVALID_REQUEST", "The request is invalid.")

    response = TestClient(test_app).get("/expected-error")

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "INVALID_REQUEST",
            "message": "The request is invalid.",
            "details": None,
        }
    }
