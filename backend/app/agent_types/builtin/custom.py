"""Picker entry for user-authored agent types.

The concrete schema is loaded from a ``custom_agent_types`` row whose id uses
the ``custom:<family>`` namespace.
"""

from __future__ import annotations

from app.agent_types.schemas import AgentTypeDefinition

TYPE = AgentTypeDefinition(
    id="custom",
    name="Custom Agent Type",
    slug="custom",
    description=(
        "A type you define yourself. Build the parameter sections, validation rules, and "
        "recommended metrics in the Custom Agent Type builder, then assign that type to an agent."
    ),
    use_cases=[
        "Agents that do not fit a built-in category",
        "Organization-specific configuration standards",
        "Extending a built-in type with extra parameters",
    ],
    capabilities=["Declarative, user-defined configuration schema"],
    default_autonomy_level=1,
    default_risk_level="low",
    parameter_definitions=[],
    metric_definitions=[],
)
