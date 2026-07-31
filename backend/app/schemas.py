from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import (
    ActionPolicyMode,
    AgentSource,
    EventType,
    GatheringMemberRole,
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
    version: str | None = None
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentUpdate(BaseModel):
    name: str | None = None
    endpoint_url: str | None = None
    description: str | None = None
    is_active: bool | None = None
    org_tag: OrgTag | None = None
    capabilities: list[str] | None = None
    is_public: bool | None = None
    version: str | None = None
    tags: list[str] | None = None
    notes: str | None = None
    metadata: dict[str, Any] | None = None


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
    version: str | None = None
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime | None = None
    downloaded: bool = False

    model_config = {"from_attributes": True}

    @classmethod
    def from_agent(cls, agent: Any, *, downloaded: bool = False) -> "AgentOut":
        return cls(
            id=agent.id,
            name=agent.name,
            agent_key=agent.agent_key,
            org_tag=agent.org_tag,
            hosting_mode=agent.hosting_mode,
            endpoint_url=agent.endpoint_url,
            description=agent.description,
            capabilities=list(agent.capabilities or []),
            is_active=agent.is_active,
            source=agent.source,
            is_public=agent.is_public,
            owner_user_id=agent.owner_user_id,
            version=agent.version,
            tags=list(agent.tags or []),
            notes=agent.notes,
            metadata=dict(agent.metadata_ or {}),
            created_at=agent.created_at,
            updated_at=getattr(agent, "updated_at", None),
            downloaded=downloaded,
        )


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
    gathering_id: UUID | None = None


class SessionOut(BaseModel):
    id: UUID
    title: str
    status: SessionStatus
    nature: SessionNature = SessionNature.multi_agent
    gathering_id: UUID | None = None
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
    gathering_id: UUID | None = None


class UserCreate(BaseModel):
    email: str
    display_name: str
    password: str = Field(min_length=6)


class UserLogin(BaseModel):
    email: str
    password: str


class UserUpdate(BaseModel):
    display_name: str | None = None
    bio: str | None = None
    organization: str | None = None
    title: str | None = None
    avatar_url: str | None = None
    profile: dict[str, Any] | None = None


class UserOut(BaseModel):
    id: UUID
    email: str
    display_name: str
    bio: str | None = None
    organization: str | None = None
    title: str | None = None
    avatar_url: str | None = None
    profile: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class GatheringCreate(BaseModel):
    name: str
    description: str | None = None


class GatheringMemberOut(BaseModel):
    id: UUID
    gathering_id: UUID
    user_id: UUID | None
    invited_email: str | None
    role: GatheringMemberRole
    display_name: str | None = None
    email: str | None = None
    bio: str | None = None
    organization: str | None = None
    title: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class GatheringSessionSummary(BaseModel):
    id: UUID
    title: str
    status: SessionStatus
    nature: SessionNature
    created_at: datetime
    invite: str | None = None
    share_url: str | None = None


class GatheringOut(BaseModel):
    id: UUID
    name: str
    description: str | None
    owner_id: UUID
    created_at: datetime
    member_count: int = 0
    agent_count: int = 0
    session_count: int = 0
    role: GatheringMemberRole | None = None

    model_config = {"from_attributes": True}


class GatheringDetailOut(GatheringOut):
    members: list[GatheringMemberOut] = Field(default_factory=list)
    agents: list[AgentOut] = Field(default_factory=list)
    sessions: list[GatheringSessionSummary] = Field(default_factory=list)


class GatheringInviteRequest(BaseModel):
    email: str


class GatheringAddAgentsRequest(BaseModel):
    agent_ids: list[UUID]


class GatheringSessionCreate(BaseModel):
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
    version: str | None = None
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


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
