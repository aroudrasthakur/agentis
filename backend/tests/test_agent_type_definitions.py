"""Built-in catalog shape and the human-in-the-loop exclusion rules."""

from __future__ import annotations

import pytest

from app.agent_types.builtin import BASE_PARAMETER_KEYS, BUILT_IN_AGENT_TYPES
from app.agent_types.guards import (
    ForbiddenAgentTypeFieldError,
    assert_no_human_loop_fields,
    find_forbidden_terms,
)

EXPECTED_TYPE_IDS = {
    "user_facing",
    "orchestration",
    "task_domain",
    "action",
    "evaluation",
    "governance",
    "retrieval_context",
    "memory",
    "operational",
    "custom",
}


def test_catalog_contains_exactly_the_specified_types():
    assert set(BUILT_IN_AGENT_TYPES) == EXPECTED_TYPE_IDS


def test_no_human_in_the_loop_agent_type_exists():
    names = {definition.name.lower() for definition in BUILT_IN_AGENT_TYPES.values()}
    assert not any("human" in name for name in names)
    assert "human_in_the_loop" not in BUILT_IN_AGENT_TYPES
    assert "hitl" not in BUILT_IN_AGENT_TYPES


@pytest.mark.parametrize("type_id", sorted(EXPECTED_TYPE_IDS))
def test_built_in_types_expose_no_human_approval_fields(type_id: str):
    definition = BUILT_IN_AGENT_TYPES[type_id]
    assert_no_human_loop_fields(definition.model_dump(mode="json", by_alias=True))
    sections = {parameter.section.value for parameter in definition.parameter_definitions}
    assert sections.isdisjoint({"approval", "reviewer", "human_intervention"})


@pytest.mark.parametrize("type_id", sorted(EXPECTED_TYPE_IDS))
def test_every_type_inherits_base_parameters(type_id: str):
    keys = {parameter.key for parameter in BUILT_IN_AGENT_TYPES[type_id].parameter_definitions}
    assert BASE_PARAMETER_KEYS <= keys


@pytest.mark.parametrize("type_id", sorted(EXPECTED_TYPE_IDS - {"custom"}))
def test_types_declare_parameters_and_metrics(type_id: str):
    definition = BUILT_IN_AGENT_TYPES[type_id]
    own = [p for p in definition.parameter_definitions if not p.inherited]
    assert own, f"{type_id} must define its own parameters"
    assert definition.metric_definitions, f"{type_id} must recommend metrics"
    assert any(metric.required for metric in definition.metric_definitions)


@pytest.mark.parametrize("type_id", sorted(EXPECTED_TYPE_IDS))
def test_parameter_ids_and_keys_are_unique(type_id: str):
    parameters = BUILT_IN_AGENT_TYPES[type_id].parameter_definitions
    assert len({p.key for p in parameters}) == len(parameters)
    assert len({p.id for p in parameters}) == len(parameters)


def test_guard_flags_human_approval_fields():
    payload = {
        "parameterDefinitions": [
            {"key": "requires_human_approval", "label": "Requires approval", "type": "boolean"}
        ]
    }
    assert find_forbidden_terms(payload)
    with pytest.raises(ForbiddenAgentTypeFieldError):
        assert_no_human_loop_fields(payload)


@pytest.mark.parametrize(
    "key",
    [
        "reviewer_role",
        "approval_stage",
        "review_threshold",
        "review_timeout_seconds",
        "escalation_path",
        "human_override_allowed",
        "workflow_resumption_mode",
        "human_intervention_policy",
    ],
)
def test_guard_flags_each_disallowed_concept(key: str):
    assert find_forbidden_terms({"key": key})


def test_guard_allows_runtime_control_wording():
    payload = {
        "key": "fallback_behavior",
        "options": [{"value": "return_control_to_runtime", "label": "Return control to runtime"}],
    }
    assert not find_forbidden_terms(payload)


def test_action_type_defaults_to_high_risk():
    assert BUILT_IN_AGENT_TYPES["action"].default_risk_level == "high"
