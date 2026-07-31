"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { getStoredUser, isLoggedIn } from "@/lib/auth";

export function SiteNav() {
  const pathname = usePathname();
  const [loggedIn, setLoggedIn] = useState(false);
  const [name, setName] = useState<string | null>(null);

  useEffect(() => {
    setLoggedIn(isLoggedIn());
    setName(getStoredUser()?.display_name ?? null);
  }, [pathname]);

  const onHome = pathname === "/";
  const hideBrandEmphasis = onHome;

  return (
    <header
      className={cn(
        "flex items-center justify-between px-6 py-4",
        onHome && "relative z-20 bg-transparent"
      )}
    >
      <Link
        href={loggedIn ? "/dashboard" : "/"}
        className={cn(
          "font-display text-xl tracking-tight text-ink",
          hideBrandEmphasis && "opacity-70 transition-opacity hover:opacity-100"
        )}
      >
        Agentis
      </Link>
      <nav className="flex items-center gap-4 text-sm">
        {loggedIn ? (
          <>
            <Link
              href="/dashboard"
              className={cn(
                "text-ink/60 hover:text-ink",
                (pathname.startsWith("/dashboard") || pathname.startsWith("/agora")) &&
                  !pathname.includes("/guild") &&
                  "font-medium text-ink"
              )}
            >
              Dashboard
            </Link>
            <Link
              href="/dashboard/guild"
              className={cn(
                "text-ink/60 hover:text-ink",
                pathname.includes("/guild") && "font-medium text-ink"
              )}
            >
              Guild
            </Link>
            {name && <span className="hidden text-ink/40 sm:inline">{name}</span>}
          </>
        ) : (
          <>
            <Link
              href="/login"
              className={cn(
                "text-ink/60 hover:text-ink",
                pathname === "/login" && "font-medium text-ink"
              )}
            >
              Sign in
            </Link>
            <Link
              href="/signup"
              className={cn(
                "text-ink/60 hover:text-ink",
                pathname === "/signup" && "font-medium text-ink"
              )}
            >
              Sign up
            </Link>
          </>
        )}
      </nav>
    </header>
  );
}
