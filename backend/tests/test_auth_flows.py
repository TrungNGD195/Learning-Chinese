import asyncio
import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from fastapi import Response
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.auth import service as auth_service
from app.auth.bootstrap_admin import bootstrap_admin
from app.auth.current_user import get_current_user
from app.auth.current_user import require_admin
from app.auth.cookies import set_auth_cookies
from app.auth.email import get_email_service
from app.auth.security import (create_access_token, hash_password, normalize_email,
    password_hasher, token_hash, verify_password)
from app.core.config import get_settings
from app.core.config import Settings
from app.database.models import (Assessment, AssessmentAttempt, PasswordResetToken,
    RefreshToken, User)
from app.database.session import SessionFactory
from app.main import app
from app.core.errors import ApplicationError


def _run(coro):
    return asyncio.run(coro)


def test_password_policy_hashing_and_email_normalization():
    assert normalize_email("  USER@Example.invalid  ") == "user@example.invalid"
    for password in ("12345678", "x" * 128):
        digest = hash_password(password)
        assert digest.startswith("$argon2id$") and digest != password
        assert verify_password(digest, password)
        assert not verify_password(digest, "wrong-password")
    for password in ("1234567", "x" * 129):
        response = TestClient(app).post("/api/v1/auth/register", json={
            "email": f"bounds-{uuid4()}@example.invalid", "password": password, "full_name": "Bounds"})
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_PASSWORD"


def test_cookie_helper_honors_secure_configuration_and_fixed_clear_paths():
    settings = Settings(_env_file=None, app_env="test", debug=False,
        test_database_url="postgresql+psycopg://test:test@localhost/chinese_learning_test",
        secret_key="test-only-signing-key-not-a-deployment-secret-0123456789", cookie_secure=True)
    response = Response()
    set_auth_cookies(response, "test-access", "test-refresh", settings)
    assert all("secure" in item.lower() for item in response.headers.getlist("set-cookie"))
    cleared = Response()
    from app.auth.cookies import clear_auth_cookies
    clear_auth_cookies(cleared, settings)
    headers = cleared.headers.getlist("set-cookie")
    assert any("access_token=" in item and "path=/;" in item.lower() for item in headers)
    assert any("refresh_token=" in item and "path=/api/v1/auth" in item.lower() for item in headers)


def test_register_login_cookie_contract_and_generic_invalid_credentials(caplog):
    email = f"  Register-{uuid4()}@Example.invalid  "
    password = "correct horse battery staple"
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/register", json={"email": email, "password": password,
            "full_name": "  Test Learner  ", "role": "ADMIN"})
        assert response.status_code == 422  # public request forbids role
        response = client.post("/api/v1/auth/register", json={"email": email, "password": password, "full_name": "  Test Learner  "})
        assert response.status_code == 201
        body = response.json()
        assert body["email"] == email.strip().lower() and body["full_name"] == "Test Learner" and body["role"] == "LEARNER"
        assert set(body) == {"id", "email", "full_name", "role"}
        cookies = response.headers.get_list("set-cookie")
        access_cookie = next(value for value in cookies if value.startswith("access_token="))
        refresh_cookie = next(value for value in cookies if value.startswith("refresh_token="))
        assert "httponly" in access_cookie.lower() and "path=/;" in access_cookie.lower()
        assert f"max-age={get_settings().access_token_expire_minutes * 60}" in access_cookie.lower()
        assert "secure" not in access_cookie.lower() and "samesite=lax" in access_cookie.lower()
        assert "httponly" in refresh_cookie.lower() and "path=/api/v1/auth" in refresh_cookie.lower()
        assert f"max-age={get_settings().refresh_token_expire_days * 86400}" in refresh_cookie.lower()
        assert "domain=" not in access_cookie.lower() and "domain=" not in refresh_cookie.lower()
        assert client.get("/api/v1/auth/me").json() == body
        duplicate = client.post("/api/v1/auth/register", json={"email": email.strip().lower(), "password": password, "full_name": "Other"})
        assert duplicate.status_code == 409 and duplicate.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"

        bad_known = client.post("/api/v1/auth/login", json={"email": email, "password": "incorrect password"})
        bad_unknown = client.post("/api/v1/auth/login", json={"email": f"missing-{uuid4()}@example.invalid", "password": "incorrect password"})
        assert (bad_known.status_code, bad_known.json()["error"]["code"]) == (401, "INVALID_CREDENTIALS")
        assert (bad_unknown.status_code, bad_unknown.json()["error"]["code"]) == (401, "INVALID_CREDENTIALS")
        assert "incorrect password" not in caplog.text and password not in caplog.text

    async def verify_storage():
        async with SessionFactory() as session:
            user = await session.scalar(select(User).where(User.email == email.strip().lower()))
            refresh_rows = list((await session.scalars(select(RefreshToken).where(RefreshToken.user_id == user.id))).all())
            return user.password_hash, [row.token_hash for row in refresh_rows]
    stored_hash, refresh_hashes = _run(verify_storage())
    assert stored_hash.startswith("$argon2id$") and stored_hash != password
    assert password_hasher.verify(stored_hash, password)
    assert len(refresh_hashes) == 1
    assert client.cookies.get("refresh_token") not in refresh_hashes

    async def cleanup():
        async with SessionFactory.begin() as session:
            await session.execute(delete(User).where(User.email == email.strip().lower()))
    _run(cleanup())


