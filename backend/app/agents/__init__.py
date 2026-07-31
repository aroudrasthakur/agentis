"""Hosted agent definitions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HostedAgentDef:
    agent_key: str
    system_prompt: str
    use_tools: bool = True
    stub_reply: str | None = None


SUPPORT_AGENT = HostedAgentDef(
    agent_key="support_agent",
    system_prompt=(
        "You are Agentis Support Agent, an internal customer support agent. "
        "You help with refund requests in a shared multi-agent session. "
        "Use tools when helpful. Be concise. Default demo order is ORD-1001. "
        "Do not claim to have issued a refund — that requires Vendor Billing and human approval."
    ),
    use_tools=True,
)

TRIAGE_AGENT = HostedAgentDef(
    agent_key="triage_agent",
    system_prompt="You are a lightweight triage agent.",
    use_tools=False,
    stub_reply=(
        "Triage complete: this looks like a billing/refund case. "
        "Handing context to Support or Vendor as needed."
    ),
)

HOSTED_AGENTS: dict[str, HostedAgentDef] = {
    SUPPORT_AGENT.agent_key: SUPPORT_AGENT,
    TRIAGE_AGENT.agent_key: TRIAGE_AGENT,
}
