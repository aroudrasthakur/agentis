from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import EventType, HostingMode, OrgTag, ParticipantKind, SessionStatus


class AgentCreate(BaseModel):
    name: str
    agent_key: str
    org_tag: OrgTag = OrgTag.external
    hosting_mode: HostingMode
    endpoint_url: str | None = None
    description: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    is_active: bool = True


class AgentUpdate(BaseModel):
    name: str | None = None
    endpoint_url: str | None = None
    description: str | None = None
    is_active: bool | None = None
    org_tag: OrgTag | None = None
    capabilities: list[str] | None = None


class AgentOut(BaseModel):
    id: UUID
    name: str
    agent_key: str
    org_tag: OrgTag
    hosting_mode: HostingMode
    endpoint_url: str | None
    description: str | None
    capabilities: list[str] = Field(default_factory=list)
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ParticipantOut(BaseModel):
    id: UUID
    session_id: UUID
    agent_id: UUID | None
    name: str
    kind: ParticipantKind
    org_tag: OrgTag
    hosting_mode: HostingMode | None
    endpoint_url: str | None
    agent_key: str | None
    granted_capabilities: list[str] | None = None
    token_expires_at: datetime | None = None
    token_revoked: bool = False

    model_config = {"from_attributes": True}


class EventOut(BaseModel):
    id: UUID
    session_id: UUID
    participant_id: UUID
    type: EventType
    content: str
    requires_approval: bool
    created_at: datetime
    sequence: int
    participant: ParticipantOut | None = None

    model_config = {"from_attributes": True}


class SessionCreate(BaseModel):
    title: str = "Customer refund request"
    agent_ids: list[UUID] = Field(default_factory=list)


class SessionOut(BaseModel):
    id: UUID
    title: str
    status: SessionStatus
    active_participant_id: UUID | None
    created_at: datetime
    share_url: str | None = None
    invite_expires_at: datetime | None = None
    participants: list[ParticipantOut] = Field(default_factory=list)
    events: list[EventOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class AttachAgentsRequest(BaseModel):
    agent_ids: list[UUID]
    # Optional per-agent capability grants; keys are agent_id strings.
    # Grant must be ⊆ agent's declared capabilities. Omit to grant full ceiling.
    capabilities: dict[str, list[str]] | None = None


class SessionCreateResponse(BaseModel):
    id: UUID
    share_url: str
    invite: str
    title: str
    status: SessionStatus