def test_duplicate_registration_race_normalizes_unique_violation():
    email, password = f"race-register-{uuid4()}@example.invalid", "register race password"
    async def register_once():
        async with SessionFactory() as session:
            try:
                return await auth_service.register(session, email, password, "Race")
            except Exception as exc:
                return exc
    async def simultaneous():
        return await asyncio.gather(register_once(), register_once())
    results = _run(simultaneous())
    assert sum(not isinstance(item, Exception) for item in results) == 1
    errors = [item for item in results if isinstance(item, Exception)]
    assert len(errors) == 1 and isinstance(errors[0], ApplicationError)
    assert errors[0].status_code == 409 and errors[0].code == "EMAIL_ALREADY_REGISTERED"
    async def cleanup():
        async with SessionFactory.begin() as session:
            await session.execute(delete(User).where(User.email == email))
    _run(cleanup())


def test_disabled_user_and_access_token_validation():
    email, password = f"disabled-{uuid4()}@example.invalid", "disabled account pass"
    with TestClient(app) as client:
        registered = client.post("/api/v1/auth/register", json={"email": email, "password": password, "full_name": "Disabled"})
        assert registered.status_code == 201
        user_id = registered.json()["id"]
        async def disable():
            async with SessionFactory.begin() as session:
                user = await session.get(User, user_id)
                user.is_active = False
        _run(disable())
        login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert login.status_code == 403 and login.json()["error"]["code"] == "ACCOUNT_DISABLED"
        assert client.get("/api/v1/auth/me").status_code == 403

        client.cookies.set("access_token", "tampered", path="/")
        invalid = client.get("/api/v1/auth/me")
        assert invalid.status_code == 401 and invalid.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"
        expired = jwt.encode({"sub": user_id, "role": "LEARNER", "iat": datetime.now(UTC)-timedelta(hours=2),
                              "exp": datetime.now(UTC)-timedelta(hours=1)}, get_settings().secret_key.get_secret_value(), algorithm="HS256")
        client.cookies.set("access_token", expired, path="/")
        assert client.get("/api/v1/auth/me").json()["error"]["code"] == "AUTHENTICATION_REQUIRED"
        malformed_sub = jwt.encode({"sub": "not-a-uuid", "role": "ADMIN", "iat": datetime.now(UTC),
                                    "exp": datetime.now(UTC)+timedelta(minutes=3)}, get_settings().secret_key.get_secret_value(), algorithm="HS256")
        client.cookies.set("access_token", malformed_sub, path="/")
        assert client.get("/api/v1/auth/me").json()["error"]["code"] == "AUTHENTICATION_REQUIRED"
        missing_user = create_access_token(uuid4(), "LEARNER")
        client.cookies.set("access_token", missing_user, path="/")
        assert client.get("/api/v1/auth/me").json()["error"]["code"] == "AUTHENTICATION_REQUIRED"
        missing_claim = jwt.encode({"sub": str(uuid4()), "iat": datetime.now(UTC), "exp": datetime.now(UTC)+timedelta(minutes=3)},
                                   get_settings().secret_key.get_secret_value(), algorithm="HS256")
        client.cookies.set("access_token", missing_claim, path="/")
        assert client.get("/api/v1/auth/me").json()["error"]["code"] == "AUTHENTICATION_REQUIRED"
    async def cleanup():
        async with SessionFactory.begin() as session:
            await session.execute(delete(User).where(User.email == email))
    _run(cleanup())


