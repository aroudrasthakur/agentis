"use client";

import { Suspense } from "react";
import { usePathname } from "next/navigation";
import { AppSidebarNavigation } from "@/components/navigation/app-sidebar";
import { isWorkspacePath } from "@/components/navigation/navigation-utils";
import { PermissionProvider } from "@/hooks/usePermission";
import { cn } from "@/lib/utils";

function SidebarSkeleton() {
  return (
    <>
      <div className="w-[var(--primary-nav-width)] border-r border-ink/[0.08] bg-surface/40" />
      <div className="w-[var(--secondary-nav-width)] border-r border-ink/[0.08] bg-surface/30" />
    </>
  );
}

function WorkspaceChrome({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const workspace = isWorkspacePath(pathname);

  if (!workspace) {
    return <>{children}</>;
  }

  return (
    <PermissionProvider>
      <div className={cn("app-workspace-shell w-full")}>
        <div className="app-workspace-nav">
          <Suspense fallback={<SidebarSkeleton />}>
            <AppSidebarNavigation />
          </Suspense>
        </div>
        <main className="min-w-0 flex-1 overflow-x-hidden">{children}</main>
      </div>
    </PermissionProvider>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  return <WorkspaceChrome>{children}</WorkspaceChrome>;
}
