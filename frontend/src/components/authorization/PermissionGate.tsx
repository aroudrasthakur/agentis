"use client";

import type { ReactNode } from "react";
import { usePermission } from "@/hooks/usePermission";

export function PermissionGate({
  permission,
  children,
  fallback = null,
}: {
  permission: string;
  children: ReactNode;
  fallback?: ReactNode;
}) {
  const { allowed, loading } = usePermission(permission);
  if (loading) {
    return <span className="text-xs text-ink/40">Checking access…</span>;
  }
  if (!allowed) {
    return <>{fallback}</>;
  }
  return <>{children}</>;
}
