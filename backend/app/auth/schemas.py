from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.auth.security import normalize_email


class AuthInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AuthEmailRequest(AuthInput):
    email: str

    @field_validator("email")
    @classmethod
    def normalize_and_validate_email(cls, value: str) -> str:
        value = normalize_email(value)
        if not value:
            raise ValueError("email must not be empty")
        return value


class RegisterRequest(AuthEmailRequest):
    password: str
    full_name: str

    @field_validator("full_name")
    @classmethod
    def full_name_not_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("full_name must not be empty")
        return value


class LoginRequest(AuthEmailRequest):
    password: str


class UserProfileResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str


class ChangePasswordRequest(AuthInput):
    current_password: str
    new_password: str


class PasswordResetRequest(AuthEmailRequest):
    pass


class PasswordResetConfirmRequest(AuthInput):
    token: str
    new_password: str
