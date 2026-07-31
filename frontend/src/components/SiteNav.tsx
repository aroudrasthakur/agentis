"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

export function SiteNav() {
  const pathname = usePathname();
  return (
    <header className="flex items-center justify-between px-6 py-4">
      <Link href="/" className="font-display text-xl tracking-tight text-ink">
        Agentis
      </Link>
      <nav className="flex items-center gap-4 text-sm">
        <Link
          href="/agents"
          className={cn(
            "text-ink/60 hover:text-ink",
            pathname.startsWith("/agents") && "text-ink font-medium"
          )}
        >
          Agents
        </Link>
      </nav>
    </header>
  );
}
