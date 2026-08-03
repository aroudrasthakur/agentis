"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { DeploymentReadiness } from "@/agent-types/schemas";

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3 py-1.5">
      <span className="text-xs uppercase tracking-[0.14em] text-ink/35">{label}</span>
      <span className="text-right text-sm text-ink/70">{value || "—"}</span>
    </div>
  );
}

export function AgentTypeReadinessPanel({
  readiness,
  deploying,
  onDeploy,
}: {
  readiness: DeploymentReadiness;
  deploying?: boolean;
  onDeploy?: () => void;
}) {
  const percent = Math.round(readiness.configurationCompleteness * 100);

  return (
    <aside className="space-y-4 rounded-xl border border-ink/10 bg-surface/70 px-5 py-5">
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="font-display text-lg text-ink">Deployment readiness</h3>
          {readiness.canDeploy ? (
            <Badge className="bg-teal-soft text-teal-deep">Ready</Badge>
          ) : (
            <Badge className="bg-coral-soft text-coral-deep">Blocked</Badge>
          )}
        </div>
        <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-ink/10">
          <div
            className={`h-full ${readiness.canDeploy ? "bg-teal" : "bg-coral"}`}
            style={{ width: `${percent}%` }}
          />
        </div>
        <p className="mt-1 text-xs text-ink/45">
          {readiness.configuredParameterCount} of {readiness.totalParameterCount} visible
          parameters configured ({percent}%)
        </p>
      </div>

      {readiness.deploymentBlockers.length > 0 && (
        <div className="rounded-lg border border-coral/30 bg-coral-soft/40 px-3 py-3">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-coral-deep">
            Deployment blockers
          </p>
          <ul className="mt-2 space-y-1 text-xs text-coral-deep">
            {readiness.deploymentBlockers.map((blocker) => (
              <li key={blocker}>· {blocker}</li>
            ))}
          </ul>
        </div>
      )}

      {readiness.missingRequiredParameters.length > 0 && (
        <div>
          <p className="text-xs uppercase tracking-[0.14em] text-ink/35">Missing required</p>
          <p className="mt-1 text-xs text-ink/55">
            {readiness.missingRequiredParameters.join(", ")}
          </p>
        </div>
      )}

      {readiness.warnings.length > 0 && (
        <div>
          <p className="text-xs uppercase tracking-[0.14em] text-ink/35">Warnings</p>
          <ul className="mt-1 space-y-1 text-xs text-ink/45">
            {readiness.warnings.map((warning, index) => (
              <li key={index}>· {warning.message}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="divide-y divide-ink/5 border-t border-ink/5 pt-2">
        <Row
          label="Agent type"
          value={
            readiness.typeName
              ? `${readiness.typeName} (v${readiness.typeVersion ?? "?"})`
              : "Not selected"
          }
        />
        <Row label="Risk level" value={readiness.riskLevel} />
        <Row label="Autonomy" value={readiness.autonomyLevel ?? "—"} />
        <Row label="State mode" value={readiness.stateMode} />
        <Row label="Execution mode" value={readiness.executionMode} />
        <Row label="Tools" value={readiness.enabledTools.join(", ")} />
        <Row label="Actions" value={readiness.enabledActions.join(", ")} />
        <Row label="Data sources" value={readiness.allowedDataSources.join(", ")} />
        <Row label="Fallback" value={readiness.fallbackBehavior} />
        <Row
          label="Metrics"
          value={`${readiness.configuredMetrics.filter((metric) => metric.enabled).length} configured`}
        />
        <Row label="Tracing" value={readiness.tracingEnabled ? "On" : "Off"} />
        <Row label="Audit logging" value={readiness.auditLoggingEnabled ? "On" : "Off"} />
        <Row label="Evaluation" value={readiness.evaluationEnabled ? "On" : "Off"} />
        <Row
          label="Deployed"
          value={
            readiness.deployedAt
              ? `${readiness.deployedTypeId} v${readiness.deployedTypeVersion}`
              : "Never"
          }
        />
      </div>

      {onDeploy && (
        <Button
          variant="teal"
          className="w-full"
          disabled={!readiness.canDeploy || deploying}
          onClick={onDeploy}
        >
          {deploying ? "Deploying…" : readiness.deployedAt ? "Redeploy agent" : "Deploy agent"}
        </Button>
      )}
    </aside>
  );
}
