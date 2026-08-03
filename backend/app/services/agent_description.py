"""Human-readable agent description and configuration profiles for the UI."""

from __future__ import annotations

import json
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.agent_types.conditions import visible_parameters
from app.agent_types.schemas import AgentParameterType, AgentTypeParameterDefinition
from app.agent_types.services import registry
from app.models import Agent

DESCRIPTION_FORMAT_KEY = "description_format"

SECTION_LABELS: dict[str, str] = {
    "identity": "Identity",
    "capabilities": "Capabilities",
    "autonomy": "Autonomy and risk",
    "tools": "Tools",
    "data": "Data",
    "actions": "Actions",
    "workflow": "Workflow",
    "evaluation": "Evaluation",
    "safety": "Safety",
    "metrics": "Metrics",
    "deployment": "Deployment",
    "custom": "Custom",
}


class ConfigFieldDisplay(BaseModel):
    key: str
    label: str
    section: str
    section_label: str
    value_display: str
    is_set: bool


class ConfigurationSectionDisplay(BaseModel):
    section: str
    section_label: str
    fields: list[ConfigFieldDisplay] = Field(default_factory=list)


class MetricSummaryDisplay(BaseModel):
    key: str
    label: str
    enabled: bool
    required: bool
    target_display: str | None = None


class AgentDescriptionSummary(BaseModel):
    agent_id: UUID
    name: str
    agent_key: str
    description_preview: str | None = None
    has_description: bool = False
    description_format: Literal["plain", "markdown"] = "plain"
    type_id: str | None = None
    type_name: str | None = None
    deployment_status: Literal["needs_type", "not_deployed", "ready", "needs_attention"]
    deployment_status_label: str
    is_active: bool
    requires_type_setup: bool
    deployment_ready: bool


class AgentDescriptionProfile(AgentDescriptionSummary):
    description: str | None = None
    hosting_mode: str
    org_tag: str
    capabilities: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None
    version: str | None = None
    type_version: int | None = None
    configuration_sections: list[ConfigurationSectionDisplay] = Field(default_factory=list)
    metrics: list[MetricSummaryDisplay] = Field(default_factory=list)
    deployed_type_id: str | None = None
    deployed_type_version: int | None = None
    deployed_at: str | None = None
    highlights: list[str] = Field(default_factory=list)


def description_format_from_metadata(metadata: dict[str, Any] | None) -> Literal["plain", "markdown"]:
    raw = dict(metadata or {}).get(DESCRIPTION_FORMAT_KEY) or dict(metadata or {}).get(
        "descriptionFormat"
    )
    return "markdown" if raw == "markdown" else "plain"


def preview_text(text: str | None, *, max_len: int = 160) -> str | None:
    if not text or not text.strip():
        return None
    one_line = " ".join(text.strip().split())
    if len(one_line) <= max_len:
        return one_line
    return one_line[: max_len - 1].rstrip() + "…"


def deployment_status(agent: Agent) -> tuple[str, str]:
    if agent.agent_type_id is None:
        return "needs_type", "Needs an agent type"
    if agent.deployed_type_id is None:
        return "not_deployed", "Not deployed yet"
    if (agent.agent_type_validation_status or {}).get("valid"):
        return "ready", "Deployed and ready"
    return "needs_attention", "Needs attention — fix configuration"


def _format_value(
    parameter: AgentTypeParameterDefinition, value: Any
) -> tuple[str, bool]:
    if value is None or value == "" or value == [] or value == {}:
        return "Not set", False

    kind = parameter.type
    options = {option.value: option.label for option in (parameter.options or [])}

    if kind is AgentParameterType.boolean:
        return ("Yes" if value else "No"), True
    if kind in (AgentParameterType.select,):
        return options.get(str(value), str(value)), True
    if kind in (
        AgentParameterType.multi_select,
        AgentParameterType.tool_selector,
        AgentParameterType.agent_selector,
        AgentParameterType.model_selector,
        AgentParameterType.data_source_selector,
    ):
        if isinstance(value, list):
            labels = [options.get(str(item), str(item)) for item in value]
            return ", ".join(labels) if labels else "Not set", bool(labels)
        return options.get(str(value), str(value)), True
    if kind is AgentParameterType.json:
        if isinstance(value, str):
            return value, True
        return json.dumps(value, indent=2), True
    if kind is AgentParameterType.number:
        return str(value), True
    if isinstance(value, list):
        return ", ".join(str(item) for item in value), True
    return str(value), True


