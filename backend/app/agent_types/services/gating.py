"""Deployment gates applied outside the agent type UI.

An agent may only be activated, attached to a session, or added to a gathering
once it has a valid agent type configuration deployed.
"""

from __future__ import annotations

from app.models import Agent


def deployment_block_reason(agent: Agent) -> str | None:
    """Return why the agent may not be used yet, or None when it is deployable."""
    if agent.agent_type_id is None:
        return (
            f"'{agent.name}' has no agent type. Select and configure a type before using it."
        )
    if agent.deployed_type_id is None:
        return (
            f"'{agent.name}' has an agent type but has not been deployed yet. "
            "Complete its configuration and deploy it."
        )
    status = agent.agent_type_validation_status or {}
    if not status.get("valid", False):
        return (
            f"'{agent.name}' has an invalid agent type configuration. "
            "Resolve the deployment blockers and redeploy."
        )
    return None


def is_deployable(agent: Agent) -> bool:
    return deployment_block_reason(agent) is None
