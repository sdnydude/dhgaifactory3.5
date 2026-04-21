"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { ShieldCheck, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type {
  IncidentDetail,
  Severity,
  IncidentStatus,
} from "@/lib/incidentsApi";
import { SEVERITY_COLORS, STATUS_COLORS } from "@/lib/incidentsApi";
import { useIncidentsStore } from "@/stores/incidents-store";
import { PostmortemForm } from "./postmortem-form";
import { SnapshotDashboard } from "./snapshot-dashboard";

interface IncidentDetailPanelProps {
  incident: IncidentDetail | null;
  loading: boolean;
}

function formatTimestamp(ts: string | null): string {
  if (!ts) return "--";
  return new Date(ts).toLocaleString();
}

function SlaRow({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-border/50 last:border-0">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="text-sm font-medium tabular-nums">{value ?? "--"}</span>
    </div>
  );
}

export function IncidentDetailPanel({
  incident,
  loading,
}: IncidentDetailPanelProps) {
  const actionLoading = useIncidentsStore((s) => s.actionLoading);
  const mitigateIncident = useIncidentsStore((s) => s.mitigateIncident);
  const resolveIncident = useIncidentsStore((s) => s.resolveIncident);

  if (loading) {
    return (
      <div className="flex flex-col gap-4 p-6">
        <Skeleton className="h-8 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (!incident) {
    return (
      <div className="flex flex-col items-center justify-center h-full py-20">
        <p className="text-sm text-muted-foreground">
          Select an incident to view details
        </p>
      </div>
    );
  }

  const events = incident.events ?? [];
  const actions = incident.actions ?? [];
  const pm = incident.postmortem;
  const children = incident.children ?? [];
  const canMitigate = incident.status === "active";
  const canResolve = incident.status === "active" || incident.status === "mitigated";

  return (
    <ScrollArea className="h-full">
      <div className="p-5">
        {/* Header */}
        <div className="mb-4">
          <div className="flex items-start justify-between gap-3">
            <h2 className="text-lg font-semibold leading-snug">
              {incident.title}
            </h2>
            <div className="flex items-center gap-2 shrink-0">
              <Badge
                className={cn(
                  "text-[10px] font-bold uppercase",
                  SEVERITY_COLORS[incident.severity as Severity],
                )}
              >
                {incident.severity}
              </Badge>
              <Badge
                variant="outline"
                className={cn(
                  "text-[10px] font-medium",
                  STATUS_COLORS[incident.status as IncidentStatus],
                )}
              >
                {incident.status}
              </Badge>
            </div>
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
            <span>Category: {incident.category}</span>
            {incident.trigger_rule && (
              <span>Trigger: {incident.trigger_rule}</span>
            )}
            <span>Detected: {formatTimestamp(incident.detected_at)}</span>
          </div>
          {incident.affected_services.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {incident.affected_services.map((svc) => (
                <span
                  key={svc}
                  className="rounded bg-muted px-2 py-0.5 text-[11px] font-mono text-muted-foreground"
                >
                  {svc}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Action Bar */}
        {(canMitigate || canResolve) && (
          <div className="flex items-center gap-2 mb-4 pb-3 border-b border-border">
            {canMitigate && (
              <Button
                size="sm"
                variant="outline"
                disabled={actionLoading}
                onClick={() => mitigateIncident(incident.id)}
                className="text-xs"
              >
                <ShieldCheck className="h-3.5 w-3.5 mr-1.5" />
                {actionLoading ? "Updating..." : "Mitigate"}
              </Button>
            )}
            {canResolve && (
              <Button
                size="sm"
                disabled={actionLoading}
                onClick={() => resolveIncident(incident.id)}
                className="text-xs"
              >
                <CheckCircle2 className="h-3.5 w-3.5 mr-1.5" />
                {actionLoading ? "Updating..." : "Resolve"}
              </Button>
            )}
          </div>
        )}

        {/* Tabs */}
        <Tabs defaultValue="overview" className="mt-2">
          <TabsList className="w-fit">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="timeline">
              Timeline
              {events.length > 0 && (
                <span className="ml-1 text-[10px] text-muted-foreground">
                  ({events.length})
                </span>
              )}
            </TabsTrigger>
            <TabsTrigger value="actions">
              Actions
              {actions.length > 0 && (
                <span className="ml-1 text-[10px] text-muted-foreground">
                  ({actions.length})
                </span>
              )}
            </TabsTrigger>
            {pm && <TabsTrigger value="postmortem">Post-Mortem</TabsTrigger>}
            {incident.system_snapshot && (
              <TabsTrigger value="snapshot">Snapshot</TabsTrigger>
            )}
          </TabsList>

          {/* Overview tab */}
          <TabsContent value="overview" className="mt-4 space-y-4">
            {/* SLA Timestamps */}
            <div className="rounded-lg border bg-card p-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                SLA Timestamps
              </h3>
              <SlaRow label="Started" value={formatTimestamp(incident.started_at)} />
              <SlaRow label="Detected" value={formatTimestamp(incident.detected_at)} />
              <SlaRow label="Mitigated" value={formatTimestamp(incident.mitigated_at)} />
              <SlaRow label="Resolved" value={formatTimestamp(incident.resolved_at)} />
            </div>

            {/* Root Cause */}
            {incident.root_cause && (
              <div className="rounded-lg border bg-card p-4">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                  Root Cause
                </h3>
                {incident.root_cause_category && (
                  <Badge variant="outline" className="mb-2 text-[10px]">
                    {incident.root_cause_category}
                  </Badge>
                )}
                <p className="text-sm text-foreground/90">{incident.root_cause}</p>
              </div>
            )}

            {/* Impact */}
            {incident.impact_summary && (
              <div className="rounded-lg border bg-card p-4">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                  Impact
                </h3>
                <p className="text-sm text-foreground/90">
                  {incident.impact_summary}
                </p>
              </div>
            )}

            {/* Prevention */}
            {incident.prevention && (
              <div className="rounded-lg border bg-card p-4">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                  Prevention
                </h3>
                <p className="text-sm text-foreground/90">
                  {incident.prevention}
                </p>
              </div>
            )}

            {/* Children */}
            {children.length > 0 && (
              <div className="rounded-lg border bg-card p-4">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                  Related Incidents ({children.length})
                </h3>
                <div className="space-y-2">
                  {children.map((child) => (
                    <div
                      key={child.id}
                      className="flex items-center justify-between rounded border px-3 py-2"
                    >
                      <span className="text-sm">{child.title}</span>
                      <Badge
                        className={cn(
                          "text-[10px]",
                          SEVERITY_COLORS[child.severity as Severity],
                        )}
                      >
                        {child.severity}
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Tags */}
            {incident.tags.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {incident.tags.map((tag) => (
                  <Badge key={tag} variant="secondary" className="text-[11px]">
                    {tag}
                  </Badge>
                ))}
              </div>
            )}

            {/* Postmortem Form — show on resolved incidents without a postmortem */}
            {incident.status === "resolved" && !pm && (
              <PostmortemForm incident={incident} />
            )}
          </TabsContent>

          {/* Timeline tab */}
          <TabsContent value="timeline" className="mt-4">
            {events.length === 0 ? (
              <p className="text-sm text-muted-foreground py-6 text-center">
                No events recorded
              </p>
            ) : (
              <div className="relative pl-4 border-l-2 border-border space-y-4">
                {events.map((evt) => (
                  <div key={evt.id} className="relative">
                    <div className="absolute -left-[21px] top-1.5 h-2.5 w-2.5 rounded-full bg-primary border-2 border-background" />
                    <div className="ml-2">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="text-[10px]">
                          {evt.event_type}
                        </Badge>
                        {evt.source && (
                          <span className="text-[10px] text-muted-foreground font-mono">
                            {evt.source}
                          </span>
                        )}
                        <span className="ml-auto text-[10px] text-muted-foreground tabular-nums">
                          {formatTimestamp(evt.timestamp)}
                        </span>
                      </div>
                      <p className="mt-1 text-sm text-foreground/90">
                        {evt.description}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </TabsContent>

          {/* Actions tab */}
          <TabsContent value="actions" className="mt-4">
            {actions.length === 0 ? (
              <p className="text-sm text-muted-foreground py-6 text-center">
                No actions recorded
              </p>
            ) : (
              <div className="space-y-3">
                {actions.map((act) => (
                  <div key={act.id} className="rounded-lg border bg-card p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Badge variant="outline" className="text-[10px]">
                        {act.action_type}
                      </Badge>
                      {act.performed_by && (
                        <span className="text-[11px] text-muted-foreground">
                          by {act.performed_by}
                        </span>
                      )}
                      <span className="ml-auto text-[10px] text-muted-foreground tabular-nums">
                        {formatTimestamp(act.performed_at)}
                      </span>
                    </div>
                    <p className="text-sm">{act.description}</p>
                    {act.command && (
                      <pre className="mt-2 rounded bg-muted p-2 text-[11px] font-mono overflow-x-auto">
                        {act.command}
                      </pre>
                    )}
                    {act.result && (
                      <p className="mt-2 text-[12px] text-muted-foreground">
                        Result: {act.result}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </TabsContent>

          {/* Post-Mortem tab */}
          {pm && (
            <TabsContent value="postmortem" className="mt-4 space-y-4">
              {pm.summary && (
                <div className="rounded-lg border bg-card p-4">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                    Summary
                  </h3>
                  <p className="text-sm">{pm.summary}</p>
                </div>
              )}
              {pm.root_cause_analysis && (
                <div className="rounded-lg border bg-card p-4">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                    Root Cause Analysis
                  </h3>
                  <p className="text-sm whitespace-pre-wrap">
                    {pm.root_cause_analysis}
                  </p>
                </div>
              )}
              {pm.impact_analysis && (
                <div className="rounded-lg border bg-card p-4">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                    Impact Analysis
                  </h3>
                  <p className="text-sm whitespace-pre-wrap">
                    {pm.impact_analysis}
                  </p>
                </div>
              )}
              {pm.resolution_details && (
                <div className="rounded-lg border bg-card p-4">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                    Resolution
                  </h3>
                  <p className="text-sm whitespace-pre-wrap">
                    {pm.resolution_details}
                  </p>
                </div>
              )}
              {pm.prevention_measures && (
                <div className="rounded-lg border bg-card p-4">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                    Prevention Measures
                  </h3>
                  <p className="text-sm whitespace-pre-wrap">
                    {pm.prevention_measures}
                  </p>
                </div>
              )}
              {pm.lessons_learned && (
                <div className="rounded-lg border bg-card p-4">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                    Lessons Learned
                  </h3>
                  <p className="text-sm whitespace-pre-wrap">
                    {pm.lessons_learned}
                  </p>
                </div>
              )}
            </TabsContent>
          )}

          {/* Snapshot tab */}
          {incident.system_snapshot && (
            <TabsContent value="snapshot" className="mt-4">
              <SnapshotDashboard
                snapshot={incident.system_snapshot as Record<string, unknown>}
              />
            </TabsContent>
          )}
        </Tabs>
      </div>
    </ScrollArea>
  );
}
