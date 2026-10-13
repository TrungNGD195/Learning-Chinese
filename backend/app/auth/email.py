from logging import getLogger
from typing import Protocol

logger = getLogger("app.auth.email")


class EmailService(Protocol):
    async def send_password_reset(self, email: str, raw_token: str) -> None: ...


class NonDeliveringEmailService:
    """Provider-neutral placeholder; production delivery is deferred to Phase 8."""

    async def send_password_reset(self, email: str, raw_token: str) -> None:
        del raw_token
        logger.info("Password reset email requested for an account")


def get_email_service() -> EmailService:
    return NonDeliveringEmailService()
