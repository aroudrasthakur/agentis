import { getToken } from "@/lib/auth";

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

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

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
  created_at: string;
  updated_at?: string | null;
  downloaded?: boolean;
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
  getGuildAgent: (agentId: string) =>
    request<Agent>(`/guild/agents/${agentId}`, undefined, true),
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

  listAgents: () => request<Agent[]>("/agents"),
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
    }),
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
  listActionPolicies: () => request<ActionPolicy[]>("/action-policies"),
  getActionPolicy: (actionType: string) =>
    request<ActionPolicy>(`/action-policies/${encodeURIComponent(actionType)}`),
  patchActionPolicy: (
    actionType: string,
    body: { mode?: ActionPolicyMode; config?: ActionPolicy["config"] }
  ) =>
    request<{ policy: ActionPolicy; change: PolicyChangeEvent }>(
      `/action-policies/${encodeURIComponent(actionType)}`,
      {
        method: "PATCH",
        body: JSON.stringify(body),
      }
    ),
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
