from __future__ import annotations

import asyncio
from uuid import uuid4

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.auth.current_user import get_current_user, require_admin, require_learner
from app.auth.security import create_access_token
from app.database.models import User
from app.database.session import SessionFactory
from app.admin.router import router as admin_router
from app.auth.router import router as auth_router
from app.conversation.router import router as conversation_router
from app.curriculum.router import router as curriculum_router
from app.exercise.router import router as exercise_router
from app.main import app
from app.progress.router import router as progress_router

ROUTERS = (
    ("/api/v1", auth_router),
    ("/api/v1", conversation_router),
    ("/api/v1", progress_router),
    ("/api/v1", curriculum_router),
    ("/api/v1", exercise_router),
    ("/api/v1", admin_router),
)


LEARNER_ENDPOINTS = (
    ("/api/v1/me/dashboard", "GET"),
    ("/api/v1/hsk-levels", "GET"),
    (f"/api/v1/assessments/{uuid4()}", "GET"),
    ("/api/v1/me/conversations", "GET"),
)


def _dependency_calls(route: APIRoute) -> set[object]:
    found: set[object] = set()

    def visit(dependant):
        for dependency in dependant.dependencies:
            if dependency.call is not None:
                found.add(dependency.call)
            visit(dependency)

    visit(route.dependant)
    return found


def _route(path: str, method: str) -> APIRoute:
    return next(
        route
        for prefix, router in ROUTERS
        for route in router.routes
        if isinstance(route, APIRoute)
        and f"{prefix}{route.path}" == path
        and method in route.methods
    )


def _role_user(role: str) -> User:
    return User(
        id=uuid4(),
        email=f"{role.lower()}-{uuid4()}@example.invalid",
        password_hash="test-only",
        full_name=role.title(),
        role=role,
        is_active=True,
    )


def test_every_learner_route_requires_learner_and_admin_routes_keep_admin_gate():
    learner_prefixes = (
        "/api/v1/me/",
        "/api/v1/pronunciation",
        "/api/v1/lessons/",
        "/api/v1/hsk-levels",
        "/api/v1/assessments/",
        "/api/v1/assessment-attempts/",
        "/api/v1/conversations",
        "/api/v1/messages/",
    )
    for prefix, router in ROUTERS:
        for route in router.routes:
            if not isinstance(route, APIRoute):
                continue
            path = f"{prefix}{route.path}"
            calls = _dependency_calls(route)
            if path.startswith(learner_prefixes):
                assert require_learner in calls, f"{path} is missing require_learner"
            if path.startswith("/api/v1/admin/"):
                assert require_admin in calls, f"{path} is missing require_admin"


def test_anonymous_learner_and_admin_apis_remain_401():
    with TestClient(app) as client:
        learner = client.get("/api/v1/me/dashboard")
        admin = client.get("/api/v1/admin/stats")

    assert learner.status_code == 401
    assert learner.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"
    assert admin.status_code == 401
    assert admin.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_role_matrix_blocks_wrong_role_before_business_lookup():
    learner = _role_user("LEARNER")
    admin = _role_user("ADMIN")

    async def current_learner():
        return learner

    async def current_admin():
        return admin

    try:
        with TestClient(app) as client:
            app.dependency_overrides[get_current_user] = current_learner
            allowed_learner = client.get("/api/v1/me/conversations")
            learner_to_admin = client.get("/api/v1/admin/stats")

            app.dependency_overrides[get_current_user] = current_admin
            admin_allowed = client.get("/api/v1/admin/stats")
            admin_to_learner = [client.request(method, path) for path, method in LEARNER_ENDPOINTS]
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert allowed_learner.status_code == 200
    assert learner_to_admin.status_code == 403
    assert learner_to_admin.json()["error"]["code"] == "ADMIN_REQUIRED"
    assert admin_allowed.status_code == 200
    assert len(admin_to_learner) == len(LEARNER_ENDPOINTS)
    for response in admin_to_learner:
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "LEARNER_REQUIRED"


def test_auth_me_remains_shared_and_reports_each_current_role():
    for role in ("LEARNER", "ADMIN"):
        current = _role_user(role)

        async def current_user():
            return current

        try:
            app.dependency_overrides[get_current_user] = current_user
            with TestClient(app) as client:
                response = client.get("/api/v1/auth/me")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert response.status_code == 200
        assert response.json()["role"] == role


def test_shared_authenticated_session_routes_have_no_role_gate():
    shared_routes = {
        ("/api/v1/auth/me", "GET"),
        ("/api/v1/auth/refresh", "POST"),
        ("/api/v1/auth/logout", "POST"),
        ("/api/v1/auth/logout-all", "POST"),
        ("/api/v1/auth/change-password", "POST"),
    }
    for path, method in shared_routes:
        calls = _dependency_calls(_route(path, method))
        assert require_learner not in calls
        assert require_admin not in calls


def test_stale_token_role_never_overrides_current_database_role():
    user_id = uuid4()
    email = f"d120-role-{user_id}@example.invalid"

    async def create_user():
        async with SessionFactory.begin() as session:
            session.add(User(
                id=user_id,
                email=email,
                password_hash="test-only",
                full_name="D-120 role test",
                role="ADMIN",
                is_active=True,
            ))

    async def set_role(role: str):
        async with SessionFactory.begin() as session:
            user = await session.get(User, user_id)
            assert user is not None
            user.role = role

    async def delete_user():
        async with SessionFactory.begin() as session:
            await session.execute(delete(User).where(User.id == user_id))

    asyncio.run(create_user())
    try:
        token_with_admin_role = create_access_token(user_id, "ADMIN")
        with TestClient(app) as client:
            client.cookies.set("access_token", token_with_admin_role, path="/")

            asyncio.run(set_role("LEARNER"))
            now_learner = client.get("/api/v1/hsk-levels")
            assert now_learner.status_code == 200

            asyncio.run(set_role("ADMIN"))
            same_token_now_admin = client.get("/api/v1/hsk-levels")

        assert same_token_now_admin.status_code == 403
        assert same_token_now_admin.json()["error"]["code"] == "LEARNER_REQUIRED"
    finally:
        asyncio.run(delete_user())


def test_require_learner_uses_current_user_and_returns_frozen_error():
    admin = _role_user("ADMIN")

    async def current_admin():
        return admin

    try:
        app.dependency_overrides[get_current_user] = current_admin
        with TestClient(app) as client:
            response = client.get("/api/v1/hsk-levels")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "LEARNER_REQUIRED"