def test_refresh_rotation_reuse_logout_and_logout_all():
    email, password = f"refresh-{uuid4()}@example.invalid", "refresh password"
    with TestClient(app) as client:
        assert client.post("/api/v1/auth/register", json={"email": email, "password": password, "full_name": "Refresh"}).status_code == 201
        copied_access = client.cookies.get("access_token")
        old = client.cookies.get("refresh_token")
        rotated = client.post("/api/v1/auth/refresh")
        assert rotated.status_code == 204
        replacement = client.cookies.get("refresh_token")
        assert old and replacement and old != replacement
        client.cookies.set("refresh_token", old, domain="testserver.local", path="/api/v1/auth")
        replay = client.post("/api/v1/auth/refresh")
        assert replay.status_code == 401 and replay.json()["error"]["code"] == "INVALID_REFRESH_TOKEN"
        clear_headers = replay.headers.get_list("set-cookie")
        assert any("access_token=" in item and "path=/;" in item.lower() for item in clear_headers)
        assert any("refresh_token=" in item and "path=/api/v1/auth" in item.lower() for item in clear_headers)
        async def rotation_state():
            async with SessionFactory() as session:
                old_row = await session.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash(old)))
                replacement_row = await session.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash(replacement)))
                return old_row.revoked_at, replacement_row.revoked_at, old_row.token_hash, replacement_row.token_hash
        old_revoked, replacement_revoked, old_stored, replacement_stored = _run(rotation_state())
        assert old_revoked is not None and replacement_revoked is None
        assert old not in {old_stored, replacement_stored} and replacement not in {old_stored, replacement_stored}
        # Replaying a prior credential does not revoke the unrelated active replacement.
        client.cookies.set("refresh_token", replacement, domain="testserver.local", path="/api/v1/auth")
        assert client.post("/api/v1/auth/refresh").status_code == 204
        current_refresh = client.cookies.get("refresh_token", domain="testserver.local", path="/api/v1/auth")
        logout_response = client.post("/api/v1/auth/logout")
        assert logout_response.status_code == 204
        assert any("access_token=" in item and "path=/;" in item.lower() for item in logout_response.headers.get_list("set-cookie"))
        assert any("refresh_token=" in item and "path=/api/v1/auth" in item.lower() for item in logout_response.headers.get_list("set-cookie"))
        client.cookies.set("access_token", copied_access, domain="testserver.local", path="/")
        assert client.get("/api/v1/auth/me").status_code == 200  # copied Access Token remains stateless until expiry
        async def revoked_by_logout():
            async with SessionFactory() as session:
                row = await session.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash(current_refresh)))
                return row.revoked_at
        assert _run(revoked_by_logout()) is not None
        assert client.post("/api/v1/auth/login", json={"email": email, "password": password}).status_code == 200
        logout_all_response = client.post("/api/v1/auth/logout-all")
        assert logout_all_response.status_code == 204
        assert any("access_token=" in item and "path=/;" in item.lower() for item in logout_all_response.headers.get_list("set-cookie"))
        assert any("refresh_token=" in item and "path=/api/v1/auth" in item.lower() for item in logout_all_response.headers.get_list("set-cookie"))
        async def all_sessions_revoked():
            async with SessionFactory() as session:
                return await session.scalar(select(RefreshToken).join(User).where(User.email == email, RefreshToken.revoked_at.is_(None)))
        assert _run(all_sessions_revoked()) is None
        client.cookies.set("refresh_token", "invalid-after-logout-all", domain="testserver.local", path="/api/v1/auth")
        assert client.post("/api/v1/auth/refresh").status_code == 401
        logout = client.post("/api/v1/auth/logout")
        assert logout.status_code == 204
        client.cookies.set("refresh_token", "unknown", domain="testserver.local", path="/api/v1/auth")
        assert client.post("/api/v1/auth/logout").status_code == 204
    async def cleanup():
        async with SessionFactory.begin() as session:
            await session.execute(delete(User).where(User.email == email))
    _run(cleanup())


