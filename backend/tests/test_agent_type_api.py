"""End-to-end coverage for assignment, deployment gating, versioning, and migration.

These tests run against the configured Postgres database (the same one the dev
server uses) and clean up every row they create. They are skipped when the
database is unreachable.
"""

from __future__ import annotations

import uuid
from typing import Any, AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.agent_types.builtin import BUILT_IN_AGENT_TYPES
from app.agent_types.defaults import default_metric_configuration
from app.db import AsyncSessionLocal, engine
from app.main import app
from app.models import Agent, AgentDownload, CustomAgentType, User


@pytest_asyncio.fixture(autouse=True)
async def _database() -> AsyncIterator[None]:
    """Each test runs on its own event loop, so pooled connections cannot be shared."""
    await engine.dispose()
    try:
        async with engine.connect():
            pass
    except Exception:  # pragma: no cover - environment dependent
        pytest.skip("Postgres is not reachable; skipping agent type API tests")
    yield
    await engine.dispose()


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http:
        yield http


@pytest_asyncio.fixture
async def auth(client: AsyncClient) -> AsyncIterator[dict[str, Any]]:
    email = f"agent-types-{uuid.uuid4().hex[:12]}@example.test"
    response = await client.post(
        "/auth/signup",
        json={"email": email, "display_name": "Type Tester", "password": "password123"},
    )
    assert response.status_code in (200, 201), response.text
    payload = response.json()
    base = {"Authorization": f"Bearer {payload['access_token']}"}
    from tests.session_roles import select_session_role

    creator = await select_session_role(client, base, "agent-creator")
    developer = await select_session_role(client, base, "agent-developer")
    operator = await select_session_role(client, base, "agent-operator")
    designer = await select_session_role(client, base, "agent-type-designer")
    user_id = uuid.UUID(payload["user"]["id"])

    yield {
        "headers": creator,
        "creator": creator,
        "developer": developer,
        "operator": operator,
        "designer": designer,
        "user_id": user_id,
    }

    async with AsyncSessionLocal() as db:
        agent_ids = (
            await db.execute(select(Agent.id).where(Agent.owner_user_id == user_id))
        ).scalars().all()
        if agent_ids:
            await db.execute(delete(AgentDownload).where(AgentDownload.agent_id.in_(agent_ids)))
            await db.execute(delete(Agent).where(Agent.id.in_(agent_ids)))
        await db.execute(delete(CustomAgentType).where(CustomAgentType.owner_user_id == user_id))
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


