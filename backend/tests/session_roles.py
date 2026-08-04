"""Helpers for session-scoped RBAC in API tests."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient


async def select_session_role(
    client: AsyncClient, headers: dict[str, str], role_slug: str
) -> dict[str, str]:
    listed = await client.get("/auth/session/roles", headers=headers)
    assert listed.status_code == 200, listed.text
    options: list[dict[str, Any]] = listed.json()
    match = next((r for r in options if r["role_slug"] == role_slug), None)
    assert match is not None, f"No session role with slug {role_slug!r}; have {[r['role_slug'] for r in options]}"
    picked = await client.post(
        "/auth/session/role",
        headers=headers,
        json={"assignment_id": match["assignment_id"]},
    )
    assert picked.status_code == 200, picked.text
    token = picked.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
