"""Hosted agent runtime — OpenAI + local tools with capability enforcement."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import HOSTED_AGENTS, TEST_AGENT_KEY
from app.config import get_settings
from app.services.access import assert_participant_can_call_tool
from app.services.tokens import CapabilityDenied, TokenError
from app.tools import OPENAI_TOOLS, run_tool


async def run_hosted_agent(
    *,
    db: AsyncSession,
    participant_id: UUID,
    agent_key: str,
    timeline_context: str,
    user_hint: str | None = None,
) -> str:
    definition = HOSTED_AGENTS.get(agent_key)
    settings = get_settings()
    if not settings.openai_api_key:
        if agent_key == TEST_AGENT_KEY:
            try:
                await assert_participant_can_call_tool(db, participant_id, "fetch_sample_explain")
                await assert_participant_can_call_tool(db, participant_id, "list_table_stats")
                await assert_participant_can_call_tool(db, participant_id, "suggest_indexes")
            except (TokenError, CapabilityDenied) as exc:
                return f"Access denied during analyst turn: {exc}"
            return (
                "Findings (stub mode): orders shows heavy seq_scan vs idx_scan — add an index on "
                "orders(created_at) and consider orders(customer_id, created_at) for the reporting "
                "join. Run EXPLAIN ANALYZE after indexing; expect the hash aggregate to shrink sharply."
            )
        return f"[{agent_key}] No API key configured."

    try:
        from openai import AsyncOpenAI
    except ImportError as exc:
        raise RuntimeError("openai package not installed") from exc

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    system = (
        definition.system_prompt
        if definition
        else "You are a helpful agent in an Agentis shared session. Be concise."
    )
    user_content = timeline_context
    if user_hint:
        user_content = f"{timeline_context}\n\nHuman redirect/hint: {user_hint}"

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]
    tools = OPENAI_TOOLS if (definition is None or definition.use_tools) else None

    for _ in range(4):
        kwargs: dict[str, Any] = {
            "model": settings.openai_model,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        response = await client.chat.completions.create(**kwargs)
        message = response.choices[0].message
        tool_calls = message.tool_calls or []

        if not tool_calls:
            return (message.content or "").strip() or "(no response)"

        messages.append(
            {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            }
        )

        for tc in tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            try:
                # Re-check on every tool call so mid-turn revoke blocks in-flight use
                await assert_participant_can_call_tool(db, participant_id, name)
                result = run_tool(name, args if isinstance(args, dict) else {})
            except (TokenError, CapabilityDenied) as exc:
                result = json.dumps({"error": "capability_denied", "detail": str(exc)})
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                }
            )

    return "I reached the tool-call limit for this turn."
