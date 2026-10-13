import ast
import asyncio
import inspect
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.auth import repository, service
from app.auth.schemas import LoginRequest, PasswordResetRequest, RegisterRequest
from app.auth.security import generate_opaque_token, hash_password
from app.core.errors import ApplicationError
from app.database.models import PasswordResetToken, RefreshToken, User
from app.database.session import SessionFactory


def test_auth_service_delegates_orm_persistence_to_repository() -> None:
    service_path = Path(inspect.getsourcefile(service))
    tree = ast.parse(service_path.read_text(encoding="utf-8"))
    direct_session_operations = {"add", "add_all", "delete", "execute", "flush", "get", "refresh", "scalar"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert not (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "session"
                and node.func.attr in direct_session_operations
            ), f"AuthService directly calls session.{node.func.attr}"
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                for child in ast.walk(target):
                    if isinstance(child, ast.Attribute):
                        assert child.attr not in {"password_hash", "revoked_at", "used_at"}, (
                            f"AuthService directly mutates ORM field {child.attr}"
                        )


@pytest.mark.parametrize("schema", [RegisterRequest, LoginRequest, PasswordResetRequest])
def test_public_auth_email_schema_normalizes_and_rejects_whitespace(schema) -> None:
    valid_payload = {"email": "  USER@Example.invalid  "}
    if schema is RegisterRequest:
        valid_payload |= {"password": "valid password", "full_name": "Learner"}
    elif schema is LoginRequest:
        valid_payload["password"] = "valid password"
    assert schema.model_validate(valid_payload).email == "user@example.invalid"

    invalid_payload = dict(valid_payload, email=" \t\n ")
    with pytest.raises(ValueError):
        schema.model_validate(invalid_payload)


class CapturingEmailService:
    def __init__(self) -> None:
        self.tokens: list[str] = []

    async def send_password_reset(self, email: str, raw_token: str) -> None:
        self.tokens.append(raw_token)


def test_concurrent_reset_requests_leave_only_one_usable_credential() -> None:
    email = f"reset-race-{uuid4()}@example.invalid"
    fake_email = CapturingEmailService()

    async def run() -> None:
        async with SessionFactory.begin() as session:
            session.add(User(email=email, password_hash=hash_password("race password"), full_name="Reset Race", role="LEARNER"))

        async def issue() -> None:
            async with SessionFactory() as session:
                await service.request_password_reset(session, email, fake_email)

        await asyncio.gather(issue(), issue())
        async with SessionFactory() as session:
            active_count = await session.scalar(
                select(func.count()).select_from(PasswordResetToken).join(User).where(
                    User.email == email,
                    PasswordResetToken.used_at.is_(None),
                    PasswordResetToken.expires_at > func.now(),
                )
            )
        assert active_count == 1
        assert len(fake_email.tokens) == 2

    try:
        asyncio.run(run())
    finally:
        async def cleanup() -> None:
            async with SessionFactory.begin() as session:
                await session.execute(User.__table__.delete().where(User.email == email))

        asyncio.run(cleanup())


@pytest.mark.parametrize("revoke_operation", ["logout_all", "change_password", "reset_confirm"])
def test_refresh_rotation_racing_all_session_revocation_leaves_no_active_session(revoke_operation, monkeypatch) -> None:
    email = f"session-race-{revoke_operation}-{uuid4()}@example.invalid"
    raw_refresh, refresh_digest = generate_opaque_token()
    raw_reset, reset_digest = generate_opaque_token()
    old_password = "old race password"

    async def run() -> None:
        async with SessionFactory.begin() as session:
            user = User(email=email, password_hash=hash_password(old_password), full_name="Session Race", role="LEARNER")
            session.add(user)
            await session.flush()
            session.add(RefreshToken(
                user_id=user.id,
                token_hash=refresh_digest,
                expires_at=datetime.now(UTC) + timedelta(days=1),
            ))
            if revoke_operation == "reset_confirm":
                session.add(PasswordResetToken(
                    user_id=user.id,
                    token_hash=reset_digest,
                    expires_at=datetime.now(UTC) + timedelta(minutes=30),
                ))

        async def rotate():
            async with SessionFactory() as session:
                try:
                    return await service.refresh(session, raw_refresh)
                except ApplicationError as error:
                    return error

        async def revoke():
            async with SessionFactory() as session:
                if revoke_operation == "logout_all":
                    user = await repository.get_user_by_email(session, email)
                    assert user is not None
                    await service.logout_all(session, user.id)
                elif revoke_operation == "change_password":
                    user = await repository.get_user_by_email(session, email)
                    assert user is not None
                    await service.change_password(session, user, old_password, "new race password")
                else:
                    await service.confirm_password_reset(session, raw_reset, "new reset password")

        rotation_result, _ = await asyncio.gather(rotate(), revoke())
        if isinstance(rotation_result, ApplicationError):
            assert rotation_result.code == "INVALID_REFRESH_TOKEN"
        async with SessionFactory() as session:
            active_count = await session.scalar(
                select(func.count()).select_from(RefreshToken).join(User).where(
                    User.email == email,
                    RefreshToken.revoked_at.is_(None),
                )
            )
        assert active_count == 0

    try:
        asyncio.run(run())
    finally:
        async def cleanup() -> None:
            async with SessionFactory.begin() as session:
                await session.execute(User.__table__.delete().where(User.email == email))

        asyncio.run(cleanup())


def test_login_does_not_issue_session_after_password_changes_during_verification(monkeypatch) -> None:
    email = f"stale-login-{uuid4()}@example.invalid"
    original_password = "original login password"
    replacement_password = "replacement login password"

    async def run() -> None:
        async with SessionFactory.begin() as session:
            user = User(email=email, password_hash=hash_password(original_password), full_name="Login Race", role="LEARNER")
            session.add(user)
            await session.flush()
            user_id = user.id

        original_lock = repository.lock_user_by_id
        injected = False

        async def concurrent_password_change(session, target_user_id):
            nonlocal injected
            if not injected:
                injected = True
                async with SessionFactory.begin() as other_session:
                    other_user = await other_session.get(User, target_user_id)
                    other_user.password_hash = hash_password(replacement_password)
            return await original_lock(session, target_user_id)

        monkeypatch.setattr(repository, "lock_user_by_id", concurrent_password_change)
        async with SessionFactory() as session:
            with pytest.raises(ApplicationError) as raised:
                await service.login(session, email, original_password)
        assert raised.value.code == "INVALID_CREDENTIALS"
        async with SessionFactory() as session:
            count = await session.scalar(select(func.count()).select_from(RefreshToken).where(RefreshToken.user_id == user_id))
        assert count == 0

    try:
        asyncio.run(run())
    finally:
        monkeypatch.undo()

        async def cleanup() -> None:
            async with SessionFactory.begin() as session:
                await session.execute(User.__table__.delete().where(User.email == email))

        asyncio.run(cleanup())
