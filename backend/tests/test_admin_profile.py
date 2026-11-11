import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.auth import service
from app.database.models import User
from app.database.session import SessionFactory
from app.main import app


def test_admin_profile_edit_and_account_wide_session_revocation():
    email, password = f'admin-profile-{uuid4()}@example.invalid', 'Profile test password'
    async def setup():
        async with SessionFactory() as session:
            return await service.create_admin(session, email, password, 'Profile Admin')
    user = asyncio.run(setup())
    try:
        with TestClient(app) as first, TestClient(app) as second:
            for client in (first, second):
                assert client.post('/api/v1/auth/login', json={'email': email, 'password': password}).status_code == 200
            response = first.patch('/api/v1/auth/me', json={'full_name': '  New Admin Name  '})
            assert response.status_code == 200
            assert response.json()['full_name'] == 'New Admin Name'
            assert response.json()['email'] == email and response.json()['role'] == 'ADMIN'
            assert first.patch('/api/v1/auth/me', json={'full_name': 'Changed', 'role': 'LEARNER'}).status_code == 422
            assert first.patch('/api/v1/auth/me', json={'full_name': '  '}).status_code == 422
            assert first.patch('/api/v1/auth/me', json={'full_name': 'x' * 121}).status_code == 422
            same = first.post('/api/v1/auth/change-password', json={'current_password': password, 'new_password': password})
            assert same.status_code == 422 and same.json()['error']['code'] == 'PASSWORD_UNCHANGED'
            assert first.post('/api/v1/auth/logout-all').status_code == 204
            assert second.get('/api/v1/auth/me').status_code == 401
            assert second.post('/api/v1/auth/refresh').status_code == 401
            for client in (first, second):
                assert client.post('/api/v1/auth/login', json={'email': email, 'password': password}).status_code == 200
            changed = first.post('/api/v1/auth/change-password', json={'current_password': password, 'new_password': 'Different profile password'})
            assert changed.status_code == 204
            assert second.get('/api/v1/auth/me').status_code == 401
            assert second.post('/api/v1/auth/refresh').status_code == 401
            assert first.post('/api/v1/auth/login', json={'email': email, 'password': password}).status_code == 401
            assert first.post('/api/v1/auth/login', json={'email': email, 'password': 'Different profile password'}).status_code == 200
            assert first.get('/api/v1/auth/me').json()['full_name'] == 'New Admin Name'
    finally:
        async def cleanup():
            async with SessionFactory.begin() as session:
                await session.execute(delete(User).where(User.id == user.id))
        asyncio.run(cleanup())