def _configuration_sections(
    definition: Any | None, configuration: dict[str, Any]
) -> list[ConfigurationSectionDisplay]:
    if definition is None:
        return []

    visible = visible_parameters(definition.parameter_definitions, configuration)
    by_section: dict[str, list[ConfigFieldDisplay]] = {}
    for parameter in visible:
        display, is_set = _format_value(parameter, configuration.get(parameter.key))
        field = ConfigFieldDisplay(
            key=parameter.key,
            label=parameter.label,
            section=parameter.section.value,
            section_label=SECTION_LABELS.get(parameter.section.value, parameter.section.value),
            value_display=display,
            is_set=is_set,
        )
        by_section.setdefault(parameter.section.value, []).append(field)

    order = list(SECTION_LABELS.keys())
    sections: list[ConfigurationSectionDisplay] = []
    for section in order:
        fields = by_section.get(section)
        if not fields:
            continue
        sections.append(
            ConfigurationSectionDisplay(
                section=section,
                section_label=SECTION_LABELS[section],
                fields=fields,
            )
        )
    for section, fields in by_section.items():
        if section in order:
            continue
        sections.append(
            ConfigurationSectionDisplay(
                section=section,
                section_label=SECTION_LABELS.get(section, section),
                fields=fields,
            )
        )
    return sections


def _metrics_summary(
    definition: Any | None, metric_configuration: dict[str, Any]
) -> list[MetricSummaryDisplay]:
    if definition is None:
        return []
    rows: list[MetricSummaryDisplay] = []
    for metric in definition.metric_definitions:
        entry = metric_configuration.get(metric.key)
        entry = entry if isinstance(entry, dict) else {}
        enabled = bool(entry.get("enabled", entry.get("Enabled", False)))
        if not enabled and not metric.required:
            continue
        target = entry.get("targetValue", entry.get("target_value"))
        target_display = str(target) if target is not None else None
        rows.append(
            MetricSummaryDisplay(
                key=metric.key,
                label=metric.label,
                enabled=enabled or metric.required,
                required=metric.required,
                target_display=target_display,
            )
        )
    return rows


def _highlights(agent: Agent, configuration: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    if agent.capabilities:
        lines.append(f"Tools on the agent record: {', '.join(agent.capabilities)}")
    risk = configuration.get("risk_level")
    autonomy = configuration.get("autonomy_level")
    if risk or autonomy is not None:
        parts = []
        if risk:
            parts.append(f"risk {risk}")
        if autonomy is not None:
            parts.append(f"autonomy level {autonomy}")
        lines.append("Configured with " + ", ".join(parts))
    tools = configuration.get("allowed_tools")
    if isinstance(tools, list) and tools:
        lines.append(f"Type allows tools: {', '.join(str(t) for t in tools)}")
    return lines


async def build_summary(agent: Agent, *, type_name: str | None = None) -> AgentDescriptionSummary:
    status, label = deployment_status(agent)
    fmt = description_format_from_metadata(agent.metadata_)
    return AgentDescriptionSummary(
        agent_id=agent.id,
        name=agent.name,
        agent_key=agent.agent_key,
        description_preview=preview_text(agent.description),
        has_description=bool(agent.description and agent.description.strip()),
        description_format=fmt,
        type_id=agent.agent_type_id,
        type_name=type_name,
        deployment_status=status,  # type: ignore[arg-type]
        deployment_status_label=label,
        is_active=agent.is_active,
        requires_type_setup=agent.agent_type_id is None,
        deployment_ready=bool((agent.agent_type_validation_status or {}).get("valid")),
    )


async def build_profile(
    agent: Agent,
    definition: Any | None = None,
    *,
    type_name: str | None = None,
) -> AgentDescriptionProfile:
    configuration = dict(agent.agent_type_configuration or {})
    metrics_cfg = dict(agent.agent_metric_configuration or {})
    summary = await build_summary(agent, type_name=type_name)

    return AgentDescriptionProfile(
        **summary.model_dump(),
        description=agent.description,
        hosting_mode=agent.hosting_mode.value if hasattr(agent.hosting_mode, "value") else str(agent.hosting_mode),
        org_tag=agent.org_tag.value if hasattr(agent.org_tag, "value") else str(agent.org_tag),
        capabilities=list(agent.capabilities or []),
        tags=list(agent.tags or []),
        notes=agent.notes,
        version=agent.version,
        type_version=agent.agent_type_version,
        configuration_sections=_configuration_sections(definition, configuration),
        metrics=_metrics_summary(definition, metrics_cfg),
        deployed_type_id=agent.deployed_type_id,
        deployed_type_version=agent.deployed_type_version,
        deployed_at=agent.deployed_at.isoformat() if agent.deployed_at else None,
        highlights=_highlights(agent, configuration),
    )


async def resolve_type_name(db, agent: Agent) -> tuple[Any | None, str | None]:
    if not agent.agent_type_id:
        return None, None
    try:
        definition = await registry.resolve_definition(
            db, agent.agent_type_id, agent.agent_type_version
        )
        return definition, definition.name
    except registry.AgentTypeNotFoundError:
        return None, agent.agent_type_id
