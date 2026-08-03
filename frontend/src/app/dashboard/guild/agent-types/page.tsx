"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  CustomAgentTypeBuilder,
  draftFromCustomType,
  emptyDraft,
  type CustomTypeDraft,
} from "@/agent-types/components/CustomAgentTypeBuilder";
import type { AgentTypeSummary, CustomAgentType } from "@/agent-types/schemas";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { isLoggedIn } from "@/lib/auth";

function draftPayload(draft: CustomTypeDraft) {
  return {
    name: draft.name.trim(),
    description: draft.description.trim() || null,
    icon: draft.icon.trim() || null,
    baseTypeId: draft.baseTypeId || null,
    defaultAutonomyLevel: draft.defaultAutonomyLevel,
    defaultRiskLevel: draft.defaultRiskLevel,
    status: draft.status,
    parameterDefinitions: draft.parameterDefinitions,
    metricDefinitions: draft.metricDefinitions,
  };
}

export default function AgentTypeManagementPage() {
  const router = useRouter();
  const [builtIn, setBuiltIn] = useState<AgentTypeSummary[]>([]);
  const [customTypes, setCustomTypes] = useState<CustomAgentType[]>([]);
  const [editing, setEditing] = useState<CustomAgentType | null>(null);
  const [draft, setDraft] = useState<CustomTypeDraft | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [types, custom] = await Promise.all([
        api.listAgentTypes(true),
        api.listCustomAgentTypes(true),
      ]);
      setBuiltIn(types.filter((type) => type.builtIn));
      setCustomTypes(custom);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load agent types");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/login");
      return;
    }
    void load();
  }, [load, router]);

  async function save() {
    if (!draft) return;
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      if (editing) {
        const updated = await api.updateCustomAgentType(editing.familyId, draftPayload(draft));
        setNotice(
          updated.version > editing.version
            ? `Saved as version ${updated.version}; agents on version ${editing.version} keep their configuration.`
            : "Custom type saved."
        );
      } else {
        await api.createCustomAgentType(draftPayload(draft));
        setNotice("Custom type created.");
      }
      setDraft(null);
      setEditing(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function duplicate(type: CustomAgentType) {
    try {
      await api.duplicateCustomAgentType(type.familyId);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Duplicate failed");
    }
  }

  async function archive(type: CustomAgentType) {
    try {
      await api.archiveCustomAgentType(type.familyId);
      setNotice(
        `${type.name} archived. Deployed agents keep working; it cannot be assigned to new agents.`
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Archive failed");
    }
  }

  return (
    <main className="mx-auto max-w-6xl px-6 pb-20 pt-4">
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <Link className="text-xs text-ink/45 hover:text-ink" href="/dashboard/guild">
            ← Guild
          </Link>
          <h1 className="mt-1 font-display text-4xl tracking-tight text-ink">Agent types</h1>
          <p className="mt-2 text-sm text-ink/55">
            Built-in types are read-only system definitions. Custom types are versioned: editing a
            type that agents already use creates a new version.
          </p>
        </div>
        {!draft && (
          <Button
            variant="teal"
            onClick={() => {
              setEditing(null);
              setDraft(emptyDraft());
            }}
          >
            New custom type
          </Button>
        )}
      </div>

      {error && <p className="mb-4 text-sm text-coral">{error}</p>}
      {notice && <p className="mb-4 text-sm text-teal-deep">{notice}</p>}

      {draft ? (
        <CustomAgentTypeBuilder
          draft={draft}
          baseTypes={builtIn}
          saving={saving}
          lockedNotice={
            editing?.inUse
              ? `${editing.name} is in use by at least one agent. Schema changes are saved as a new version instead of modifying version ${editing.version}.`
              : null
          }
          onChange={setDraft}
          onSave={() => void save()}
          onCancel={() => {
            setDraft(null);
            setEditing(null);
          }}
        />
      ) : loading ? (
        <p className="text-sm text-ink/45">Loading agent types…</p>
      ) : (
        <div className="space-y-8">
          <section>
            <h2 className="mb-3 font-display text-xl text-ink">Custom types</h2>
            {customTypes.length === 0 ? (
              <p className="text-sm text-ink/45">
                No custom types yet. Create one to define your own parameter schema.
              </p>
            ) : (
              <ul className="space-y-3">
                {customTypes.map((type) => (
                  <li
                    key={type.familyId}
                    className="flex flex-wrap items-start justify-between gap-3 rounded-xl border border-ink/10 bg-surface/70 px-4 py-4"
                  >
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="font-medium text-ink">{type.name}</h3>
                        <Badge className="bg-ink/5 text-ink/50">v{type.version}</Badge>
                        <Badge
                          className={
                            type.status === "active"
                              ? "bg-teal-soft text-teal-deep"
                              : "bg-ink/10 text-ink/60"
                          }
                        >
                          {type.status}
                        </Badge>
                        {type.inUse && (
                          <Badge className="bg-coral-soft text-coral-deep">In use</Badge>
                        )}
                      </div>
                      <p className="mt-1 text-xs text-ink/45">
                        {type.parameterDefinitions.length} custom parameters ·{" "}
                        {type.metricDefinitions.length} metrics
                        {type.baseTypeId ? ` · extends ${type.baseTypeId}` : ""}
                      </p>
                      {type.description && (
                        <p className="mt-2 max-w-2xl text-sm text-ink/60">{type.description}</p>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          setEditing(type);
                          setDraft(draftFromCustomType(type));
                        }}
                      >
                        Edit
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => void duplicate(type)}>
                        Duplicate
                      </Button>
                      {type.status !== "archived" && (
                        <Button size="sm" variant="ghost" onClick={() => void archive(type)}>
                          Archive
                        </Button>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section>
            <h2 className="mb-3 font-display text-xl text-ink">Built-in types</h2>
            <ul className="grid gap-3 md:grid-cols-2">
              {builtIn.map((type) => (
                <li
                  key={type.id}
                  className="rounded-xl border border-ink/10 bg-surface/70 px-4 py-4"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-medium text-ink">{type.name}</h3>
                    <Badge className="bg-ink/5 text-ink/50">System</Badge>
                    <Badge className="bg-ink/5 text-ink/50">{type.defaultRiskLevel} risk</Badge>
                  </div>
                  <p className="mt-2 text-sm text-ink/60">{type.description}</p>
                  <p className="mt-2 text-[11px] uppercase tracking-[0.18em] text-ink/35">
                    {type.parameterCount} parameters · {type.metricCount} metrics
                  </p>
                </li>
              ))}
            </ul>
          </section>
        </div>
      )}
    </main>
  );
}
