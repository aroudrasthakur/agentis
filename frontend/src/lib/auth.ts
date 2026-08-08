"use client";

import type { SessionRole, User } from "@/lib/auth-types";

export type AuthUser = User;
export type StoredSessionRole = SessionRole;

const TOKEN_KEY = "agentis_token";
const USER_KEY = "agentis_user";
const SESSION_ROLE_KEY = "agentis_session_role";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function getSessionRole(): StoredSessionRole | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(SESSION_ROLE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as StoredSessionRole;
  } catch {
    return null;
  }
}

export function setAuth(
  token: string,
  user: AuthUser,
  sessionRole?: StoredSessionRole | null
) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
  if (sessionRole === undefined) return;
  if (sessionRole) {
    localStorage.setItem(SESSION_ROLE_KEY, JSON.stringify(sessionRole));
  } else {
    localStorage.removeItem(SESSION_ROLE_KEY);
  }
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  localStorage.removeItem(SESSION_ROLE_KEY);
}

export const SESSION_ROLE_CHANGED_EVENT = "agentis:session-role-changed";

export function notifySessionRoleChanged() {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(SESSION_ROLE_CHANGED_EVENT));
}

export function isLoggedIn(): boolean {
  return Boolean(getToken());
}
