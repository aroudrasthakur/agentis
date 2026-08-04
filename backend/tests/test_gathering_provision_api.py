"""Full-page gathering provisioning: roles, settings, invites, agents."""

from __future__ import annotations

import uuid
from typing import Any, AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.db import AsyncSessionLocal, engine
from app.main import app
from app.models import Gathering, GatheringMember, User
from app.models.authorization import (
    AuthGatheringAuthorizationSettings,
    AuthRole,
    AuthRoleCategory,
    AuthUserRoleAssignment,
    GatheringAccessMode,
)


@pytest_asyncio.fixture(autouse=True)
async def _database() -> AsyncIterator[None]:
    await engine.dispose()
    try:
        async with engine.connect():
            pass
    except Exception:  # pragma: no cover - environment dependent
        pytest.skip("Postgres is not reachable; skipping gathering provisioning tests")
    yield
    await engine.dispose()


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http:
        yield http


@pytest_asyncio.fixture
async def auth(client: AsyncClient) -> AsyncIterator[dict[str, Any]]:
    email = f"gathering-{uuid.uuid4().hex[:12]}@example.test"
    response = await client.post(
        "/auth/signup",
        json={"email": email, "display_name": "Gathering Tester", "password": "password123"},
    )
    assert response.status_code in (200, 201), response.text
    payload = response.json()
    user_id = uuid.UUID(payload["user"]["id"])

    yield {
        "headers": {"Authorization": f"Bearer {payload['access_token']}"},
        "user_id": user_id,
        "email": email,
    }

    async with AsyncSessionLocal() as db:
        gathering_ids = (
            await db.execute(select(Gathering.id).where(Gathering.owner_id == user_id))
        ).scalars().all()
        await db.execute(
            delete(AuthUserRoleAssignment).where(AuthUserRoleAssignment.user_id == user_id)
        )
        if gathering_ids:
            await db.execute(delete(Gathering).where(Gathering.id.in_(gathering_ids)))
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


@pytest.mark.asyncio
async def test_provision_creates_roles_settings_and_members(
    client: AsyncClient, auth: dict[str, Any]
):
    invitee = f"invitee-{uuid.uuid4().hex[:8]}@example.test"
    response = await client.post(
        "/gatherings/provision",
        headers=auth["headers"],
        json={
            "name": f"Reliability {uuid.uuid4().hex[:6]}",
            "description": "Owns uptime",
            "access_mode": "centrally_managed",
            "future_grants_enabled": False,
            "invite_emails": [invitee, invitee.upper(), auth["email"]],
            "agent_ids": [],
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    gathering_id = uuid.UUID(body["gathering"]["id"])

    assert body["gathering"]["role"] == "owner"
    assert body["provisioning"]["invited_emails"] == [invitee]
    assert sorted(body["provisioning"]["skipped_emails"]) == sorted(
        [invitee, auth["email"]]
    )
    assert "owner" in body["provisioning"]["access_role_slugs"]

    async with AsyncSessionLocal() as db:
        settings = await db.get(AuthGatheringAuthorizationSettings, gathering_id)
        assert settings is not None
        assert settings.access_mode == GatheringAccessMode.centrally_managed
        assert settings.future_grants_enabled is False

        roles = (
            await db.execute(
                select(AuthRole).where(
                    AuthRole.workspace_id == gathering_id,
                    AuthRole.category == AuthRoleCategory.gathering_access,
                )
            )
        ).scalars().all()
        assert {r.slug.rsplit("-", 1)[-1] for r in roles} >= {"reader", "owner"}

        owner_role = next(r for r in roles if r.slug.endswith("-owner"))
        assignment = (
            await db.execute(
                select(AuthUserRoleAssignment).where(
                    AuthUserRoleAssignment.user_id == auth["user_id"],
                    AuthUserRoleAssignment.role_id == owner_role.id,
                    AuthUserRoleAssignment.workspace_id == gathering_id,
                )
            )
        ).scalar_one_or_none()
        assert assignment is not None

        members = (
            await db.execute(
                select(GatheringMember).where(GatheringMember.gathering_id == gathering_id)
            )
        ).scalars().all()
        assert {m.invited_email for m in members} == {auth["email"], invitee}


@pytest.mark.asyncio
async def test_provision_requires_a_name(client: AsyncClient, auth: dict[str, Any]):
    response = await client.post(
        "/gatherings/provision",
        headers=auth["headers"],
        json={"name": "   "},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Name is required"


@pytest.mark.asyncio
async def test_provision_rejects_unknown_agent(client: AsyncClient, auth: dict[str, Any]):
    response = await client.post(
        "/gatherings/provision",
        headers=auth["headers"],
        json={
            "name": f"Bad agents {uuid.uuid4().hex[:6]}",
            "agent_ids": [str(uuid.uuid4())],
        },
    )
    assert response.status_code == 400
    assert "Invalid agent" in response.json()["detail"]


@pytest.mark.asyncio
async def test_provision_defaults_to_owner_managed(client: AsyncClient, auth: dict[str, Any]):
    response = await client.post(
        "/gatherings/provision",
        headers=auth["headers"],
        json={"name": f"Defaults {uuid.uuid4().hex[:6]}"},
    )
    assert response.status_code == 201, response.text
    gathering_id = uuid.UUID(response.json()["gathering"]["id"])

    async with AsyncSessionLocal() as db:
        settings = await db.get(AuthGatheringAuthorizationSettings, gathering_id)
        assert settings is not None
        assert settings.access_mode == GatheringAccessMode.owner_managed
        assert settings.future_grants_enabled is True
