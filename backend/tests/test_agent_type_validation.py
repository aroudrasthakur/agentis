"""Validation, compatibility, conditional visibility, and version diffing."""

from __future__ import annotations

from typing import Any

import pytest

from app.agent_types.builtin import BUILT_IN_AGENT_TYPES
from app.agent_types.conditions import is_visible, visible_parameters
from app.agent_types.defaults import default_configuration, default_metric_configuration
from app.agent_types.schemas import (
    AgentParameterSection,
    AgentParameterType,
    AgentTypeDefinition,
    AgentTypeParameterDefinition,
    ParameterOption,
    ParameterValidation,
    ParameterVisibility,
)
from app.agent_types.services import compatibility, migration
from app.agent_types.services.validation import ValidationContext, validate_configuration

CONTEXT = ValidationContext(
    tools=frozenset({"list_table_stats", "suggest_indexes", "fetch_sample_explain"}),
    agent_ids=frozenset({"11111111-1111-1111-1111-111111111111"}),
    data_sources=frozenset({"postgres_metrics", "uploaded_documents", "policy_library"}),
    models=frozenset({"gpt-4o", "gpt-4o-mini"}),
)


def metrics_for(definition: AgentTypeDefinition) -> dict[str, Any]:
    return {
        key: entry.model_dump(by_alias=True)
        for key, entry in default_metric_configuration(definition).items()
    }


def base_valid_config(type_id: str, **overrides: Any) -> dict[str, Any]:
    definition = BUILT_IN_AGENT_TYPES[type_id]
    configuration = default_configuration(definition)
    for parameter in definition.parameter_definitions:
        if not parameter.required or parameter.key in configuration:
            continue
        configuration[parameter.key] = _sample_value(parameter)
    configuration.update(overrides)
    # Only keep values whose parameters are visible for the resulting configuration.
    visible = {item.key for item in visible_parameters(definition.parameter_definitions, configuration)}
    return {key: value for key, value in configuration.items() if key in visible}


def _sample_value(parameter: AgentTypeParameterDefinition) -> Any:
    kind = parameter.type
    if kind is AgentParameterType.boolean:
        return True
    if kind is AgentParameterType.number:
        rules = parameter.validation or ParameterValidation()
        return rules.min if rules.min is not None else 1
    if kind is AgentParameterType.json:
        return {"rule": "value"}
    if kind is AgentParameterType.select:
        return parameter.options[0].value if parameter.options else "value"
    if kind is AgentParameterType.multi_select:
        return [parameter.options[0].value] if parameter.options else []
    if kind is AgentParameterType.tool_selector:
        return ["list_table_stats"]
    if kind is AgentParameterType.agent_selector:
        return ["11111111-1111-1111-1111-111111111111"]
    if kind is AgentParameterType.model_selector:
        return ["gpt-4o"]
    if kind is AgentParameterType.data_source_selector:
        return ["postgres_metrics"]
    if parameter.validation and parameter.validation.pattern:
        return "test-namespace"
    return "configured value for testing purposes"


def test_complete_configuration_is_deployable():
    definition = BUILT_IN_AGENT_TYPES["task_domain"]
    result = validate_configuration(
        definition, base_valid_config("task_domain"), metrics_for(definition), CONTEXT
    )
    assert result.valid, result.errors
    assert result.deployment_blockers == []


def test_missing_required_parameters_block_deployment():
    definition = BUILT_IN_AGENT_TYPES["task_domain"]
    configuration = base_valid_config("task_domain")
    configuration.pop("domain")
    result = validate_configuration(definition, configuration, metrics_for(definition), CONTEXT)

    assert not result.valid
    assert "domain" in result.missing_required_parameters
    assert result.deployment_blockers


def test_empty_configuration_blocks_deployment():
    definition = BUILT_IN_AGENT_TYPES["user_facing"]
    result = validate_configuration(definition, {}, metrics_for(definition), CONTEXT)
    assert not result.valid
    assert "tone_guidelines" in result.missing_required_parameters


