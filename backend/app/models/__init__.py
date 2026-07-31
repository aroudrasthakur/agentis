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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    participants: Mapped[list["Participant"]] = relationship(back_populates="agent")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[SessionStatus] = mapped_column(
        session_status_enum, default=SessionStatus.active, nullable=False
    )
    active_participant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    invite_jti: Mapped[str | None] = mapped_column(String(64), nullable=True)
    invite_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

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
