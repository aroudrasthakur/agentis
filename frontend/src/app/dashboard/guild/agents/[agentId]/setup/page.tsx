"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { AgentDescriptionEditor } from "@/components/agents/AgentDescriptionEditor";
import { AgentTypeConfigForm } from "@/agent-types/components/AgentTypeConfigForm";
import { AgentTypeMetricsForm } from "@/agent-types/components/AgentTypeMetricsForm";
import { AgentTypeOverview } from "@/agent-types/components/AgentTypeOverview";
import { AgentTypeReadinessPanel } from "@/agent-types/components/AgentTypeReadinessPanel";
import { AgentTypeSelector } from "@/agent-types/components/AgentTypeSelector";
import { AgentTypeVersionMigration } from "@/agent-types/components/AgentTypeVersionMigration";
import type {
  AgentMetricConfiguration,
  AgentTypeConfiguration,
  AgentTypeDefinition,
  AgentTypeSummary,
  DeploymentReadiness,
  MetricConfigurationEntry,
  SelectorCatalogs,
  TypeMigrationPreview,
  ValidationIssue,
} from "@/agent-types/schemas";
import { incompatibleKeys } from "@/agent-types/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { Agent } from "@/lib/api";
import { api } from "@/lib/api";
import { isLoggedIn } from "@/lib/auth";

type Step = "about" | "type" | "configure" | "metrics";

const STEPS: { id: Step; label: string }[] = [
  { id: "about", label: "1. About" },
  { id: "type", label: "2. Agent type" },
  { id: "configure", label: "3. Configuration" },
  { id: "metrics", label: "4. Metrics" },
];