def test_number_and_length_constraints_are_enforced():
    definition = BUILT_IN_AGENT_TYPES["retrieval_context"]
    configuration = base_valid_config("retrieval_context", top_k=9999)
    result = validate_configuration(definition, configuration, metrics_for(definition), CONTEXT)
    assert not result.valid
    assert any(issue.parameter_key == "top_k" for issue in result.errors)


def test_unknown_tool_reference_is_rejected():
    definition = BUILT_IN_AGENT_TYPES["task_domain"]
    configuration = base_valid_config("task_domain", allowed_tools=["does_not_exist"])
    result = validate_configuration(definition, configuration, metrics_for(definition), CONTEXT)
    assert not result.valid
    assert any(issue.parameter_key == "allowed_tools" for issue in result.errors)


def test_unknown_agent_and_data_source_references_are_rejected():
    definition = BUILT_IN_AGENT_TYPES["orchestration"]
    configuration = base_valid_config(
        "orchestration", downstream_agents=["99999999-9999-9999-9999-999999999999"]
    )
    result = validate_configuration(definition, configuration, metrics_for(definition), CONTEXT)
    assert any(issue.parameter_key == "downstream_agents" for issue in result.errors)

    definition = BUILT_IN_AGENT_TYPES["task_domain"]
    configuration = base_valid_config("task_domain", knowledge_sources=["nope"])
    result = validate_configuration(definition, configuration, metrics_for(definition), CONTEXT)
    assert any(issue.parameter_key == "knowledge_sources" for issue in result.errors)


def test_incomplete_fallback_configuration_blocks_deployment():
    definition = BUILT_IN_AGENT_TYPES["task_domain"]
    configuration = base_valid_config("task_domain", fallback_behavior="fallback_agent")
    configuration.pop("fallback_agent_id", None)
    result = validate_configuration(definition, configuration, metrics_for(definition), CONTEXT)
    assert not result.valid
    assert any("fallback agent" in blocker.lower() for blocker in result.deployment_blockers)


def test_actions_require_the_action_agent_type():
    definition = BUILT_IN_AGENT_TYPES["user_facing"]
    configuration = base_valid_config("user_facing", allowed_actions=["delete_record"])
    result = validate_configuration(definition, configuration, metrics_for(definition), CONTEXT)
    assert not result.valid
    assert any("Action agent type" in blocker for blocker in result.deployment_blockers)


def test_high_risk_action_agent_must_expose_risk_metadata():
    definition = BUILT_IN_AGENT_TYPES["action"]
    configuration = base_valid_config("action", risk_level="critical")
    configuration.pop("reversibility")
    configuration.pop("external_systems")

    result = validate_configuration(definition, configuration, metrics_for(definition), CONTEXT)
    assert not result.valid
    blockers = " ".join(result.deployment_blockers)
    assert "reversibility" in blockers
    assert "external_systems" in blockers


def test_high_risk_agent_cannot_disable_audit_logging():
    definition = BUILT_IN_AGENT_TYPES["action"]
    configuration = base_valid_config("action", risk_level="high", audit_logging_enabled=False)
    result = validate_configuration(definition, configuration, metrics_for(definition), CONTEXT)
    assert not result.valid
    assert any("Audit logging" in blocker for blocker in result.deployment_blockers)


def test_required_metrics_must_be_configured():
    definition = BUILT_IN_AGENT_TYPES["task_domain"]
    configuration = base_valid_config("task_domain")
    metrics = metrics_for(definition)
    metrics["task_accuracy"]["enabled"] = False

    result = validate_configuration(definition, configuration, metrics, CONTEXT)
    assert not result.valid
    assert any("Required metric" in blocker for blocker in result.deployment_blockers)


def test_conditional_parameters_only_apply_when_visible():
    definition = BUILT_IN_AGENT_TYPES["orchestration"]
    by_key = {item.key: item for item in definition.parameter_definitions}
    max_depth = by_key["max_planning_depth"]

    assert is_visible(max_depth, {"planning_enabled": True}, by_key)
    assert not is_visible(max_depth, {"planning_enabled": False}, by_key)

    configuration = base_valid_config("orchestration", planning_enabled=False)
    result = validate_configuration(definition, configuration, metrics_for(definition), CONTEXT)
    assert "max_planning_depth" not in result.missing_required_parameters


