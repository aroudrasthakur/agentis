import { getToken } from "@/lib/auth";
import type {
  AgentMetricConfiguration,
  AgentMetricDefinition,
  AgentTypeConfiguration,
  AgentTypeDefinition,
  AgentTypeSummary,
  AgentTypeValidationResult,
  CompatibilityReport,
  CustomAgentType,
  DeploymentReadiness,
  SelectorCatalogs,
  TypeMigrationPreview,
} from "@/agent-types/schemas";

export type OrgTag = "Internal" | "External";
export type HostingMode = "hosted" | "remote_mcp";
export type SessionStatus = "active" | "paused" | "completed";
export type ParticipantKind = "human" | "internal_agent" | "external_agent";
export type SessionNature = "training" | "multi_agent";
export type AgentSource = "local" | "downloaded" | "directory";
export type GatheringMemberRole = "owner" | "member";
export type GuildTab = "local" | "downloaded" | "directory";

export type EventType =
  | "message"
  | "action_pending"
  | "action_approved"
  | "action_denied"
  | "redirect"
  | "handoff"
  | "agent_attached"
  | "agent_detached"
  | "plan_proposed"
  | "plan_approved"
  | "plan_denied"
  | "action_executed";

export type ActionPolicyMode =
  | "step_by_step"
  | "confidence_gated"
  | "plan_then_execute";

export interface ActionPolicy {
  id: string;
  action_type: string;
  mode: ActionPolicyMode;
  config: {
    max_amount?: number;
    min_confidence?: number;
    gate_on?: string[];
    [key: string]: unknown;
  };
  updated_at: string;
}

export interface PlanStep {
  id: string;
  action_type: string;
  description?: string;
  params?: Record<string, unknown>;
  confidence?: number;
}

export interface PlanContent {
  plan_id: string;
  title: string;
  steps: PlanStep[];
}

export interface PolicyChangeEvent {
  id: string;
  action_type: string;
  before: Record<string, unknown>;
  after: Record<string, unknown>;
  created_at: string;
}

export interface User {
  id: string;
  email: string;
  display_name: string;
  bio?: string | null;
  organization?: string | null;
  title?: string | null;
  avatar_url?: string | null;
  profile?: Record<string, unknown>;
  created_at: string;
  updated_at?: string | null;
}

export interface SessionRole {
  assignment_id: string;
  role_id: string;
  role_name: string;
  role_slug: string;
  category: string;
  workspace_id?: string | null;
  workspace_name?: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
  session_role?: SessionRole | null;
}

export interface PermissionDefinition {
  key: string;
  label: string;
  description: string;
  category: string;
  supported_scopes: string[];
  sensitive: boolean;
  assignable_to_custom_roles: boolean;
  dependencies: string[];
  conflicts: string[];
}

export interface RolePermissionRow {
  permission_key: string;
  effect: "allow" | "deny";
  scope: string;
  resource_type?: string | null;
  resource_ids?: string[];
}

export interface RoleSummary {
  id: string;
  workspace_id?: string | null;
  name: string;
  slug: string;
  description?: string | null;
  kind: "system" | "custom";
  category?: string;
  status: "active" | "archived" | "deprecated";
  is_default: boolean;
  is_immutable: boolean;
  is_managed?: boolean;
  assignable_to_users?: boolean;
  resource_type?: string | null;
  resource_id?: string | null;
  member_count: number;
  permissions: RolePermissionRow[];
  inherited_role_ids?: string[];
  inheriting_role_ids?: string[];
}

export type RoleCreatePayload = {
  name: string;
  description?: string | null;
  workspace_id?: string | null;
  permissions: RolePermissionRow[];
  parent_role_ids?: string[];
};

