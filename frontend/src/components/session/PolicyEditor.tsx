"use client";

import { useEffect, useState } from "react";
import type { ActionPolicy, ActionPolicyMode } from "@/lib/api";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const MODES: ActionPolicyMode[] = [
  "step_by_step",
  "confidence_gated",
  "plan_then_execute",
];

export function PolicyEditor({ actionType = "process_refund" }: { actionType?: string }) {
  const [policy, setPolicy] = useState<ActionPolicy | null>(null);
  const [mode, setMode] = useState<ActionPolicyMode>("step_by_step");
  const [maxAmount, setMaxAmount] = useState("50");
  const [minConfidence, setMinConfidence] = useState("0.9");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [savedNote, setSavedNote] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const p = await api.getActionPolicy(actionType);
        setPolicy(p);
        setMode(p.mode);
        if (p.config.max_amount != null) setMaxAmount(String(p.config.max_amount));
        if (p.config.min_confidence != null) {
          setMinConfidence(String(p.config.min_confidence));
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load policy");
      }
    })();
  }, [actionType]);

  async function save() {
    setSaving(true);
    setError(null);
    setSavedNote(null);
    try {
      const config =
        mode === "confidence_gated"
          ? {
              max_amount: Number(maxAmount),
              min_confidence: Number(minConfidence),
              gate_on: ["amount", "confidence"],
            }
          : {};
      const res = await api.patchActionPolicy(actionType, { mode, config });
      setPolicy(res.policy);
      setSavedNote(`Saved · audit ${res.change.id.slice(0, 8)}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  if (error && !policy) {
    return <p className="text-xs text-coral">{error}</p>;
  }

  if (!policy) {
    return <p className="text-xs text-ink/45">Loading policy…</p>;
  }

  return (
    <div className="space-y-3 border-t border-ink/10 pt-3">
      <div>
        <h3 className="text-sm font-semibold text-ink">HITL policy</h3>
        <p className="text-[11px] text-ink/45">{actionType}</p>
      </div>
      <label className="block text-xs text-ink/60">
        Mode
        <select
          className="mt-1 w-full rounded-md border border-ink/15 bg-surface px-2 py-1.5 text-sm text-ink"
          value={mode}
          onChange={(e) => setMode(e.target.value as ActionPolicyMode)}
        >
          {MODES.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </label>
      {mode === "confidence_gated" && (
        <div className="space-y-2">
          <label className="block text-xs text-ink/60">
            Max amount (auto)
            <Input
              className="mt-1"
              value={maxAmount}
              onChange={(e) => setMaxAmount(e.target.value)}
              inputMode="decimal"
            />
          </label>
          <label className="block text-xs text-ink/60">
            Min confidence (auto)
            <Input
              className="mt-1"
              value={minConfidence}
              onChange={(e) => setMinConfidence(e.target.value)}
              inputMode="decimal"
            />
          </label>
        </div>
      )}
      <Button size="sm" variant="teal" disabled={saving} onClick={() => void save()}>
        {saving ? "Saving…" : "Update policy"}
      </Button>
      {savedNote && <p className="text-[11px] text-teal-deep">{savedNote}</p>}
      {error && <p className="text-[11px] text-coral">{error}</p>}
      <p className="text-[10px] text-ink/40">
        Updated {new Date(policy.updated_at).toLocaleString()}
      </p>
    </div>
  );
}
