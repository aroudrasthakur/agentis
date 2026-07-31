"use client";

import { useEffect, useMemo, useState } from "react";
import type { PlanContent, PlanStep, SessionEvent } from "@/lib/api";
import { parsePlanContent } from "@/lib/api";
import { Button } from "@/components/ui/button";

export function PlanReviewPanel({
  events,
  onAction,
}: {
  events: SessionEvent[];
  onAction: (payload: Record<string, unknown>) => void;
}) {
  const latestPlan = useMemo(() => {
    const sorted = [...events].sort((a, b) => b.sequence - a.sequence);
    const pending = sorted.find((e) => e.type === "plan_proposed" && e.requires_approval);
    if (!pending) return null;
    // Ignore if a later plan_approved/denied exists for same or newer sequence
    const laterOutcome = sorted.find(
      (e) =>
        (e.type === "plan_approved" || e.type === "plan_denied") &&
        e.sequence > pending.sequence
    );
    if (laterOutcome) return null;
    const plan = parsePlanContent(pending.content);
    if (!plan) return null;
    return { event: pending, plan };
  }, [events]);

  const [removed, setRemoved] = useState<Set<string>>(new Set());

  useEffect(() => {
    setRemoved(new Set());
  }, [latestPlan?.event.id]);

  if (!latestPlan) return null;

  const { plan } = latestPlan;
  const visibleSteps = plan.steps.filter((s) => !removed.has(s.id));

  function toggleStep(step: PlanStep) {
    setRemoved((prev) => {
      const next = new Set(prev);
      if (next.has(step.id)) next.delete(step.id);
      else next.add(step.id);
      return next;
    });
  }

  return (
    <div className="mx-4 mb-3 rounded-lg border border-ink/15 bg-white/80 p-4 animate-fade-up">
      <div className="mb-2 flex items-baseline justify-between gap-2">
        <h2 className="font-display text-lg text-ink">{plan.title || "Proposed plan"}</h2>
        <span className="text-[10px] uppercase tracking-wider text-ink/40">plan review</span>
      </div>
      <p className="mb-3 text-xs text-ink/55">
        Remove steps you do not want, then approve the remaining plan. Nested steps will not
        re-propose plans.
      </p>
      <ul className="mb-4 space-y-2">
        {plan.steps.map((step) => {
          const isRemoved = removed.has(step.id);
          return (
            <li
              key={step.id}
              className={`flex items-start justify-between gap-3 rounded-md border px-3 py-2 text-sm ${
                isRemoved
                  ? "border-ink/10 bg-ink/5 text-ink/40 line-through"
                  : "border-ink/10 bg-sand/60 text-ink/85"
              }`}
            >
              <div>
                <div className="font-medium">{step.action_type}</div>
                {step.description && (
                  <div className="text-xs text-ink/60">{step.description}</div>
                )}
                {step.confidence != null && (
                  <div className="text-[11px] text-ink/45">
                    confidence {step.confidence}
                  </div>
                )}
              </div>
              <Button size="sm" variant="outline" onClick={() => toggleStep(step)}>
                {isRemoved ? "Restore" : "Remove"}
              </Button>
            </li>
          );
        })}
      </ul>
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          variant="teal"
          disabled={visibleSteps.length === 0}
          onClick={() => {
            onAction({
              action: "approve_plan",
              removed_step_ids: Array.from(removed),
            });
            setRemoved(new Set());
          }}
        >
          Approve plan ({visibleSteps.length})
        </Button>
        <Button
          size="sm"
          variant="coral"
          onClick={() => {
            onAction({ action: "deny_plan" });
            setRemoved(new Set());
          }}
        >
          Deny plan
        </Button>
      </div>
    </div>
  );
}

/** Helper export for ControlBar gating */
export function findPendingPlan(events: SessionEvent[]): PlanContent | null {
  const sorted = [...events].sort((a, b) => b.sequence - a.sequence);
  const pending = sorted.find((e) => e.type === "plan_proposed" && e.requires_approval);
  if (!pending) return null;
  const later = sorted.find(
    (e) =>
      (e.type === "plan_approved" || e.type === "plan_denied") && e.sequence > pending.sequence
  );
  if (later) return null;
  return parsePlanContent(pending.content);
}