export interface Agent {
  id: string;
  name: string;
  agent_key: string;
  org_tag: OrgTag;
  hosting_mode: HostingMode;
  endpoint_url: string | null;
  description: string | null;
  capabilities: string[];
  is_active: boolean;
  source?: AgentSource;
  is_public?: boolean;
  owner_user_id?: string | null;
  version?: string | null;
  tags?: string[];
  notes?: string | null;
  metadata?: Record<string, unknown>;
  agent_type_id?: string | null;
  agent_type_version?: number | null;
  agent_type_configuration?: AgentTypeConfiguration;
  agent_metric_configuration?: AgentMetricConfiguration;
  agent_type_validation_status?: Record<string, unknown>;
  deployed_type_id?: string | null;
  deployed_type_version?: number | null;
  deployed_at?: string | null;
  requires_type_setup?: boolean;
  deployment_ready?: boolean;
  description_format?: "plain" | "markdown";
  created_at: string;
  updated_at?: string | null;
  downloaded?: boolean;
}

export interface AgentDescriptionSummary {
  agent_id: string;
  name: string;
  agent_key: string;
  description_preview?: string | null;
  has_description: boolean;
  description_format: "plain" | "markdown";
  type_id?: string | null;
  type_name?: string | null;
  deployment_status: "needs_type" | "not_deployed" | "ready" | "needs_attention";
  deployment_status_label: string;
  is_active: boolean;
  requires_type_setup: boolean;
  deployment_ready: boolean;
}

export interface ConfigFieldDisplay {
  key: string;
  label: string;
  section: string;
  section_label: string;
  value_display: string;
  is_set: boolean;
}

export interface ConfigurationSectionDisplay {
  section: string;
  section_label: string;
  fields: ConfigFieldDisplay[];
}

export interface MetricSummaryDisplay {
  key: string;
  label: string;
  enabled: boolean;
  required: boolean;
  target_display?: string | null;
}

export interface AgentDescriptionProfile extends AgentDescriptionSummary {
  description?: string | null;
  hosting_mode: string;
  org_tag: string;
  capabilities: string[];
  tags: string[];
  notes?: string | null;
  version?: string | null;
  type_version?: number | null;
  configuration_sections: ConfigurationSectionDisplay[];
  metrics: MetricSummaryDisplay[];
  deployed_type_id?: string | null;
  deployed_type_version?: number | null;
  deployed_at?: string | null;
  highlights: string[];
}

export interface Gathering {
  id: string;
  name: string;
  description: string | null;
  owner_id: string;
  created_at: string;
  member_count: number;
  agent_count: number;
  session_count: number;
  role?: GatheringMemberRole | null;
}

export interface GatheringMember {
  id: string;
  gathering_id: string;
  user_id: string | null;
  invited_email: string | null;
  role: GatheringMemberRole;
  display_name?: string | null;
  email?: string | null;
  bio?: string | null;
  organization?: string | null;
  title?: string | null;
  created_at: string;
}

export interface GatheringSessionSummary {
  id: string;
  title: string;
  status: SessionStatus;
  nature: SessionNature;
  created_at: string;
  invite?: string | null;
  share_url?: string | null;
}

export interface GatheringDetail extends Gathering {
  members: GatheringMember[];
  agents: Agent[];
  sessions: GatheringSessionSummary[];
}

export type GatheringAccessMode = "owner_managed" | "centrally_managed";

export interface GatheringProvisionRequest {
  name: string;
  description?: string;
  access_mode: GatheringAccessMode;
  future_grants_enabled: boolean;
  invite_emails: string[];
  agent_ids: string[];
}

export interface GatheringProvisionResponse {
  gathering: Gathering;
  provisioning: {
    invited_emails: string[];
    skipped_emails: string[];
    attached_agent_ids: string[];
    access_role_slugs: string[];
  };
}

export interface Participant {
  id: string;
  session_id: string;
  agent_id: string | null;
  name: string;
  kind: ParticipantKind;
  org_tag: OrgTag;
  hosting_mode: HostingMode | null;
  endpoint_url: string | null;
  agent_key: string | null;
  granted_capabilities?: string[] | null;
  token_expires_at?: string | null;
  token_revoked?: boolean;
}

