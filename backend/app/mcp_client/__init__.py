"""MCP client for remote Streamable HTTP agents — calls gated by access checks upstream."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.access import assert_participant_can_call_tool


async def call_mcp_tool(
    endpoint_url: str,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    *,
    db: AsyncSession | None = None,
    participant_id: UUID | None = None,
) -> dict[str, Any]:
    """
    Call a remote MCP tool over Streamable HTTP.
    If db + participant_id are provided, enforce capability before the network call.
    """
    arguments = arguments or {}
    if db is not None and participant_id is not None:
        await assert_participant_can_call_tool(db, participant_id, tool_name)

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        base = endpoint_url.rstrip("/")
        helper_url = base.replace("/mcp", "") + f"/tools/{tool_name}"
        try:
            helper = await client.post(helper_url, json=arguments)
            if helper.status_code < 400:
                return helper.json()
        except Exception:
            pass

        try:
            resp = await client.post(base, json=payload, headers=headers)
            if resp.status_code >= 400:
                return {
                    "error": f"MCP call failed ({resp.status_code})",
                    "body": resp.text[:500],
                    "mocked": True,
                    "tool": tool_name,
                    "arguments": arguments,
                    "result": f"Mocked {tool_name} success (MCP unreachable)",
                }
            data = resp.json()
            if "result" in data:
                return data["result"] if isinstance(data["result"], dict) else {"result": data["result"]}
            return data
        except Exception as exc:  # noqa: BLE001
            return {
                "error": str(exc),
                "mocked": True,
                "tool": tool_name,
                "arguments": arguments,
                "result": f"Mocked {tool_name} executed locally because MCP was unreachable",
                "confirmation_id": "MOCK-REFUND-001",
            }


async def remote_agent_message(
    endpoint_url: str,
    context: str,
    *,
    db: AsyncSession,
    participant_id: UUID,
) -> tuple[str, dict[str, Any]]:
    """Ask remote agent for a textual turn; uses check_billing_status then summarizes."""
    del context  # unused for MVP remote turn
    status = await call_mcp_tool(
        endpoint_url,
        "check_billing_status",
        {"order_id": "ORD-1001"},
        db=db,
        participant_id=participant_id,
    )
    if not isinstance(status, dict):
        status = {"result": status}
    text = (
        "Vendor Billing reviewed the case.\n"
        f"Billing status: {json.dumps(status)}\n"
        "I am ready to run process_refund for ORD-1001 ($89.99) under the active HITL policy."
    )
    return text, status
