"use client";

import { Suspense } from "react";
import { usePathname } from "next/navigation";
import { AppSidebar, isWorkspacePath } from "@/components/AppSidebar";
import { PermissionProvider } from "@/hooks/usePermission";

function SidebarFallback() {
  return (
    <aside
      className="w-[15.5rem] shrink-0 border-r border-ink/[0.08] bg-surface/40"
      aria-hidden
    />
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const workspace = isWorkspacePath(pathname);

  if (!workspace) {
    return <>{children}</>;
  }

  return (
    <div className="flex min-h-[calc(100vh-4.5rem)] w-full">
      <Suspense fallback={<SidebarFallback />}>
        <AppSidebar />
      </Suspense>
      <div className="min-w-0 flex-1">
        <PermissionProvider>{children}</PermissionProvider>
      </div>
    </div>
  );
}
