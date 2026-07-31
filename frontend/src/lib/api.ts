export type OrgTag = "Internal" | "External";
export type HostingMode = "hosted" | "remote_mcp";
export type SessionStatus = "active" | "paused" | "completed";
export type ParticipantKind = "human" | "internal_agent" | "external_agent";
export type EventType =
  | "message"
  | "action_pending"
  | "action_approved"
  | "action_denied"
  | "redirect"
  | "handoff"
  | "agent_attached"
  | "agent_detached";

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
  created_at: string;
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
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function withInvite(path: string, invite?: string | null) {
  if (!invite) return path;
  const sep = path.includes("?") ? "&" : "?";
  return `${path}${sep}invite=${encodeURIComponent(invite)}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}

export const api = {
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
  createSession: (body?: { title?: string; agent_ids?: string[] }) =>
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
};

export function wsUrl(sessionId: string, invite: string) {
  const base = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
  return `${base}/sessions/${sessionId}/ws?invite=${encodeURIComponent(invite)}`;
}
