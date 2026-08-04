"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { isLoggedIn, SESSION_ROLE_CHANGED_EVENT } from "@/lib/auth";

type PermissionContextValue = {
  permissions: Set<string>;
  loading: boolean;
  refresh: () => Promise<void>;
  can: (permission: string) => boolean;
};

const PermissionContext = createContext<PermissionContextValue | null>(null);

export function PermissionProvider({ children }: { children: React.ReactNode }) {
  const [permissions, setPermissions] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!isLoggedIn()) {
      setPermissions(new Set());
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const result = await api.myEffectivePermissions();
      setPermissions(new Set(result.permissions));
    } catch {
      setPermissions(new Set());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    const onRoleChange = () => {
      void refresh();
    };
    window.addEventListener(SESSION_ROLE_CHANGED_EVENT, onRoleChange);
    return () => window.removeEventListener(SESSION_ROLE_CHANGED_EVENT, onRoleChange);
  }, [refresh]);

  const value = useMemo(
    () => ({
      permissions,
      loading,
      refresh,
      can: (permission: string) => permissions.has(permission),
    }),
    [permissions, loading, refresh]
  );

  return <PermissionContext.Provider value={value}>{children}</PermissionContext.Provider>;
}

export function usePermission(permission: string) {
  const ctx = useContext(PermissionContext);
  if (!ctx) {
    return { allowed: false, loading: true };
  }
  return { allowed: ctx.can(permission), loading: ctx.loading };
}

export function usePermissions() {
  const ctx = useContext(PermissionContext);
  if (!ctx) {
    throw new Error("usePermissions requires PermissionProvider");
  }
  return ctx;
}