class FakeEmailService:
    def __init__(self, fail=False):
        self.tokens = []
        self.fail = fail
    async def send_password_reset(self, email, raw_token):
        self.tokens.append((email, raw_token))
        if self.fail:
            raise RuntimeError("provider detail must not escape")


def test_password_reset_enumeration_rotation_and_compensation(caplog):
    email, password = f"reset-{uuid4()}@example.invalid", "reset password"
    fake = FakeEmailService()
    app.dependency_overrides[get_email_service] = lambda: fake
    try:
        with TestClient(app) as client:
            client.post("/api/v1/auth/register", json={"email": email, "password": password, "full_name": "Reset"})
            existing = client.post("/api/v1/auth/password-reset/request", json={"email": f"  {email.upper()}  "})
            missing = client.post("/api/v1/auth/password-reset/request", json={"email": f"absent-{uuid4()}@example.invalid"})
            assert existing.status_code == missing.status_code == 202
            assert len(fake.tokens) == 1
            assert fake.tokens[0][0] == email
            raw_first = fake.tokens[0][1]
            client.post("/api/v1/auth/password-reset/request", json={"email": email})
            raw_second = fake.tokens[1][1]
            assert raw_first != raw_second
            assert raw_first not in caplog.text and raw_second not in caplog.text
            async def state():
                async with SessionFactory() as session:
                    rows = list((await session.scalars(select(PasswordResetToken).join(User).where(User.email == email))).all())
                    return [(row.token_hash, row.used_at) for row in rows]
            rows = _run(state())
            assert any(value == token_hash(raw_first) and used is not None for value, used in rows)
            assert any(value == token_hash(raw_second) and used is None for value, used in rows)
            assert all(value not in {raw_first, raw_second} for value, _ in rows)
            invalidated = client.post("/api/v1/auth/password-reset/confirm", json={"token": raw_first, "new_password": "new password"})
            assert invalidated.status_code == 400 and invalidated.json()["error"]["code"] == "INVALID_RESET_TOKEN"
            confirmed = client.post("/api/v1/auth/password-reset/confirm", json={"token": raw_second, "new_password": "new password"})
            assert confirmed.status_code == 204
            assert any("access_token=" in item and "path=/;" in item.lower() for item in confirmed.headers.get_list("set-cookie"))
            assert any("refresh_token=" in item and "path=/api/v1/auth" in item.lower() for item in confirmed.headers.get_list("set-cookie"))
            async def sessions_revoked():
                async with SessionFactory() as session:
                    return await session.scalar(select(RefreshToken).join(User).where(User.email == email, RefreshToken.revoked_at.is_(None)))
            assert _run(sessions_revoked()) is None
            assert client.post("/api/v1/auth/login", json={"email": email, "password": "new password"}).status_code == 200
            used = client.post("/api/v1/auth/password-reset/confirm", json={"token": raw_second, "new_password": "third password"})
            assert used.status_code == 400 and used.json()["error"]["code"] == "INVALID_RESET_TOKEN"

            failing = FakeEmailService(fail=True)
            app.dependency_overrides[get_email_service] = lambda: failing
            assert client.post("/api/v1/auth/password-reset/request", json={"email": email}).status_code == 202
            assert "provider detail must not escape" not in caplog.text
            async def no_usable_reset():
                async with SessionFactory() as session:
                    row = await session.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash(failing.tokens[0][1])))
                    return row.used_at
            assert _run(no_usable_reset()) is not None
    finally:
        app.dependency_overrides.pop(get_email_service, None)
        async def cleanup():
            async with SessionFactory.begin() as session:
                await session.execute(delete(User).where(User.email == email))
        _run(cleanup())


