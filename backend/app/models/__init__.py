import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class OrgTag(str, enum.Enum):
    internal = "Internal"
    external = "External"


class HostingMode(str, enum.Enum):
    hosted = "hosted"
    remote_mcp = "remote_mcp"


class SessionStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    completed = "completed"


class ParticipantKind(str, enum.Enum):
    human = "human"
    internal_agent = "internal_agent"
    external_agent = "external_agent"


class EventType(str, enum.Enum):
    message = "message"
    action_pending = "action_pending"
    action_approved = "action_approved"
    action_denied = "action_denied"
    redirect = "redirect"
    handoff = "handoff"
    agent_attached = "agent_attached"
    agent_detached = "agent_detached"
    plan_proposed = "plan_proposed"
    plan_approved = "plan_approved"
    plan_denied = "plan_denied"
    action_executed = "action_executed"


class ActionPolicyMode(str, enum.Enum):
    step_by_step = "step_by_step"
    confidence_gated = "confidence_gated"
    plan_then_execute = "plan_then_execute"


class SessionNature(str, enum.Enum):
    """Immutable purpose of a session — set at creation only."""

    training = "training"
    multi_agent = "multi_agent"


class AgentSource(str, enum.Enum):
    local = "local"
    downloaded = "downloaded"
    directory = "directory"


class AgoraMemberRole(str, enum.Enum):
    owner = "owner"
    member = "member"


org_tag_enum = Enum(OrgTag, name="org_tag", values_callable=lambda x: [e.value for e in x])
hosting_mode_enum = Enum(
    HostingMode, name="hosting_mode", values_callable=lambda x: [e.value for e in x]
)
session_status_enum = Enum(
    SessionStatus, name="session_status", values_callable=lambda x: [e.value for e in x]
)
participant_kind_enum = Enum(
    ParticipantKind, name="participant_kind", values_callable=lambda x: [e.value for e in x]
)
event_type_enum = Enum(EventType, name="event_type", values_callable=lambda x: [e.value for e in x])
action_policy_mode_enum = Enum(
    ActionPolicyMode,
    name="action_policy_mode",
    values_callable=lambda x: [e.value for e in x],
)
session_nature_enum = Enum(
    SessionNature, name="session_nature", values_callable=lambda x: [e.value for e in x]
)
agent_source_enum = Enum(
    AgentSource, name="agent_source", values_callable=lambda x: [e.value for e in x]
)
agora_member_role_enum = Enum(
    AgoraMemberRole, name="agora_member_role", values_callable=lambda x: [e.value for e in x]
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owned_agoras: Mapped[list["Agora"]] = relationship(back_populates="owner")
    memberships: Mapped[list["AgoraMember"]] = relationship(back_populates="user")
    agents: Mapped[list["Agent"]] = relationship(back_populates="owner")
    downloads: Mapped[list["AgentDownload"]] = relationship(back_populates="user")


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    org_tag: Mapped[OrgTag] = mapped_column(org_tag_enum, nullable=False)
    hosting_mode: Mapped[HostingMode] = mapped_column(hosting_mode_enum, nullable=False)
    endpoint_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    capabilities: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source: Mapped[AgentSource] = mapped_column(
        agent_source_enum, default=AgentSource.directory, nullable=False
    )
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    participants: Mapped[list["Participant"]] = relationship(back_populates="agent")
    owner: Mapped[User | None] = relationship(back_populates="agents")
    agora_links: Mapped[list["AgoraAgent"]] = relationship(back_populates="agent")
    downloads: Mapped[list["AgentDownload"]] = relationship(back_populates="agent")


class AgentDownload(Base):
    __tablename__ = "agent_downloads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="downloads")
    agent: Mapped[Agent] = relationship(back_populates="downloads")


class Agora(Base):
    __tablename__ = "agoras"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner: Mapped[User] = relationship(back_populates="owned_agoras")
    members: Mapped[list["AgoraMember"]] = relationship(
        back_populates="agora", cascade="all, delete-orphan"
    )
    agents: Mapped[list["AgoraAgent"]] = relationship(
        back_populates="agora", cascade="all, delete-orphan"
    )
    sessions: Mapped[list["Session"]] = relationship(back_populates="agora")


class AgoraMember(Base):
    __tablename__ = "agora_members"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agora_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agoras.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    invited_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    role: Mapped[AgoraMemberRole] = mapped_column(
        agora_member_role_enum, default=AgoraMemberRole.member, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    agora: Mapped[Agora] = relationship(back_populates="members")
    user: Mapped[User | None] = relationship(back_populates="memberships")


class AgoraAgent(Base):
    __tablename__ = "agora_agents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agora_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agoras.id", ondelete="CASCADE"), nullable=False
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    agora: Mapped[Agora] = relationship(back_populates="agents")
    agent: Mapped[Agent] = relationship(back_populates="agora_links")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[SessionStatus] = mapped_column(
        session_status_enum, default=SessionStatus.active, nullable=False
    )
    nature: Mapped[SessionNature] = mapped_column(
        session_nature_enum, default=SessionNature.multi_agent, nullable=False
    )
    agora_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agoras.id", ondelete="SET NULL"), nullable=True
    )
    active_participant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    invite_jti: Mapped[str | None] = mapped_column(String(64), nullable=True)
    invite_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    agora: Mapped[Agora | None] = relationship(back_populates="sessions")
    participants: Mapped[list["Participant"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )
    events: Mapped[list["Event"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="Event.sequence"
    )


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[ParticipantKind] = mapped_column(participant_kind_enum, nullable=False)
    org_tag: Mapped[OrgTag] = mapped_column(org_tag_enum, nullable=False)
    hosting_mode: Mapped[HostingMode | None] = mapped_column(hosting_mode_enum, nullable=True)
    endpoint_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    agent_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    granted_capabilities: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    token_jti: Mapped[str | None] = mapped_column(String(64), nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    token_revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped["Session"] = relationship(back_populates="participants", foreign_keys=[session_id])
    agent: Mapped[Agent | None] = relationship(back_populates="participants")
    events: Mapped[list["Event"]] = relationship(back_populates="participant")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("participants.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[EventType] = mapped_column(event_type_enum, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)

    session: Mapped["Session"] = relationship(back_populates="events")
    participant: Mapped["Participant"] = relationship(back_populates="events")


class ActionPolicy(Base):
    __tablename__ = "action_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_type: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    mode: Mapped[ActionPolicyMode] = mapped_column(action_policy_mode_enum, nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PolicyChangeEvent(Base):
    __tablename__ = "policy_change_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_type: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    before: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    after: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
