"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Check, IdCard } from "lucide-react";
import { api, type SessionRole } from "@/lib/api";
import {
  getSessionRole,
  getStoredUser,
  isLoggedIn,
  notifySessionRoleChanged,
  setAuth,
} from "@/lib/auth";
import { NavTooltip } from "@/components/navigation/nav-tooltip";
import { cn } from "@/lib/utils";

function roleLabel(role: SessionRole | null) {
  if (!role) return "No role";
  return role.workspace_name ? `${role.role_name} · ${role.workspace_name}` : role.role_name;
}

export function SessionRoleSelector({ showTooltip = false }: { showTooltip?: boolean }) {
  const [roles, setRoles] = useState<SessionRole[]>([]);
  const [active, setActive] = useState<SessionRole | null>(null);
  const [open, setOpen] = useState(false);
  const [switching, setSwitching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const load = useCallback(async () => {
    if (!isLoggedIn()) {
      setRoles([]);
      setActive(null);
      return;
    }
    try {
      const [list, current] = await Promise.all([
        api.listSessionRoles(),
        api.getSessionRole().catch(() => null),
      ]);
      setRoles(list);
      setActive(current ?? getSessionRole());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load roles");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  async function selectRole(role: SessionRole) {
    if (role.assignment_id === active?.assignment_id) {
      setOpen(false);
      return;
    }
    setSwitching(true);
    setError(null);
    try {
      const res = await api.selectSessionRole(role.assignment_id);
      const user = getStoredUser();
      if (user) {
        setAuth(res.access_token, user, res.session_role ?? null);
      }
      setActive(res.session_role ?? role);
      setOpen(false);
      notifySessionRoleChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not switch role");
    } finally {
      setSwitching(false);
    }
  }

  if (!isLoggedIn() || roles.length === 0) {
    return null;
  }

  const trigger = (
    <button
      type="button"
      onClick={() => setOpen((value) => !value)}
      disabled={switching}
      aria-haspopup="menu"
      aria-expanded={open}
      aria-label={`Session role — ${roleLabel(active)}`}
      className={cn(
        "relative flex h-10 w-10 items-center justify-center rounded-lg text-ink/55 transition-colors duration-150",
        "hover:bg-ink/[0.06] hover:text-ink",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal/60",
        open && "bg-ink/[0.08] text-ink",
        switching && "opacity-60"
      )}
    >
      <IdCard className="h-[21px] w-[21px] shrink-0" strokeWidth={1.75} aria-hidden />
    </button>
  );

  return (
    <div ref={containerRef} className="relative">
      {showTooltip && !open ? (
        <NavTooltip label={`Session role — ${roleLabel(active)}`}>{trigger}</NavTooltip>
      ) : (
        trigger
      )}

      {open && (
        <div
          role="menu"
          aria-label="Select session role"
          className={cn(
            "absolute bottom-0 left-full z-50 ml-2 w-64 overflow-hidden rounded-lg border border-ink/10",
            "bg-surface-elevated shadow-lg"
          )}
        >
          <div className="border-b border-ink/[0.08] px-3 py-2">
            <p className="text-[11px] font-medium uppercase tracking-wide text-ink/40">
              Session role
            </p>
            <p className="mt-0.5 truncate text-sm text-ink">{roleLabel(active)}</p>
          </div>
          <ul className="scroll-area max-h-72 overflow-y-auto py-1">
            {roles.map((role) => {
              const selected = role.assignment_id === active?.assignment_id;
              return (
                <li key={role.assignment_id}>
                  <button
                    type="button"
                    role="menuitemradio"
                    aria-checked={selected}
                    disabled={switching}
                    onClick={() => void selectRole(role)}
                    className={cn(
                      "flex w-full items-center gap-2 px-3 py-2 text-left text-[13px] transition-colors",
                      "hover:bg-ink/[0.05] focus-visible:outline focus-visible:outline-2 focus-visible:outline-teal/60",
                      selected ? "text-ink" : "text-ink/70"
                    )}
                  >
                    <Check
                      className={cn("h-4 w-4 shrink-0 text-teal", !selected && "opacity-0")}
                      aria-hidden
                    />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate">{role.role_name}</span>
                      {role.workspace_name && (
                        <span className="block truncate text-xs text-ink/45">
                          {role.workspace_name}
                        </span>
                      )}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
          {error && (
            <p className="border-t border-ink/[0.08] px-3 py-2 text-xs text-coral" role="alert">
              {error}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
