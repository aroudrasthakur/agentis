from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agent_types.builtin import BUILT_IN_AGENT_TYPES
from app.agent_types.defaults import default_metric_configuration
from app.config import get_settings
from app.models import (
    Agent,
    AgentSource,
    Event,
    EventType,
    HostingMode,
    OrgTag,
    Participant,
    ParticipantKind,
    Session,
)
from app.services.tokens import (
    TokenError,
    intersect_capabilities,
    mint_agent_access_token,
    mint_session_invite,
)


from app.agents import TEST_AGENT_KEY


DEFAULT_CAPABILITIES: dict[str, list[str]] = {
    TEST_AGENT_KEY: [
        "fetch_sample_explain",
        "list_table_stats",
        "suggest_indexes",
    ],
}

async def next_sequence(db: AsyncSession, session_id: UUID) -> int:
    result = await db.execute(
        select(func.coalesce(func.max(Event.sequence), 0)).where(Event.session_id == session_id)
    )
    return int(result.scalar_one()) + 1


async def create_event(
    db: AsyncSession,
    *,
    session_id: UUID,
    participant_id: UUID,
    event_type: EventType,
    content: str,
    requires_approval: bool = False,
) -> Event:
    seq = await next_sequence(db, session_id)
    event = Event(
        session_id=session_id,
        participant_id=participant_id,
        type=event_type,
        content=content,
        requires_approval=requires_approval,
        sequence=seq,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event


def kind_for_agent(agent: Agent) -> ParticipantKind:
    if agent.hosting_mode == HostingMode.hosted:
        return ParticipantKind.internal_agent
    return ParticipantKind.external_agent


async def attach_agent_to_session(
    db: AsyncSession,
    session: Session,
    agent: Agent,
    human: Participant | None = None,
    requested_capabilities: list[str] | None = None,
) -> tuple[Participant, Event]:
    try:
        granted = intersect_capabilities(agent.capabilities, requested_capabilities)
    except TokenError as exc:
        raise ValueError(str(exc)) from exc

    participant = Participant(
        session_id=session.id,
        agent_id=agent.id,
        name=agent.name,
        kind=kind_for_agent(agent),
        org_tag=agent.org_tag,
        hosting_mode=agent.hosting_mode,
        endpoint_url=agent.endpoint_url,
        agent_key=agent.agent_key,
        granted_capabilities=granted,
    )
    db.add(participant)
    await db.flush()

    token, claims = mint_agent_access_token(
        session_id=session.id,
        participant_id=participant.id,
        capabilities=granted,
    )
    participant.access_token = token
    participant.token_jti = claims.jti
    participant.token_expires_at = claims.exp
    participant.token_revoked_at = None

    actor = human
    if actor is None:
        result = await db.execute(
            select(Participant).where(
                Participant.session_id == session.id,
                Participant.kind == ParticipantKind.human,
            )
        )
        actor = result.scalar_one()

    caps_label = ", ".join(granted) if granted else "none"
    event = await create_event(
        db,
        session_id=session.id,
        participant_id=actor.id,
        event_type=EventType.agent_attached,
        content=(
            f"Attached {agent.name} ({agent.org_tag.value}, {agent.hosting_mode.value}) "
            f"with scoped capabilities: [{caps_label}]"
        ),
    )
    return participant, event


async def get_session_full(db: AsyncSession, session_id: UUID) -> Session | None:
    result = await db.execute(
        select(Session)
        .where(Session.id == session_id)
        .options(
            selectinload(Session.participants),
            selectinload(Session.events).selectinload(Event.participant),
        )
    )
    return result.scalar_one_or_none()


def _test_agent_type_configuration(capabilities: list[str]) -> dict[str, Any]:
    """A complete Task / Domain type configuration for the seeded test agent."""
    return {
        "autonomy_level": "2",
        "risk_level": "low",
        "state_mode": "session",
        "execution_mode": "interactive_workflow",
        "allowed_tools": list(capabilities),
        "fallback_behavior": "return_control_to_runtime",
        "audit_logging_enabled": True,
        "tracing_enabled": True,
        "evaluation_enabled": False,
        "domain": "PostgreSQL performance",
        "supported_tasks": ["analysis", "diagnosis", "recommendation"],
        "input_formats": ["plain_text", "sql", "logs"],
        "output_format": "markdown",
        "structured_output_required": False,
        "domain_instructions": (
            "Analyze PostgreSQL EXPLAIN output and table statistics, then recommend indexes "
            "and query rewrites with explicit trade-offs. Cite the tool output you relied on."
        ),
        "knowledge_sources": ["postgres_metrics"],
        "required_evidence": ["tool_output"],
        "confidence_threshold": 0.7,
        "data_freshness_requirement": "any",
        "failure_behavior": "return_control_to_runtime",
        "domain_validation_rules": {
            "requires_tool_evidence": True,
            "max_recommendations": 5,
        },
        "unsupported_task_behavior": "return_control_to_runtime",
        "allowed_tool_categories": ["read_only", "analysis"],
    }


def _test_agent_metric_configuration() -> dict[str, Any]:
    definition = BUILT_IN_AGENT_TYPES["task_domain"]
    return {
        key: entry.model_dump(by_alias=True)
        for key, entry in default_metric_configuration(definition).items()
    }


def _apply_test_agent_type(agent: Agent) -> None:
    """Keep the seeded demo agent deployable under the agent type requirement."""
    definition = BUILT_IN_AGENT_TYPES["task_domain"]
    configuration = _test_agent_type_configuration(list(agent.capabilities or []))
    metrics = _test_agent_metric_configuration()

    agent.agent_type_id = definition.id
    agent.agent_type_version = definition.version
    agent.agent_type_configuration = configuration
    agent.agent_metric_configuration = metrics
    agent.agent_type_validation_status = {
        "valid": True,
        "errors": [],
        "missingRequiredParameters": [],
        "deploymentBlockers": [],
        "requiresTypeSetup": False,
        "checkedAt": datetime.now(timezone.utc).isoformat(),
    }
    agent.deployed_type_id = definition.id
    agent.deployed_type_version = definition.version
    agent.deployed_configuration = configuration
    agent.deployed_metric_configuration = metrics
    agent.deployed_at = agent.deployed_at or datetime.now(timezone.utc)


async def seed_default_agents(db: AsyncSession) -> None:
    """Retire legacy demo agents and ensure a single active test agent in the registry."""
    result = await db.execute(select(Agent))
    for row in result.scalars().all():
        if row.agent_key == TEST_AGENT_KEY:
            continue
        row.is_active = False

    caps = DEFAULT_CAPABILITIES[TEST_AGENT_KEY]
    test_agent = Agent(
        name="PostgreSQL Performance Analyst",
        agent_key=TEST_AGENT_KEY,
        org_tag=OrgTag.internal,
        hosting_mode=HostingMode.hosted,
        endpoint_url=None,
        description=(
            "Test agent focused on PostgreSQL EXPLAIN analysis, table statistics, and index design. "
            "Use in gatherings to demo scoped tools and domain-specific collaboration."
        ),
        capabilities=caps,
        is_active=True,
        source=AgentSource.directory,
        is_public=True,
        version="0.1.0",
        tags=["postgresql", "performance", "database", "test"],
        notes="Single seeded test agent; legacy support/triage/vendor agents are retired.",
        metadata_={"domain": "postgresql_performance"},
    )

    existing = await db.execute(select(Agent).where(Agent.agent_key == TEST_AGENT_KEY))
    row = existing.scalar_one_or_none()
    if row is None:
        _apply_test_agent_type(test_agent)
        db.add(test_agent)
    else:
        row.name = test_agent.name
        row.description = test_agent.description
        row.capabilities = list(caps)
        row.is_active = True
        row.hosting_mode = HostingMode.hosted
        row.org_tag = OrgTag.internal
        row.endpoint_url = None
        row.tags = test_agent.tags
        row.notes = test_agent.notes
        row.version = test_agent.version
        row.metadata_ = test_agent.metadata_
        row.is_public = True
        _apply_test_agent_type(row)
    await db.commit()


def issue_session_invite(session: Session) -> str:
    token, jti, exp = mint_session_invite(session_id=session.id)
    session.invite_jti = jti
    session.invite_expires_at = exp
    return token


def session_share_url(session_id: UUID, invite: str | None = None) -> str:
    settings = get_settings()
    base = f"{settings.frontend_origin.rstrip('/')}/session/{session_id}"
    if invite:
        return f"{base}?invite={invite}"
    return base