async def create_agent(client: AsyncClient, headers: dict[str, str], name="Type test agent"):
    response = await client.post(
        "/guild/agents/local",
        headers=headers,
        json={
            "name": name,
            "agent_key": f"type_test_{uuid.uuid4().hex[:12]}",
            "hosting_mode": "hosted",
            "capabilities": ["list_table_stats"],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def task_domain_configuration(**overrides: Any) -> dict[str, Any]:
    configuration = {
        "autonomy_level": "2",
        "risk_level": "low",
        "state_mode": "session",
        "execution_mode": "request_response",
        "fallback_behavior": "return_control_to_runtime",
        "audit_logging_enabled": True,
        "tracing_enabled": True,
        "evaluation_enabled": False,
        "domain": "PostgreSQL performance",
        "supported_tasks": ["analysis"],
        "input_formats": ["plain_text"],
        "output_format": "markdown",
        "structured_output_required": False,
        "domain_instructions": "Analyze database performance and recommend indexes clearly.",
        "knowledge_sources": ["postgres_metrics"],
        "required_evidence": ["tool_output"],
        "confidence_threshold": 0.7,
        "data_freshness_requirement": "any",
        "failure_behavior": "return_control_to_runtime",
        "domain_validation_rules": {"requires_evidence": True},
        "unsupported_task_behavior": "decline",
        "allowed_tool_categories": ["read_only"],
    }
    configuration.update(overrides)
    return configuration


def task_domain_metrics() -> dict[str, Any]:
    return {
        key: entry.model_dump(by_alias=True)
        for key, entry in default_metric_configuration(BUILT_IN_AGENT_TYPES["task_domain"]).items()
    }


async def configure_valid_agent(client: AsyncClient, auth: dict[str, Any]) -> dict[str, Any]:
    creator = auth["creator"]
    developer = auth["developer"]
    agent = await create_agent(client, creator)
    assign = await client.post(
        f"/guild/agents/{agent['id']}/type",
        headers=developer,
        json={"typeId": "task_domain", "configuration": task_domain_configuration()},
    )
    assert assign.status_code == 200, assign.text
    save = await client.patch(
        f"/guild/agents/{agent['id']}/type/configuration",
        headers=developer,
        json={
            "configuration": task_domain_configuration(),
            "metricConfiguration": task_domain_metrics(),
        },
    )
    assert save.status_code == 200, save.text
    return save.json()["agent"]


async def post_deploy(client: AsyncClient, auth: dict[str, Any], agent_id: str):
    return await client.post(
        f"/guild/agents/{agent_id}/deploy",
        headers=auth["operator"],
    )


@pytest.mark.asyncio
async def test_new_agent_is_inactive_and_requires_a_type(client, auth):
    agent = await create_agent(client, auth["creator"])
    assert agent["is_active"] is False
    assert agent["requires_type_setup"] is True
    assert agent["deployment_ready"] is False

    readiness = await client.get(
        f"/guild/agents/{agent['id']}/deployment-readiness", headers=auth["developer"]
    )
    assert readiness.status_code == 200
    body = readiness.json()
    assert body["canDeploy"] is False
    assert "No agent type selected" in body["deploymentBlockers"]


@pytest.mark.asyncio
async def test_deploy_is_blocked_without_a_type(client, auth):
    agent = await create_agent(client, auth["creator"])
    response = await post_deploy(client, auth, agent["id"])
    assert response.status_code == 400
    assert "No agent type selected" in response.json()["detail"]


@pytest.mark.asyncio
async def test_deploy_is_blocked_while_required_parameters_are_missing(client, auth):
    agent = await create_agent(client, auth["creator"])
    assign = await client.post(
        f"/guild/agents/{agent['id']}/type",
        headers=auth["developer"],
        json={"typeId": "task_domain"},
    )
    assert assign.status_code == 200, assign.text
    assert assign.json()["validation"]["valid"] is False
    assert "domain" in assign.json()["validation"]["missingRequiredParameters"]

    deploy = await post_deploy(client, auth, agent["id"])
    assert deploy.status_code == 400


@pytest.mark.asyncio
async def test_valid_configuration_can_be_deployed_and_activates_the_agent(client, auth):
    agent = await configure_valid_agent(client, auth)
    deploy = await post_deploy(client, auth, agent["id"])
    assert deploy.status_code == 200, deploy.text

    body = deploy.json()
    assert body["agent"]["is_active"] is True
    assert body["agent"]["deployed_type_id"] == "task_domain"
    assert body["agent"]["deployment_ready"] is True
    assert body["readiness"]["canDeploy"] is True
    assert body["readiness"]["deployedAt"]


@pytest.mark.asyncio
async def test_deployed_snapshot_survives_later_configuration_edits(client, auth):
    agent = await configure_valid_agent(client, auth)
    await post_deploy(client, auth, agent["id"])

    edited = await client.patch(
        f"/guild/agents/{agent['id']}/type/configuration",
        headers=auth["developer"],
        json={
            "configuration": task_domain_configuration(domain="Something else entirely"),
            "metricConfiguration": task_domain_metrics(),
        },
    )
    assert edited.status_code == 200

    async with AsyncSessionLocal() as db:
        row = await db.get(Agent, uuid.UUID(agent["id"]))
        assert row is not None
        assert row.agent_type_configuration["domain"] == "Something else entirely"
        assert row.deployed_configuration["domain"] == "PostgreSQL performance"


@pytest.mark.asyncio
async def test_changing_type_preserves_compatible_values_and_revalidates(client, auth):
    agent = await configure_valid_agent(client, auth)

    response = await client.post(
        f"/guild/agents/{agent['id']}/type",
        headers=auth["developer"],
        json={"typeId": "retrieval_context"},
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert "risk_level" in body["compatibility"]["preservedKeys"]
    assert "domain" in body["compatibility"]["incompatibleKeys"]
    assert body["agent"]["agent_type_id"] == "retrieval_context"
    assert "domain" not in body["agent"]["agent_type_configuration"]
    assert body["validation"]["valid"] is False


@pytest.mark.asyncio
async def test_undeployed_agent_cannot_be_activated_or_attached(client, auth):
    agent = await configure_valid_agent(client, auth)

    activate = await client.patch(
        f"/guild/agents/{agent['id']}",
        headers=auth["developer"],
        json={"is_active": True},
    )
    assert activate.status_code == 400
    assert "has not been deployed" in activate.json()["detail"]

    session = await client.post("/sessions", json={"title": "Gate test", "agent_ids": []})
    assert session.status_code == 201, session.text
    created = session.json()
    attach = await client.post(
        f"/sessions/{created['id']}/agents?invite={created['invite']}",
        json={"agent_ids": [agent["id"]]},
    )
    assert attach.status_code == 400


@pytest.mark.asyncio
async def test_attachable_list_only_contains_deployed_agents(client, auth):
    agent = await configure_valid_agent(client, auth)

    before = await client.get("/guild/agents/attachable", headers=auth["creator"])
    assert agent["id"] not in [item["id"] for item in before.json()]

    await post_deploy(client, auth, agent["id"])

    after = await client.get("/guild/agents/attachable", headers=auth["creator"])
    assert agent["id"] in [item["id"] for item in after.json()]


@pytest.mark.asyncio
async def test_built_in_catalog_exposes_no_human_loop_configuration(client, auth):
    headers = auth["designer"]
    listing = await client.get("/agent-types", headers=headers)
    assert listing.status_code == 200
    built_in = [item for item in listing.json() if item["builtIn"]]
    assert len(built_in) == 10

    for summary in built_in:
        detail = await client.get(f"/agent-types/{summary['id']}", headers=headers)
        assert detail.status_code == 200
        payload = detail.text.lower()
        for term in ("approval", "reviewer", "human_intervention", "hitl", "escalation"):
            assert term not in payload, f"{summary['id']} exposes '{term}'"


@pytest.mark.asyncio
async def test_custom_type_rejects_human_approval_fields(client, auth):
    headers = auth["designer"]
    response = await client.post(
        "/agent-types/custom",
        headers=headers,
        json={
            "name": "Needs approval",
            "parameterDefinitions": [
                {
                    "id": "",
                    "key": "requires_approval",
                    "label": "Requires approval",
                    "type": "boolean",
                    "section": "safety",
                    "required": True,
                }
            ],
        },
    )
    assert response.status_code == 400
    assert "human" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_custom_type_editing_creates_a_new_version_when_in_use(client, auth):
    creator = auth["creator"]
    headers = auth["designer"]
    created = await client.post(
        "/agent-types/custom",
        headers=headers,
        json={
            "name": f"Ops helper {uuid.uuid4().hex[:6]}",
            "description": "Custom type used by tests",
            "status": "active",
            "parameterDefinitions": [
                {
                    "id": "",
                    "key": "queue_name",
                    "label": "Queue name",
                    "type": "text",
                    "section": "custom",
                    "required": True,
                }
            ],
            "metricDefinitions": [
                {
                    "id": "",
                    "key": "queue_depth",
                    "label": "Queue depth",
                    "category": "reliability",
                    "unit": "count",
                    "direction": "lower_is_better",
                    "required": False,
                }
            ],
        },
    )
    assert created.status_code == 201, created.text
    custom = created.json()
    assert custom["version"] == 1

    agent = await create_agent(client, creator, name="Custom typed agent")
    assign = await client.post(
        f"/guild/agents/{agent['id']}/type",
        headers=creator,
        json={
            "typeId": custom["id"],
            "configuration": task_domain_configuration(queue_name="jobs"),
        },
    )
    assert assign.status_code == 200, assign.text
    assert assign.json()["agent"]["agent_type_version"] == 1

    updated = await client.patch(
        f"/agent-types/custom/{custom['familyId']}",
        headers=headers,
        json={
            "parameterDefinitions": [
                {
                    "id": "",
                    "key": "queue_name",
                    "label": "Queue name",
                    "type": "text",
                    "section": "custom",
                    "required": True,
                },
                {
                    "id": "",
                    "key": "max_backlog",
                    "label": "Max backlog",
                    "type": "number",
                    "section": "custom",
                    "required": True,
                },
            ]
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["version"] == 2

    # The assigned agent stays on version 1 until it is migrated.
    agent_after = await client.get(f"/guild/agents/{agent['id']}", headers=creator)
    assert agent_after.json()["agent_type_version"] == 1

    preview = await client.get(
        f"/guild/agents/{agent['id']}/type/migration-preview", headers=auth["developer"]
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["fromVersion"] == 1
    assert body["toVersion"] == 2
    assert [item["key"] for item in body["addedParameters"]] == ["max_backlog"]
    assert "max_backlog" in body["newlyRequiredParameters"]
    assert body["blocksDeployment"] is True

    migrated = await client.post(
        f"/guild/agents/{agent['id']}/type/migrate",
        headers=auth["developer"],
        json={"targetVersion": 2},
    )
    assert migrated.status_code == 200, migrated.text
    assert migrated.json()["agent"]["agent_type_version"] == 2
    assert migrated.json()["validation"]["valid"] is False


@pytest.mark.asyncio
async def test_archived_custom_type_cannot_be_assigned(client, auth):
    creator = auth["creator"]
    headers = auth["designer"]
    created = await client.post(
        "/agent-types/custom",
        headers=headers,
        json={"name": f"Archived type {uuid.uuid4().hex[:6]}", "status": "active"},
    )
    assert created.status_code == 201
    custom = created.json()

    archived = await client.post(
        f"/agent-types/custom/{custom['familyId']}/archive", headers=headers
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"

    agent = await create_agent(client, creator, name="Archived assignment")
    response = await client.post(
        f"/guild/agents/{agent['id']}/type",
        headers=auth["developer"],
        json={"typeId": custom["id"]},
    )
    assert response.status_code == 400
    assert "archived" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_action_agent_requires_risk_metadata_before_deploying(client, auth):
    creator = auth["creator"]
    developer = auth["developer"]
    agent = await create_agent(client, creator, name="Action agent")
    definition = BUILT_IN_AGENT_TYPES["action"]

    configuration = {
        "autonomy_level": "1",
        "risk_level": "critical",
        "state_mode": "stateless",
        "execution_mode": "request_response",
        "fallback_behavior": "return_control_to_runtime",
        "audit_logging_enabled": True,
        "tracing_enabled": True,
        "evaluation_enabled": False,
        "action_catalog": ["issue_refund"],
        "action_categories": ["financial"],
        "action_risk_classification": "critical",
        "runtime_confirmation_requirement": "always",
        "rollback_supported": False,
        "idempotency_behavior": "idempotency_key",
        "transaction_limits": {"max_amount": 100},
        "retry_safety": "retry_with_key",
        "audit_requirements": ["action_log"],
        "dry_run_supported": True,
        "action_validation_rules": {"amount_positive": True},
        "partial_failure_behavior": "return_control_to_runtime",
        "duplicate_action_prevention": "idempotency_key",
    }
    metrics = {
        key: entry.model_dump(by_alias=True)
        for key, entry in default_metric_configuration(definition).items()
    }

    assign = await client.post(
        f"/guild/agents/{agent['id']}/type",
        headers=developer,
        json={"typeId": "action", "configuration": configuration, "metricConfiguration": metrics},
    )
    assert assign.status_code == 200, assign.text
    blockers = " ".join(assign.json()["validation"]["deploymentBlockers"])
    assert "Action permissions are not configured" in blockers
    assert "Missing high-risk action metadata: required_permissions" in blockers
    assert "Missing high-risk action metadata: external_systems" in blockers

    complete = {
        **configuration,
        "required_permissions": ["billing"],
        "reversibility": "partially_reversible",
        "external_systems": ["payments"],
        "result_verification": "read_back",
    }
    saved = await client.patch(
        f"/guild/agents/{agent['id']}/type/configuration",
        headers=developer,
        json={"configuration": complete, "metricConfiguration": metrics},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["validation"]["valid"] is True, saved.json()["validation"]["errors"]

    deploy = await post_deploy(client, auth, agent["id"])
    assert deploy.status_code == 200, deploy.text


@pytest.mark.asyncio
async def test_validate_endpoint_does_not_persist_changes(client, auth):
    agent = await configure_valid_agent(client, auth)
    response = await client.post(
        f"/guild/agents/{agent['id']}/validate",
        headers=auth["developer"],
        json={"configuration": {"risk_level": "low"}},
    )
    assert response.status_code == 200
    assert response.json()["valid"] is False

    async with AsyncSessionLocal() as db:
        row = await db.get(Agent, uuid.UUID(agent["id"]))
        assert row is not None
        assert row.agent_type_configuration["domain"] == "PostgreSQL performance"


@pytest.mark.asyncio
async def test_legacy_agents_without_a_type_are_left_intact_but_gated(client, auth):
    """Mirrors what migration 006 leaves behind for pre-existing rows."""
    async with AsyncSessionLocal() as db:
        legacy = Agent(
            name="Legacy agent",
            agent_key=f"legacy_{uuid.uuid4().hex[:12]}",
            org_tag="Internal",
            hosting_mode="hosted",
            capabilities=["list_table_stats"],
            is_active=True,
            source="local",
            owner_user_id=auth["user_id"],
        )
        db.add(legacy)
        await db.commit()
        await db.refresh(legacy)
        legacy_id = legacy.id
        assert legacy.agent_type_id is None
        assert legacy.capabilities == ["list_table_stats"]

    attachable = await client.get("/guild/agents/attachable", headers=auth["creator"])
    assert str(legacy_id) not in [item["id"] for item in attachable.json()]

    listing = await client.get("/guild/agents?tab=local", headers=auth["creator"])
    entry = next(item for item in listing.json() if item["id"] == str(legacy_id))
    assert entry["requires_type_setup"] is True
    assert entry["capabilities"] == ["list_table_stats"]
