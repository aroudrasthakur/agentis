"""Central securable resource type identifiers."""

from typing import Literal

SecurableResourceType = Literal[
    "account",
    "gathering",
    "agent",
    "agent_configuration",
    "agent_tool_binding",
    "agent_data_source_binding",
    "agent_type",
    "agent_type_version",
    "deployment",
    "run",
    "tool",
    "data_source",
    "action_policy",
    "gathering_membership",
    "role",
    "user",
    "audit_log",
    "application_setting",
]

SECURABLE_RESOURCE_TYPES: frozenset[str] = frozenset(
    {
        "account",
        "gathering",
        "agent",
        "agent_configuration",
        "agent_tool_binding",
        "agent_data_source_binding",
        "agent_type",
        "agent_type_version",
        "deployment",
        "run",
        "tool",
        "data_source",
        "action_policy",
        "gathering_membership",
        "role",
        "user",
        "audit_log",
        "application_setting",
    }
)
