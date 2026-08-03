"""Shared base configuration every agent type inherits (BaseAgentTypeConfig)."""

from __future__ import annotations

from app.agent_types.builtin._helpers import (
    ACTIONS,
    AGENT_SELECTOR,
    AUTONOMY,
    BOOLEAN,
    DATA,
    DATA_SOURCE_SELECTOR,
    DEPLOYMENT,
    IDENTITY,
    MODEL_SELECTOR,
    MULTI_SELECT,
    NUMBER,
    SELECT,
    TEXTAREA,
    TOOL_SELECTOR,
    TOOLS,
    WORKFLOW,
    param,
    when,
)
from app.agent_types.schemas import AgentTypeParameterDefinition

AUTONOMY_LEVELS = [
    ("0", "0 — Suggestion only"),
    ("1", "1 — Single step with runtime control"),
    ("2", "2 — Multi-step within one task"),
    ("3", "3 — Multi-task within a workflow"),
    ("4", "4 — Cross-workflow autonomy"),
    ("5", "5 — Fully autonomous operation"),
]

RISK_LEVELS = [("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")]

STATE_MODES = [
    ("stateless", "Stateless"),
    ("session", "Session"),
    ("workflow", "Workflow"),
    ("long_term", "Long term"),
    ("event_based", "Event based"),
]

EXECUTION_MODES = [
    ("request_response", "Request / response"),
    ("event_driven", "Event driven"),
    ("scheduled", "Scheduled"),
    ("batch", "Batch"),
    ("continuous_monitoring", "Continuous monitoring"),
    ("interactive_workflow", "Interactive workflow"),
    ("multi_agent", "Multi-agent"),
]

FALLBACK_BEHAVIORS = [
    ("fail", "Fail"),
    ("retry", "Retry"),
    ("fallback_agent", "Hand to fallback agent"),
    ("fallback_model", "Switch to fallback model"),
    ("return_control_to_runtime", "Return control to runtime"),
]


def _definitions() -> list[AgentTypeParameterDefinition]:
    return [
        param(
            "summary",
            "Operational summary",
            TEXTAREA,
            IDENTITY,
            description="What this agent is responsible for inside the system.",
            max_length=2000,
        ),
        param(
            "autonomy_level",
            "Autonomy level",
            SELECT,
            AUTONOMY,
            required=True,
            choices=AUTONOMY_LEVELS,
            default="1",
            description="How much the agent may decide without returning control to the runtime.",
        ),
        param(
            "risk_level",
            "Risk level",
            SELECT,
            AUTONOMY,
            required=True,
            choices=RISK_LEVELS,
            default="low",
            description="Risk classification used by the runtime when planning execution.",
        ),
        param(
            "state_mode",
            "State mode",
            SELECT,
            AUTONOMY,
            required=True,
            choices=STATE_MODES,
            default="stateless",
        ),
        param(
            "execution_mode",
            "Execution mode",
            SELECT,
            AUTONOMY,
            required=True,
            choices=EXECUTION_MODES,
            default="request_response",
        ),
        param("max_steps", "Maximum steps", NUMBER, AUTONOMY, min=1, max=1000),
        param("max_tool_calls", "Maximum tool calls", NUMBER, TOOLS, min=0, max=1000),
        param("timeout_seconds", "Timeout (seconds)", NUMBER, WORKFLOW, min=1, max=86400),
        param("retry_limit", "Retry limit", NUMBER, WORKFLOW, min=0, max=20),
        param("token_budget", "Token budget", NUMBER, DEPLOYMENT, min=0),
        param("cost_budget", "Cost budget", NUMBER, DEPLOYMENT, min=0),
        param(
            "allowed_tools",
            "Allowed tools",
            TOOL_SELECTOR,
            TOOLS,
            description="Tools this agent may call. Must be a subset of registered capabilities.",
        ),
        param(
            "allowed_data_sources",
            "Allowed data sources",
            DATA_SOURCE_SELECTOR,
            DATA,
            description="Data sources this agent may read.",
        ),
        param("allowed_actions", "Allowed actions", MULTI_SELECT, ACTIONS),
        param(
            "fallback_behavior",
            "Fallback behavior",
            SELECT,
            WORKFLOW,
            required=True,
            choices=FALLBACK_BEHAVIORS,
            default="return_control_to_runtime",
            description=(
                "What happens when the agent cannot complete its work. "
                "'Return control to runtime' stops execution and hands the workflow back "
                "to the application runtime."
            ),
        ),
        param(
            "fallback_agent_id",
            "Fallback agent",
            AGENT_SELECTOR,
            WORKFLOW,
            required=True,
            visible_when=when("fallback_behavior", "equals", "fallback_agent"),
        ),
        param(
            "fallback_model_id",
            "Fallback model",
            MODEL_SELECTOR,
            WORKFLOW,
            required=True,
            visible_when=when("fallback_behavior", "equals", "fallback_model"),
        ),
        param(
            "audit_logging_enabled",
            "Audit logging enabled",
            BOOLEAN,
            DEPLOYMENT,
            required=True,
            default=True,
        ),
        param("tracing_enabled", "Tracing enabled", BOOLEAN, DEPLOYMENT, required=True, default=True),
        param(
            "evaluation_enabled",
            "Evaluation enabled",
            BOOLEAN,
            DEPLOYMENT,
            required=True,
            default=False,
        ),
    ]


BASE_PARAMETERS: list[AgentTypeParameterDefinition] = [
    definition.model_copy(update={"inherited": True}) for definition in _definitions()
]

BASE_PARAMETER_KEYS: frozenset[str] = frozenset(
    definition.key for definition in BASE_PARAMETERS
)
