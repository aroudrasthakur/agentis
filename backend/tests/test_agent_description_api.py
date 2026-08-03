"""Guild agent description list, profile, and update."""

from __future__ import annotations

import uuid
from typing import Any, AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.db import AsyncSessionLocal, engine
from app.main import app
from app.models import Agent, AgentDownload, CustomAgentType, User


@pytest_asyncio.fixture(autouse=True)
async def _database() -> AsyncIterator[None]:
    await engine.dispose()
    try:
        async with engine.connect():
            pass
    except Exception:  # pragma: no cover
        pytest.skip("Postgres is not reachable; skipping agent description API tests")
    yield
    await engine.dispose()


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http:
        yield http


@pytest_asyncio.fixture
async def auth(client: AsyncClient) -> AsyncIterator[dict[str, Any]]:
    email = f"agent-desc-{uuid.uuid4().hex[:12]}@example.test"
    response = await client.post(
        "/auth/signup",
        json={"email": email, "display_name": "Desc Tester", "password": "password123"},
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
        await db.execute(delete(CustomAgentType).where(CustomAgentType.owner_user_id == user_id))
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


async def create_agent(client: AsyncClient, headers: dict[str, str]) -> dict[str, Any]:
    response = await client.post(
        "/guild/agents/local",
        headers=headers,
        json={
            "name": "Description test agent",
            "agent_key": f"desc_test_{uuid.uuid4().hex[:12]}",
            "hosting_mode": "hosted",
            "capabilities": ["list_table_stats"],
        },
    )
    assert response.status_code in (200, 201), response.text
    return response.json()


@pytest.mark.asyncio
async def test_list_get_and_update_description(client: AsyncClient, auth: dict[str, Any]):
    headers = auth["headers"]
    agent = await create_agent(client, headers)
    agent_id = agent["id"]

    listed = await client.get("/guild/agents/descriptions", headers=headers)
    assert listed.status_code == 200
    ids = {item["agent_id"] for item in listed.json()}
    assert agent_id in ids

    profile = await client.get(f"/guild/agents/{agent_id}/description", headers=headers)
    assert profile.status_code == 200
    body = profile.json()
    assert body["agent_id"] == agent_id
    assert body["description"] in (None, "")
    assert body["description_format"] == "plain"

    updated = await client.put(
        f"/guild/agents/{agent_id}/description",
        headers=headers,
        json={
            "description": "## Purpose\n\nHelps with **Postgres**.",
            "description_format": "markdown",
        },
    )
    assert updated.status_code == 200
    data = updated.json()
    assert "Postgres" in data["description"]
    assert data["description_format"] == "markdown"
    assert isinstance(data.get("configuration_sections"), list)

    again = await client.get(f"/guild/agents/{agent_id}/description", headers=headers)
    assert again.status_code == 200
    assert again.json()["description_format"] == "markdown"


@pytest.mark.asyncio
async def test_update_description_requires_owner(client: AsyncClient, auth: dict[str, Any]):
    headers = auth["headers"]
    agent = await create_agent(client, headers)

    other_email = f"other-{uuid.uuid4().hex[:12]}@example.test"
    signup = await client.post(
        "/auth/signup",
        json={"email": other_email, "display_name": "Other", "password": "password123"},
    )
    assert signup.status_code in (200, 201)
    other_headers = {"Authorization": f"Bearer {signup.json()['access_token']}"}

    response = await client.put(
        f"/guild/agents/{agent['id']}/description",
        headers=other_headers,
        json={"description": "Nope"},
    )
    assert response.status_code == 404