def test_expired_reset_and_disabled_refresh_are_blocked_safely():
    email, password, raw = f"expired-{uuid4()}@example.invalid", "expired token password", "opaque-expired-test-token"
    async def setup():
        async with SessionFactory.begin() as session:
            user = User(email=email, password_hash=hash_password(password), full_name="Expiry", role="LEARNER")
            session.add(user)
            await session.flush()
            session.add(PasswordResetToken(user_id=user.id, token_hash=token_hash(raw), expires_at=datetime.now(UTC)-timedelta(minutes=1)))
            session.add(RefreshToken(user_id=user.id, token_hash=token_hash("refresh-for-disabled"), expires_at=datetime.now(UTC)+timedelta(days=1)))
            user.is_active = False
    _run(setup())
    with TestClient(app) as client:
        fake = FakeEmailService()
        app.dependency_overrides[get_email_service] = lambda: fake
        expired = client.post("/api/v1/auth/password-reset/confirm", json={"token": raw, "new_password": "replacement password"})
        assert expired.status_code == 400 and expired.json()["error"]["code"] == "INVALID_RESET_TOKEN"
        client.cookies.set("refresh_token", "refresh-for-disabled", domain="testserver.local", path="/api/v1/auth")
        disabled = client.post("/api/v1/auth/refresh")
        assert disabled.status_code == 403 and disabled.json()["error"]["code"] == "ACCOUNT_DISABLED"
        assert any("refresh_token=" in item and "path=/api/v1/auth" in item.lower() for item in disabled.headers.get_list("set-cookie"))
        assert client.post("/api/v1/auth/password-reset/request", json={"email": email}).status_code == 202
        assert fake.tokens == []
        app.dependency_overrides.pop(get_email_service, None)
    async def cleanup():
        async with SessionFactory.begin() as session:
            await session.execute(delete(User).where(User.email == email))
    _run(cleanup())


def test_admin_guard_database_role_authority_and_bootstrap():
    learner_email, admin_email = f"learner-{uuid4()}@example.invalid", f"admin-{uuid4()}@example.invalid"
    password = "role change password"
    with TestClient(app) as client:
        assert client.get("/api/v1/admin/stats").status_code == 401
        learner = client.post("/api/v1/auth/register", json={"email": learner_email, "password": password, "full_name": "Learner"})
        assert learner.status_code == 201
        assert client.get("/api/v1/admin/stats").json()["error"]["code"] == "ADMIN_REQUIRED"
        try:
            _run(bootstrap_admin(learner_email, password, "Must not promote"))
        except ApplicationError as exc:
            assert exc.status_code == 409
        else:
            raise AssertionError("Admin bootstrap must refuse an existing LEARNER")
        _run(bootstrap_admin(f"  {admin_email.upper()}  ", password, "Bootstrap Admin"))
        admin_login = client.post("/api/v1/auth/login", json={"email": admin_email, "password": password})
        assert admin_login.status_code == 200 and admin_login.json()["role"] == "ADMIN"
        assert client.get("/api/v1/admin/stats").status_code == 200
        admin_id = admin_login.json()["id"]
        async def demote():
            async with SessionFactory.begin() as session:
                (await session.get(User, admin_id)).role = "LEARNER"
        _run(demote())
        assert client.get("/api/v1/admin/stats").status_code == 403
        assert client.get("/api/v1/admin/stats").json()["error"]["code"] == "ADMIN_REQUIRED"
        assert "bootstrap_admin" not in open("app/main.py", encoding="utf-8").read()
    async def cleanup():
        async with SessionFactory.begin() as session:
            await session.execute(delete(User).where(User.email.in_([learner_email, admin_email])))
    _run(cleanup())


def test_real_auth_cookie_preserves_attempt_ownership():
    owner_email, reader_email = f"owner-{uuid4()}@example.invalid", f"reader-{uuid4()}@example.invalid"
    assessment_id, attempt_id = uuid4(), uuid4()
    password = "ownership password"
    async def seed():
        async with SessionFactory.begin() as session:
            owner = User(id=uuid4(), email=owner_email, password_hash=hash_password(password), full_name="Owner", role="LEARNER")
            reader = User(id=uuid4(), email=reader_email, password_hash=hash_password(password), full_name="Reader", role="LEARNER")
            session.add_all([owner, reader])
            await session.flush()
            session.add(Assessment(id=assessment_id, type="PERIODIC_TEST", title="Ownership", status="PUBLISHED", pass_threshold=90))
            session.add(AssessmentAttempt(id=attempt_id, user_id=owner.id, assessment_id=assessment_id, attempt_number=1, status="IN_PROGRESS"))
    _run(seed())
    with TestClient(app) as client:
        assert client.post("/api/v1/auth/login", json={"email": reader_email, "password": password}).status_code == 200
        result = client.get(f"/api/v1/me/assessment-attempts/{attempt_id}")
        assert result.status_code == 404
    async def cleanup():
        async with SessionFactory.begin() as session:
            await session.execute(delete(AssessmentAttempt).where(AssessmentAttempt.id == attempt_id))
            await session.execute(delete(Assessment).where(Assessment.id == assessment_id))
            await session.execute(delete(User).where(User.email.in_([owner_email, reader_email])))
    _run(cleanup())


