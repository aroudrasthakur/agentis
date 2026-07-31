from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import (
    ActionPolicyMode,
    AgentSource,
    AgoraMemberRole,
    EventType,
    HostingMode,
    OrgTag,
    ParticipantKind,
    SessionNature,
    SessionStatus,
)


class AgentCreate(BaseModel):
    name: str
    agent_key: str
    org_tag: OrgTag = OrgTag.external
    hosting_mode: HostingMode
    endpoint_url: str | None = None
    description: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    is_active: bool = True
    is_public: bool = False


class AgentUpdate(BaseModel):
    name: str | None = None
    endpoint_url: str | None = None
    description: str | None = None
    is_active: bool | None = None
    org_tag: OrgTag | None = None
    capabilities: list[str] | None = None
    is_public: bool | None = None


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
    source: AgentSource = AgentSource.directory
    is_public: bool = False
    owner_user_id: UUID | None = None
    created_at: datetime
    downloaded: bool = False

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
    nature: SessionNature = SessionNature.multi_agent
    agora_id: UUID | None = None


class SessionOut(BaseModel):
    id: UUID
    title: str
    status: SessionStatus
    nature: SessionNature = SessionNature.multi_agent
    agora_id: UUID | None = None
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
    nature: SessionNature = SessionNature.multi_agent
    agora_id: UUID | None = None


class UserCreate(BaseModel):
    email: str
    display_name: str
    password: str = Field(min_length=6)


class UserLogin(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: UUID
    email: str
    display_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class AgoraCreate(BaseModel):
    name: str
    description: str | None = None


class AgoraMemberOut(BaseModel):
    id: UUID
    agora_id: UUID
    user_id: UUID | None
    invited_email: str | None
    role: AgoraMemberRole
    display_name: str | None = None
    email: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AgoraSessionSummary(BaseModel):
    id: UUID
    title: str
    status: SessionStatus
    nature: SessionNature
    created_at: datetime
    invite: str | None = None
    share_url: str | None = None


class AgoraOut(BaseModel):
    id: UUID
    name: str
    description: str | None
    owner_id: UUID
    created_at: datetime
    member_count: int = 0
    agent_count: int = 0
    session_count: int = 0
    role: AgoraMemberRole | None = None

    model_config = {"from_attributes": True}


class AgoraDetailOut(AgoraOut):
    members: list[AgoraMemberOut] = Field(default_factory=list)
    agents: list[AgentOut] = Field(default_factory=list)
    sessions: list[AgoraSessionSummary] = Field(default_factory=list)


class AgoraInviteRequest(BaseModel):
    email: str


class AgoraAddAgentsRequest(BaseModel):
    agent_ids: list[UUID]


class AgoraSessionCreate(BaseModel):
    title: str
    nature: SessionNature
    agent_ids: list[UUID] = Field(default_factory=list)


class LocalAgentCreate(BaseModel):
    name: str
    agent_key: str
    org_tag: OrgTag = OrgTag.internal
    hosting_mode: HostingMode = HostingMode.hosted
    endpoint_url: str | None = None
    description: str | None = None
    capabilities: list[str] = Field(default_factory=list)


class ActionPolicyOut(BaseModel):
    id: UUID
    action_type: str
    mode: ActionPolicyMode
    config: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime

    model_config = {"from_attributes": True}


class ActionPolicyUpdate(BaseModel):
    mode: ActionPolicyMode | None = None
    config: dict[str, Any] | None = None


class PolicyChangeEventOut(BaseModel):
    id: UUID
    action_type: str
    before: dict[str, Any]
    after: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class ActionPolicyPatchResponse(BaseModel):
    policy: ActionPolicyOut
    change: PolicyChangeEventOut