def test_draft_and_archived_types_cannot_be_deployed():
    definition = BUILT_IN_AGENT_TYPES["task_domain"].model_copy(update={"status": "archived"})
    result = validate_configuration(
        definition, base_valid_config("task_domain"), metrics_for(definition), CONTEXT
    )
    assert not result.valid
    assert any("archived" in blocker.lower() for blocker in result.deployment_blockers)


def test_schema_with_human_approval_fields_is_rejected():
    definition = BUILT_IN_AGENT_TYPES["task_domain"]
    tainted = definition.model_copy(
        update={
            "parameter_definitions": [
                *definition.parameter_definitions,
                AgentTypeParameterDefinition(
                    id="x",
                    key="requires_human_approval",
                    label="Requires human approval",
                    type=AgentParameterType.boolean,
                    section=AgentParameterSection.safety,
                    required=False,
                ),
            ]
        }
    )
    result = validate_configuration(
        tainted, base_valid_config("task_domain"), metrics_for(tainted), CONTEXT
    )
    assert not result.valid
    assert any("unsupported fields" in blocker for blocker in result.deployment_blockers)


def test_compatible_values_are_preserved_and_incompatible_ones_reported():
    source = BUILT_IN_AGENT_TYPES["task_domain"]
    target = BUILT_IN_AGENT_TYPES["retrieval_context"]
    configuration = base_valid_config("task_domain")

    report = compatibility.analyze(target, configuration, previous=source)
    assert "risk_level" in report.preserved_keys
    assert "domain" in report.incompatible_keys

    carried = compatibility.carry_over(target, configuration)
    assert carried["risk_level"] == configuration["risk_level"]
    assert "domain" not in carried


def test_carry_over_drops_values_outside_new_option_set():
    definition = BUILT_IN_AGENT_TYPES["user_facing"]
    carried = compatibility.carry_over(definition, {"conversation_mode": "telepathy"})
    assert carried == {}


def test_version_migration_preview_lists_diffs():
    current = BUILT_IN_AGENT_TYPES["task_domain"]
    extra = AgentTypeParameterDefinition(
        id="new",
        key="escalation_free_new_field",
        label="New required field",
        type=AgentParameterType.text,
        section=AgentParameterSection.custom,
        required=True,
    )
    changed = [
        item.model_copy(update={"options": [ParameterOption(label="Only", value="only")]})
        if item.key == "output_format"
        else item
        for item in current.parameter_definitions
    ]
    target = current.model_copy(
        update={"version": 2, "parameter_definitions": [*changed, extra]}
    )

    preview = migration.preview(current, target, base_valid_config("task_domain"))
    assert preview.to_version == 2
    assert [item.key for item in preview.added_parameters] == ["escalation_free_new_field"]
    assert any(item.key == "output_format" for item in preview.changed_parameters)
    assert "escalation_free_new_field" in preview.newly_required_parameters
    assert preview.blocks_deployment


def test_visibility_chain_respects_hidden_parents():
    parent = AgentTypeParameterDefinition(
        id="a", key="a", label="A", type=AgentParameterType.boolean, section=AgentParameterSection.custom
    )
    child = AgentTypeParameterDefinition(
        id="b",
        key="b",
        label="B",
        type=AgentParameterType.text,
        section=AgentParameterSection.custom,
        visible_when=ParameterVisibility(parameter_key="a", operator="truthy"),
    )
    grandchild = AgentTypeParameterDefinition(
        id="c",
        key="c",
        label="C",
        type=AgentParameterType.text,
        section=AgentParameterSection.custom,
        visible_when=ParameterVisibility(parameter_key="b", operator="truthy"),
    )

    visible = visible_parameters([parent, child, grandchild], {"a": False, "b": "set"})
    assert [item.key for item in visible] == ["a"]


@pytest.mark.parametrize("type_id", sorted(BUILT_IN_AGENT_TYPES.keys() - {"custom"}))
def test_defaults_plus_samples_validate_for_every_built_in_type(type_id: str):
    definition = BUILT_IN_AGENT_TYPES[type_id]
    result = validate_configuration(
        definition, base_valid_config(type_id), metrics_for(definition), CONTEXT
    )
    assert result.valid, (type_id, result.errors)
