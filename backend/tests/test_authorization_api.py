"""RBAC API integration tests."""

from __future__ import annotations

import uuid
from typing import Any, AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.authorization.constants.system_roles import USER_ROLE_ID
from app.db import AsyncSessionLocal, engine
from app.main import app
from app.models import Agent, AgentDownload, CustomAgentType, User
from app.models.authorization import AuthUserRoleAssignment


@pytest_asyncio.fixture(autouse=True)
async def _database() -> AsyncIterator[None]:
    await engine.dispose()
    try:
        async with engine.connect():
            pass
    except Exception:  # pragma: no cover
        pytest.skip("Postgres is not reachable; skipping authorization tests")
    yield
    await engine.dispose()


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http:
        yield http


@pytest_asyncio.fixture
async def auth(client: AsyncClient) -> AsyncIterator[dict[str, Any]]:
    email = f"rbac-{uuid.uuid4().hex[:12]}@example.test"
    response = await client.post(
        "/auth/signup",
        json={"email": email, "display_name": "RBAC Tester", "password": "password123"},
    )
    assert response.status_code in (200, 201), response.text
    payload = response.json()
    headers = {"Authorization": f"Bearer {payload['access_token']}"}
    user_id = uuid.UUID(payload["user"]["id"])

    yield {"headers": headers, "user_id": user_id}

    async with AsyncSessionLocal() as db:
        agent_ids = (
            await db.execute(select(Agent.id).where(Agent.owner_user_id == user_id))
        ).scalars().all()
        if agent_ids:
            await db.execute(delete(AgentDownload).where(AgentDownload.agent_id.in_(agent_ids)))
            await db.execute(delete(Agent).where(Agent.id.in_(agent_ids)))
        await db.execute(
            delete(AuthUserRoleAssignment).where(AuthUserRoleAssignment.user_id == user_id)
        )
        await db.execute(delete(CustomAgentType).where(CustomAgentType.owner_user_id == user_id))
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


@pytest.mark.asyncio
async def test_signup_assigns_user_role(client: AsyncClient, auth: dict[str, Any]):
    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(AuthUserRoleAssignment.role_id).where(
                    AuthUserRoleAssignment.user_id == auth["user_id"]
                )
            )
        ).scalars().all()
    assert USER_ROLE_ID in rows


@pytest.mark.asyncio
async def test_user_without_agent_create_cannot_create_local_agent(
    client: AsyncClient, auth: dict[str, Any]
):
    async with AsyncSessionLocal() as db:
        from app.models.authorization import AuthRolePermission

        await db.execute(
            delete(AuthUserRoleAssignment).where(
                AuthUserRoleAssignment.user_id == auth["user_id"],
                AuthUserRoleAssignment.role_id != USER_ROLE_ID,
            )
        )
        await db.commit()

    response = await client.post(
        "/guild/agents/local",
        headers=auth["headers"],
        json={
            "name": "Denied",
            "agent_key": f"denied_{uuid.uuid4().hex[:8]}",
            "hosting_mode": "hosted",
            "capabilities": [],
        },
    )
    assert response.status_code == 403
    body = response.json()
    assert body["detail"]["code"] == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_select_session_role_returns_new_token(client: AsyncClient, auth: dict[str, Any]):
    listed = await client.get("/auth/session/roles", headers=auth["headers"])
    assert listed.status_code == 200
    roles = listed.json()
    assert len(roles) >= 1
    user_role = next((r for r in roles if r["role_slug"] == "user"), roles[0])
    picked = await client.post(
        "/auth/session/role",
        headers=auth["headers"],
        json={"assignment_id": user_role["assignment_id"]},
    )
    assert picked.status_code == 200
    body = picked.json()
    assert body["session_role"]["assignment_id"] == user_role["assignment_id"]
    assert body["access_token"]

    current = await client.get(
        "/auth/session/role",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert current.status_code == 200
    assert current.json()["role_slug"] == user_role["role_slug"]


@pytest.mark.asyncio
async def test_authorization_check_endpoint(client: AsyncClient, auth: dict[str, Any]):
    response = await client.post(
        "/authorization/check",
        headers=auth["headers"],
        json={"permission": "profile.read_self"},
    )
    assert response.status_code == 200
    assert response.json()["allowed"] is True


@pytest.mark.asyncio
async def test_list_roles_denied_without_role_list_permission(
    client: AsyncClient, auth: dict[str, Any]
):
    response = await client.get("/authorization/roles", headers=auth["headers"])
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_legacy_agents_route_requires_auth(client: AsyncClient):
    response = await client.get("/agents")
    assert response.status_code == 401