export interface SessionEvent {
  id: string;
  session_id: string;
  participant_id: string;
  type: EventType;
  content: string;
  requires_approval: boolean;
  created_at: string;
  sequence: number;
  participant?: Participant | null;
}

export interface Session {
  id: string;
  title: string;
  status: SessionStatus;
  nature?: SessionNature;
  gathering_id?: string | null;
  active_participant_id: string | null;
  created_at: string;
  share_url?: string | null;
  invite_expires_at?: string | null;
  participants: Participant[];
  events: SessionEvent[];
}

export interface SessionCreateResponse {
  id: string;
  share_url: string;
  invite: string;
  title: string;
  status: SessionStatus;
  nature?: SessionNature;
  gathering_id?: string | null;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function withInvite(path: string, invite?: string | null) {
  if (!invite) return path;
  const sep = path.includes("?") ? "&" : "?";
  return `${path}${sep}invite=${encodeURIComponent(invite)}`;
}

async function request<T>(path: string, init?: RequestInit, auth = false): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  };
  if (auth) {
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  const res = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (!res.ok) {
    const text = await res.text();
    let message = text || res.statusText;
    try {
      const json = JSON.parse(text) as { detail?: string };
      if (json.detail) message = json.detail;
    } catch {
      /* keep text */
    }
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

export const api = {
  signup: (body: { email: string; display_name: string; password: string }) =>
    request<AuthResponse>("/auth/signup", { method: "POST", body: JSON.stringify(body) }),
  login: (body: { email: string; password: string }) =>
    request<AuthResponse>("/auth/login", { method: "POST", body: JSON.stringify(body) }),
  listSessionRoles: () => request<SessionRole[]>("/auth/session/roles", undefined, true),
  getSessionRole: () => request<SessionRole>("/auth/session/role", undefined, true),
  selectSessionRole: (assignment_id: string) =>
    request<AuthResponse>(
      "/auth/session/role",
      { method: "POST", body: JSON.stringify({ assignment_id }) },
      true
    ),
  me: () => request<User>("/auth/me", undefined, true),
  updateMe: (body: {
    display_name?: string;
    bio?: string;
    organization?: string;
    title?: string;
    avatar_url?: string;
    profile?: Record<string, unknown>;
  }) =>
    request<User>("/auth/me", { method: "PATCH", body: JSON.stringify(body) }, true),
  getPerson: (userId: string) =>
    request<User>(`/auth/people/${userId}`, undefined, true),

  listGatherings: () => request<Gathering[]>("/gatherings", undefined, true),
  createGathering: (body: { name: string; description?: string }) =>
    request<Gathering>("/gatherings", { method: "POST", body: JSON.stringify(body) }, true),
  provisionGathering: (body: GatheringProvisionRequest) =>
    request<GatheringProvisionResponse>(
      "/gatherings/provision",
      { method: "POST", body: JSON.stringify(body) },
      true
    ),
  getGathering: (id: string) => request<GatheringDetail>(`/gatherings/${id}`, undefined, true),
  inviteToGathering: (id: string, email: string) =>
    request<GatheringMember>(
      `/gatherings/${id}/invite`,
      { method: "POST", body: JSON.stringify({ email }) },
      true
    ),
  addAgentsToGathering: (id: string, agent_ids: string[]) =>
    request<Agent[]>(
      `/gatherings/${id}/agents`,
      { method: "POST", body: JSON.stringify({ agent_ids }) },
      true
    ),
  createGatheringSession: (
    id: string,
    body: { title: string; nature: SessionNature; agent_ids?: string[] }
  ) =>
    request<SessionCreateResponse>(
      `/gatherings/${id}/sessions`,
      { method: "POST", body: JSON.stringify(body) },
      true
    ),
  openGatheringSession: (gatheringId: string, sessionId: string) =>
    request<SessionCreateResponse>(
      `/gatherings/${gatheringId}/sessions/${sessionId}/open`,
      { method: "POST" },
      true
    ),

  guildAgents: (tab: GuildTab, q?: string) => {
    const params = new URLSearchParams({ tab });
    if (q?.trim()) params.set("q", q.trim());
    return request<Agent[]>(`/guild/agents?${params}`, undefined, true);
  },
  attachableAgents: (gatheringId?: string | null) => {
    const params = gatheringId ? `?gathering_id=${encodeURIComponent(gatheringId)}` : "";
    return request<Agent[]>(`/guild/agents/attachable${params}`, undefined, true);
  },
  getGuildAgent: (agentId: string) =>
    request<Agent>(`/guild/agents/${agentId}`, undefined, true),
  listAgentDescriptions: () =>
    request<AgentDescriptionSummary[]>("/guild/agents/descriptions", undefined, true),
  getAgentDescription: (agentId: string) =>
    request<AgentDescriptionProfile>(`/guild/agents/${agentId}/description`, undefined, true),
  updateAgentDescription: (
    agentId: string,
    body: { description?: string | null; description_format?: "plain" | "markdown" }
  ) =>
    request<AgentDescriptionProfile>(
      `/guild/agents/${agentId}/description`,
      { method: "PUT", body: JSON.stringify(body) },
      true
    ),
  updateGuildAgent: (
    agentId: string,
    body: {
      name?: string;
      description?: string | null;
      version?: string | null;
      tags?: string[];
      notes?: string | null;
      metadata?: Record<string, unknown>;
      endpoint_url?: string | null;
      capabilities?: string[];
    }
  ) =>
    request<Agent>(`/guild/agents/${agentId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }, true),
  createLocalAgent: (body: {
    name: string;
    agent_key: string;
    org_tag?: OrgTag;
    hosting_mode?: HostingMode;
    endpoint_url?: string | null;
    description?: string | null;
    capabilities?: string[];
    version?: string | null;
    tags?: string[];
    notes?: string | null;
    metadata?: Record<string, unknown>;
  }) =>
    request<Agent>("/guild/agents/local", { method: "POST", body: JSON.stringify(body) }, true),
  downloadAgent: (agentId: string) =>
    request<Agent>(`/guild/agents/${agentId}/download`, { method: "POST" }, true),

  // Agent types
  listAgentTypes: (includeArchived = false) =>
    request<AgentTypeSummary[]>(
      `/agent-types?include_archived=${includeArchived}`,
      undefined,
      true
    ),
  getAgentType: (typeId: string, version?: number | null) => {
    const params = version != null ? `?version=${version}` : "";
    return request<AgentTypeDefinition>(
      `/agent-types/${encodeURIComponent(typeId)}${params}`,
      undefined,
      true
    );
  },
  getAgentTypeMetrics: (typeId: string, version?: number | null) => {
    const params = version != null ? `?version=${version}` : "";
    return request<AgentMetricDefinition[]>(
      `/agent-types/${encodeURIComponent(typeId)}/metrics${params}`,
      undefined,
      true
    );
  },
  getSelectorCatalogs: () =>
    request<SelectorCatalogs>("/agent-types/catalogs", undefined, true),

  listCustomAgentTypes: (includeArchived = false) =>
    request<CustomAgentType[]>(
      `/agent-types/custom?include_archived=${includeArchived}`,
      undefined,
      true
    ),
  getCustomAgentType: (familyId: string, version?: number | null) => {
    const params = version != null ? `?version=${version}` : "";
    return request<CustomAgentType>(
      `/agent-types/custom/${familyId}${params}`,
      undefined,
      true
    );
  },
  listCustomAgentTypeVersions: (familyId: string) =>
    request<CustomAgentType[]>(`/agent-types/custom/${familyId}/versions`, undefined, true),
  createCustomAgentType: (body: Record<string, unknown>) =>
    request<CustomAgentType>(
      "/agent-types/custom",
      { method: "POST", body: JSON.stringify(body) },
      true
    ),
  updateCustomAgentType: (familyId: string, body: Record<string, unknown>) =>
    request<CustomAgentType>(
      `/agent-types/custom/${familyId}`,
      { method: "PATCH", body: JSON.stringify(body) },
      true
    ),
  duplicateCustomAgentType: (familyId: string) =>
    request<CustomAgentType>(
      `/agent-types/custom/${familyId}/duplicate`,
      { method: "POST" },
      true
    ),
  archiveCustomAgentType: (familyId: string) =>
    request<CustomAgentType>(
      `/agent-types/custom/${familyId}/archive`,
      { method: "POST" },
      true
    ),

  // Agent type assignment and deployment
  assignAgentType: (
    agentId: string,
    body: {
      typeId: string;
      typeVersion?: number | null;
      configuration?: AgentTypeConfiguration;
      metricConfiguration?: AgentMetricConfiguration;
      discardIncompatible?: boolean;
    }
  ) =>
    request<{
      agent: Agent;
      validation: AgentTypeValidationResult;
      compatibility: CompatibilityReport;
      readiness: DeploymentReadiness;
      definition: AgentTypeDefinition;
    }>(
      `/guild/agents/${agentId}/type`,
      { method: "POST", body: JSON.stringify(body) },
      true
    ),
  saveAgentTypeConfiguration: (
    agentId: string,
    body: {
      configuration?: AgentTypeConfiguration;
      metricConfiguration?: AgentMetricConfiguration;
    }
  ) =>
    request<{
      agent: Agent;
      validation: AgentTypeValidationResult;
      readiness: DeploymentReadiness;
    }>(
      `/guild/agents/${agentId}/type/configuration`,
      { method: "PATCH", body: JSON.stringify(body) },
      true
    ),
  validateAgentType: (
    agentId: string,
    body?: {
      configuration?: AgentTypeConfiguration;
      metricConfiguration?: AgentMetricConfiguration;
    }
  ) =>
    request<AgentTypeValidationResult>(
      `/guild/agents/${agentId}/validate`,
      { method: "POST", body: JSON.stringify(body ?? {}) },
      true
    ),
  getDeploymentReadiness: (agentId: string) =>
    request<DeploymentReadiness>(
      `/guild/agents/${agentId}/deployment-readiness`,
      undefined,
      true
    ),
  deployAgent: (agentId: string) =>
    request<{ agent: Agent; readiness: DeploymentReadiness }>(
      `/guild/agents/${agentId}/deploy`,
      { method: "POST" },
      true
    ),
  previewAgentTypeMigration: (agentId: string, targetVersion?: number | null) => {
    const params = targetVersion != null ? `?target_version=${targetVersion}` : "";
    return request<TypeMigrationPreview>(
      `/guild/agents/${agentId}/type/migration-preview${params}`,
      undefined,
      true
    );
  },
  migrateAgentType: (
    agentId: string,
    body: {
      targetVersion?: number | null;
      configuration?: AgentTypeConfiguration;
      metricConfiguration?: AgentMetricConfiguration;
    }
  ) =>
    request<{
      agent: Agent;
      validation: AgentTypeValidationResult;
      readiness: DeploymentReadiness;
      preview: TypeMigrationPreview;
    }>(
      `/guild/agents/${agentId}/type/migrate`,
      { method: "POST", body: JSON.stringify(body) },
      true
    ),

  listAgents: () => request<Agent[]>("/agents", undefined, true),
  createAgent: (body: {
    name: string;
    agent_key: string;
    org_tag: OrgTag;
    hosting_mode: HostingMode;
    endpoint_url?: string | null;
    description?: string | null;
    capabilities?: string[];
  }) =>
    request<Agent>("/agents", {
      method: "POST",
      body: JSON.stringify(body),
    }, true),
  createSession: (body?: {
    title?: string;
    agent_ids?: string[];
    nature?: SessionNature;
  }) =>
    request<SessionCreateResponse>("/sessions", {
      method: "POST",
      body: JSON.stringify(body || {}),
    }),
  getSession: (id: string, invite: string) =>
    request<Session>(withInvite(`/sessions/${id}`, invite)),
  attachAgents: (sessionId: string, invite: string, agent_ids: string[]) =>
    request<Session>(withInvite(`/sessions/${sessionId}/agents`, invite), {
      method: "POST",
      body: JSON.stringify({ agent_ids }),
    }),
  detachAgent: (sessionId: string, invite: string, participantId: string) =>
    request<Session>(
      withInvite(`/sessions/${sessionId}/agents/${participantId}`, invite),
      { method: "DELETE" }
    ),
  startSession: (sessionId: string, invite: string) =>
    request<Session>(withInvite(`/sessions/${sessionId}/start`, invite), {
      method: "POST",
    }),
  listActionPolicies: () => request<ActionPolicy[]>("/action-policies", undefined, true),
  getActionPolicy: (actionType: string) =>
    request<ActionPolicy>(`/action-policies/${encodeURIComponent(actionType)}`, undefined, true),
  patchActionPolicy: (
    actionType: string,
    body: { mode?: ActionPolicyMode; config?: ActionPolicy["config"] }
  ) =>
    request<{ policy: ActionPolicy; change: PolicyChangeEvent }>(
      `/action-policies/${encodeURIComponent(actionType)}`,
      {
        method: "PATCH",
        body: JSON.stringify(body),
      },
      true
    ),

  listRoles: () => request<RoleSummary[]>("/authorization/roles", undefined, true),
  getRole: (roleId: string) =>
    request<RoleSummary>(`/authorization/roles/${roleId}`, undefined, true),
  listPermissionDefinitions: () =>
    request<PermissionDefinition[]>("/authorization/permissions", undefined, true),
  createRole: (body: RoleCreatePayload) =>
    request<RoleSummary>(
      "/authorization/roles",
      { method: "POST", body: JSON.stringify(body) },
      true
    ),
  myEffectivePermissions: () =>
    request<{ permissions: string[]; evaluated_at: string }>(
      "/authorization/me/permissions",
      undefined,
      true
    ),
  checkPermission: (body: {
    permission: string;
    workspace_id?: string;
    resource_type?: string;
    resource_id?: string;
  }) =>
    request<{ allowed: boolean; decision: Record<string, unknown> }>(
      "/authorization/check",
      { method: "POST", body: JSON.stringify(body) },
      true
    ),
  checkPermissionBatch: (checks: {
    permission: string;
    workspace_id?: string;
    resource_type?: string;
    resource_id?: string;
  }[]) =>
    request<{ results: { permission: string; decision: Record<string, unknown> }[] }>(
      "/authorization/check-batch",
      { method: "POST", body: JSON.stringify({ checks }) },
      true
    ),
  explainAuthorization: (body: {
    user_id: string;
    permission: string;
    workspace_id?: string;
    resource_type?: string;
    resource_id?: string;
  }) =>
    request<Record<string, unknown>>(
      "/authorization/explain",
      { method: "POST", body: JSON.stringify(body) },
      true
    ),
  getGatheringAuthSettings: (gatheringId: string) =>
    request<{
      gathering_id: string;
      access_mode: string;
      future_grants_enabled?: boolean;
    }>(`/authorization/gatherings/${gatheringId}/settings`, undefined, true),
  getAgentAccess: (agentId: string) =>
    request<Record<string, unknown>>(`/authorization/agents/${agentId}/access`, undefined, true),
};

export function parsePlanContent(content: string): PlanContent | null {
  try {
    const data = JSON.parse(content) as PlanContent;
    if (!data || !Array.isArray(data.steps)) return null;
    return data;
  } catch {
    return null;
  }
}

export function wsUrl(sessionId: string, invite: string) {
  const base = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
  return `${base}/sessions/${sessionId}/ws?invite=${encodeURIComponent(invite)}`;
}