export default function AgentTypeSetupPage() {
  const params = useParams<{ agentId: string }>();
  const router = useRouter();
  const agentId = params.agentId;

  const [agent, setAgent] = useState<Agent | null>(null);
  const [types, setTypes] = useState<AgentTypeSummary[]>([]);
  const [definition, setDefinition] = useState<AgentTypeDefinition | null>(null);
  const [catalogs, setCatalogs] = useState<SelectorCatalogs | null>(null);
  const [readiness, setReadiness] = useState<DeploymentReadiness | null>(null);
  const [migration, setMigration] = useState<TypeMigrationPreview | null>(null);

  const [configuration, setConfiguration] = useState<AgentTypeConfiguration>({});
  const [metricConfiguration, setMetricConfiguration] = useState<AgentMetricConfiguration>({});
  const [issues, setIssues] = useState<ValidationIssue[]>([]);

  const [step, setStep] = useState<Step>("type");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savingDescription, setSavingDescription] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [migrating, setMigrating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [pendingType, setPendingType] = useState<AgentTypeSummary | null>(null);

  const applyAgent = useCallback((next: Agent) => {
    setAgent(next);
    setConfiguration({ ...(next.agent_type_configuration ?? {}) });
    setMetricConfiguration({ ...(next.agent_metric_configuration ?? {}) });
  }, []);

  const loadDefinition = useCallback(async (typeId: string, version?: number | null) => {
    const loaded = await api.getAgentType(typeId, version ?? undefined);
    setDefinition(loaded);
    return loaded;
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [loadedAgent, typeList, catalogList] = await Promise.all([
        api.getGuildAgent(agentId),
        api.listAgentTypes(),
        api.getSelectorCatalogs(),
      ]);
      applyAgent(loadedAgent);
      setTypes(typeList);
      setCatalogs(catalogList);

      if (!loadedAgent.description?.trim()) {
        setStep("about");
      } else if (loadedAgent.agent_type_id) {
        await loadDefinition(loadedAgent.agent_type_id, loadedAgent.agent_type_version);
        setStep("configure");
        const [readinessResult, migrationResult] = await Promise.all([
          api.getDeploymentReadiness(agentId),
          api.previewAgentTypeMigration(agentId).catch(() => null),
        ]);
        setReadiness(readinessResult);
        setIssues(readinessResult.validation.errors);
        setMigration(migrationResult);
      } else {
        setStep("type");
        setReadiness(await api.getDeploymentReadiness(agentId));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load agent setup");
    } finally {
      setLoading(false);
    }
  }, [agentId, applyAgent, loadDefinition]);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/login");
      return;
    }
    void load();
  }, [load, router]);

  async function saveDescription(description: string, descriptionFormat: "plain" | "markdown") {
    setSavingDescription(true);
    setError(null);
    setNotice(null);
    try {
      await api.updateAgentDescription(agentId, {
        description,
        description_format: descriptionFormat,
      });
      const refreshed = await api.getGuildAgent(agentId);
      applyAgent(refreshed);
      setNotice("Description saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save description");
    } finally {
      setSavingDescription(false);
    }
  }

  async function selectType(summary: AgentTypeSummary, discardIncompatible = true) {
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const response = await api.assignAgentType(agentId, {
        typeId: summary.id,
        typeVersion: summary.version,
        discardIncompatible,
      });
      applyAgent(response.agent);
      setDefinition(response.definition);
      setReadiness(response.readiness);
      setIssues(response.validation.errors);
      setMigration(await api.previewAgentTypeMigration(agentId).catch(() => null));
      setStep("configure");
      if (response.compatibility.incompatibleKeys.length) {
        setNotice(
          `Removed values that this type cannot use: ${response.compatibility.incompatibleKeys.join(", ")}.`
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to assign agent type");
    } finally {
      setSaving(false);
      setPendingType(null);
    }
  }

  function requestTypeChange(summary: AgentTypeSummary) {
    if (!definition || summary.id === definition.id) {
      void selectType(summary);
      return;
    }
    setPendingType(summary);
  }

  // Preview which values the target type cannot keep; the server decides authoritatively.
  const [droppedByPendingType, setDroppedByPendingType] = useState<string[]>([]);

  useEffect(() => {
    if (!pendingType) {
      setDroppedByPendingType([]);
      return;
    }
    let cancelled = false;
    void api
      .getAgentType(pendingType.id, pendingType.version)
      .then((target) => {
        if (!cancelled) setDroppedByPendingType(incompatibleKeys(target, configuration));
      })
      .catch(() => {
        if (!cancelled) setDroppedByPendingType([]);
      });
    return () => {
      cancelled = true;
    };
  }, [pendingType, configuration]);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const response = await api.saveAgentTypeConfiguration(agentId, {
        configuration,
        metricConfiguration,
      });
      applyAgent(response.agent);
      setReadiness(response.readiness);
      setIssues(response.validation.errors);
      setNotice("Configuration saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save configuration");
    } finally {
      setSaving(false);
    }
  }

  async function deploy() {
    setDeploying(true);
    setError(null);
    try {
      await api.saveAgentTypeConfiguration(agentId, { configuration, metricConfiguration });
      const response = await api.deployAgent(agentId);
      applyAgent(response.agent);
      setReadiness(response.readiness);
      setIssues(response.readiness.validation.errors);
      setNotice("Agent deployed. It can now be activated and attached to sessions.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Deployment failed");
      setReadiness(await api.getDeploymentReadiness(agentId).catch(() => readiness));
    } finally {
      setDeploying(false);
    }
  }

  async function migrate() {
    if (!migration) return;
    setMigrating(true);
    setError(null);
    try {
      const response = await api.migrateAgentType(agentId, {
        targetVersion: migration.toVersion,
      });
      applyAgent(response.agent);
      setReadiness(response.readiness);
      setIssues(response.validation.errors);
      if (response.agent.agent_type_id) {
        await loadDefinition(response.agent.agent_type_id, response.agent.agent_type_version);
      }
      setMigration(await api.previewAgentTypeMigration(agentId).catch(() => null));
      setNotice(`Migrated to version ${response.preview.toVersion}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Migration failed");
    } finally {
      setMigrating(false);
    }
  }

  function updateParameter(key: string, value: unknown) {
    setConfiguration((previous) => ({ ...previous, [key]: value }));
  }

  function updateMetric(key: string, entry: MetricConfigurationEntry) {
    setMetricConfiguration((previous) => ({ ...previous, [key]: entry }));
  }

  if (loading) {
    return (
      <main className="mx-auto max-w-6xl px-6 pb-20 pt-6">
        <p className="text-sm text-ink/45">Loading agent setup…</p>
      </main>
    );
  }

  if (!agent) {
    return (
      <main className="mx-auto max-w-6xl px-6 pb-20 pt-6">
        <p className="text-sm text-coral">{error ?? "Agent not found."}</p>
        <Link className="mt-4 inline-block text-sm text-teal" href="/dashboard/guild">
          Back to Guild
        </Link>
      </main>
    );
  }

  const metricsSource =
    definition?.metricDefinitions ?? [];

  return (
    <main className="mx-auto max-w-6xl px-6 pb-20 pt-4">
      <div className="mb-6">
        <Link className="text-xs text-ink/45 hover:text-ink" href={`/dashboard/guild/agents/${agentId}/description`}>
          View full description & configuration
        </Link>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <Link className="text-xs text-ink/45 hover:text-ink" href="/dashboard/guild">
            ← Guild
          </Link>
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <h1 className="font-display text-3xl tracking-tight text-ink">{agent.name}</h1>
          <Badge className="bg-ink/5 text-ink/50">{agent.agent_key}</Badge>
          {agent.requires_type_setup ? (
            <Badge className="bg-coral-soft text-coral-deep">Type required</Badge>
          ) : agent.deployed_type_id ? (
            <Badge className="bg-teal-soft text-teal-deep">Deployed</Badge>
          ) : (
            <Badge className="bg-ink/10 text-ink/60">Not deployed</Badge>
          )}
        </div>
        <p className="mt-2 text-sm text-ink/55">
          Describe your agent, choose its type, then configure parameters and metrics.
        </p>
      </div>

      {error && <p className="mb-4 text-sm text-coral">{error}</p>}
      {notice && <p className="mb-4 text-sm text-teal-deep">{notice}</p>}

      <div className="mb-6 flex flex-wrap gap-2 border-b border-ink/10 pb-4">
        {STEPS.map((item) => (
          <button
            key={item.id}
            type="button"
            disabled={(item.id === "configure" || item.id === "metrics") && !definition}
            onClick={() => setStep(item.id)}
            className={`rounded-md px-3 py-1.5 text-sm transition disabled:opacity-40 ${
              step === item.id
                ? "bg-ink text-sand"
                : "text-ink/55 hover:bg-ink/5 hover:text-ink"
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="space-y-6">
          {step === "about" && (
            <>
              <AgentDescriptionEditor
                key={`${agent.id}-${agent.description ?? ""}-${agent.description_format ?? "plain"}`}
                description={agent.description ?? ""}
                descriptionFormat={agent.description_format ?? "plain"}
                saving={savingDescription}
                onSave={(desc, fmt) => void saveDescription(desc, fmt)}
              />
              <Button type="button" variant="outline" onClick={() => setStep("type")}>
                Continue to agent type
              </Button>
            </>
          )}

          {step === "type" && (
            <>
              <p className="text-sm text-ink/55">
                Every agent needs a type. The type decides which parameters are required, which
                controls are available, and which metrics are tracked.
              </p>
              <AgentTypeSelector
                types={types}
                selectedTypeId={agent.agent_type_id}
                onSelect={requestTypeChange}
              />
            </>
          )}

          {step === "configure" && definition && (
            <>
              <AgentTypeOverview definition={definition} onChangeType={() => setStep("type")} />
              {migration && migration.fromVersion !== migration.toVersion && (
                <AgentTypeVersionMigration
                  preview={migration}
                  busy={migrating}
                  onMigrate={() => void migrate()}
                />
              )}
              <AgentTypeConfigForm
                definition={definition}
                configuration={configuration}
                issues={issues}
                catalogs={catalogs}
                onChange={updateParameter}
              />
            </>
          )}

          {step === "metrics" && definition && (
            <section className="space-y-4">
              <div>
                <h2 className="font-display text-xl text-ink">Metrics</h2>
                <p className="mt-1 text-sm text-ink/55">
                  Required metrics are always tracked. Enable optional metrics and set targets or
                  thresholds.
                </p>
              </div>
              <AgentTypeMetricsForm
                metrics={metricsSource}
                configuration={metricConfiguration}
                onChange={updateMetric}
              />
            </section>
          )}

          {definition && (
            <div className="flex flex-wrap gap-3">
              <Button variant="outline" disabled={saving} onClick={() => void save()}>
                {saving ? "Saving…" : "Save configuration"}
              </Button>
              {step === "configure" && (
                <Button variant="ghost" onClick={() => setStep("metrics")}>
                  Continue to metrics
                </Button>
              )}
            </div>
          )}
        </div>

        {readiness && (
          <AgentTypeReadinessPanel
            readiness={readiness}
            deploying={deploying}
            onDeploy={definition ? () => void deploy() : undefined}
          />
        )}
      </div>

      <Dialog open={Boolean(pendingType)} onOpenChange={(open) => !open && setPendingType(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Change agent type?</DialogTitle>
          </DialogHeader>
          <div className="mt-3 space-y-3 text-sm text-ink/65">
            <p>
              Switching to <strong>{pendingType?.name}</strong> keeps every value the new type can
              still use and revalidates the whole configuration.
            </p>
            {droppedByPendingType.length > 0 && (
              <p className="text-coral">
                These values will be removed: {droppedByPendingType.join(", ")}.
              </p>
            )}
            <div className="flex gap-2">
              <Button
                variant="teal"
                disabled={saving}
                onClick={() => pendingType && void selectType(pendingType)}
              >
                {saving ? "Applying…" : "Change type"}
              </Button>
              <Button variant="ghost" onClick={() => setPendingType(null)}>
                Cancel
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </main>
  );
}