def test_change_password_revokes_sessions_and_requires_login_again():
    email, old_password = f"change-{uuid4()}@example.invalid", "old password"
    with TestClient(app) as client:
        assert client.post("/api/v1/auth/register", json={"email": email, "password": old_password, "full_name": "Change"}).status_code == 201
        access_before_change = client.cookies.get("access_token")
        wrong = client.post("/api/v1/auth/change-password", json={"current_password": "wrong password", "new_password": "new password"})
        assert wrong.status_code == 400 and wrong.json()["error"]["code"] == "INVALID_CURRENT_PASSWORD"
        changed = client.post("/api/v1/auth/change-password", json={"current_password": old_password, "new_password": "new password"})
        assert changed.status_code == 204
        assert any("access_token=" in item and "path=/;" in item.lower() for item in changed.headers.get_list("set-cookie"))
        assert any("refresh_token=" in item and "path=/api/v1/auth" in item.lower() for item in changed.headers.get_list("set-cookie"))
        # A copied short-lived Access Token is deliberately not blacklisted.
        client.cookies.set("access_token", access_before_change, domain="testserver.local", path="/")
        assert client.get("/api/v1/auth/me").status_code == 200
        assert client.post("/api/v1/auth/login", json={"email": email, "password": old_password}).status_code == 401
        assert client.post("/api/v1/auth/login", json={"email": email, "password": "new password"}).status_code == 200
    async def cleanup():
        async with SessionFactory.begin() as session:
            await session.execute(delete(User).where(User.email == email))
    _run(cleanup())


def test_refresh_concurrent_reuse_has_at_most_one_winner():
    email, raw = f"race-{uuid4()}@example.invalid", None
    async def run_race():
        nonlocal raw
        from app.auth.security import generate_opaque_token
        raw, digest = generate_opaque_token()
        async with SessionFactory.begin() as session:
            user = User(email=email, password_hash=hash_password("race password"), full_name="Race", role="LEARNER")
            session.add(user)
            await session.flush()
            session.add(RefreshToken(user_id=user.id, token_hash=digest, expires_at=datetime.now(UTC)+timedelta(days=1)))
        async def use_token():
            async with SessionFactory() as session:
                try:
                    return await auth_service.refresh(session, raw)
                except Exception as exc:
                    return exc
        results = await asyncio.gather(use_token(), use_token())
        successes = [item for item in results if not isinstance(item, Exception)]
        errors = [item for item in results if isinstance(item, Exception)]
        assert len(successes) == 1 and len(errors) == 1
        assert getattr(errors[0], "code", None) == "INVALID_REFRESH_TOKEN"
    _run(run_race())
    async def cleanup():
        async with SessionFactory.begin() as session:
            await session.execute(delete(User).where(User.email == email))
    _run(cleanup())


def test_auth_openapi_contracts_are_safe_and_complete():
    schema = app.openapi()
    paths = schema["paths"]
    prefix = "/api/v1/auth/"
    suffixes = {"register", "login", "refresh", "logout", "logout-all", "me", "change-password",
        "password-reset/request", "password-reset/confirm"}
    assert {path.removeprefix(prefix) for path in paths if path.startswith(prefix)} == suffixes
    components = schema["components"]["schemas"]
    for name in ("RegisterRequest", "LoginRequest", "ChangePasswordRequest", "PasswordResetRequest", "PasswordResetConfirmRequest"):
        assert "user_id" not in components[name].get("properties", {})
        assert "role" not in components[name].get("properties", {})
        assert "token_hash" not in components[name].get("properties", {})
    for suffix in ("refresh", "logout", "logout-all", "change-password", "password-reset/confirm"):
        assert "content" not in paths[prefix + suffix]["post"]["responses"]["204"]
    for suffix in ("refresh", "logout"):
        assert "requestBody" not in paths[prefix + suffix]["post"]
    for route in app.routes:
        if getattr(route, "path", "").startswith("/api/v1/admin/"):
            assert any(dependency.call is require_admin for dependency in route.dependant.dependencies)
